// Generated by CoffeeScript 1.3.1
var completion, gexf, ids;

jQuery.fn.disableTextSelect = function() {
  return this.each(function() {
    if (typeof this.onselectstart !== "undefined") {
      return this.onselectstart = function() {
        return false;
      };
    } else if (typeof this.style.MozUserSelect !== "undefined") {
      return this.style.MozUserSelect = "none";
    } else {
      this.onmousedown = function() {
        return false;
      };
      return this.style.cursor = "default";
    }
  });
};

ids = 0;

completion = {};

gexf = "";

$(document).ready(function() {
  var cache, closeBox, collectFilters, loadGraph, popfilter, xhrs;
  log("document ready.. installing whoswho");
  loadGraph = function(g) {
    gexf = g;
    log("url query: " + g);
    log("injecting applet");
    if ($('#frame').length === 0) {
      return $("#visualization").html("<iframe src=\"tinaframe.html" + (location.search != null ? location.search : '') + "\" class=\"frame\" border=\"0\" frameborder=\"0\" scrolling=\"no\" id=\"frame\" name=\"frame\"></iframe>");
    } else {
      return log("applet already exists");
    }
  };


  // small filter closing function
  closeThisBox = function() {
    var targetId = this.getAttribute("for")
    if (targetId) {
        var tgtBox = document.getElementById(targetId)
        // start transition
        tgtBox.style.opacity = 0
        // remove box
        setTimeout(function(){tgtBox.remove()}, 500)
        return true
    }
    else {
        console.warn('closeThisBox: no @for attribute!')
        return false
    }
  }

  // autocomplete
  popfilter = function(label, type, options) {
    var footer, header, id, id1, id2, input, closebox, labelization;
    id = ids++;
    id1 = "filter" + id;
    id2 = "combo" + id;
    id3 = "close" + id;
    header = "<li id=\"" + id1 + "\" class=\"comex-nav-item filter\" style=\"padding-top: 5px;\">";
    labelization = "<span style=\"color: #fff;\">&nbsp; " + label + " </span>";
    input = "<input type=\"text\" id=\"" + id2 + "\" class=\"medium filter" + type + "\" placeholder=\"" + type + "\" />";
    closebox = "<div id=\""+id3+"\" for=\""+id1+"\" class=\"filter-close operation-light\">x</div>"
    footer = "</li>;";
    $(header + labelization + input + closebox + footer).insertBefore("#refine");
    $('#' + id3).click(closeThisBox)

    // debug
    // console.log("whoswho.popfilter: adding autocomplete menu", $("#" + id1))

    $("#" + id2).autocomplete({
        source: function (req, resp) {
            $.ajax({
                dataType: "json",
                type: "GET",
                url: "/search_filter.php",
                data: {
                    "category": type,
                    "term": req.term,
                },
                success: function(data){
                    resp(data.results)
                },
                error: function(response) {
                    console.log("ERROR from search_filter AJAX", response)
                }
            }) ;
        },
        minLength: 2
    })

    $("" + id1).hide();
    show("#" + id1);
    $("#" + id2).focus();
    return false;
  };
  // jQuery(".unselectable").disableTextSelect();
  jQuery(".unselectable").disableSelection();
  $(".unselectable").hover((function() {
    return $(this).css("cursor", "default");
  }), function() {
    return $(this).css("cursor", "auto");
  });
  hide("#search-form");
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
    return popfilter("in", "countries", []);
  });
  $("#addfilterorganization").click(function() {
    return popfilter("from", "organizations", []);
  });
  $("#addfilterlaboratory").click(function() {
    var prefix;
    prefix = "working";
    return popfilter("" + prefix + " at", "laboratories", []);
  });
  $("#addfilterkeyword").click(function() {
    var prefix;
    prefix = "working";
    return popfilter("" + prefix + " on", "keywords", []);
  });
  $("#addfiltertag").click(function() {
    return popfilter("tagged", "tags", []);
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
        $("#print2").click(function() {
          return window.open("/print_scholar_directory.php?query=" + ui.item.id, "Scholar's list");
        });
        $("#generate2").click(function() {
          return window.open('/explorerjs.html?type="uid"&nodeidparam="' + ui.item.id + '"');
        });
      }
    }
  })

  // main form collect function
  collectFilters = function(cb) {
    var collect, query;
    collect = function(k) {
      var t;
      t = [];
      log("collecting .filter:" + k);
      $(".filter" + k).each(function(i, e) {
        var value;

        // debug
        // console.log('collecting (filter '+k+') from elt:' + e)

        value = $(e).val();
        if (value != null && value != "") {
          log("got: " + value);
          value = $.trim(value);
          log("sanitized: " + value);
          if (value !== " " || value !== "") {
            log("keeping " + value);
            return t.push(value);
          }
        }
      });
      return t;
    };
    log("reading filters forms..");


    query = {

    // TODO in the future multiple categories
    // categorya: $.trim($("#categorya :selected").text()),
    // categoryb: $.trim($("#categoryb :selected").text()),

    // TODO in the future coloredby
    // query.coloredby =  []

    }

    for (filterName of ["keywords", "countries", "laboratories", "tags", "organizations"]) {
        var filterValuesArray = collect(filterName)

        // we add only if something to add :)
        if (filterValuesArray.length) {
            query[filterName] = filterValuesArray
        }
    }

    log("raw query: ");
    log(query);

    query = encodeURIComponent(JSON.stringify(query));

    // debug
    // console.log("calling callback with encoded query:", query)

    return cb(query);
  };


  // refine filters => tinawebjs graphexplorer
  $("#generate").click(function() {
    console.log("clicked on generate")
    hide(".hero-unit");
    $("#welcome").fadeOut("slow");
    // console.log("initiating graphexplorer")
    show("#loading", "fast");
    return collectFilters(function(query) {
      // debug
      // console.log("collected filters: " + query);
      return window.location.href='/explorerjs.html?type="filter"&nodeidparam="' + escape(query) +'"';
      //return loadGraph("getgraph.php?query=" + query);
    });
  });
  $("#print").click(function() {
    console.log("clicked on print");
    return collectFilters(function(query) {
      // debug
      // console.log("collected filters: " + query);
      return window.open("/print_directory.php?query=" + query, "Scholar's list");
    });
  });
  hide("#loading");
  cache = {};
  return xhrs = {};
});
