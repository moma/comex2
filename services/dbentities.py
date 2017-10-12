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

if __package__ == 'services':
    from services.dbcrud  import FULL_SCHOLAR_SQL
else:
    from dbcrud           import FULL_SCHOLAR_SQL



class DBEntity:
    def init(self, entityName):
        pass

    def toPivot(self):
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

        TODO add a 4th column "content" with html for information div
        POSS add a 5th column "attributes" with json for coloring
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
    def toPivot(self):
        return """
        SELECT uid AS pivotID, orgs.orgid AS entityID
        FROM sch_org
        LEFT JOIN orgs
            ON orgs.orgid = sch_org.orgid
        WHERE orgs.class = "lab" AND orgs.name != "_NULL"
        """

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
    def toPivot(self):
        return """
        SELECT uid AS pivotID, orgs.orgid AS entityID
        FROM sch_org
        LEFT JOIN orgs
            ON orgs.orgid = sch_org.orgid
        WHERE orgs.class = "inst"
        """

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
    def toPivot(self):
        return "SELECT uid AS pivotID, kwid AS entityID FROM sch_kw"

    def getInfos(self):
        return """
                SELECT keywords.kwid AS entityID,
                       keywords.kwstr AS label,
                       keywords.occs AS nodeweight,
                       nbjobs
                FROM keywords
                LEFT JOIN (
                    SELECT kwid, count(kwid) AS nbjobs
                    FROM job_kw
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
            'total_occurrences': nd['nodeweight'],
            'nbjobs':            nd['nbjobs']
          }
        }

class DBHashtags(DBEntity):
    """
    hashtags from hashtags table
    """
    def toPivot(self):
        return "SELECT uid AS pivotID, htid AS entityID FROM sch_ht"

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
    def toPivot(self):
        return "SELECT luid AS pivotID, country AS entityID FROM scholars"

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

    def toPivot(self):
        return "SELECT luid AS pivotID, luid AS entityID FROM scholars"

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
        content += '<p class=bigger><b>'+nd['label']+'</b></p>'

        # other infos in vcard
        content += '<p>'
        content += '<b>Country: </b>' + nd['country'] + '</br>'

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
          'content': self.toHTML(content),
          'attributes': {
            'country':   nd['country'] if nd['country'] else "-",
            'ACR':   nd['org'] if nd['org'] else "-",
          }
        }


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
