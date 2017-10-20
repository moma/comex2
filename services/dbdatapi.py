"""
DB data querying:
  - aggregations on almost any DB fields via FIELDS_FRONTEND_TO_SQL
  - BipartiteExtractor subset selections originally made by Samuel
  - multimatch subset selections
"""
__author__    = "CNRS"
__copyright__ = "Copyright 2016 ISCPIF-CNRS"
__email__     = "romain.loth@iscpif.fr"

from MySQLdb          import connect, cursors
from MySQLdb.cursors  import DictCursor

from networkx  import Graph, DiGraph
from random    import randint
from math      import floor, log, log1p, sqrt
from cgi       import escape
from re        import sub, match
from traceback import format_tb
from json      import loads

if __package__ == 'services':
    from services.tools import mlog, REALCONFIG
    from services.dbcrud  import connect_db, FULL_SCHOLAR_SQL
    from services.dbentities import DBScholars, DBLabs, DBInsts, DBKeywords, \
                                    DBHashtags, DBCountries, DBScholarsAndJobs, Org
else:
    from tools          import mlog, REALCONFIG
    from dbcrud         import connect_db, FULL_SCHOLAR_SQL
    from dbentities     import DBScholars, DBLabs, DBInsts, DBKeywords, \
                               DBHashtags, DBCountries, DBScholarsAndJobs, Org


# options work for both matching algorithms (BipartiteExtractor and multimatch)
MATCH_OPTIONS = {
    # same-side (00 and 11 edges)
    # ----------------------------
    # NB: here dist metric is always jaccard

    # merge edges X->Y with Y->X if X and Y are nodes of the same type
    "avg_bidirectional_links":    True,

    # cross-relations (XR edges)
    # --------------------------
    # constant factor to increase weight of cross-relations (bipartite edges)
    # because they play an important role in the structure of the graph
    "XR_weight_constant": 10,

    # weight of sch-kw XR edges divided by log(1+scholar["total_keywords_nb"])
    "normalize_schkw_by_sch_totkw" : True,

    # weight of sch-kw XR edges divided by log(1+keyword["total_occs"])
    "normalize_schkw_by_kw_totoccs": True
}

# for multi-matching
TYPE_MAP = {
    # entities that support *scholar* pivot
    "lab" :  DBLabs,
    "inst" : DBInsts,
    "ht" :   DBHashtags,
    "country" :   DBCountries,

    # entities that support *keyword* pivot
    "jobs_and_candidates" : DBScholarsAndJobs,

    # entities that support both pivots
    "sch" :  DBScholars,
    "kw" :   DBKeywords
}


# col are for str stats api
# grouped is for full_scholar filters
FIELDS_FRONTEND_TO_SQL = {
    "keywords":      {'col':"keywords.kwstr",
                      'type': "LIKE_relation",
                      'grouped': "keywords_list"},
    "tags":          {'col':"hashtags.htstr",
                      'type': "LIKE_relation",
                      'grouped': "hashtags_list"},
    "hashtags":      {'col':"hashtags.htstr",
                      'type': "LIKE_relation",
                      'grouped': "hashtags_list"},

    "countries":     {'col':"scholars.country",
                      'type': "EQ_relation",
                      'grouped': "country"},
    "gender":        {'col':"scholars.gender",
                      'type': "EQ_relation",
                      'grouped': "gender"},

    "organizations": {'col':"orgs.label",
                      'class': "*",                 # all organizations
                      'type': "LIKE_relation",
                      'grouped': "orgs_list"},
    "institutions": {'col':"orgs.label",
                      'class': "inst",              #  <= local where clause
                      'type': "LIKE_relation",
                      'grouped': "orgs_list"},
    "laboratories":  {'col':"orgs.label",
                      'class': "lab",               #  <= idem
                      'type': "LIKE_relation",
                      'grouped': "orgs_list"},

    # (POSS: locs.locname to factorize orgs.locname, jobs.locname at write time)
    "cities":       {'col':"orgs.locname",
                      'type': "LIKE_relation",
                      'grouped': "locnames_list",
                      'class': "*"},

    "jobcities":    {'col':"jobs.locname",
                      'type': "LIKE_relation",
                      'grouped': "locnames_list"},

    "linked":          {'col':"linked_ids.ext_id_type", 'type': "EQ_relation"}
}


# explorer REST "filters" syntax => sql "WHERE" constraints on scholars
# =====================================================================

def rest_filters_to_sql(filter_dict):
    """
    Returns WHERE clauses from dict representing an input URL query like:

      filter_dict = tools.restparse(
        "?type0=ht&type1=inst&keywords[]=love&keywords[]=natural hazards&countries[]=France&countries[]=Italy".decode()
        )

    exemple input: dict = {
           'type0': 'ht'
           'type1': 'inst',
            'keywords': [
                 'natural hazards',
                 'love'
             ],
            'countries': [
                 'Italy',
                 'France'
             ],
            'qtype': 'filters'
         }

    exemple output: array of SQL constraints = [
            "(country IN ('France', 'Italy'))",
            "(keywords_list LIKE '%%natural hazards%%' OR keywords_list LIKE '%%love%%')"
        ]

    """
    sql_constraints = []

    for key in filter_dict:
        known_filter = None
        sql_column = None

        if key not in FIELDS_FRONTEND_TO_SQL:
            continue
        else:
            known_filter = key
            sql_field = FIELDS_FRONTEND_TO_SQL[key]['grouped']

            # "LIKE_relation" or "EQ_relation"
            rel_type = FIELDS_FRONTEND_TO_SQL[key]['type']

        # now create the constraints
        val = filter_dict[known_filter]

        if len(val):
            # clause exemples
            # "col IN (val1, val2)"
            # "col = val"
            # "col LIKE '%escapedval%'"

            if (not isinstance(val, list)
              and not isinstance(val, tuple)):
                mlog("WARNING", "direct graph api query without tina")
                clause = sql_field + type_to_sql_filter(val)

            # normal case
            # tina sends an array of str filters
            else:
                tested_array = [x for x in val if x]
                # mlog("DEBUG", "[filters to sql]: tested_array", tested_array)
                if len(tested_array):
                    if rel_type == "EQ_relation":
                        qwliststr = repr(tested_array)
                        qwliststr = sub(r'^\[', '(', qwliststr)
                        qwliststr = sub(r'\]$', ')', qwliststr)
                        clause = sql_field + ' IN '+qwliststr
                        # ex: country IN ('France', 'USA')

                    elif rel_type == "LIKE_relation":
                        like_clauses = []
                        for singleval in tested_array:
                            if type(singleval) == str and len(singleval):
                                like_clauses.append(
                                   sql_field+" LIKE '%"+quotestr(singleval)+"%'"
                                )
                        clause = " OR ".join(like_clauses)

            if len(clause):
                sql_constraints.append("(%s)" % clause)

    return sql_constraints


def kw_neighbors(uid, db_cursor = None):
    """
    list of neighbors of a scholar by common keyword

    exemple return value:
        ({'cooc': 12, 'uid': 4206},
         {'cooc': 3, 'uid': 3794},
         {'cooc': 2, 'uid': 3234},
         {'cooc': 2, 'uid': 2730},
         {'cooc': 1, 'uid': 3873},
         {'cooc': 1, 'uid': 2732},
         {'cooc': 1, 'uid': 3942})
    """

    if (not db_cursor):
        db = connect_db()
        cursor = db.cursor(DictCursor)
    else:
        cursor = db_cursor

    # we use the sch_kw table (scholars <=> kw map)
    sql_query="""
    SELECT
        scholars.luid,
        scholars.initials,
        neighbors_by_kw.uid,
        COUNT(matching.kwid) AS cooc

    FROM scholars

    -- step 1
    JOIN sch_kw AS matching
                ON matching.uid = scholars.luid
    -- step 2
    JOIN sch_kw AS neighbors_by_kw
                ON neighbors_by_kw.kwid = matching.kwid

    WHERE luid = "%s"

    AND (
        record_status = 'active'
        OR
        (record_status = 'legacy' AND valid_date >= NOW())
    )
    GROUP BY neighbors_by_kw.uid
    ORDER BY cooc DESC
    """ % str(uid)

    cursor.execute(sql_query)
    results=cursor.fetchall()

    if (not db_cursor):
        db.close()

    return results




