<?php

/*
 * A place to factorize the injected JS
 * TODO use more eg for charts
 */


// to autoselect current whoswho filters
// NB: uses global value $data
// $auto_popfilters_snippet = '<script type="text/javascript">' ;
// if (isset($data) && $data) {
//     foreach ($data as $filter => $array_vals) {
//         foreach ($array_vals as $val) {
//             $auto_popfilters_snippet .= '
//             whoswho.popfilter("'.$filter.'", {"prefill":"'.$val.'"});
//             ';
//         }
//     }
// }
// $auto_popfilters_snippet .= '</script>';


// exemple snippet this one is to use in html context
$rm_ads_snippet = <<< ENDHTML
<script type="text/javascript">
  document.addEventListener("DOMContentLoaded", function(event) {
      setTimeout( function() {
          var ads = document.getElementsByClassName("highcharts-credits")
          for (var ad of ads) {
              ad.style.WebkitTransition = 'opacity 1s';
              ad.style.MozTransition = 'opacity 1s';
              ad.style.opacity = 0;
              setTimeout (function() {
                  ad.innerHTML = ""
              }, 1000)
          }
      }, 5000)
  })
</script>
ENDHTML;



function tagcloud_snippet($sorted_key_val_array) {
  return '
  <script type="text/javascript">
    // for the tagcloud (inspired by ProjectExplorer:methods.htmlProportionalLabels)
    function writeHtmlProportionalLabels(elems, tgtDivId) {
        let tgtDiv = document.getElementById(tgtDivId)
        if (! tgtDiv) {
          console.error ("can\'t find div: "+tgtDivId)
          return
        }

        let resHtmlArr=[]
        let resHtml=""
        if(elems.length==0) {
          resHtml = "No related items."
        }
        else {
          let limit = 50

          let tagcloudFontsizeMin = .7
          let tagcloudFontsizeMax = 2.5

          let fontSize   // <-- normalized for display

          // we assume already sorted
          let frecMax = elems[0].value
          let frecMin = elems.slice(-1)[0].value

          let sourceRange = frecMax - frecMin
          let targetRange = tagcloudFontsizeMax - tagcloudFontsizeMin

          for(var i in elems){
              if(i==limit)
                  break
              let kwstr=elems[i].key
              let frec=elems[i].value

              if (sourceRange) {
                fontSize = ((frec - frecMin) * (targetRange) / (sourceRange)) + tagcloudFontsizeMin
                fontSize = parseInt(1000 * fontSize) / 1000
              }
              else {
                // 1em when all elements have the same freq
                fontSize = 1
              }

              // debug
              // console.log("php htmlfied_tagcloud (",kwstr,") freq",frec," fontSize", fontSize)

              // using em instead of px to allow global x% resize at css box level
              let htmlLabel = "<span class=\"tagcloud-item\" style=\"font-size:"+fontSize+"em;\" title=\""+kwstr+" ("+frec+")"+"\">"+ kwstr + "</span>";
              resHtmlArr.push(htmlLabel)
          }
          resHtml = resHtmlArr.join("\n")
        }

        tgtDiv.innerHTML = resHtml
    }

    let kwCounts = '. json_encode($sorted_key_val_array) .'

    // writes directly to the div
    writeHtmlProportionalLabels(kwCounts, "kw_tagcloud_div")
  </script>
  ';
}

?>
