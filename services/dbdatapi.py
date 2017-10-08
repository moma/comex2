"""
DB data querying:
  - aggregations on almost any DB fields via FIELDS_FRONTEND_TO_SQL
  - BipartiteExtractor subset selections originally made by Samuel
  - soon multimatch subset selections
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
    from services.dbcrud  import connect_db
    from services.dbentities import DBScholars, DBLabs, DBInsts, DBKeywords, \
                                    DBHashtags, DBCountries
else:
    from tools          import mlog, REALCONFIG
    from dbcrud         import connect_db
    from dbentities     import DBScholars, DBLabs, DBInsts, DBKeywords, \
                               DBHashtags, DBCountries


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


# NB we must cascade join because
#    orgs, hashtags and keywords are one-to-many
full_scholar_sql = """
    SELECT
        sch_org_n_tags.*,

        -- kws info
        GROUP_CONCAT(keywords.kwstr) AS keywords_list

    FROM (
        SELECT
            scholars_and_orgs.*,
            -- hts info
            GROUP_CONCAT(hashtags.htstr) AS hashtags_list

        FROM (
          SELECT scholars.*,
                 -- org info
                 -- GROUP_CONCAT(orgs.orgid) AS orgs_ids_list,
                 GROUP_CONCAT(orgs_set.label) AS orgs_list
          FROM scholars
          LEFT JOIN sch_org ON luid = sch_org.uid
          LEFT JOIN (
            SELECT * FROM orgs
          ) AS orgs_set ON sch_org.orgid = orgs_set.orgid
          GROUP BY luid
        ) AS scholars_and_orgs
        LEFT JOIN sch_ht
            ON uid = luid
        LEFT JOIN hashtags
            ON sch_ht.htid = hashtags.htid
        GROUP BY luid
    ) AS sch_org_n_tags

    -- two step JOIN for keywords
    LEFT JOIN sch_kw
        ON uid = luid
    -- we directly exclude scholars with no keywords here
    JOIN keywords
        ON sch_kw.kwid = keywords.kwid

    WHERE (
        record_status = 'active'
        OR
        (record_status = 'legacy' AND valid_date >= NOW())
    )

    GROUP BY luid