# multimatch(nodetype_1, nodetype_2)
# ==================================
def multimatch(source_type, target_type, pivot_filters = [], pivot_type = 'scholars'):
    """
    @args:
      - source_type ∈ {'kw', 'ht'}
      - target_type ∈ {'sch', 'lab', 'inst', 'country', 'jobs_and_candidates'}

      + optional pivot_filters on scholars table as strings of the form:
            'WHERE colA IN ("valA1", "valA2") AND colB LIKE "%%valB1%%"'

    NB: An alternate pivot_type 'keywords' can be specified for some DBEntities.

        For instance for "job matching" the source and pivot is keywords and
        target is jobs_and_candidates (union of jobs and job-looking scholars).

        It is supported because scholars and jobs both have their own related
        keywords (via sch_kw and job_kw). The keyword pivots allow constructing
        the similarity between the job description and the job candidates.

    ----------------------------------------------------------------------------
    Returns a bipartite graph with:

    - a list of nodes (objects of source_type U related objects of target_type)

    - a list of edges between the objects of type 1 and those of type 2,
      via their matching scholars (used as pivot and for filtering)
      (weights of cross-relations edges use the normalizations of MATCH_OPTIONS)

    - 2 lists of internal edges (between type 1 nodes and type 2 nodes resp.)

    - weights of internal edges use jaccard weights using:
      => marginal sums of M1[type1 to pivot] and M2[pivot to type2]
      => coefs of the dotproduct of M1 o M1⁻¹
                              or of (M1 o M2)⁻¹ o (M1 o M2)
    """

    # unsupported entities
    if ( source_type not in TYPE_MAP
      or target_type not in TYPE_MAP ):
        return []

    # instanciating appropriate DBEntity class
    o1 = TYPE_MAP[source_type]()
    o2 = TYPE_MAP[target_type]()

    db = connect_db()
    db_c = db.cursor(DictCursor)

    # idea: we can always (SELECT subq1)
    #       and JOIN with (SELECT subq2)
    #       because they both expose pivotID
    subq1 = o1.toPivot(pivotType = pivot_type)
    subq2 = o2.toPivot(pivotType = pivot_type)

    # additional filter step: the middle pivot step allows filtering pivots
    #                         by any information that can be related to it
    subqmidfilters = ''
    if (len(pivot_filters)):
        subqmidfilters = "WHERE " + " AND ".join(pivot_filters)

    if pivot_type == 'scholars':
        # make some columns available for filtering
        # luid
        # country
        # job_looking
        # job_looking_date
        # orgs_list
        # hashtags_list
        # keywords_list
        subqmid =  """
                    SELECT * FROM (
                        %s
                    ) AS full_scholar
                    -- our filtering constraints fit here
                    %s
        """ % (FULL_SCHOLAR_SQL, subqmidfilters)
    elif pivot_type == 'keywords':
        # for keywords (used in job matching) we have only 3 fields for filter: label (LIKE), n_occs, nb_jobs
        subqmid =  """
                    SELECT * FROM keywords
                    -- our filtering constraints fit here
                    %s
        """ % subqmidfilters

    # ------------------------------------------------------------  Explanations
    #
    # At this point in matrix representation:
    #  - subq1 is M1 [source_type x filtered_pivots]
    #  - subq2 is M2 [filtered_pivots x target_type]
    #
    #
    # The SQL match_table built below will correspond to the cross-relations XR:
    #
    #   M1 o M2 = XR [source_type x target_type]      aka "opposite neighbors"
    #                                                      in ProjectExplorer
    #
    # Finally we will have two possibilities to build the "sameside neighbors"
    # (let Neighs_11 represent them within type 1, Neighs_22 within type 2)
    #
    # (i) using all transitions (ie via pivot edges and via opposite type edges)
    #  Neighs_11 = XR o XR⁻¹   = (M1 o M2)   o (M1 o M2)⁻¹
    #  Neighs_22 = XR⁻¹ o XR   = (M1 o M2)⁻¹ o (M1 o M2)
    #
    # (ii) or via pivot edges only
    #  Neighs_11 = M1 o M1⁻¹
    #  Neighs_22 = M2⁻¹ o M2
    #
    # +results with (ii) are filtered by sources that matched a target (for 11)
    #                                 or targets that matched a source (for 22)
    #
    # In practice, we will use formula (ii) for Neighs_11,
    #                      and formula (i)  for Neighs_22,
    #   because:
    #     - type_1 ∈ {kw, ht}
    #       The app's allowed source_types (keywords, community tags) tend to
    #       have a ???-to-many relationship with pivot (following only pivot
    #       edges already yields meaningful connections for Neighs_11)
    #
    #     - type_2 ∈ {sch, lab, inst, country}
    #       Allowed target_types (scholars, labs, orgs, countries) tend to have
    #       a ???-to-1 relation with pivot (a scholar has usually one country,
    #       one lab..) (using pivot edges only wouldn't create much links)
    #
    # Finally count(pivotID) is our weight
    #   for instance: if we match keywords <=> laboratories
    #                 the weight of the  kw1 -- lab2 edge is
    #                 the number of scholars from lab2 with kw1
    #
    # ------------------------------------------------------------ /Explanations


    # threshold = 1 if target_type != 'sch' else 0
    threshold = 0

    matchq = """
    -- filtered pivot
    CREATE TEMPORARY TABLE IF NOT EXISTS pivot_filtered_ids AS (
        SELECT %(pivotIDField)s AS pivotID FROM ( %(pfiltersq)s ) AS filtered_on_infos
    );
    CREATE INDEX filteridx ON pivot_filtered_ids(pivotID);

    -- eg: kw to sch pivot
    -- eg: kw as source to itself as pivot (step is a useless then, but kept to remain in the general scenario)
    CREATE TEMPORARY TABLE IF NOT EXISTS sources AS (
        SELECT sem_matrix.* FROM (%(sourcesq)s) AS sem_matrix
        JOIN pivot_filtered_ids
            ON sem_matrix.pivotID = pivot_filtered_ids.pivotID
    );
    CREATE INDEX semidx ON sources(pivotID, entityID);

    -- eg: sch pivot to orgs
    -- eg: sch pivot to itself as result (same remark about useless step kept as special case of the general scenario)
    -- eg: kw pivot to jobs+candidates
    CREATE TEMPORARY TABLE IF NOT EXISTS targets  AS (
        SELECT soc_matrix.* FROM (%(targetsq)s) AS soc_matrix
        JOIN pivot_filtered_ids
            ON soc_matrix.pivotID = pivot_filtered_ids.pivotID
    );
    CREATE INDEX socidx ON targets(pivotID, entityID);


    -- =============
    -- matching part (aka XR table)
    -- =============
    CREATE TEMPORARY TABLE IF NOT EXISTS match_table AS (
        SELECT * FROM (
            SELECT count(sources.pivotID) as weight,
                   sources.entityID AS sourceID,
                   targets.entityID AS targetID
            FROM sources
            -- target entities as type1 nodes
            LEFT JOIN targets
                ON sources.pivotID = targets.pivotID
            GROUP BY sourceID, targetID
            ) AS match_table
        WHERE match_table.weight > %(threshold)i
          AND sourceID IS NOT NULL
          AND targetID IS NOT NULL

    );
    CREATE INDEX mt1idx ON match_table(sourceID, targetID);
    """ % {
            'pivotIDField': 'kwid' if pivot_type == 'keywords' else 'luid',
            'sourcesq': subq1,
            'targetsq': subq2,
            'pfiltersq': subqmid,
            'threshold': threshold
    }

    mlog("DEBUGSQL", "multimatch sql query", matchq)

    # this table is the crossrels edges but will be reused for the other data (sameside edges and node infos)
    db_c.execute(matchq)

    # 1 - fetch it
    db_c.execute("SELECT * FROM match_table")
    edges_XR = db_c.fetchall()
    len_XR = len(edges_XR)


    # intermediate step: create marginal sums (for each source its cardinality in pivots)
    #                                         (for each target its cardinality in pivots)
    #
    # => these sums will be used as |Ai| and |Bj|
    #     to "jaccardize" the cooc similarities
    #    (cooc sims are equivalent to |Ai ∩ Bj|)

    src_sumsq = """
        -- to do the operations in sql
        CREATE TEMPORARY TABLE IF NOT EXISTS source_sums AS (
            SELECT sourceID, sum(weight) AS card FROM match_table GROUP BY sourceID
        );
        CREATE INDEX ssums_idx ON source_sums(sourceID, card);
    """
    tgt_sumsq = """
        -- to do the operations in sql
        CREATE TEMPORARY TABLE IF NOT EXISTS target_sums AS (
            SELECT targetID, sum(weight) AS card FROM match_table GROUP BY targetID
        );
        CREATE INDEX tsums_idx ON target_sums(targetID, card);
    """

    # several copies needed for self-joining
    # --------------
    # cf "You cannot refer to a TEMPORARY table more than once in the same query"
    # in https://dev.mysql.com/doc/refman/5.7/en/temporary-table-problems.html
    do_copies = """
            CREATE TEMPORARY TABLE IF NOT EXISTS source_sums_2 AS (
                SELECT * FROM source_sums
            );
            CREATE INDEX ssums2_idx ON source_sums_2(sourceID, card);
            CREATE TEMPORARY TABLE IF NOT EXISTS target_sums_2 AS (
                SELECT * FROM target_sums
            );
            CREATE INDEX tsums2_idx ON target_sums_2(targetID, card);
    """

    # mlog("DEBUG", "margsums sources sql query", src_sumsq)
    # mlog("DEBUG", "margsums targets sql query", tgt_sumsq)

    db_c.execute(src_sumsq)
    db_c.execute(tgt_sumsq)
    db_c.execute(do_copies)   # <= because apparently can't use an alias ?

    # ...or to do the operations in python
    # src_sums = db_c.fetchall()
    # tgt_sums = db_c.fetchall()

    # 2 - matrix product M1·M1⁻¹ to build 'direct sameside' edges
    #                           A
    #              x  pivot [        ]
    #           pivot       [   M1   ]
    #         [      ]
    #      A  [  M1  ]         square
    #         [      ]        sameside
    sameside_direct_format = """
        -- the coocWeights operation after reporting sums
        SELECT dotproduct.*,
                -- keywords.kwstr, k2.kwstr,
               coocWeight/(sum_i + sum_j - coocWeight) AS jaccardWeight
        FROM (
            -- reporting sums
            SELECT nid_i,
                   nid_j,
                   coocWeight,
                   -- all sum_i the same for a nid_i
                   source_local_sums.localMargSum AS sum_i,
                   source_local_sums_2.localMargSum AS sum_j

            FROM (
                -- -----------------------
                -- grouping (nid_i, nid_j)
                -- -----------------------
                SELECT
                    sources.entityID   AS nid_i,
                    sources_2.entityID AS nid_j,
                    COUNT(*) AS coocWeight      -- here: how often each distinct pairs i,j was used
                FROM sources
                JOIN sources_2
                    ON sources.pivotID = sources_2.pivotID
                WHERE sources.entityID != sources_2.entityID
                GROUP BY nid_i, nid_j
            ) AS source_local_coocs
            LEFT JOIN source_local_sums
                ON source_local_sums.nid = nid_i
            LEFT JOIN source_local_sums_2
                ON source_local_sums_2.nid = nid_j

        ) AS dotproduct
            -- WHERE coocWeight > %(threshold)i

             -- JOIN keywords ON nid_i = keywords.kwid
             -- JOIN keywords AS k2 ON nid_j = k2.kwid

        -- ORDER BY jaccardWeight DESC
    """

    # 2a we'll need a few elements for the M1 table
    db_c.execute("""
    CREATE TEMPORARY TABLE IF NOT EXISTS sources_2 AS (
        SELECT * FROM sources
    );
    CREATE INDEX sem2idx ON sources_2(pivotID, entityID);

    -- prepare sums on M1
    CREATE TEMPORARY TABLE IF NOT EXISTS source_local_sums AS (
        SELECT
            entityID AS nid,
            count(pivotID) AS localMargSum
        FROM sources
        GROUP BY entityID
    );
    CREATE INDEX slsums_idx ON source_local_sums(nid, localMargSum);

    -- and one more copy
    CREATE TEMPORARY TABLE IF NOT EXISTS source_local_sums_2 AS (
        SELECT * FROM source_local_sums
    );
    CREATE INDEX slsums2_idx ON source_local_sums_2(nid, localMargSum);
    """)

    # 2b sameside edges type0 <=> type0
    dot_threshold = 0

    edges_00_q = sameside_direct_format
    mlog("DEBUG", "edges_00_q", edges_00_q)
    db_c.execute(edges_00_q)
    edges_00 = db_c.fetchall()

    # 3 - matrix product XR⁻¹·XR to build 'indirect sameside' edges
    #                         B
    #                x  A [        ]
    #             A       [   XR   ]
    #         [      ]
    #      B  [  XR  ]       square
    #         [      ]      sameside

    # nid_type is the output (eg entity type B)
    # transi_type disappears in the operation
    sameside_indirect_format = """
        SELECT dotproduct.*,
               -- scholars.email, s2.email,
               coocWeight/(sum_i + sum_j - coocWeight) AS jaccardWeight
        FROM (
            SELECT
                match_table.%(nid_type)s   AS nid_i,
                match_table_2.%(nid_type)s AS nid_j,
                sum(
                    match_table.weight * match_table_2.weight
                ) AS coocWeight,
                max(sums_1.card) AS sum_i,
                max(sums_2.card) AS sum_j
            FROM match_table
            JOIN match_table_2
                ON match_table.%(transi_type)s = match_table_2.%(transi_type)s
            LEFT JOIN %(nid_type_sums)s AS sums_1
                ON sums_1.%(nid_type)s = match_table.%(nid_type)s
            LEFT JOIN %(nid_type_sums)s_2 AS sums_2
                ON sums_2.%(nid_type)s = match_table_2.%(nid_type)s
            GROUP BY nid_i, nid_j
        ) AS dotproduct
                -- JOIN scholars ON nid_i = scholars.luid
                -- JOIN scholars AS s2 ON nid_j = s2.luid
        WHERE nid_i != nid_j
                --  AND coocWeight > %(threshold)i
                -- ORDER BY jaccardWeight DESC
    """

    # 3a we'll need a copy of the XR table
    db_c.execute("""
    CREATE TEMPORARY TABLE IF NOT EXISTS match_table_2 AS (
        SELECT * FROM match_table
    );
    CREATE INDEX mt2idx ON match_table_2(sourceID, targetID);
    """)

    # 3b sameside edges type1 <=> type1
    dot_threshold = 1
    # mlog("DEBUG", "multimatch tgt dot_threshold", dot_threshold, len_XR)

    edges_11_q = sameside_indirect_format % {'nid_type': "targetID",
                                          'transi_type': "sourceID",
                                        'nid_type_sums': "target_sums",
                                            'threshold': dot_threshold}
    mlog("DEBUG", "edges_11_q", edges_11_q)
    db_c.execute(edges_11_q)
    edges_11 = db_c.fetchall()

    # example edge result
    # +-------+-------+------------+-------+-------+---------------+
    # | nid_i | nid_j | coocWeight | sum_i | sum_j | jaccardWeight |
    # +-------+-------+------------+-------+-------+---------------+
    # |    17 |    26 |          2 |     4 |     3 |        0.4000 |
    # |    25 |    27 |          1 |     2 |     4 |        0.2000 |
    # |    25 |    30 |          1 |     2 |     3 |        0.2500 |
    # |    26 |    17 |          2 |     3 |     4 |        0.4000 |
    # |    26 |    31 |          1 |     3 |     3 |        0.2000 |
    # |    27 |    25 |          1 |     4 |     2 |        0.2000 |
    # |    28 |    30 |          1 |     2 |     3 |        0.2500 |
    # |    30 |    25 |          1 |     3 |     2 |        0.2500 |
    # |    30 |    28 |          1 |     3 |     2 |        0.2500 |
    # |    30 |    32 |          1 |     3 |     2 |        0.2500 |
    # |    31 |    26 |          1 |     3 |     3 |        0.2000 |
    # |    32 |    30 |          1 |     2 |     3 |        0.2500 |
    # +-------+-------+------------+-------+-------+---------------+

    # print("edges_11", edges_11)

    # 4 - we use DBEntity.getInfos() to build node sets (attach node info to id)
    get_nodes_sql = """
        SELECT entity_infos.*
        FROM (   %(entity_infos_q)s   ) AS entity_infos
        -- filter by the matched ids
        JOIN (
            SELECT %(id_field)s AS ID FROM match_table
            GROUP BY %(id_field)s
        ) AS matched_ids
            ON matched_ids.ID = entity_infos.entityID
    """

    # node infos for entities of respective ID tables 'sources' and 'targets'
    node_infos = {}

    for ntype, ntable, nidfield, nclass in [
            (source_type, 'sources', 'sourceID', o1),
            (target_type, 'targets', 'targetID', o2)
        ]:

        nds_q = get_nodes_sql % {
            'id_field': nidfield,
            'id_table': ntable,
            'entity_infos_q': nclass.getInfos(),
        }

        # spec case: jobs_and_candidates need subtype from their toPivot table
        #                                 and 2 x getInfos subqueries
        if ntype == "jobs_and_candidates":
            nds_q_with_class = """
                -- spec start from the toPivot ntable ("targets" table)
                --                (it's the only that has the subtype field)
                SELECT target_entities.*,
                       job_infos.*,
                       sch_infos.*
                FROM (
                  SELECT entityID, max(subtype) AS subtype FROM targets
                  GROUP BY entityID
                ) AS target_entities

                -- filter by the matched ids
                JOIN (
                    SELECT targetID AS ID FROM match_table
                    GROUP BY targetID
                ) AS matched_ids
                    ON matched_ids.ID = target_entities.entityID

                -- getInfos for jobs entities (NULL for scholars)
                LEFT JOIN (
                    %(entity_infos_q_for_jobs)s
                ) AS job_infos
                    ON job_infos.jobid = target_entities.entityID

                -- getInfos for scholars (NULL for jobs)
                LEFT JOIN (
                    %(entity_infos_q_for_scholars)s
                ) AS sch_infos
                    ON sch_infos.entityID = target_entities.entityID
            """ % {
                    'entity_infos_q_for_scholars': nclass.getInfos(subtype="sch"),
                    'entity_infos_q_for_jobs': nclass.getInfos(subtype="job")
                 }
            nds_q = nds_q_with_class

        # in all cases
        mlog("DEBUGSQL", "nds_q (for %s)" % ntable, nds_q)
        db_c.execute(nds_q)
        node_infos[ntable] = db_c.fetchall()

    # connection close also removes the temp tables
    #                       -----------------------
    db.close()

    # mlog("DEBUG", "node_infos", node_infos)

    # build the graph structure (POSS: reuse Sam's networkx Graph object ?)
    graph = {}
    graph["nodes"] = {}
    graph["links"] = {}

    if MATCH_OPTIONS["normalize_schkw_by_sch_totkw"] or MATCH_OPTIONS["normalize_schkw_by_kw_totoccs"]:
        nodes_normfactors = {}

    for ntype, ntable, nclass in [(source_type, 'sources', o1),(target_type, 'targets', o2)]:
        ndata = node_infos[ntable]
        # mlog("DEBUG", "ntype", ntype)
        for nd in ndata:
            nid = make_node_id(ntype, nd['entityID'])

            # node creation (dict of each node to export to json)
            graph["nodes"][nid] = nclass.formatNode(nd, ntype)

            # store optional normalization values
            if ntype == 'sch' and MATCH_OPTIONS["normalize_schkw_by_sch_totkw"]:
                nodes_normfactors[nid] = 1 / log1p(nd['keywords_nb'])

            if ntype == 'kw' and MATCH_OPTIONS["normalize_schkw_by_kw_totoccs"]:
                # if kw then nodeweight is the total of scholars with the kw
                nodes_normfactors[nid] = 1 / log1p(nd['nodeweight'])

    for endtype, edata in [(source_type, edges_00), (target_type,edges_11)]:
        for ed in edata:
            # if endtype == source_type:
            #     print("ed:", ed)
            if not MATCH_OPTIONS["avg_bidirectional_links"]:
                nidi = make_node_id(endtype, ed['nid_i'])
                nidj = make_node_id(endtype, ed['nid_j'])
                eid  =  nidi+';'+nidj
                graph["links"][eid] = {
                  's': nidi,
                  't': nidj,
                  'w': float(round(ed['jaccardWeight'], 5))
                }
            else:
                nids = [make_node_id(endtype, ed['nid_i']), make_node_id(endtype, ed['nid_j'])]
                nids = sorted(nids)
                eid  =  nids[0]+';'+nids[1]
                if eid in graph["links"]:
                    # merging by average like in traditional BipartiteExtractor
                    # (NB just taking the sum would also make sense)
                    graph["links"][eid]["w"] = round((graph["links"][eid]["w"] + float(ed['jaccardWeight']))/2, 5)
                else:
                    graph["links"][eid] = {
                      's': nids[0],
                      't': nids[1],
                      'w': float(round(ed['jaccardWeight'], 5))
                    }

    for ed in edges_XR:
        nidi = make_node_id(source_type, ed['sourceID'])
        nidj = make_node_id(target_type, ed['targetID'])
        eid  =  nidi+';'+nidj
        wei  = MATCH_OPTIONS['XR_weight_constant'] * ed['weight']

        if source_type == 'kw' and target_type == 'sch':
            if MATCH_OPTIONS["normalize_schkw_by_kw_totoccs"]:
                # different than jaccard normalization by sum_i because normfactor counted on all DB
                wei *= nodes_normfactors[nidi]
            if MATCH_OPTIONS["normalize_schkw_by_sch_totkw"]:
                # same remark
                wei *= nodes_normfactors[nidj]
        else:
            wei = float(round(
                    MATCH_OPTIONS['XR_weight_constant'] * ed['weight'], 5
                ))

        graph["links"][eid] = {
          's': nidi,
          't': nidj,
          'w': float(round(wei, 5))
        }

    return graph



