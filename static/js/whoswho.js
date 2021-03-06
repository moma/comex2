// Generated by CoffeeScript 1.3.1
var completion, gexf, ids;
// module fragment to expose selected functions
var whoswho = {};

// create or retrieve a tab id
if (!sessionStorage.tabid) {
  sessionStorage.tabid = ""+parseInt(performance.now()*1000)
}

ids = 0;

completion = {};

gexf = "";

whoswho = (function(ww) {

    // selected types
    ww.nodetypes = ["kw", "sch"]
    ww.allowedTypes = {
      "kw": "Keywords",
      "ht": "Community tags",
      "sch": "Scholars",
      "lab": "Labs",
      "inst": "Orgs",
      "country": "Countries"
    }

    ww.select = function(typeId, opt) {
      let itype = parseInt(typeId)
      if (isNaN(itype) || itype < 0 || itype > whoswho.nodetypes.length - 1) {
        console.warn("ww.select: incorrect typeId", typeId)
        return
      }

      if (! (opt in whoswho.allowedTypes)) {
        console.warn("ww.select: incorrect optval", opt)
        return
      }
      else {
        // store into our main var
        ww.nodetypes[itype] = opt

        // display label in html
        let label = whoswho.allowedTypes[opt]
        let ntButton = document.getElementById("selected-node"+itype)
        if (ntButton) {
          ntButton.innerHTML = label + '<i class="caret"></i>'
        }
      }
    }

    // filter type => label
    ww.filters = {
        'countries': "in",
        'institutions': "from",
        'laboratories': "working at",
        'keywords': "working on",
        'tags': "tagged"
    }

    // autocomplete
    ww.popfilter = function(type, options) {
        var label, footer, header, id, id1, id2, input, closebox, labelization;

        if (!options) {
            options = {}
        }

        if (! options.prefill) {
            options['prefill']=''
        }

        label = ww.filters[type];
        id = ids++;
        id1 = "filter" + id;
        id2 = "combo" + id;
        id3 = "close" + id;
        header = "<li id=\"" + id1 + "\" class=\"comex-nav-item filter\" style=\"padding-top: 5px;\">";
        labelization = "<span style=\"color: #fff;\">&nbsp; " + label + " </span>";
        input = "<input type=\"text\" id=\"" + id2 + "\" class=\"medium filter" + type + "\" placeholder=\"" + type + "\" / value=\""+options['prefill']+"\">";
        closebox = "<div id=\""+id3+"\" for=\""+id1+"\" class=\"filter-close operation-light\">x</div>"
        footer = "</li>;";
        $(header + labelization + input + closebox + footer).insertBefore("#refine");
        $('#' + id3).click(whoswho.closeThisBox)

        // debug
        // console.log("whoswho.popfilter: adding autocomplete menu", $("#" + id1))

        $("#" + id2).autocomplete({
            source: function (req, resp) {
                $.ajax({
                    dataType: "json",
                    type: "GET",
                    // url: "/search_filter.php",
                    url: "/services/api/aggs",
                    data: {
                        "field": type,
                        "like": req.term,
                    },
                    success: function(data){
                        resp(data.map(function(info) {
                            return {
                                'label': info.x,
                                'score': info.n
                            }
                        }))
                    },
                    error: function(response) {
                        console.log("ERROR from search_filter AJAX", response)
                    }
                }) ;
            },
            minLength: 2
        })

        $("" + id1).hide();
        $("#" + id1).show();
        $("#" + id2).focus();
        whoswho.shiftPage()
        return false;
    };

    // small filter closing function
    ww.closeThisBox = function() {
      var targetId = this.getAttribute("for")
      if (targetId) {
          var tgtBox = document.getElementById(targetId)
          // start transition
          tgtBox.style.opacity = 0
          // remove box
          setTimeout(function(){
            tgtBox.remove(); whoswho.shiftPage();
            // re-collect filters to update cache
            whoswho.collectFilters()
          }, 500)

          return true
      }
      else {
          console.warn('closeThisBox: no @for attribute!')
          return false
      }
    }

    // call it to adjust page position if topbar becomes thick
    ww.shiftPage = function() {
      // console.log("SHIFT PAGE")
      var topbar = document.getElementsByClassName('topbar')[0]
      var page = document.getElementsByClassName('page')[0]
      if (!page) {
          page = document.getElementsByClassName('full-directory')[0]
      }
      if (topbar && page) {
          var topContainer = topbar.querySelector('.container-fluid')
          if (topContainer && topContainer.offsetHeight) {
              page.style.marginTop = topContainer.offsetHeight
          }
      }
    }

    // main form collect function
    ww.collectFilters = function(cb) {
      var collect, query;
      collect = function(k) {
        var t;
        t = [];
        // console.log("collecting .filter:" + k);
        $(".filter" + k).each(function(i, e) {
          var value;

          // debug
          // console.log('collecting (filter '+k+') from elt:' + e)

          value = $(e).val();
          if (value != null && value != "") {
            // console.log("got: " + value);
            value = $.trim(value);
            // console.log("sanitized: " + value);
            if (value !== " " || value !== "") {
              // console.log("keeping " + value);
              return t.push(value);
            }
          }
        });
        return t;
      };
      // console.log("reading filters forms..");

      // for multimatch
      query = {
        '_node0': whoswho.nodetypes[0],
        '_node1': whoswho.nodetypes[1]
      }
      // POSS in the future coloredby
      // query.coloredby =  []

      let nFilters = 0
      for (filterName of ["keywords", "countries", "laboratories", "tags", "institutions"]) {
          var filterValuesArray = collect(filterName)

          // we add only if something to add
          if (filterValuesArray.length) {
              query[filterName] = filterValuesArray
              nFilters ++
          }
      }

      // cache
      sessionStorage.setItem("whoswhoq-"+sessionStorage.tabid, JSON.stringify(query))

      if (cb && typeof cb == "function") {
        // debug
        // console.log("calling callback with query:", query)
        return cb(query, nFilters);
      }
      else {
        return query
      }

    };

    return ww;
})(whoswho);