"""

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
                mlog("DEBUG", "[filters to sql]: tested_array", tested_array)
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


# multimatch(nodetype_1, nodetype_2)
# ==================================
def multimatch(source_type, target_type, pivot_filters = []):
    """
    Returns a list of edges between the objects of type 1 and those of type 2,
    via their matching scholars (used as pivot and for filtering)

    src_type ∈ {kw, ht}
    tgt_type ∈ {sch, lab, inst, country}
    """

    type_map = {
        "sch" :  DBScholars,
        "lab" :  DBLabs,
        "inst" : DBInsts,
        "kw" :   DBKeywords,
        "ht" :   DBHashtags,
        "country" :   DBCountries,
    }

    # unsupported entities
    if ( source_type not in type_map
      or target_type not in type_map ):
        return []

    # instanciating appropriate DBEntity class
    o1 = type_map[source_type]()
    o2 = type_map[target_type]()

    db = connect_db()
    db_c = db.cursor(DictCursor)

    # idea: we can always (SELECT subq1)
    #       and JOIN with (SELECT subq2)
    #       because they both expose pivotID
    subq1 = o1.toPivot()
    subq2 = o2.toPivot()

    # additional filter step: the middle pivot step allows filtering pivots
    #                         by any information that can be related to it
    subqmidfilters = ''
    if (len(pivot_filters)):
        subqmidfilters = "WHERE " + " AND ".join(pivot_filters)

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
    """ % (full_scholar_sql, subqmidfilters)

    # ------------------------------------------------------------  Explanations
    #
    # At this point in matrix representation:
    #  - subq1 is M1 [source_type x filtered_scholars]
    #  - subq2 is M2 [filtered_scholars x target_type]
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
    -- matching part
    CREATE TEMPORARY TABLE IF NOT EXISTS match_table AS (
        SELECT * FROM (
            SELECT count(sources.pivotID) as weight,
                   sources.entityID AS sourceID,
                   targets.entityID AS targetID
            FROM (%s) AS sources

            -- inner join as filter
            JOIN (%s) AS pivot_filtered_ids
                ON sources.pivotID = pivot_filtered_ids.luid

            -- target entities as type1 nodes
            LEFT JOIN (%s) AS targets
                ON sources.pivotID = targets.pivotID
            GROUP BY sourceID, targetID
            ) AS match_table
        WHERE match_table.weight > %i
          AND sourceID IS NOT NULL
          AND targetID IS NOT NULL

    );
    CREATE INDEX mt1idx ON match_table(sourceID, targetID)
    """ % (
        subq1,
        subqmid,
        subq2,
        threshold
        )

    # mlog("DEBUG", "multimatch sql query", matchq)

    # this table is the crossrels edges but will be reused for the other data (sameside edges and node infos)
    db_c.execute(matchq)

    # 1 - fetch it
    db_c.execute("SELECT * FROM match_table")
    edges_XR = db_c.fetchall()
    len_XR = len(edges_XR)

    # 2 - matrix product XR·XR⁻¹ to build 'sameside' edges
    #                         A
    #                x  B [        ]
    #             B       [   XR   ]
    #         [      ]
    #      A  [  XR  ]       square
    #         [      ]      sameside

    # 2a we'll need a copy of the XR table
    db_c.execute("""
    CREATE TEMPORARY TABLE IF NOT EXISTS match_table_2 AS (
        SELECT * FROM match_table
    );
    CREATE INDEX mt2idx ON match_table_2(sourceID, targetID)
    """)

    # nid_type is A and transi_type is B
    sameside_format = """
        SELECT * FROM (
            SELECT
                match_table.%(nid_type)s   AS nid_i,
                match_table_2.%(nid_type)s AS nid_j,
                sum(
                    match_table.weight * match_table_2.weight
                ) AS dotweight
            FROM match_table
            JOIN match_table_2
                ON match_table.%(transi_type)s = match_table_2.%(transi_type)s
            GROUP BY nid_i, nid_j
        ) AS dotproduct
        WHERE nid_i != nid_j
          AND dotweight > %(threshold)i
    """

    # 2b sameside edges type0 <=> type0
    dot_threshold = floor(.5 + len_XR/3000)
    edges_00_q = sameside_format % {'nid_type': "sourceID",
                                   'transi_type': "targetID",
                                   'threshold': dot_threshold}
    # print("DEBUGSQL", "edges_00_q", edges_00_q)
    mlog("DEBUG", "multimatch src dot_threshold src", dot_threshold, len_XR)
    db_c.execute(edges_00_q)
    edges_00 = db_c.fetchall()


    # 2c sameside edges type1 <=> type1
    # dot_threshold = floor(10*sqrt(len_XR)) if target_type != 'sch' else 0
    dot_threshold = floor(len_XR/3000)
    edges_11_q = sameside_format % {'nid_type': "targetID",
                                   'transi_type': "sourceID",
                                   'threshold': dot_threshold}
    # print("DEBUGSQL", "edges_11_q", edges_11_q)
    mlog("DEBUG", "multimatch tgt dot_threshold", dot_threshold, len_XR)
    db_c.execute(edges_11_q)
    edges_11 = db_c.fetchall()

    # 3 - we use DBEntity.getInfos() to build node sets
    get_nodes_format = """
        SELECT entity_infos.* FROM match_table
        LEFT JOIN (%s) AS entity_infos
            ON entity_infos.entityID = match_table.%s
        GROUP BY entity_infos.entityID
    """
    src_nds_q = get_nodes_format % (o1.getInfos(), 'sourceID')
    db_c.execute(src_nds_q)
    nodes_src = db_c.fetchall()

    tgt_nds_q = get_nodes_format % (o2.getInfos(), 'targetID')
    db_c.execute(tgt_nds_q)
    nodes_tgt = db_c.fetchall()

    # connection close also removes the temp tables
    db.close()

    # build the graph structure (POSS: reuse Sam's networkx Graph object ?)
    graph = {}
    graph["nodes"] = {}
    graph["links"] = {}

    for ntype, ndata in [(source_type, nodes_src),(target_type, nodes_tgt)]:
        for nd in ndata:
            nid = make_node_id(ntype, nd['entityID'])
            graph["nodes"][nid] = {
              'label': nd['label'],
              'type': ntype,
              'size': log1p(nd['nodeweight']),
              'color': '243,183,19' if ntype == source_type else '139,28,28'
            }


    for endtype, edata in [(source_type, edges_00), (target_type,edges_11)]:
        for ed in edata:
            nidi = make_node_id(endtype, ed['nid_i'])
            nidj = make_node_id(endtype, ed['nid_j'])
            eid  =  nidi+';'+nidj
            graph["links"][eid] = {
              's': nidi,
              't': nidj,
            #   'w': log1p(int(ed['dotweight']))
              'w': sqrt(int(ed['dotweight']))
            #   'w': float(ed['dotweight'])
            }

    for ed in edges_XR:
        nidi = make_node_id(source_type, ed['sourceID'])
        nidj = make_node_id(target_type, ed['targetID'])
        eid  =  nidi+';'+nidj
        graph["links"][eid] = {
          's': nidi,
          't': nidj,
          'w': int(ed['weight']*100)
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


class Org:
    " tiny helper class to serialize/deserialize orgs TODO use more OOP :) "

    def __init__(self, org_array, org_class=None):
        if len(org_array) < 3:
            raise ValueError("Org is implemented for at least [name, acr, loc]")
        self.name = org_array[0]
        self.acro = org_array[1]
        self.locname = org_array[2]
        self.org_class = org_class

        # DB specifications say that at least one of name||acr is NOT NULL
        self.any = self.acro if self.acro else self.name
        self.label  = (  ( self.name if self.name else "")
                        + ((' ('+self.acro+')') if self.acro else "")
                        + ((', '+self.locname) if self.locname else "")
                        )


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


    def jaccard(self,cooc,occ1,occ2):
        """
        Used for SOC edges (aka nodes1 or edgesA)

        (Cooc normalized by total scholars occs)
        """
        if occ1==0 or occ2==0:
            return 0
        else:
            return cooc*cooc/float(occ1*occ2)

    def log_sim(self,cooc,occ1,occ2):
        """
        Alternative for SOC edges
            => preserves monotony
            => + log scale (=> good for display !!)
        """
        return log1p(self.jaccard(cooc,
                                  occ1,occ2))

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

                # we use the sch_kw table (scholars <=> kw map)
                sql_query="""
                SELECT
                    neighbors_by_kw.uid,
                    scholars.initials,
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
                """ % unique_id

                self.cursor.execute(sql_query)
                results=self.cursor.fetchall()

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
                # mlog("DEBUG", "getScholarsList<==scholar_array", scholar_array)

            elif qtype == "filters":
                sql_query = None

                mlog("INFO", "filters: REST query is", filter_dict)

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

                    """ % (full_scholar_sql, " AND ".join(sql_constraints))

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
                info['initials'] = res3['initials'];
                info['doors_uid'] = res3['doors_uid'];
                info['pic_src'] = pic_src ;
                info['first_name'] = res3['first_name'];
                info['mid_initial'] = res3['middle_name'][0] if res3['middle_name'] else ""
                info['last_name'] = res3['last_name'];
                info['keywords_nb'] = res3['keywords_nb'];
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

        # constant for bipartite edge weights
        bipaW = 8
        # explanation:
        #  - same sides edge weights are of magnitude ~~ coocc / occ²
        #  - but bipart edge weights are of magnitude ~~     1 / occ²
        #  - used like this with a forceAtlas, the visual result of graphs
        #    will then always cluster nodes of each type together (stronger ties for same side edges)
        #  - used with the constant this effect is avoided (stronger ties for bipartite edges)

        mlog('DEBUG', 'extractDataCustom:'+" ".join([self.scholars[i]['initials'] for i in self.scholars]))

        for i in self.scholars:
            self.scholars_colors[self.scholars[i]['email'].strip()]=0;
            scholar_keywords = self.scholars[i]['keywords_ids'];
            for k in range(len(scholar_keywords)):
                kw_k = scholar_keywords[k]

                # TODO join keywords and count to do this part already via sql
                # mlog('DEBUG', 'extractDataCustom:keyword '+kw_k)

                if kw_k != None and kw_k!="":
                    # mlog("DEBUG", kw_k)
                    if kw_k in termsMatrix:
                        termsMatrix[kw_k]['occ'] = termsMatrix[kw_k]['occ'] + 1

                        for l in range(len(scholar_keywords)):
                            kw_l = scholar_keywords[l]
                            if kw_l in termsMatrix[kw_k]['cooc']:
                                termsMatrix[kw_k]['cooc'][kw_l] += 1
                            else:
                                termsMatrix[kw_k]['cooc'][kw_l] = 1;

                    else:
                        termsMatrix[kw_k]={}
                        termsMatrix[kw_k]['occ'] = 1;
                        termsMatrix[kw_k]['cooc'] = {};
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
            info['occurrences'] = res['occs']
            info['kwstr'] = res['kwstr']

            # job counter: how many times a term in cited in job ads
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
                if term_scholars[k] in scholarsMatrix:
                    scholarsMatrix[term_scholars[k]]['occ'] = scholarsMatrix[term_scholars[k]]['occ'] + 1
                    for l in range(len(term_scholars)):
                        if term_scholars[l] in self.scholars:
                            if term_scholars[l] in scholarsMatrix[term_scholars[k]]['cooc']:
                                scholarsMatrix[term_scholars[k]]['cooc'][term_scholars[l]] += 1
                            else:
                                scholarsMatrix[term_scholars[k]]['cooc'][term_scholars[l]] = 1;

                else:
                    scholarsMatrix[term_scholars[k]]={}
                    scholarsMatrix[term_scholars[k]]['occ'] = 1;
                    scholarsMatrix[term_scholars[k]]['cooc'] = {};

                    for l in range(len(term_scholars)):
                        if term_scholars[l] in self.scholars:
                            if term_scholars[l] in scholarsMatrix[term_scholars[k]]['cooc']:
                                scholarsMatrix[term_scholars[k]]['cooc'][term_scholars[l]] += 1
                            else:
                                scholarsMatrix[term_scholars[k]]['cooc'][term_scholars[l]] = 1;

                                # eg matrix entry for scholar k
                                # 'S::SK/04047': {'occ': 1, 'cooc': {'S::SL/02223': 1}}
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

                            # term--scholar weight: constant / log(1+total keywords of scholar)
                            weight = bipaW / log1p(scholarsMatrix[scholar]['occ'])
                            self.Graph.add_edge( source , target , {'weight':weight,'type':"bipartite"})

        for term in self.terms_dict:
            nodeId1 = self.terms_dict[term]['kwid'];
            if str(nodeId1) in termsMatrix:
                neighbors = termsMatrix[str(nodeId1)]['cooc'];
                for i, neigh in enumerate(neighbors):
                    if neigh != term:
                        source="K::"+term
                        target="K::"+neigh

                        # term--term weight: number of common scholars / (total occs of t1 x total occs of t2)
                        weight=neighbors[neigh]/(self.terms_dict[term]['occurrences'] * self.terms_dict[neigh]['occurrences'])

                        # detailed debug
                        # if neighbors[neigh] != 1:
                        #     mlog("DEBUG", "extractDataCustom.extract edges b/w terms====")
                        #     mlog("DEBUG", "term:", self.terms_dict[term]['kwstr'], "<===> neighb:", self.terms_dict[neigh]['kwstr'])
                        #     mlog("DEBUG", "kwoccs:", self.terms_dict[term]['occurrences'])
                        #     mlog("DEBUG", "neighbors[neigh]:", neighbors[neigh])
                        #     mlog("DEBUG", "edge w", weight)

                        self.Graph.add_edge( source , target , {'weight':weight,'type':"nodes2"})

        for scholar in self.scholars:
            nodeId1 = scholar;
            if str(nodeId1) in scholarsMatrix:

                # weighted list of other scholars
                neighbors=scholarsMatrix[str(nodeId1)]['cooc'];
                # eg {'S::KW/03291': 1, 'S::WTB/04144': 3}


                for i, neigh in enumerate(neighbors):
                    if neigh != str(scholar):
                        source=str(scholar)
                        target=str(neigh)
                        # scholar--scholar weight: number of common terms / (total keywords of scholar 1 x total keywords of scholar 2)
                        weight=self.jaccard(neighbors[str(neigh)],
                                                scholarsMatrix[nodeId1]['occ'],
                                                scholarsMatrix[neigh]['occ'])
                        #mlog("DEBUG", "\t"+source+","+target+" = "+str(weight))
                        self.Graph.add_edge( source , target , {'weight':weight,'type':"nodes1"})

        # ------- debug nodes1 -------------------------
        # print(">>>>>>>>>scholarsMatrix<<<<<<<<<")
        # print(scholarsMatrix)

        # exemple:
        # {'S::PFC/00002': {'occ': 6,
        #                   'cooc': {'S::PFC/00002': 6,
        #                            'S::fl/00009': 1,
        #                            'S::DC/00010': 1}
        #                   },
        #   'S::fl/00009': {'occ': 9,
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
                    node["attributes"]["normfactor"] = "%.5f" % (1/log1p(len(self.scholars[idNode]["keywords_ids"])))
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

