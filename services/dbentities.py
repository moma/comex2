"""
DB data relationships
"""
__author__    = "CNRS"
__copyright__ = "Copyright 2017 ISCPIF-CNRS"
__email__     = "romain.loth@iscpif.fr"

from math      import log1p, floor
from random    import randint
from json      import loads
from cgi       import escape
from re        import sub

if __package__ == 'services':
    from services.dbcrud  import FULL_SCHOLAR_SQL
else:
    from dbcrud           import FULL_SCHOLAR_SQL



class DBEntity:
    def init(self, entityName):
        pass

    def toPivot(self, pivotType):
        """
        SQL to get the list of DBEntities with their association to a pivotID

        Result must provide a pivotID column and an entityID column for further JOIN-ing.

        pivotID can also be used to JOIN the pivot table and use it for filters
        """
        pass

    def getInfos(self):
        """
        SQL to get detailed node's information (JOIN with match query or any list of EntityIDs)

        NB: the SQL is often similar to toPivot but grouped by entityID
            (same difference as list of edges vs list of nodes...)

        Result must provide 3 cols:
          - entityID
          - label
          - nodeweight

         Any other columns also possible:
            - cf. formatNode which takes these fields and creates node attributes and content
           - columns for an "attributes" subdict, for coloring etc.
           - columns to use in a "content" property (html str for sidepanel info)
        """
        pass

    def formatNode(self, nd, ntype):
        """
        Create a dict with node properties, ready to be exported to JSON

        The implementation below is a simple example overridden by each DBEntity

        Input nd is the SQL row fetched with cursorDict or any equivalent dict.
        """
        return {
          'label': nd['label'],
          'type': ntype,
          'size': round(log1p(nd['nodeweight']), 3) if ntype != 'sch' else 2,
          'color': '243,183,19' if ntype in ['kw', 'ht'] else '139,28,28'
        }


class DBLabs(DBEntity):
    """
    organizations from orgs table, of the "lab" class
    """
    def toPivot(self, pivotType):
        sqlq = None
        if pivotType == 'scholars':
            sqlq = """
            SELECT uid AS pivotID, orgs.orgid AS entityID
            FROM sch_org
            LEFT JOIN orgs
                ON orgs.orgid = sch_org.orgid
            WHERE orgs.class = "lab" AND orgs.name != "_NULL"
            """
        else:
            raise TypeError("the DBLabs entity is only related to scholars pivot in our DB structure.")
        return sqlq

    def getInfos(self):
        return """
        SELECT orgs.orgid AS entityID, orgs.label AS label,
               count(sch_org.uid) AS nodeweight,
               acro, lab_code, locname, url
        FROM orgs
        LEFT JOIN sch_org
            ON orgs.orgid = sch_org.orgid
        WHERE orgs.class = "lab"
        GROUP BY orgs.orgid
        """

    def formatNode(self, nd, ntype):
        return {
          'label': nd['acro'] if nd['acro'] else nd['label'],
          'type': ntype,
          'size': round(log1p(log1p(nd['nodeweight'])), 3),
          'color': '76,161,216',
          'content': '<div class=information-others><p>%s %s</p></div>' % (
            nd['label'],
            nd['lab_code'] if nd['lab_code'] else ''
          ),
          'attributes': {
            'url':      nd['url'],
            'locname':  nd['locname'],
            'lab_code': nd['lab_code']
          }
        }


class DBInsts(DBEntity):
    """
    organizations from orgs table, of the "institution" class
    """
    def toPivot(self, pivotType):
        sqlq = None
        if pivotType == 'scholars':
            sqlq = """
            SELECT uid AS pivotID, orgs.orgid AS entityID
            FROM sch_org
            LEFT JOIN orgs
                ON orgs.orgid = sch_org.orgid
            WHERE orgs.class = "inst"
            """
        else:
            raise TypeError("the DBInsts entity is only related to scholars pivot in our DB structure.")
        return sqlq

    def getInfos(self):
        return """
        SELECT orgs.orgid AS entityID,
               orgs.label AS label,
               count(sch_org.uid) AS nodeweight,
               inst_type, locname, url
        FROM orgs
        LEFT JOIN sch_org
            ON orgs.orgid = sch_org.orgid
        WHERE orgs.class = "inst"
        GROUP BY orgs.orgid
        """

    def formatNode(self, nd, ntype):
        return {
          'label': nd['label'],
          'type': ntype,
          'size': round(log1p(log1p(nd['nodeweight'])), 3),
          'color': '174,216,76',
          'attributes': {
            'inst_type': nd['inst_type'],
            'url':       nd['url'],
            'locname':   nd['locname']
          }
        }

