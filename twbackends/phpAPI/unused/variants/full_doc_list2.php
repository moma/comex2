<?php
include('tools.php');
include('parameters_details.php');
$db = $gexf_db[$gexf];

$base = new PDO("sqlite:../" ."data/terrorism/data.db");

echo "sqlite:../" ."data/terrorism/data.db";
$output = "<ul>"; // string sent to the javascript for display
#http://localhost/branch_ademe/php/test.php?type=social&query=[%22marwah,%20m%22]


$type = $_GET["type"];
$query = str_replace( '__and__', '&', $_GET["query"] );
$terms_of_query=json_decode($_GET["query"]);
$elems = json_decode($query);

// nombre d'item dans les tables
$sql='SELECT COUNT(*) FROM ISIABSTRACT';
foreach ($base->query($sql) as $row) {
  $table_size=$row['COUNT(*)'];
}

$table = "";
$column = "";
$id="";

if($type=="social"){
  $table = "ISIAUTHOR";
  $column = "data";
  $id = "id";
  $restriction='';
  $factor=10;// factor for normalisation of stars
}

if($type=="semantic"){
  $table = "ISItermsListV1";
  $column = "data";
  $id = "id";
  $restriction='';
  $factor=10;
}


$sql = 'SELECT count(*),'.$id.'
FROM '.$table.' where (';
        foreach($elems as $elem){
                $sql.=' '.$column.'="'.$elem.'" OR ';
        }
#$querynotparsed=$sql;#####
        $sql = substr($sql, 0, -3);
        $sql = str_replace( ' & ', '" OR '.$column.'="', $sql );

        $sql.=')'.$restriction.'
GROUP BY '.$id.'
ORDER BY count('.$id.') DESC
LIMIT 1000';

#$queryparsed=$sql;#####

$wos_ids = array();
$sum=0;

//The final query!
// array of all relevant documents with score

foreach ($base->query($sql) as $row) {
        // on pondère le score par le nombre de termes mentionnés par l'article

        //$num_rows = $result->numRows();
        $wos_ids[$row[$id]] = $row["count(*)"];
        $sum = $row["count(*)"] +$sum;
}


//arsort($wos_ids);

$number_doc=ceil(count($wos_ids)/3);
$count=0;
foreach ($wos_ids as $id => $score) {
  if ($count<1000){
    // retrieve publication year
    $sql = 'SELECT data FROM ISIpubdate WHERE id='.$id;
    foreach ($base->query($sql) as $row) {
      $pubdate="2014";
    }

    // to filter under some conditions
    $to_display=true;
    if ($to_display){
      $count+=1;
      $output.="<li title='".$score."'>";
      $output.=imagestar($score,$factor,$our_libs_root).' ';
      $sql = 'SELECT data FROM ISITITLE WHERE id='.$id." group by data";

      foreach ($base->query($sql) as $row) {
         $output.='<a href="'.$our_php_root.'/default_doc_details2.php?gexf='.urlencode($gexf).'&type='.urlencode($_GET["type"]).'&query='.urlencode($query).'&id='.$id.'">'.$row['data']." </a> ";

                        //this should be the command:
      //$output.='<a href="JavaScript:newPopup(\''.$our_php_root.'/default_doc_details.php?db='.urlencode($datadb).'&id='.$id.'  \')">'.$row['data']." </a> ";

                        //the old one:
      //$output.='<a href="JavaScript:newPopup(\''.$our_php_root.'/default_doc_details.php?id='.$id.'  \')">'.$row['data']." </a> ";
        $external_link="<a href=http://scholar.google.com/scholar?q=".urlencode('"'.$row['data'].'"')." target=blank>".' <img width=20px src="'.$our_libs_root.'/img/gs.png"></a>';
      }

  // get the authors
      $sql = 'SELECT data FROM ISIAUTHOR WHERE id='.$id;
      foreach ($base->query($sql) as $row) {
        $output.=strtoupper($row['data']).', ';
      }

  //<a href="JavaScript:newPopup('http://www.quackit.com/html/html_help.cfm');">Open a popup window</a>'

      $output.=$external_link."</li><br>";
    }

  }else{
    continue;
  }
}

$output= '<h3>'.$count.' items related to: '.implode(' OR ', $elems).'</h3>'.$output;



echo $output;

?>