$(document).ready(function() {
  var closeBox, loadGraph;
  console.log("document ready.. installing whoswho");
  loadGraph = function(g) {
    gexf = g;
    console.log("url query: " + g);
    console.log("injecting applet");
    if ($('#frame').length === 0) {
      return $("#visualization").html("<iframe src=\"tinaframe.html" + (location.search != null ? location.search : '') + "\" class=\"frame\" border=\"0\" frameborder=\"0\" scrolling=\"no\" id=\"frame\" name=\"frame\"></iframe>");
    } else {
      return console.log("applet already exists");
    }
  };

  $(".topbar").hover((function() {
    return $(this).stop().animate({
      opacity: 0.98
    }, "fast");
  }), function() {
    return $(this).stop().animate({
      opacity: 0.93
    }, "fast");
  });

  $("#addfiltercountry").click(function() {
    return whoswho.popfilter("countries");
  });
  // $("#addfilterorganization").click(function() {
  //   return whoswho.popfilter("organizations");
  // });
  $("#addfilterinstitution").click(function() {
    return whoswho.popfilter("institutions");
  });
  $("#addfilterlaboratory").click(function() {
    return whoswho.popfilter("laboratories");
  });
  $("#addfilterkeyword").click(function() {
    return whoswho.popfilter("keywords");
  });
  $("#addfiltertag").click(function() {
    return whoswho.popfilter("tags");
  });
  $("#register").click(function() {
    return window.open("/services/user/register/");
  });

  $("#searchname").autocomplete({
    source: function (req, resp) {
        $.ajax({
            dataType: "json",
            type: "GET",
            url: "/search_scholar.php",
            data: {
                "category": "login",
                "login": req.term,
                // TODO rename s/login/uid/ in search_scholar.php
            },
            success: function(data){
                var compList = [] ;
                if (data.results) {
                    for (var i in data.results) {
                        var item = data.results[i]
                        compList.push({
                            // TODO middle initials here and in search_scholar
                            'label': item.firstname + ' ' + item.lastname,
                            'id': item.id
                        })
                    }
                }
                resp(compList)
            },
            error: function(response) {
                console.log("ERROR from search_scholar AJAX", response)
            }
        }) ;
    },
    minLength: 2,
    select: function(event, ui) {
      if (ui.item != null) {
        console.log("Selected: " + ui.item.label + " aka " + ui.item.id);

        // NB #searchname's value <= ui.label
        //     (by default widget behavior)

        // change the 2 onclick events
        changeTargetId(ui.item.id)
      }
    }
  })

  changeTargetId = function(nodeId) {
      document.getElementById('print2').onclick = function() {
        if (uinfo && uinfo.luid) {
          window.location = "/print_scholar_directory.php?query=" + nodeId + "&user="+uinfo.luid;
        }
        else {
          window.location = "/print_scholar_directory.php?query=" + nodeId;
        }
      }
      document.getElementById('generate2').onclick = function() {
        // POSS add user in url params and find a way to load and call cmxClt.elts.topbar.create
        window.location = '/explorerjs.html?sourcemode="api"&type="uid"&srcparams="' + nodeId + '"';
      }
  }


  // refine filters => tinawebjs graphexplorer
  $("#generate").click(function() {
    // console.log("clicked on generate")
    // console.log("initiating graphexplorer")
    return whoswho.collectFilters(function(query, nFilters) {
      // debug
      // console.log("collected filters: " + decodeURI(query));

      rawQuery = query

      query = encodeURIComponent(JSON.stringify(query))

      // exemples
      // normal with filters : {_node0: "kw", _node1: "sch", keywords: Array(1)}
      // forbidden matchall:   {_node0: "kw", _node1: "sch"}
      // allowed matchall:     {_node0: "kw", _node1: "lab"}


      // empty query => conditional warning
      if (nFilters == 0 && rawQuery['_node0'] == 'kw' && rawQuery['_node1'] == 'sch') {
          if (document.getElementById('refine-warning')) {
            cmxClt.elts.box.toggleBox("refine-warning")
          }
          else {
            cmxClt.elts.box.addGenericBox('refine-warning',
                "No filters were selected",
                "Please fill at least a filter before generating a MAP <br/>(mapping without filters takes a long time and overloads servers)"
              )
            cmxClt.elts.box.toggleBox("refine-warning")
          }
          return null
      }
      else {
        // load the graph URL
        window.location = '/explorerjs.html?sourcemode="api"&type="filter"&srcparams="' + escape(query) +'"';
      }
    });
  });
  $("#print").click(function() {
    // console.log("clicked on print");
    return whoswho.collectFilters(function(query, nFilters) {
      // debug
      // console.log("collected filters: " + query);

      query = encodeURIComponent(JSON.stringify(query))

      if (uinfo && uinfo.luid) {
        window.location = "/print_directory.php?query=" + query + "&user="+uinfo.luid;
      }
      else {
        window.location = "/print_directory.php?query=" + query;
      }
    });
  });

  // retrieve last whoswho types and query from cache
  var whoswhoq = {}
  var sourcetype = null
  if (sessionStorage.hasOwnProperty("whoswhoq-"+sessionStorage.tabid)) {
    try {
      whoswhoq = JSON.parse(sessionStorage["whoswhoq-"+sessionStorage.tabid])
    }
    catch(e) {
      whoswhoq = {}
    }
    sourcetype = "sessionStorage"
  }
  // if explorerjs is present we can use its already parsed arguments
  // POSS: when uniqueid (typeof == string) show the name of the scholar
  else if (typeof(TW) != "undefined" && TW.APIQuery && typeof TW.APIQuery == "object") {
    whoswhoq = TW.APIQuery
    sourcetype = "URL param"
  }
  console.log(`whoswhoq (from ${sourcetype})`, whoswhoq)

  // reinstate any cached types and filters
  for (var filterName in whoswhoq) {
    if (/^_node[0-1]$/.test(filterName)) {
      let itype = parseInt(filterName.charAt(filterName.length-1))
      let opt = whoswhoq[filterName]
      whoswho.select(itype, opt)
    }
    else if (! /^_/.test(filterName)) {
      for (var i in whoswhoq[filterName]) {
        var filterVal = whoswhoq[filterName][i]
        // console.log("whoswho: pop from session cache", filterName, filterVal)
        whoswho.popfilter(filterName, {'prefill':filterVal})
      }
    }
  }

  return;
});