class DBKeywords(DBEntity):
    """
    keywords from keywords table
    """
    def toPivot(self, pivotType = "scholars"):
        # normal multimatch case
        if pivotType == "scholars":
            return "SELECT uid AS pivotID, kwid AS entityID FROM sch_kw"

        # when keywords are themselves the pivot
        elif pivotType == "keywords":
            return "SELECT kwid AS pivotID, kwid AS entityID FROM keywords"


    def getInfos(self):
        """
        We add one to nodeweight like a Laplace smoothing for the case
        when job adds reference a new keyword that would have 0 occurrences.
        """
        return """
                SELECT keywords.kwid AS entityID,
                       keywords.kwstr AS label,
                       keywords.occs + 1 AS nodeweight,
                       nbjobs
                FROM keywords
                LEFT JOIN (
                    SELECT job_kw.kwid, count(job_kw.jobid) AS nbjobs
                    FROM job_kw
                     LEFT JOIN jobs
                        ON jobs.jobid = job_kw.jobid
                     WHERE jobs.job_valid_date >= CURDATE()
                    GROUP BY kwid
                ) AS jobcounts ON jobcounts.kwid = keywords.kwid
                """

    def formatNode(self, nd, ntype):
        return {
          'label': nd['label'],
          'type': ntype,
          'size': round(log1p(nd['nodeweight']), 3),
          'color': '200,20,19',
          'attributes': {
             # we add 1 for keywords in jobs but with no occs among scholars
            'total_occurrences': nd['nodeweight'],
            'nbjobs':            nd['nbjobs']
          }
        }

class DBHashtags(DBEntity):
    """
    hashtags from hashtags table
    """
    def toPivot(self, pivotType):
        sqlq = None
        if pivotType == 'scholars':
            sqlq = "SELECT uid AS pivotID, htid AS entityID FROM sch_ht"
        else:
            raise TypeError("the DBHashtags entity is only related to scholars pivot in our DB structure.")
        return sqlq

    def getInfos(self):
        return """
                SELECT hashtags.htid AS entityID,
                      hashtags.htstr AS label,
                      count(sch_ht.uid) AS nodeweight
                FROM hashtags
                LEFT JOIN sch_ht ON sch_ht.htid = hashtags.htid
                GROUP BY hashtags.htid
               """

    def formatNode(self, nd, ntype):
        return {
          'label': nd['label'],
          'type': ntype,
          'size': round(log1p(nd['nodeweight']), 3),
          'color': '255,20,19'
        }


class DBCountries(DBEntity):
    """
    countries from scholars table
    """
    def toPivot(self, pivotType):
        sqlq = None
        if pivotType == 'scholars':
            sqlq = "SELECT luid AS pivotID, country AS entityID FROM scholars"
        else:
            raise TypeError("the DBCountry entity only implements relation with scholars as pivot.")
        return sqlq

    def getInfos(self):
        return "SELECT country AS entityID, country AS label, count(luid) AS nodeweight FROM scholars GROUP BY country"

    def formatNode(self, nd, ntype):
        return {
          'label': nd['label'],
          'type': ntype,
          'size': round(log1p(log1p(nd['nodeweight'])), 3),
           'color': '255,255,255',
           'attributes': {
              'country': nd['label']
            }
        }