#            mlog("DEBUG", "SCH","\t",idNode,"\t",nodeLabel)

                nodesA+=1

        GG = Graph()
        for n in self.Graph.edges_iter():
            s = n[0]
            t = n[1]
            w = float(self.Graph[n[0]][n[1]]['weight'])
            tp = self.Graph[n[0]][n[1]]['type']

            if GG.has_edge(s,t):
                oldw = GG[s][t]['weight']
                avgw = (oldw+w)/2      # TODO this avg faster but not indifferent to sequence
                GG[s][t]['weight'] = avgw
            else:
                GG.add_edge( s , t , { "weight":w , "type":tp } )

        e = 0
        for n in GG.edges_iter():#Memory, what's wrong with you?
            wr = 0.0
            origw = GG[n[0]][n[1]]['weight']
            for i in range(2,10):
                wr = round( origw , i)
                if wr > 0.0: break
            edge = {}
            edge["s"] = n[0]
            edge["t"] = n[1]
            edge["w"] = str(wr)
#        edge["type"] = GG[n[0]][n[1]]['type']
            if GG[n[0]][n[1]]['type']=="nodes1": edgesA+=1
            if GG[n[0]][n[1]]['type']=="nodes2": edgesB+=1
            if GG[n[0]][n[1]]['type']=="bipartite": edgesAB+=1

