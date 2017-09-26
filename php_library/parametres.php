<?php

/* liste de parametres */

$comex_user_id = '';
if (isset($_GET['user'])) {
  $comex_user_id = $_GET['user'];
}

$min_num_friends=0;// nombre minimal de voisin que doit avoir un scholar pour être affiché
// $compress='No';

/* reading external app params
   ===========================

   The params we want:
   - SQL_HOST
   - DOORS_HOST
   - DOORS_PORT
   - DOORS_NOSSL

    The values are by priority:
      1 - retrieved from bash ENV (set by docker-compose or admin)
      2 - otherwise retrieved from the INI file "config/parametres_comex.ini"
      3 - otherwise hard-coded defaults
*/

// we initialize with the defaults
$app_params = array(
  'SQL_HOST' =>  '172.17.0.2', // (first docker IP)
  'DOORS_HOST' => 'doors.iscpif.fr',
  'DOORS_PORT' => '443',
  'DOORS_NOSSL' => false
);

// prepare INI file read
$ini_params = parse_ini_file("config/parametres_comex.ini");

foreach ($app_params as $key => $param) {
  # 1 - ENV read
  if (getenv($key)) {
    $app_params[$key] = getenv($key);
  }
  # 2 - INI read
  elseif (array_key_exists($key, $ini_params)) {
    $app_params[$key] = $ini_params[$key];
  }
}

// echodump("finalized params", $app_params);

$dbglog = "<p>got sql_host={$app_params['SQL_HOST']}</p>";

/* initializing SQL connection
   ===========================
 */
# other sql vars never change
$db   = 'comex_shared';
$user = 'root';
$pass = 'very-safe-pass';
$charset = 'utf8';

/* final MySQL config: will be used for all php db connections */
$dsn = "mysql:host={$app_params['SQL_HOST']};dbname=$db;charset=$charset";
$opt = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
];


/* Common SQL fragment to select full scholars infos (with labs, orgs, kws..) */
// about the query stucture cf. doc/cascade_full_scholar_info.sql
$sql_full_scholar_select = <<< ENDSQL
SELECT
    scholars_orgs_and_keywords.*,
    GROUP_CONCAT(htstr) AS hashtags_list
FROM (
    SELECT
        scholars_and_orgs.*,
        GROUP_CONCAT(kwstr) AS keywords_list,
        GROUP_CONCAT(keywords.kwid) AS keywords_ids,
        COUNT(keywords.kwid) AS keywords_nb
    FROM (
        SELECT
            scholars_and_labs.*,
            GROUP_CONCAT(insts.orgid SEPARATOR ',') AS insts_ids,
            GROUP_CONCAT(insts.label SEPARATOR '%%%') AS insts_list

            FROM (
                SELECT
                    scholars.*,
                    GROUP_CONCAT(labs.orgid SEPARATOR ',') AS labs_ids,
                    GROUP_CONCAT(labs.label SEPARATOR '%%%') AS labs_list
                FROM scholars
            LEFT JOIN sch_org AS map_labs
                    ON map_labs.uid = luid
                LEFT JOIN (
                    SELECT * FROM orgs WHERE class='lab'
                ) AS labs
                    ON map_labs.orgid = labs.orgid
                WHERE (record_status = 'active'
                        OR (record_status = 'legacy' AND valid_date >= NOW()))
                GROUP BY luid
                ) AS scholars_and_labs
            LEFT JOIN sch_org AS map_insts
                ON map_insts.uid = luid
            LEFT JOIN (
                SELECT * FROM orgs WHERE class='inst'
            ) AS insts
                ON map_insts.orgid = insts.orgid

            GROUP BY luid
    ) AS scholars_and_orgs

    LEFT JOIN sch_kw
        ON sch_kw.uid = scholars_and_orgs.luid
    LEFT JOIN keywords
        ON sch_kw.kwid = keywords.kwid
    GROUP BY luid

) AS scholars_orgs_and_keywords
LEFT JOIN sch_ht
    ON sch_ht.uid = luid
LEFT JOIN hashtags
    ON sch_ht.htid = hashtags.htid
GROUP BY luid
ENDSQL;


?>