class DBScholars(DBEntity):
    """
    scholars from scholars table
    """

    def toPivot(self, pivotType):
        sqlq = None
        if pivotType == 'scholars':
            sqlq = "SELECT luid AS pivotID, luid AS entityID FROM scholars"
        elif pivotType == 'keywords':
            sqlq = "SELECT kwid AS pivotID, uid AS entityID FROM sch_kw"
        else:
            raise TypeError("the DBScholars entity only implements relation with itself or keywords as pivots.")

        return sqlq

    def getInfos(self):
        """
        full_scholar
        """
        return """
            SELECT luid AS entityID,
                   CONCAT_WS(' ',
                          hon_title,
                          first_name,
                          middle_name,
                          last_name
                    ) AS label,
                    1 AS nodeweight,
                    full_scholar.*
             FROM (
                %s
            ) AS full_scholar
            """ % FULL_SCHOLAR_SQL

    @classmethod
    def toHTML(self,string):
        escaped = escape(string).encode("ascii", "xmlcharrefreplace").decode()
        return escaped

    def formatNode(self, nd, ntype):
        # pic size setting
        imsize = 80

        # color prepare
        color = '139,28,28'
        if nd['job_looking']:
            color = '43,44,141'
        elif nd['nb_proposed_jobs'] > 0:
            color = '41,189,243'


        # pic source
        if 'pic_fname' in nd and nd['pic_fname']:
            pic_src = '/data/shared_user_img/'+nd['pic_fname']
        elif 'pic_url' in nd and nd['pic_url']:
            pic_src = nd['pic_url']
        else:
            pic_src = ''

        # lab and insts prepare
        # NB instead of secondary query for orgs.*, we can
        # simply parse orgs infos
        # and take labs[0] and insts[0]
        labs  = list(map(
                lambda arr: Org(arr, org_class='lab'),
                loads('['+nd['labs_list'] +']')
        ))
        insts = list(map(
                lambda arr: Org(arr, org_class='insts'),
                loads('['+nd['insts_list']+']')
        ))
        nd['team_lab'] = labs[0].label;
        nd['org'] = insts[0].label;
        nd['ACR'] = labs[0].acro if labs[0].acro else labs[0].any

        if len(labs) > 1:
            nd['lab2'] = labs[1].label
        if len(insts) > 1:
            nd['affiliation2'] = insts[1].label

        nd['job_ids'] = nd['job_ids'].split(',') if nd['job_ids'] else [];
        nd['job_titles'] = loads('['+nd['job_titles']+']') if nd['job_titles'] else [];


        # HTML additional content
        content="<div class='information-vcard'>"

        # pic in vcard
        if pic_src and pic_src != "":
            content += '<img  src="'+pic_src+'" width=' + str(imsize) + 'px>';
        else:
            im_id = int(floor(randint(0, 11)))
            content += '<img src="static/img/'+str(im_id)+'.png" width='  + str(imsize) +  'px>'

        # label in vcard
        content += '<p class=bigger><b>'+str(nd['label'])+'</b></p>'

        # other infos in vcard
        content += '<p>'
        content += '<b>Country: </b>' + str(nd['country']) + '</br>'

        if nd['position'] and nd['position'] != "":
            content += '<b>Position: </b>' +nd['position'].replace("&"," and ")+ '</br>'

        affiliation=""
        if nd['team_lab'] and nd['team_lab'] not in ["", "_NULL"]:
            affiliation += nd['team_lab']+ ','
        if nd['org'] and nd['org'] != "":
            affiliation += nd['org']

        if affiliation != "":
            content += '<b>Affiliation: </b>' + escape(affiliation) + '</br>'

        if len(nd['keywords_list']) > 3:
            content += '<b>Keywords: </b>' + nd['keywords_list'].replace(",",", ")+'.</br>'

        if nd['home_url']:
            if nd['home_url'][0:3] == "www":
                content += '[ <a href=http://' +nd['home_url'].replace("&"," and ")+ ' target=blank > View homepage </a ><br/>]'
            elif nd['home_url'][0:4] == "http":
                content += '[ <a href=' +nd['home_url'].replace("&"," and ")+ ' target=blank > View homepage </a >]<br/>'


        content += '</p>'

        # also add pointers to jobs
        if nd['nb_proposed_jobs'] > 0:
            # mlog("DEBUG", "adding jobs for", idNode, "nb_proposed_jobs", nd['nb_proposed_jobs'])
            content += """
                <hr>
                <div class=information-others>
                <h5> Related jobs </h5>
                <ul class=infoitems>
                """
            for j, jobid in enumerate(nd['job_ids']):
                content += "<li>"
                content += "<a href=\"/services/job/"+jobid+"\" target=\"_blank\">"+ nd['job_titles'][j]
                content += "</a></li>"
            content += '</ul></div>'

        content += '</div>'

        return {
          'label': nd['label'],
          'type': ntype,
          'size': 2,
          'color': color,
          'content': DBScholars.toHTML(content),
          'attributes': {
            'country':   nd['country'] if nd['country'] else "-",
            'ACR':   nd['org'] if nd['org'] else "-",
          }
        }