def make_node_id(type, id):
    return str(type)+'::'+str(id)

# TODO also add paging as param and to postfilters
def get_field_aggs(a_field,
                   hapax_threshold = None,
                   search_filter_str = None,
                   users_status = "ALL"):
    """
    Use case: /services/api/aggs?field=a_field
             ---------------------------------
       => Retrieves distinct field values and count having it

       => about *n* vs *occs*:
           - for tables != keywords count is scholar count
           - for table keywords count is occurrences count

    Parameters
    ----------
        a_field: str
            a front-end fieldname to aggregate, like "keywords" "countries"
            (allowed values cf. FIELDS_FRONTEND_TO_SQL)

            POSS: allow other fields than those in the mapping
                  if they are already in sql table.col format?

        search_filter_str: str
            if present, select only results LIKE this %%str%%

        hapax_threshold: int
            for all data_types, categories with a total equal or below this will be excluded from results
            TODO: put them in an 'others' category
            POSS: have a different threshold by type


        POSSible:
            pre-filters
                ex: users_status : str
            shoudl define the perimeter (set of scholars over which we work),
    """

    agg_rows = []

    if a_field in FIELDS_FRONTEND_TO_SQL:

        sql_col = FIELDS_FRONTEND_TO_SQL[a_field]['col']
        sql_tab = sql_col.split('.')[0]

        mlog('INFO', "AGG API sql_col", sql_col)

        db = connect_db()
        db_c = db.cursor(DictCursor)

        # constraints 2, if any
        postfilters = []

        if search_filter_str is not None and len(search_filter_str):
            search_filter_str = quotestr(search_filter_str)
            postfilters.append( "x LIKE '%%%s%%'" % search_filter_str)

        if hapax_threshold > 0:
            count_col = 'occs' if sql_tab in ['keywords', 'hashtags'] else 'n'
            postfilters.append( "%s > %i" % (count_col, hapax_threshold) )

        if len(postfilters):
            post_where = "WHERE "+" AND ".join(
                                                ['('+f+')' for f in postfilters]
                                                    )
        else:
            post_where = ""


        # retrieval cases
        if sql_tab == 'scholars':
            stmt = """
                SELECT x, n FROM (
                    SELECT %(col)s AS x, COUNT(*) AS n
                    FROM scholars
                    GROUP BY %(col)s
                ) AS allcounts
                %(post_filter)s
                ORDER BY n DESC
            """ % {'col': sql_col, 'post_filter': post_where}

        elif sql_tab == 'orgs':
            sql_class = FIELDS_FRONTEND_TO_SQL[a_field]['class']
            sql_class_clause = ""
            if len(sql_class) and sql_class != "*":
                sql_class_clause = "WHERE class='%s'" % sql_class
            stmt = """
                SELECT x, n FROM (
                    SELECT %(col)s AS x, COUNT(*) AS n
                    FROM sch_org
                    -- 0 or 1
                    LEFT JOIN orgs
                        ON sch_org.orgid = orgs.orgid
                    %(class_clause)s
                    GROUP BY %(col)s
                ) AS allcounts
                %(post_filter)s
                ORDER BY n DESC
            """ % {'col': sql_col, 'class_clause': sql_class_clause,
                   'post_filter': post_where}

        elif sql_tab == 'linked_ids':
            stmt = """
                SELECT x, n FROM (
                    SELECT %(col)s AS x, COUNT(*) AS n
                    FROM scholars
                    -- 0 or 1
                    LEFT JOIN linked_ids
                        ON scholars.luid = linked_ids.uid
                    GROUP BY %(col)s
                ) AS allcounts
                %(post_filter)s
                ORDER BY n DESC
            """ % {'col': sql_col, 'post_filter': post_where}

        elif sql_tab == 'keywords':
            stmt = """
                SELECT x, occs FROM (
                    SELECT %(col)s AS x, COUNT(*) AS occs
                    FROM scholars
                    -- 0 or many
                    LEFT JOIN sch_kw
                        ON scholars.luid = sch_kw.uid
                    LEFT JOIN keywords
                        ON sch_kw.kwid = keywords.kwid
                    GROUP BY %(col)s
                ) AS allcounts
                %(post_filter)s
                ORDER BY occs DESC
            """ % {'col': sql_col, 'post_filter': post_where}

        elif sql_tab == 'hashtags':
            stmt = """
                SELECT x, occs FROM (
                    SELECT %(col)s AS x, COUNT(*) AS occs
                    FROM scholars
                    -- 0 or many
                    LEFT JOIN sch_ht
                        ON scholars.luid = sch_ht.uid
                    LEFT JOIN hashtags
                        ON sch_ht.htid = hashtags.htid
                    GROUP BY %(col)s
                ) AS allcounts
                %(post_filter)s
                ORDER BY occs DESC
            """ % {'col': sql_col, 'post_filter': post_where}

        elif sql_tab == 'jobs':
            stmt = """
                SELECT x, n FROM (
                    SELECT %(col)s AS x, COUNT(*) AS n
                    FROM jobs
                    GROUP BY %(col)s
                ) AS allcounts
                %(post_filter)s
                ORDER BY n DESC
            """ % {'col': sql_col, 'post_filter': post_where}

        mlog("DEBUGSQL", "get_field_aggs STATEMENT:\n-- SQL\n%s\n-- /SQL" % stmt)

        # do it
        n_rows = db_c.execute(stmt)

        if n_rows > 0:
            agg_rows = db_c.fetchall()
        else:
            mlog('WARNING', 'no rows for query')

        db.close()

    # mlog('DEBUG', "aggregation over %s: result rows =" % a_field, agg_rows)

    return agg_rows


