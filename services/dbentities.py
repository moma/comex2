"""
DB data relationships
"""
__author__    = "CNRS"
__copyright__ = "Copyright 2017 ISCPIF-CNRS"
__email__     = "romain.loth@iscpif.fr"

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
               count(sch_org.uid) AS nodeweight
        FROM orgs
        LEFT JOIN sch_org
            ON orgs.orgid = sch_org.orgid
        WHERE orgs.class = "lab"
        GROUP BY orgs.orgid
        """

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
               count(sch_org.uid) AS nodeweight
        FROM orgs
        LEFT JOIN sch_org
            ON orgs.orgid = sch_org.orgid
        WHERE orgs.class = "inst"
        GROUP BY orgs.orgid
        """

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
                      count(sch_kw.uid) AS nodeweight
                FROM keywords
                LEFT JOIN sch_kw ON sch_kw.kwid = keywords.kwid
                GROUP BY keywords.kwid
                """

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

class DBCountries(DBEntity):
    """
    countries from scholars table
    """
    def toPivot(self):
        return "SELECT luid AS pivotID, country AS entityID FROM scholars"

    def getInfos(self):
        return "SELECT country AS entityID, country AS label, count(luid) AS nodeweight FROM scholars GROUP BY country"

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