class DBJobs(DBEntity):
    """
    The only use case at this point is as container of helper functions for DBScholarsAndJobs
    """
    def getInfos(self):
        return """
        SELECT
            jobs.jobid AS entityID,
            CONCAT(jobs.jobid, "-", IFNULL(jobs.jtitle, "")) AS label,

            1 AS nodeweight,
            jobs.*,
            GROUP_CONCAT(keywords.kwstr) AS keywords_list,
            COUNT(keywords.kwid) AS keywords_nb
        FROM jobs
        LEFT JOIN job_kw
            ON job_kw.jobid = jobs.jobid
        LEFT JOIN keywords
            ON job_kw.kwid = keywords.kwid
        GROUP BY jobs.jobid
        """

    def formatNode(self, nd, ntype):
        title = nd['jtitle'] if nd['jtitle'] else "(no title)"

        # sidebar content
        content = "<div class=information-vcard>"

        content += "<h4>Job: "+title+"</h4>"


        # prepare keywords
        kws_html =  ''
        for kw in nd['keywords_list'].split(','):
            kws_html += '<div class="box-highlight minibox">'+kw+'</div>'

        # 1) list of meta infos
        content += "<p><b>Keywords:</b> "+kws_html+"</p>"
        content += "<p><b>Posted on:</b> "+nd['last_modified'].strftime("%d/%m/%y")+"</p>"
        if nd['job_valid_date']:
            content += "<p><b>Valid until:</b> "+nd['job_valid_date'].strftime("%d/%m/%y")+"</p>"

        content += "<p class=red><b>Contact:</b> "+nd['email']+"</p>"

        # 2) overview (like a v-card of the job)
        full_location = []
        if nd['locname']:
            full_location.append(nd['locname'])

        if nd['country']:
            full_location.append(nd['country'])
        content += "<p><b>Location</b><br>"+",".join(full_location)+"</p>"

        if nd['mission_text']:
            content += "<p><b>Mission</b><br>"+sub('\n', '<br>', nd['mission_text'])+"</p>"
        if nd['recruiter_org_text'] and len(nd['recruiter_org_text']):
            content += "<p><b>Organization</b><br>"+sub('\n', '<br>', nd['recruiter_org_text'])+"</p>"

        # link to original
        content += "<a href=\"/services/job/"+str(nd['jobid'])+"\" target=\"_blank\">See the full job ("+ title +")</a>"

        content += '</div>'



        return {
          'label': nd['label'],
          'type': ntype,
          'size': 3,
           'color': '136,42,164',                      # violet,
           'content': DBScholars.toHTML(content),      # link
           'attributes': {
            }
        }


class DBScholarsAndJobs(DBEntity):
    """
    Job-looking scholars and jobs as one entity with pivot == keywords
                                                     -----------------

    (allows simplified job-candidate matchmaking via their common keywords)

    cf board.iscpif.fr/project/22/task/334
    """
    def toPivot(self, pivotType = 'keywords'):
        if pivotType != 'keywords':
            raise NotImplementedError
        else:
            return """
            SELECT * FROM (
                (SELECT
                    job_kw.jobid AS entityID,
                    job_kw.kwid AS pivotID,
                    'job' AS subtype
                 FROM job_kw
                 LEFT JOIN jobs
                    ON jobs.jobid = job_kw.jobid
                 WHERE jobs.job_valid_date >= CURDATE()
                 )
                UNION
                (SELECT
                    uid AS entityID,
                    kwid AS pivotID,
                    'sch' AS subtype
                 FROM sch_kw
                 LEFT JOIN scholars
                    ON sch_kw.uid = scholars.luid
                 WHERE scholars.job_looking = TRUE
                  AND (
                        scholars.job_looking_date IS NULL
                     OR
                        scholars.job_looking_date >= CURDATE()
                      )
                  AND (
                        record_status = 'active'
                      OR
                        (record_status = 'legacy' AND valid_date >= NOW())
                      )
                 )
             ) AS jobs_and_candidates
            """

    def getInfos(self, subtype="sch"):
        """
        Special case: 2 x getInfos respectively of jobs     (custom)
                                               and scholars (inherited)

        => to distinguish their properties will get a subtype-specific prefix
             ex  2 cols "sch_infos.country" and "job_infos.country"
        """
        if subtype == "sch":
            return DBScholars.getInfos(self)
        elif subtype == "job":
            return DBJobs.getInfos(self)

    def formatNode(self, nd, ntype):
        # remove subquery prefix from property names
        if nd['subtype'] == "sch":
            ok_ns='sch_infos.'
            ko_ns='job_infos.'
        elif nd['subtype'] == "job":
            ok_ns='job_infos.'
            ko_ns='sch_infos.'
        else:
            raise Exception("wrong subtype:", nd['subtype'])
        strlen_ok_ns = len(ok_ns)
        strlen_ko_ns = len(ko_ns)

        # "sch_infos.label" => "label", etc
        clean_ndata = {}
        for key in nd:
            # shorten relevent ones
            if key[0:strlen_ok_ns] == ok_ns:
                clean_key = key[strlen_ok_ns:]
                clean_ndata[clean_key] = nd[key]
            elif key[0:strlen_ko_ns] == ko_ns:
                continue
            # we copy the rest without overwrite
            # (some keys like 'country', 'label' can belong to theother subtype)
            elif key not in clean_ndata:
                clean_ndata[key] = nd[key]

        nd = clean_ndata

        # forward to parent function
        if nd['subtype'] == "sch":
            return DBScholars.formatNode(self, clean_ndata, ntype)
        elif nd['subtype'] == "job":
            return DBJobs.formatNode(self, clean_ndata, ntype)


class Org:
    " tiny helper class to serialize/deserialize orgs"

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