#        mlog("DEBUG", edge["type"],"\t",nodes[n[0]]["label"],"\t",nodes[n[1]]["label"],"\t",edge["w"])

#        if edge["type"]=="nodes1": mlog("DEBUG", wr)
            edges[str(e)] = edge
            e+=1
            #if e%1000 == 0:
            #    mlog("INFO", e)
#    for n in GG.nodes_iter():
#        if nodes[n]["type"]=="Keywords":
#            concepto = nodes[n]["label"]
#            nodes2 = []
#            neigh = GG.neighbors(n)
#            for i in neigh:
#                if nodes[i]["type"]=="Keywords":
#                    nodes2.append(nodes[i]["label"])
#            mlog("DEBUG", concepto,"\t",", ".join(nodes2))

        graph = {}
        graph["nodes"] = nodes
        graph["links"] = edges
        graph["stats"] = { "sch":nodesA,"kw":nodesB,"n11(soc)":edgesA,"n22(sem)":edgesB,"nXR(bi)":edgesAB ,  }
        graph["ID"] = self.unique_id

        mlog("INFO", graph["stats"])

        # mlog("DEBUG", "scholars",nodesA)
        # mlog("DEBUG", "concept_tags",nodesB)
        # mlog("DEBUG", "nodes1",edgesA)
        # mlog("DEBUG", "nodes2",edgesB)
        # mlog("DEBUG", "bipartite",edgesAB)
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