def find_scholar(some_key, some_str_value, cmx_db = None):
    """
    Get the luid of a scholar based on some str value

    To make sense, the key should be a unique one
    but this function doesn't check it !
    """
    luid = None

    if cmx_db:
        db = cmx_db
    else:
        db = connect_db()
    db_c = db.cursor(DictCursor)

    try:
        db_c.execute('''SELECT luid
                        FROM scholars
                        WHERE %s = "%s"
                        ''' % (some_key, some_str_value))
        first_row = db_c.fetchone()
        if first_row:
            luid = first_row['luid']
    except:
        mlog('WARNING', 'unsuccessful attempt to identify a scholar on key %s' % some_key)

    if not cmx_db:
        db.close()

    return luid

class BipartiteExtractor:
    """
    JSON FILTERS => SQL SELECT => scholars subset
                                       ||
                                       VV
                                     keywords
                                       ||
                                       VV
                                     neighboors
    """

    # class var: last terms_colors max
    terms_color_max = 1

    def __init__(self,dbhost):
        self.connection=connect(
            host=dbhost, db="comex_shared",
            user="root", passwd="very-safe-pass",
            charset="utf8"
        )
        mlog("DEBUGSQL", "MyExtractor connected:", self.connection)
        self.cursor=self.connection.cursor(cursors.DictCursor)
        mlog("DEBUGSQL", "MyExtractor gotcursor:", self.cursor)
        self.scholars = {}
        self.scholars_colors = {}
        self.terms_colors = {}
        self.Graph = DiGraph()
        self.min_num_friends=0
        self.imsize=80
        self.terms_dict = {}
        self.unique_id = {}


    def pseudojaccard(self,cooc,occ1,occ2):
        """
        Not a real jaccard (products instead of union: more like PMI)
        Was used for SOC edges (aka nodes1 or edgesA)
        """
        if occ1==0 or occ2==0:
            return 0
        else:
            return cooc*cooc/float(occ1*occ2)


    def jaccard(self,cooc,occ1,occ2):
        """
        To use for all sameside edges (aka nodes1/edgesA and nodes2/edgesB)

        (intersect (=cooc) normalized by union (=totals in this query - cooc))
        """
        return cooc/(occ1+occ2-cooc)


    def comex_sim(self,cooc,occ1,occ2):
        """
        experiments that could be used instead of jaccard

        POSS for keywords case, counts could be normalized by log(total_occ) in the corpus
             where total_occ is available from info['occurrences'] from results4
        """
        # pass

    def getScholarsList(self,qtype,filter_dict):
        """
        select one or more scholars to map in the graph

        the filters take only active scholars or legacy with date <= 3 months

        returns a dict of scholar's uids

        method1 (qtype "uid")
          - filter_dict['unique_id'] defines our starting point (scholar_0)
          - we follow all 2 step coupling paths (scholar_0 <=> keyword_X <=> scholar_i)

        method2 (qtype "filters" constraints)
          - filter_thing is a dict of all the whoswho filters
            ex: {'countries':[France,USA], 'keywords':[blabla]}
          - they are converted to WHERE-clauses in an SQL query

        TODO factorize someday with services.db.get_full_scholar
        """
        scholar_array = {}
        sql_query = None

        # debug
        mlog("DEBUG", "=> getScholarsList.qtype", qtype)
        mlog("DEBUG", "=> getScholarsList.filter_dict", filter_dict)

        try:
            if qtype == "uid":
                # remove quotes from id
                unique_id = sub(r'^"|"$', '', filter_dict['unique_id'])

                mlog("INFO", "unique_id: query is", unique_id)

                # we use the sch_kw table (scholars <=> kw map)
                results = kw_neighbors(unique_id, self.cursor)

                # debug
                mlog("DEBUG", "getScholarsList<== len(all 2-step neighbors) =", len(results))


                if len(results) == 0:
                    # should never happen if input unique_id is valid
                    return []

                if len(results)>0:
                    for row in results:
                        # mlog("DEBUG", "the row:", row)
                        node_uid = row['uid']
                        node_shortid = "S::"+row['initials']+"/%05i"%int(node_uid);

                        #    old way: candidate = ( integerID , realSize , #keywords )
                        #    new way: scholars_array[uid] = ( ID , occ size )

                        scholar_array[node_uid] = 1
                # debug
                # mlog("DEBUGSQL", "getScholarsList<==scholar_array", scholar_array)

            elif qtype == "filters":
                sql_query = None

                mlog("INFO", "filters: query is", filter_dict)

                if "query" in filter_dict and filter_dict["query"] == "*":
                    # query is "*" <=> all scholars
                    sql_query = """
                        SELECT luid
                        FROM scholars
                        WHERE (
                            record_status = 'active'
                            OR
                            (record_status = 'legacy' AND valid_date >= NOW())
                        )
                    """
                else:
                    # query is a set of filters like: key <=> array of values
                    # (expressed as rest parameters: "keyA[]=valA1&keyB[]=valB1&keyB[]=valB2")

                    # 1. we receive it as a dict of arrays
                    # 2. we map it to an sql conjunction of alternatives
                    #    ==> WHERE colA IN ("valA1") AND colB IN ("valB1", "valB2")

                    # build constraints from the args
                    # ================================
                    sql_constraints = rest_filters_to_sql(filter_dict)

                    # use constraints as WHERE-clause
                    sql_query = """
                    SELECT * FROM (
                        %s

                    ) AS full_scholar
                    -- our filtering constraints fit here
                    WHERE  %s

                    """ % (FULL_SCHOLAR_SQL, " AND ".join(sql_constraints))

                mlog("DEBUGSQL", "getScholarsList SELECT:  ", sql_query)

                # in both cases "*" or constraints
                self.cursor.execute(sql_query)
                scholar_rows=self.cursor.fetchall()
                for row in scholar_rows:
                    scholar_array[ row['luid'] ] = 1


            # mlog("DEBUG", "getScholarsList: total scholars in subset = ", len(scholar_array))

            return scholar_array

        except Exception as error:
            mlog("ERROR", "===== getScholarsList SQL ERROR ====")
            if filter_dict != None:
                mlog("ERROR", "qtype "+qtype+" received REST queryargs:\t"+str(filter_dict))
            if sql_query != None:
                mlog("ERROR", "qtype filter attempted SQL query:\t"+sql_query)
            mlog("ERROR", repr(error) + "("+error.__doc__+")")
            mlog("ERROR", "stack (\n\t"+"\t".join(format_tb(error.__traceback__))+"\n)")
            mlog("ERROR", "==== /getScholarsList SQL ERROR ====")


    def extract(self,scholar_array):
        """
        Adding each connected scholar per unique_id

        (getting details for selected scholars into graph object)
        # POSS if filters, could do it along with previous step getScholarsList
        # (less modular but a lot faster)

        NB here scholar_array is actually a dict :/ ...
        """
        # debug
        # mlog("DEBUG", "MySQL extract scholar_array:", scholar_array)
        # scholar_array = list(scholar_array.keys())[0:3]

        sql3='''
            SELECT
                scholars_and_orgs.*,
                COUNT(keywords.kwid) AS keywords_nb,
                GROUP_CONCAT(keywords.kwid) AS keywords_ids,
                GROUP_CONCAT(kwstr) AS keywords_list
            FROM (
                SELECT
                    scholars_and_insts.*,
                    -- small serializations here to avoid 2nd query
                    GROUP_CONCAT(
                      JSON_ARRAY(labs.name, labs.acro, labs.locname)
                    ) AS labs_list
                FROM (
                    SELECT
                        scholars_and_jobs.*,
                        GROUP_CONCAT(
                          JSON_ARRAY(insts.name, insts.acro, insts.locname)
                        ) AS insts_list
                    FROM
                        (
                        SELECT scholars.*,
                               IFNULL(jobs_count.nb_proposed_jobs, 0) AS nb_proposed_jobs,
                               jobs_count.job_ids,
                               jobs_count.job_titles
                        FROM scholars
                        LEFT JOIN (
                            SELECT uid,
                            count(jobid) AS nb_proposed_jobs,
                            GROUP_CONCAT(jobid) AS job_ids,
                            GROUP_CONCAT(JSON_QUOTE(jtitle)) AS job_titles
                            FROM jobs
                            WHERE job_valid_date >= CURDATE()
                            GROUP BY uid
                            ) AS jobs_count ON jobs_count.uid = scholars.luid
                        ) AS scholars_and_jobs
                        LEFT JOIN sch_org ON scholars_and_jobs.luid = sch_org.uid
                        LEFT JOIN (
                            SELECT * FROM orgs WHERE class = 'inst'
                        ) AS insts ON sch_org.orgid = insts.orgid
                    WHERE (record_status = 'active'
                        OR (record_status = 'legacy' AND valid_date >= NOW()))
                    GROUP BY luid
                ) AS scholars_and_insts
                LEFT JOIN sch_org ON luid = sch_org.uid
                LEFT JOIN (
                    SELECT * FROM orgs WHERE class = 'lab'
                ) AS labs ON sch_org.orgid = labs.orgid
                GROUP BY luid
            ) AS scholars_and_orgs

            LEFT JOIN sch_kw
                ON sch_kw.uid = scholars_and_orgs.luid
            LEFT JOIN keywords
                ON sch_kw.kwid = keywords.kwid
            WHERE luid IN %s
            GROUP BY luid ;
        ''' %  ('('+','.join(map(str, list(scholar_array.keys())))+')')

        # debug
        mlog("DEBUGSQL", "db.extract: sql3="+sql3)

        ide = None

        try:
            self.cursor.execute(sql3)

            for res3 in self.cursor:
                info = {};

                # semantic short ID
                # ex "S::JFK/00001"

                if 'pic_fname' in res3 and res3['pic_fname']:
                    pic_src = '/data/shared_user_img/'+res3['pic_fname']
                elif 'pic_url' in res3 and res3['pic_url']:
                    pic_src = res3['pic_url']
                else:
                    pic_src = ''

                # NB instead of secondary query for orgs.*, we can
                # simply parse orgs infos
                # and take labs[0] and insts[0]
                labs  = list(map(
                        lambda arr: Org(arr, org_class='lab'),
                        loads('['+res3['labs_list'] +']')
                ))
                insts = list(map(
                        lambda arr: Org(arr, org_class='insts'),
                        loads('['+res3['insts_list']+']')
                ))

                # POSSIBLE: in the future (SQL VERSION >= 8) USE JSON_ARRAYAGG
                # https://dev.mysql.com/doc/refman/8.0/en/group-by-functions.html#function_json-arrayagg

                # mlog("DEBUGSQL", "res main lab:", labs[0].label)
                # mlog("DEBUGSQL", "res main inst:", insts[0].label)

                # all detailed node data
                ide="S::"+res3['initials']+("/%05i"%int(res3['luid']));
                info['id'] = ide;
                info['luid'] = res3['luid'];
                info['doors_uid'] = res3['doors_uid'];
                info['pic_src'] = pic_src ;
                info['first_name'] = res3['first_name'];
                info['mid_initial'] = res3['middle_name'][0] if res3['middle_name'] else ""
                info['last_name'] = res3['last_name'];

                # card(keywords) of this scholar **in the DB**
                # (because queries take all keywords, it should be equal to scholarsMatrix[term_scholars[k]]['marginal_tot_kws'])
                info['keywords_nb'] = res3['keywords_nb'];
                info["normfactor"] = 1/log1p(res3['keywords_nb'])
                info['keywords_ids'] = res3['keywords_ids'].split(',') if res3['keywords_ids'] else [];
                info['keywords_list'] = res3['keywords_list'];
                info['country'] = res3['country'];
                info['ACR'] = labs[0].acro if labs[0].acro else labs[0].any
                #info['CC'] = res3['norm_country'];
                info['home_url'] = res3['home_url'];
                info['team_lab'] = labs[0].label;
                info['org'] = insts[0].label;
                info['nb_proposed_jobs'] = res3['nb_proposed_jobs'];
                info['job_ids'] = res3['job_ids'].split(',') if res3['job_ids'] else [];
                info['job_titles'] = loads('['+res3['job_titles']+']') if res3['job_titles'] else [];

                if len(labs) > 1:
                    info['lab2'] = labs[1].label
                if len(insts) > 1:
                    info['affiliation2'] = insts[1].label
                info['hon_title'] = res3['hon_title'] if res3['hon_title'] else ""
                info['position'] = res3['position'];
                info['job_looking'] = res3['job_looking'];
                info['job_looking_date'] = res3['job_looking_date'];
                info['email'] = res3['email'];
                if info['keywords_nb']>0:
                    self.scholars[ide] = info;

        except Exception as error:
            mlog("ERROR", "=====  extract ERROR ====")
            if ide:
                mlog("ERROR", "extract on scholar no %s" % str(ide))
            elif sql3 != None:
                mlog("ERROR", "extract attempted SQL query:\t"+sql3)
            mlog("ERROR", repr(error) + "("+error.__doc__+")")
            mlog("ERROR", "stack (\n\t"+"\t".join(format_tb(error.__traceback__))+"\n)")
            mlog("ERROR", "===== /extract ERROR ====")


        # génère le gexf
        # include('gexf_generator.php');
        imsize=80;
        termsMatrix = {};
        scholarsMatrix = {};
        scholarsIncluded = 0;

        for i in self.scholars:
            mlog('DEBUGSQL', 'extractDataCustom:'+self.scholars[i]['email'])
            self.scholars_colors[self.scholars[i]['email'].strip()]=0;
            scholar_keywords = self.scholars[i]['keywords_ids'];

            for k in range(len(scholar_keywords)):
                kw_k = scholar_keywords[k]

                if kw_k != None and kw_k!="":
                    # mlog("DEBUG", kw_k)
                    if kw_k not in termsMatrix:
                        termsMatrix[kw_k]={}
                        termsMatrix[kw_k]['marginal_tot_occs'] =  0;
                        termsMatrix[kw_k]['cooc'] = {};

                    # total occs within this query
                    # (count of sch having this kw **among sch of this query**)
                    # (this is not total occs in the DB because queries don't take all scholars of a keyword)
                    termsMatrix[kw_k]['marginal_tot_occs'] += 1;

                    for l in range(len(scholar_keywords)):
                        kw_l = scholar_keywords[l]
                        if kw_l in termsMatrix[kw_k]['cooc']:
                            termsMatrix[kw_k]['cooc'][kw_l] += 1
                        else:
                            termsMatrix[kw_k]['cooc'][kw_l] = 1;

        # ------- debug -------------------------------
        # print(">>>>>>>>>termsMatrix<<<<<<<<<")
        # print(termsMatrix)
        # ------- /debug ------------------------------

        query = """SELECT kwstr,keywords.kwid,occs,nbjobs FROM keywords
                   LEFT JOIN (
                        SELECT kwid, count(kwid) AS nbjobs
                        FROM job_kw
                        GROUP BY kwid
                        ) AS jobcounts
                   ON jobcounts.kwid = keywords.kwid
                   WHERE keywords.kwid IN """
        conditions = ' (' + ','.join(sorted(list(termsMatrix))) + ')'

        # debug
        # mlog("DEBUG", "SQL query ===============================")
        # mlog("DEBUG", query+conditions)
        # mlog("DEBUG", "/SQL query ==============================")

        self.cursor.execute(query+conditions)
        results4 = self.cursor.fetchall()

        for res in results4:
            idT = res['kwid']
            info = {}
            info['kwid'] = idT
            info['occurrences'] = res['occs']   # total occs in the DB
                                                # (used as normalization if
                                                # normalize_schkw_by_kw_totoccs)
            info['kwstr'] = res['kwstr']

            # job counter: how many times a term is cited in job ads
            if res['nbjobs']:
                info['nbjobs'] = int(res['nbjobs'])
                # mlog("DEBUG", "nbjobs", info['kwstr'], int(res['nbjobs']))
            else:
                info['nbjobs'] = 0

            # save
            self.terms_dict[str(idT)] = info

        # set the colors factor and max
        # will affect red and green level of default color (cf. colorRed, colorGreen)
        for term in self.terms_dict:
            self.terms_colors[term] = self.terms_dict[term]['nbjobs']
            # if (self.terms_colors[term] != 0):
                # mlog("DEBUG", "self.terms_colors[term]", term, self.terms_colors[term])
            if self.terms_colors[term] > BipartiteExtractor.terms_color_max:
                BipartiteExtractor.terms_color_max = self.terms_colors[term]

        for term_id in self.terms_dict:
            sql="SELECT uid, initials FROM sch_kw JOIN scholars ON uid=luid WHERE kwid=%s" % term_id
            term_scholars=[]
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            for row in rows:
                term_scholars.append("S::"+row['initials']+"/%05i"%int(row['uid']))

            for k in range(len(term_scholars)):
                if term_scholars[k] not in scholarsMatrix:
                    scholarsMatrix[term_scholars[k]]={}
                    scholarsMatrix[term_scholars[k]]['marginal_tot_kws'] = 0 ;
                    scholarsMatrix[term_scholars[k]]['cooc'] = {};

                # total nbkws of scholar within this filter (should == total nbkws of this scholar)
                scholarsMatrix[term_scholars[k]]['marginal_tot_kws'] += 1

                for l in range(len(term_scholars)):
                    if term_scholars[l] in self.scholars:
                        if term_scholars[l] in scholarsMatrix[term_scholars[k]]['cooc']:
                            scholarsMatrix[term_scholars[k]]['cooc'][term_scholars[l]] += 1
                        else:
                            scholarsMatrix[term_scholars[k]]['cooc'][term_scholars[l]] = 1;

            # eg matrix entry for scholar k
            # 'S::SK/04047': {'marginal_tot_occs': 1, 'cooc': {'S::SL/02223': 1}}
            nodeId = "K::"+str(term)
            self.Graph.add_node(nodeId)

        for scholar in self.scholars:
            if scholar in scholarsMatrix:
                if len(scholarsMatrix[scholar]['cooc']) >= self.min_num_friends:
                    scholarsIncluded += 1;
                    nodeId = str(scholar);
                    self.Graph.add_node(nodeId, weight=3)

        edgeid = 0
        for scholar in self.scholars:
            if scholar in scholarsMatrix:
                if len(scholarsMatrix[scholar]['cooc']) >= 1:

                    for keyword in self.scholars[scholar]['keywords_ids']:
                        if keyword:
                            source= str(scholar)
                            target="K::"+str(keyword)

                            # term--scholar weight: constant * optional factors
                            weight = MATCH_OPTIONS['XR_weight_constant']

                            # 1/log(1+total_keywords_of_scholar)
                            if MATCH_OPTIONS['normalize_schkw_by_sch_totkw']:
                                weight *= self.scholars[scholar]['normfactor']

                            # 1/log(1+total_scholars_of_keyword)
                            if MATCH_OPTIONS['normalize_schkw_by_kw_totoccs']:
                                weight *= 1/log1p(self.terms_dict[keyword]['occurrences'])

                            self.Graph.add_edge( source , target , {'weight':round(weight,5),'type':"bipartite"})

        for term in self.terms_dict:
            nodeId1 = self.terms_dict[term]['kwid'];
            if str(nodeId1) in termsMatrix:
                neighbor_coocs = termsMatrix[str(nodeId1)]['cooc'];
                id1_occs = termsMatrix[str(nodeId1)]['marginal_tot_occs']
                for i, neigh in enumerate(neighbor_coocs):
                    if neigh != term:
                        source="K::"+term
                        target="K::"+neigh

                        id2_occs = termsMatrix[str(neigh)]['marginal_tot_occs']

                        # term--term weight
                        weight=self.jaccard(neighbor_coocs[neigh],
                                            id1_occs,
                                            id2_occs)


                        # jaccard: cooc / (total_query_occ_i + total_query_occ_j - cooc)

                        # total_query_occ_i: total occs within this query

                        # NB: total occurrences within DB also available for normalization
                        #     in self.terms_dict[neigh]['occurrences'])

                        # detailed debug:
                        # if neighbor_coocs[neigh] != 1:
                        #     mlog("DEBUG", "extractDataCustom.extract edges b/w terms====")
                        #     mlog("DEBUG", "term:", self.terms_dict[term]['kwstr'], "<===> neighb:", self.terms_dict[neigh]['kwstr'])
                        #     mlog("DEBUG", "kwoccs:", self.terms_dict[term]['occurrences'])
                        #     mlog("DEBUG", "neighbor_coocs[neigh]:", neighbor_coocs[neigh])
                        #     mlog("DEBUG", "edge w", weight)

                        # cf also final edge weights after rounding in buildJSON

                        self.Graph.add_edge( source , target , {'weight':round(weight,5),'type':"nodes2"})

        for scholar in self.scholars:
            nodeId1 = scholar;
            if str(nodeId1) in scholarsMatrix:

                # weighted list of other scholars
                neighbor_coocs=scholarsMatrix[str(nodeId1)]['cooc'];
                # eg {'S::KW/03291': 1, 'S::WTB/04144': 3}


                for i, neigh in enumerate(neighbor_coocs):
                    if neigh != str(scholar):
                        source=str(scholar)
                        target=str(neigh)
                        # scholar--scholar weight: number of common terms / (total keywords of scholar 1 x total keywords of scholar 2)

                        # actual: pseudojaccard: cooc*cooc/float(occ1*occ2)
                        # jaccard: cooc / (total_occ_i + total_occ_j - cooc)

                        weight = self.jaccard(
                            neighbor_coocs[str(neigh)],
                            scholarsMatrix[nodeId1]['marginal_tot_kws'],
                            scholarsMatrix[neigh]['marginal_tot_kws']
                        )
                        #mlog("DEBUG", "\t"+source+","+target+" = "+str(weight))
                        self.Graph.add_edge( source , target , {'weight':round(weight,5),'type':"nodes1"})

        # ------- debug nodes1 -------------------------
        # print(">>>>>>>>>scholarsMatrix<<<<<<<<<")
        # print(scholarsMatrix)

        # exemple:
        # {'S::PFC/00002': {'marginal_tot_kws': 6,
        #                   'cooc': {'S::PFC/00002': 6,
        #                            'S::fl/00009': 1,
        #                            'S::DC/00010': 1}
        #                   },
        #   'S::fl/00009': {'marginal_tot_kws': 9,
        #                   'cooc': {'S::fl/00009': 9,
        #                            'S::PFC/00002': 1}
        #                  }
        # ------- /debug ------------------------------



    def toHTML(self,string):
        escaped = escape(string).encode("ascii", "xmlcharrefreplace").decode()
        return escaped


    def buildJSON(self,graph,coordsRAW=None):
        nodesA=0
        nodesB=0
        edgesA=0
        edgesB=0
        edgesAB=0
        # mlog("DEBUG", "printing in buildJSON_sansfa2()")
        nodes = {}
        edges = {}
        if coordsRAW:
            xy = coordsRAW #For FA2.java: loads(coordsRAW)
            #mlog("DEBUG", xy)
            coords = {}
            for i in xy:
                coords[i['sID']] = {}
                coords[i['sID']]['x'] = i['x']
                coords[i['sID']]['y'] = i['y']
            #mlog("DEBUG", coords)

        for idNode in graph.nodes_iter():
            if idNode[0]=="K": #If it is Keyword

                kwid=idNode.split("::")[1]
                try:
                    nodeLabel= self.terms_dict[kwid]['kwstr'].replace("&"," and ")
                    ratio = self.terms_colors[kwid]/BipartiteExtractor.terms_color_max
                    colorRed=int(180+75*ratio)
                    colorGreen=int(180-140*ratio)

                    term_occ = self.terms_dict[kwid]['occurrences']

                    # debug
                    # mlog("DEBUG", "coloring terms idNode:", colorRed, colorGreen)

                except KeyError:
                    mlog("WARNING", "couldn't find label and meta for term " + kwid)
                    nodeLabel = "UNKNOWN"
                    colorRed = 180
                    colorGreen = 180
                    term_occ = 1

                node = {}
                node["type"] = "Keywords"
                node["label"] = nodeLabel
                node["color"] = str(colorRed)+","+str(colorGreen)+",25"
                node["term_occ"] = term_occ

                # new tina: any parsable attributes directly become facets
                node["attributes"] = {
                    "total_occurrences": term_occ,
                    "nbjobs": self.terms_dict[kwid]['nbjobs'],
                }
                if coordsRAW: node["x"] = str(coords[idNode]['x'])
                if coordsRAW: node["y"] = str(coords[idNode]['y'])

                nodes[idNode] = node

#            mlog("DEBUG", "NGR","\t",idNode,"\t",nodeLabel,"\t",term_occ)

                nodesB+=1

            # adding here node properties
            if idNode[0]=='S':#If it is scholar

                nodeLabel= self.scholars[idNode]['hon_title']+" "+self.scholars[idNode]['first_name']+" "+self.scholars[idNode]['mid_initial']+" "+self.scholars[idNode]['last_name']
                color=""
                if self.scholars_colors[self.scholars[idNode]['email']]==1:
                    color='243,183,19'
                elif self.scholars[idNode]['job_looking']:
                    color = '43,44,141'
                elif self.scholars[idNode]['nb_proposed_jobs'] > 0:
                    color = '41,189,243'
                else:
                    color = '78,193,127'

                 # content is an instance of #information.our-vcard
                 # --------------------------------------------------
                 #     <img src="....">
                 #     <ul>
                 #         <li class=bigger>
                 #             <b>{{ hon_title }}
                 #                 {{ first_name }}
                 #                 {{ mid_initials }}
                 #                 {{ last_name }}</b>
                 #                 <br/>
                 #                 <br/>
                 #         </li>
                 #         <li>
                 #             <b>Country: </b>{{ country }}<br>
                 #             <b>Position: </b>{{ position }}<br>
                 #             <b>Keywords: </b>{{ keywords }}<br>
                 #             [ <a href="{{ info.home_url }}" target="blank">
                 #                 View homepage
                 #             </a>]
                 #             <br>
                 #         </li>
                 #     </ul>


                content="<div class='information-vcard'>"


                # pic in vcard
                pic_src=self.scholars[idNode]['pic_src']
                if pic_src and pic_src != "":
                    content += '<img  src="'+pic_src+'" width=' + str(self.imsize) + 'px>';
                else:
                    if len(self.scholars)<2000:
                        im_id = int(floor(randint(0, 11)))
                        content += '<img src="static/img/'+str(im_id)+'.png" width='  + str(self.imsize) +  'px>'

                # label in vcard
                content += '<p class=bigger><b>'+nodeLabel+'</b></p>'

                # other infos in vcard
                content += '<p>'
                content += '<b>Country: </b>' + self.scholars[idNode]['country'] + '</br>'

                if self.scholars[idNode]['position'] and self.scholars[idNode]['position'] != "":
                    content += '<b>Position: </b>' +self.scholars[idNode]['position'].replace("&"," and ")+ '</br>'

                affiliation=""
                if self.scholars[idNode]['team_lab'] and self.scholars[idNode]['team_lab'] not in ["", "_NULL"]:
                    affiliation += self.scholars[idNode]['team_lab']+ ','
                if self.scholars[idNode]['org'] and self.scholars[idNode]['org'] != "":
                    affiliation += self.scholars[idNode]['org']

                if affiliation != "":
                    content += '<b>Affiliation: </b>' + escape(affiliation) + '</br>'

                if len(self.scholars[idNode]['keywords_list']) > 3:
                    content += '<b>Keywords: </b>' + self.scholars[idNode]['keywords_list'].replace(",",", ")+'.</br>'

                if self.scholars[idNode]['home_url']:
                    if self.scholars[idNode]['home_url'][0:3] == "www":
                        content += '[ <a href=http://' +self.scholars[idNode]['home_url'].replace("&"," and ")+ ' target=blank > View homepage </a ><br/>]'
                    elif self.scholars[idNode]['home_url'][0:4] == "http":
                        content += '[ <a href=' +self.scholars[idNode]['home_url'].replace("&"," and ")+ ' target=blank > View homepage </a >]<br/>'


                content += '</p>'

                # also add pointers to jobs
                if self.scholars[idNode]['nb_proposed_jobs'] > 0:
                    # mlog("DEBUG", "adding jobs for", idNode, "nb_proposed_jobs", self.scholars[idNode]['nb_proposed_jobs'])
                    content += """
                        <hr>
                        <div class=information-others>
                        <h5> Related jobs </h5>
                        <ul class=infoitems>
                        """
                    for j, jobid in enumerate(self.scholars[idNode]['job_ids']):
                        content += "<li>"
                        content += "<a href=\"/services/job/"+jobid+"\" target=\"_blank\">"+ self.scholars[idNode]['job_titles'][j]
                        content += "</a></li>"
                    content += '</ul></div>'

                content += '</div>'

                node = {}
                node["type"] = "Scholars"
                node["label"] = nodeLabel
                node["color"] = color

                # new tina: any values under .attributes can be mapped to a color
                #           or used in any other way by ProjectExplorer
                node["attributes"] = {}

                # special attribute normalizing factor
                if self.scholars[idNode]["keywords_ids"] and len(self.scholars[idNode]["keywords_ids"]):
                    node["attributes"]["normfactor"] = self.scholars[idNode]["normfactor"]
                else:
                    node["attributes"]["normfactor"] = 1

                # country code
                dacountry = self.scholars[idNode]["country"]
                if dacountry: node["attributes"]["country"] = dacountry
                else: node["attributes"]["country"]="-"

                # Affiliation
                node["attributes"]["ACR"] = self.scholars[idNode]["org"]
                if node["attributes"]["ACR"]=="": node["attributes"]["ACR"]="-"

                # /!\ Fixed weight for all SOC nodes /!\
                # cf. node.size in sigma.parseCustom.js
                node["term_occ"] = "12"
                if coordsRAW: node["x"] = str(coords[idNode]['x'])
                if coordsRAW: node["y"] = str(coords[idNode]['y'])
                node["content"] = str(self.toHTML(content))

                nodes[idNode] = node

                # mlog("DEBUG", "SCH","\t",idNode,"\t",nodeLabel)

                nodesA+=1

        if MATCH_OPTIONS['avg_bidirectional_links']:
            GG = Graph()
            for n in self.Graph.edges_iter():
                s = n[0]
                t = n[1]
                w = float(self.Graph[n[0]][n[1]]['weight'])
                tp = self.Graph[n[0]][n[1]]['type']

                if GG.has_edge(s,t):
                    # (case when same edge, both directions)
                    oldw = GG[s][t]['weight']
                    # NB this avg works because at max 2 values
                    avgw = (oldw+w)/2
                    GG[s][t]['weight'] = avgw
                else:
                    GG.add_edge( s , t , { "weight":round(w,5) , "type":tp } )
        else:
            GG = DiGraph()
            for n in self.Graph.edges_iter():
                s = n[0]
                t = n[1]
                w = float(self.Graph[n[0]][n[1]]['weight'])
                tp = self.Graph[n[0]][n[1]]['type']
                GG.add_edge( s , t , { "weight":round(w,5) , "type":tp } )

        e = 0
        for n in GG.edges_iter():#Memory, what's wrong with you?
            wr = 0.0
            origw = GG[n[0]][n[1]]['weight']
            wr = round( origw , 5 )
            edge = {}
            edge["s"] = n[0]
            edge["t"] = n[1]
            edge["w"] = str(wr)
            if GG[n[0]][n[1]]['type']=="nodes1": edgesA+=1
            if GG[n[0]][n[1]]['type']=="nodes2": edgesB+=1
            if GG[n[0]][n[1]]['type']=="bipartite": edgesAB+=1

            # --------------------------------------
            # final edge weights for all edge types
            # --------------------------------------
            # mlog("DEBUG", nodes[n[0]]["label"],"\t",nodes[n[1]]["label"],"\t",edge["w"])

            edges[str(e)] = edge
            e+=1
            # if e%1000 == 0:
            #    mlog("INFO", e)

        graph = {}
        graph["nodes"] = nodes
        graph["links"] = edges
        graph["stats"] = { "sch":nodesA,"kw":nodesB,"n1(soc)":edgesA,"n2(sem)":edgesB,"nbi":edgesAB ,  }
        graph["ID"] = self.unique_id

        mlog("INFO", "BipartiteExtractor results:", graph["stats"])

        return graph



def quotestr(a_str):
    "helper function if we need to quote values ourselves"
    return sub(r"(?<!\\)[']",r"\\'",a_str)


def type_to_sql_filter(val):
    "helper functions if we need to build test filters ourselves"

    if isinstance(val, int):
        rhs = '= %i' % val
    elif isinstance(val, float):
        rhs = '= %f' % val
    # elif isinstance(val, str):
    #     rhs = '= "%s"' % val
    elif isinstance(val, str):
        rhs = 'LIKE "%'+quotestr(val)+'%"'
    return rhs
