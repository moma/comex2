
// for new SigmaUtils
// new sigma.js: POSS to use autoResize global setting
function sigmaLimits( sigmacanvas ) {
    pw=$( sigmacanvas ).width();
    ph=$( sigmacanvas ).height();

    sidebar=$('#rightcolumn').width();
    anchototal=$('#fixedtop').width();
    altototal=$('#rightcolumn').height();
    altofixtop=$('#fixedtop').height()
    altodeftop=$('#defaultop').height()
    $( sigmacanvas ).width(anchototal-sidebar);
    $( sigmacanvas ).height(altototal-altofixtop-altodeftop-4);


    // todo take into account leftcolumn
        //sidebar_left=$('#leftcolumn').width();
        //sidebar_right=$('#rightcolumn').width();
        //$( sigmacanvas ).width(anchototal-sidebar_right-sidebar_left);


    pw=$( sigmacanvas ).width();
    ph=$( sigmacanvas ).height();
    return "new canvas! w:"+pw+" , h:"+ph;
}





// will be instanciated as SelInst
SelectionEngine = function() {


    // TODO REFA this block was used for area selection
    // (!at least partly replaceable by getNodes from new sigma.misc.bindEvents)
    // ----------------------------------------------------------8<-------------
    // Selection Engine!! finally...
    this.SelectorEngine_part01 = (function(cursorsize, area ) {
        var clickedNodes = []
        if(cursorsize>0) {
            clickedNodes = this.SelectThis2( area )
        } else {
            clickedNodes = TW.partialGraph.graph.nodes().filter(function(n) {
                            return !!n['hover'];
                        }).map(function(n) {
                            return n.id;
                        });
        }

        return clickedNodes.map(Number);
    }).index();

    this.SelectorEngine_part02 = (function( addvalue , clicktype , prevsels , currsels ) {

        console.log("Add[]:")
        console.log(addvalue)
        console.log("clicktype:")
        console.log(clicktype)
        console.log("prevsels:")
        console.log(prevsels)
        console.log("currsels:")
        console.log(currsels)
        console.log(" - - - - - - ")

        var buffer = Object.keys(prevsels).map(Number).sort(this.sortNumber);
        var targeted = currsels.map(Number).sort(this.sortNumber);

        if(clicktype=="double" && targeted.length==0) return [];

        // if(targeted.length>0) {
        if(buffer.length>0) {
            if(JSON.stringify(buffer)==JSON.stringify(targeted)) {
                // this is just effective for Add[ ] ...
                // If previous selection is equal to the current one, you've nothing :D
                cancelSelection(false);
                return [];
            }
            var inter = this.intersect_safe(buffer,targeted)
            if(inter.length>0) {
                var blacklist = {} , whitelist = {};
                for(var i in inter) blacklist[inter[i]]=true;
                for(var i in buffer){
                    e = buffer[i]
                    if(!blacklist[e]) {
                        whitelist[e] = true;
                    }
                }
                for(var i in targeted){
                    e = targeted[i]
                    if(!blacklist[e]) {
                        whitelist[e] = true;
                    }
                }
                targeted = Object.keys(whitelist).map(Number);
            } else {// inter = 0 ==> click in other portion of the graph (!= current selection)
                // Union!
                if(addvalue) {
                    targeted = targeted.concat(buffer.filter(function (item) {
                        return targeted.indexOf(item) < 0;
                    }));
                }
                return targeted;
            }
        } else return targeted;
        // }

        return targeted;
    }).index();
    // ----------------------------------------------------------8<-------------

    this.SelectorEngine = (function( cursorsize , area , addvalue , clicktype , prevsels , currsels ) {
        var targeted = []
        var buffer = Object.keys(prevsels).map(Number).sort(this.sortNumber);

        if( isUndef(currsels) ) { // bunch of nodes from a click in the map
            if(cursorsize>0) {
                targeted = this.SelectThis2( area )
            } else {
                targeted = TW.partialGraph.graph.nodes().filter(function(n) {
                                return !!n['hover'];
                            }).map(function(n) {
                                return n.id;
                            });
            }
        } else { // OR one node from the tagcloud or a bunch of nodes from the searchbar
            currsels = currsels.map(Number).sort(this.sortNumber);
            if(addvalue) {
                targeted = currsels.concat(buffer.filter(function (item) {
                    return currsels.indexOf(item) < 0;
                }));
            } else targeted = currsels;
            return targeted;
        }

        targeted = targeted.map(Number)

        if(clicktype=="double" && targeted.length==0) return [];

        targeted = targeted.sort(this.sortNumber);

        if(targeted.length>0) {
            if(buffer.length>0) {
                if(JSON.stringify(buffer)==JSON.stringify(targeted)) {
                    // this is just effective for Add[ ] ...
                    // If previous selection is equal to the current one, you've nothing :D
                    cancelSelection(false);
                    return [];
                }
                var inter = this.intersect_safe(buffer,targeted)
                if(inter.length>0) {
                    var blacklist = {} , whitelist = {};
                    for(var i in inter) blacklist[inter[i]]=true;
                    for(var i in buffer){
                        e = buffer[i]
                        if(!blacklist[e]) {
                            whitelist[e] = true;
                        }
                    }
                    for(var i in targeted){
                        e = targeted[i]
                        if(!blacklist[e]) {
                            whitelist[e] = true;
                        }
                    }
                    targeted = Object.keys(whitelist).map(Number);
                } else {// inter = 0 ==> click in other portion of the graph (!= current selection)
                    // Union!
                    if(addvalue) {
                        targeted = targeted.concat(buffer.filter(function (item) {
                            return targeted.indexOf(item) < 0;
                        }));
                    }
                    return targeted;
                }
            } else return targeted;
        }

        return targeted;
    }).index();

    // uses: SelectorEngine() and MultipleSelection2()
    // we assume string is normalized
    this.search_n_select = function(string) {

        // alert("search is happening !")
        cancelSelection(false);

        if (typeof string != "string") {
            return -1 ;
        }
        else if (string.length == 0) {
            // alert("really? empty query?") ;
            return 0 ;
        }
        else {
            var id_node = '';
            var results = find(string)

            var coincd=[]
            for(var i in results) {
                coincd.push(results[i].id)
            }
            var targeted = this.SelectorEngine( {
                            addvalue:checkBox,
                            clicktype:"simple",
                            prevsels:selections,
                            currsels:coincd
                        } )

            if(targeted.length>0) {
                // got results
                // -----------
                this.MultipleSelection2({nodes:targeted});
            }
            else {
                // no results
                // ----------
                // we send event for plugins
                // (eg: propose to add the missing string to the graph)
                $('#searchinput').trigger({
                    type: "tw:emptyNodeSet",
                    q: string,
                    nodeIds: []
                });
                // console.log("\n\n\n  sent [[ emptyNodes ]] \n\n ")
            }

            // anyway
            // ------
            TW.lastQuery = string ;
            $("input#searchinput").val("");
            $("input#searchinput").autocomplete( "close" );
            TW.partialGraph.refresh({ skipIndexation: true });

            return targeted.length
        }
    }

    //Util
    this.sortNumber = function(a,b) {
        return a - b;
    }

    //Util
    this.intersect_safe = function(a, b) {
        var ai=0, bi=0;
        var result = new Array();

        while( ai < a.length && bi < b.length ) {
            if      (a[ai] < b[bi] ){ ai++; }
            else if (a[ai] > b[bi] ){ bi++; }
            else /* they're equal */ {
                result.push(a[ai]);
                ai++;
                bi++;
            }
        }
        return result;
    }

    // return Nodes-ids under the clicked Area
    //  external usage : partialGraph
    this.SelectThis2 = function( area ) {
        var x1 = area.x1;
        var y1 = area.y1;

        //Multiple selection
        var counter=0;
        var actualSel=[];
        TW.partialGraph.iterNodes(function(n){
            if(!n.hidden){
                distance = Math.sqrt(
                    Math.pow((x1-parseInt(n.displayX)),2) +
                    Math.pow((y1-parseInt(n.displayY)),2)
                    );
                if(parseInt(distance)<=cursor_size) {
                    counter++;
                    actualSel.push(n.id);
                }
            }
        });
        return actualSel;
    }


    /**
     * Main function for any selecting action
     *
     * @nodes: eg targeted array
     */
    //  external usage : partialGraph , updateLeftPanel_fix();
    this.MultipleSelection2 = (function(nodes,nodesDict,edgesDict) {

        console.log("IN SelectionEngine.MultipleSelection2:")
        console.log("nodes", nodes)
        greyEverything();

        // TW.partialGraph.states.slice(-1)[0] is the present graph state
        var typeNow = TW.partialGraph.states.slice(-1)[0].type.map(Number).join("|")
        // console.log ("console.loging the Type:")
        // console.log (typeNow)
        // console.log (" - - - - - - ")
        // Dictionaries of: selection+neighbors

        var nodes_2_colour = (nodesDict)? nodesDict : {};
        var edges_2_colour = (edgesDict)? edgesDict : {};

        selections = {}

        var ndsids=[]
        if(nodes) {
            if(! $.isArray(nodes)) ndsids.push(nodes);
            else ndsids=nodes;
            for(var i in ndsids) {
                s = ndsids[i];
                if(TW.Relations[typeNow] && TW.Relations[typeNow][s] ) {
                    neigh = TW.Relations[typeNow][s]
                    if(neigh) {
                        for(var j in neigh) {
                            t = neigh[j]
                            nodes_2_colour[t]=false;
                            edges_2_colour[s+";"+t]=true;
                            edges_2_colour[t+";"+s]=true;
                        }
                    }
                }
            }
            for(var i in ndsids) {
                nodes_2_colour[ndsids[i]]=true;
                selections[ndsids[i]]=1; // to delete please
            }
        }

        for(var i in nodes_2_colour) {
            if(i) {
                n = TW.partialGraph.graph.nodes(i)
                if(n) {
                    n.color = n.customAttrs['true_color'];
                    n.customAttrs['grey'] = 0;
                    if(nodes_2_colour[i]) {
                        n.active = nodes_2_colour[i];
                        selections[i]=1
                    }
                }
            }
        }
        for(var i in edges_2_colour) {
            an_edge = TW.partialGraph.graph.edges(i)
            if(!isUndef(an_edge) && !an_edge.hidden){
                an_edge.color = an_edge.customAttrs['true_color'];
                an_edge.customAttrs['grey'] = 0;
            }
        }

        // show the button to remove selection
        $("#unselectbutton").show() ;

        var the_new_sels = Object.keys(selections).map(Number)
        TW.partialGraph.states.slice(-1)[0].selections = the_new_sels;
        TW.partialGraph.states.slice(-1)[0].setState( { sels: the_new_sels} )

        // alert("MultipleSelection2=======\nthe_new_sels:" + JSON.stringify(the_new_sels))

        // we send our "gotNodeSet" event
        // (signal for plugins that a search-selection was done or a new hand picked selection)
        $('#searchinput').trigger({
            type: "tw:gotNodeSet",
            q: $("#searchinput").val(),
            nodeIds: the_new_sels
        });
        // console.log("Event [gotNodeSet] sent from Tinaweb MultipleSelection2")


        var neighsDict = {}
        if(TW.Relations["1|1"]) {
            for(var s in the_new_sels) {
                var neighs = TW.Relations["1|1"][the_new_sels[s]];
                for(var n in neighs) {
                    if (!neighsDict[neighs[n]])
                        neighsDict[neighs[n]] = 0;
                    neighsDict[neighs[n]]++;
                }
            }
        }

        var oppos = ArraySortByValue(neighsDict, function(a,b){
            return b-a
        });


        overNodes=true;

        TW.partialGraph.refresh({skipIndexation:true});

        updateLeftPanel_fix( selections , oppos );

        for(var n in neighsDict)
            delete neighsDict[n]

    }).index()
};

// REFA tempo expose selectionEngine and methods
var SelInst


TinaWebJS = function ( sigmacanvas ) {
    this.sigmacanvas = sigmacanvas;

    this.init = function () {
        console.log("hola mundo")
    }

    this.getSigmaCanvas = function () {
        return this.sigmacanvas;
    }

    this.AdjustSigmaCanvas = function ( sigmacanvas ) {
        var canvasdiv = "";
        if( sigmacanvas ) canvasdiv = sigmacanvas;
        else canvasdiv = this.sigmacanvas;

        return sigmaLimits( canvasdiv );
    }

    this.SearchListeners = function () {

        // REFA tempo expose
        // var SelInst = new SelectionEngine();
        SelInst = new SelectionEngine();

        //~ $.ui.autocomplete.prototype._renderItem = function(ul, item) {
            //~ var searchVal = $("#searchinput").val();
            //~ var desc = extractContext(item.desc, searchVal);
            //~ return $('<li onclick=\'var s = "'+item.label+'"; search(s);$("#searchinput").val(strSearchBar);\'></li>')
            //~ .data('item.autocomplete', item)
            //~ .append("<a><span class=\"labelresult\">" + item.label + "</span></a>" )
            //~ .appendTo(ul);
        //~ };

        $('input#searchinput').autocomplete({
            source: function(request, response) {
                // console.log("in autocomplete:")

                // labels initialized in settings, filled in updateSearchLabels
                // console.log(labels.length)
                // console.log(" - - - - - - - - - ")
                matches = [];
                var matcher = new RegExp($.ui.autocomplete.escapeRegex(request.term), "i");
                // grep at heart
                var results = $.grep(labels, function(e) {
                    return matcher.test(e.label); //|| matcher.test(e.desc);
                });

                if (!results.length) {
                    $("#noresults").text("Pas de résultats");
                } else {
                    $("#noresults").empty();
                }
                matches = results.slice(0, maxSearchResults);
                response(matches);

            },
            minLength: minLengthAutoComplete,


            // ----------------------->8---------------------
            // send a "no more suggestions event"
            response: function (event, ui_response_array) {
                // exemple in ui_response_array
                // {"content":
                //  [{id: 239, label:"warning system",desc:"ISIterms.."},
                //   ...
                //  ]
                // }

                if (ui_response_array.content.length == 0) {
                    // we send our "noAutocomplete" event
                    $('#searchinput').trigger("tw:noAutocomplete");
                    // (signal for plugins like crowdsourcing that
                    //  are sensitive to autocomplete being empty)
                    // console.log("000 Event [noAutocomplete] sent from Tinaweb search")
                }
                else {
                    // we send a "hasAutocomplete" event
                    // (/!\ will be sent for each typed char)
                    $('#searchinput').trigger("tw:gotAutocomplete");
                    // console.log("+++ Event [gotAutocomplete] sent from Tinaweb search")
                }
            }
            // ----------------------->8---------------------
        });

        // is_open flag for keydown choice
        $('#searchinput').bind('autocompleteopen', function(event, ui) {
            $(this).data('is_open',true);
        });
        $('#searchinput').bind('autocompleteclose', function(event, ui) {
            $(this).data('is_open',false);
        });

        // default search value now handled through input/@placeholder
        // $("#searchinput").focus(function () {        });
        // $("#searchinput").blur(function () {        });


        // i click on the search button, independently from autocomplete
        $("#searchbutton").click(function() {
            var query = normalizeString($("#searchinput").val())
            // console.log('===\nyour query was: "'+query+'"');

            // --- SelectionEngine.search() -------------------
            //   -> will call sigmaUtils.find()
            //           over sigmaUtils.getnodesIndex()
            //   -> then call this.SelectorEngine
            //            and this.MultipleSelection2
            SelInst.search_n_select(query)
            // ------------------------------------------------
        });


        // i've a list of coincidences and i press enter like a boss >:D
        //  external usage: partialGraph, SelectorEngine() , MultipleSelection2()
        $("#searchinput").keydown(function (e) {
            if (e.keyCode == 13 && $("input#searchinput").data('is_open') === true) {
                // Search has several results and you pressed ENTER
                if(!is_empty(matches)) {
                    var coincidences = []
                    for(j=0;j<matches.length;j++){
                        coincidences.push(matches[j].id)
                    }
                    $.doTimeout(30,function (){
                        targeted = SelInst.SelectorEngine( {
                                        addvalue:checkBox,
                                        clicktype:"double",
                                        prevsels:selections,
                                        currsels:coincidences
                                    } )

                        // tricky stuff for simulating a multiple selection D:
                        // ... to be improved in the future ...
                        var prev_cursor_size = cursor_size;
                        if(targeted.length>0) {
                            cursor_size = (cursor_size==0)? 1 : cursor_size;
                            cancelSelection(false);
                            SelInst.MultipleSelection2({nodes:targeted});
                            cursor_size = prev_cursor_size;
                        }
                        TW.partialGraph.draw();

                        $("input#searchinput").val("");
                        $("input#searchinput").autocomplete( "close" );
                    });
                    //$("input#searchinput").trigger('autocompleteclose');
                }

            // alert("matches[].id\n" + JSON.stringify(matches.map(function(n) {return n.id})))
            }
            else if (e.keyCode == 13 && $("input#searchinput").data('is_open') !== true) {
                // pressed down [ENTER] but with no autocomplete
                // it really means "do search_and_select()"
                // (but we know the results will be empty)
                // (we still do it for the side effects: events, cleaning)
                var query = normalizeString($("#searchinput").val())
                SelInst.search_n_select(query)
            }
        });

        // i was navigating (with the up|down) sur the coincidences-list and i pressed enter!
        //  external usage: partialGraph, SelectorEngine() , MultipleSelection2()
        $("#searchinput").keyup(function (e) {
            if (e.keyCode == 13 && $("input#searchinput").data('is_open') !== true) {
                var targeted = [] ;
                var exfnd = exactfind( $("#searchinput").val() )
                if (exfnd!=null) {
                    console.log("search KEY UP");
                    $.doTimeout(30,function (){

                            targeted = SelInst.SelectorEngine( {
                                        addvalue:checkBox,
                                        clicktype:"double",
                                        prevsels:selections,
                                        currsels:[exfnd.id]
                                    } )
                            if(targeted.length>0) {
                                cancelSelection(false);
                                SelInst.MultipleSelection2({nodes:targeted});
                            }
                            TW.partialGraph.draw();

                            $("input#searchinput").val("");
                            $("input#searchinput").autocomplete( "close" );
                    });
                }
            }
        });
    }

    //  external usage: SelectorEngine*() , MultipleSelection2() ,
    //      enviroment.js:changeType()|changeLevel()|NodeWeightFilter()|EdgeWeightFilter
    this.initListeners = function (categories, partialGraph) {

        var SelInst = new SelectionEngine();

        $("#semLoader").hide();

        $("#closeloader").click();

        var body=document.getElementsByTagName('body')[0];
        body.style.paddingTop="41px";

        $('.etabs').click(function(){
            $.doTimeout(500,function () {
                $("#opossiteNodes").readmore({maxHeight:200});
                $("#sameNodes").readmore({maxHeight:200});
            });
        });

        $("#changetype").click(function(){
            console.log("")
            console.log(" ############  changeTYPE click");
            partialGraph.stopForceAtlas2();
            changeType();

            $.doTimeout(500,function (){
                $('.etabs a[href="#tabs1"]').trigger('click');
            });
            ChangeGraphAppearanceByAtt(true)
            console.log(" ############  / changeTYPE click");
            console.log("")
        });

        $("#changelevel").click(function(){
            console.log("")
            console.log(" ############  changeLEVEL click");

            changeLevel(); // <- est-ce que ça fait quelquechose ?
            // $("#tabs1").click()
            ChangeGraphAppearanceByAtt(true)  // cf. extras_explorer
            console.log(" ############  / changeLEVEL click");
            console.log("")
        });

        //  ===  un/hide leftpanel  === //
        $("#aUnfold").click(function(e) {
            //SHOW rightcolumn
            sidebar = $("#rightcolumn");
            fullwidth=$('#fixedtop').width();
            e.preventDefault();
            // $("#wrapper").toggleClass("active");
            if(parseFloat(sidebar.css("right"))<0){
                $("#aUnfold").attr("class","rightarrow");
                sidebar.animate({
                    "right" : sidebar.width()+"px"
                }, { duration: 400, queue: false });

                $("#ctlzoom").animate({
                        "right": (sidebar.width()+10)+"px"
                }, { duration: 400, queue: false });

                // $('#sigma-example').width(fullwidth-sidebar.width());
                $('#sigma-example').animate({
                        "width": fullwidth-sidebar.width()+"px"
                }, { duration: 400, queue: false });
                setTimeout(function() {
                      partialGraph.resize();
                      partialGraph.refresh();
                }, 400);
            }
            else {
                //HIDE rightcolumn
                $("#aUnfold").attr("class","leftarrow");
                sidebar.animate({
                    "right" : "-" + sidebar.width() + "px"
                }, { duration: 400, queue: false });

                $("#ctlzoom").animate({
                        "right": "0px"
                }, { duration: 400, queue: false });

                    // $('#sigma-example').width(fullwidth);
                $('#sigma-example').animate({
                        "width": fullwidth+"px"
                },{ duration: 400, queue: false });
                setTimeout(function() {
                      partialGraph.resize();
                      partialGraph.refresh();
                }, 400);
            }
        });

        pushSWClick("social");

        cancelSelection(false);

        $("#tips").html(getTips());

        showMeSomeLabels(6);

        // updateDownNodeEvent(false);

        $("#saveAs").click(function() {
            $('#savemodal').modal('show');
        });

        this.SearchListeners();

        // button CENTER
        $("#lensButton").click(function () {
            // new sigma.js
            partialGraph.camera.goTo({x:0, y:0, ratio:1})
        });

        // new sigma.js: attempt to use sigma events bindings

        // cases:
        // [DONE] - simple click, one node
        // [TODO] - simple click, area

        // one node:
        TW.partialGraph.bind('clickNode', function(e, node) {
          // new sigma.js gives easy access to clicked node!
          theNodeId = e.data.node.id
          cancelSelection(false);
          SelInst.MultipleSelection2({nodes:[theNodeId]})
        })

            // TODO
            // TW.partialGraph.bind('click', function(e) {
            //   console.log("===click===");
            //   console.log("e", e);
            // })

            // TW.partialGraph.bind('downgraph upgraph', function(e) {
            //   console.log("===downgraph upgraph===");
            //   console.log("e", e);
            // })


            // --------------------------------------------fragment from v1.customized
            // TW.partialGraph.bind('mousedown mouseup', function(e) {
            //
            //   console.log("---------- event", e)
            //   var targeted = self.graph.nodes.filter(function(n) {
            //       return !!n['hover'];
            //   }).map(function(n) {
            //       return n.id;
            //   });
            //   console.log("---------- targeted by hover check loop", targeted)
            // })
            //
            // self.dispatch(
            //     e['type'] == 'mousedown' ?
            //     'downgraph' :
            //     'upgraph'
            //     );
            //
            // if (targeted.length) {
            //     self.dispatch(
            //         e['type'] == 'mousedown' ?
            //         'downnodes' :
            //         'upnodes',
            //         targeted
            //         );
            //  }
            // }
            // -------------------------------------------/fragment from v1.customized



        // Double Click
        //  external usage: SelectorEngine_part01() and SelectorEngine_part02()

        TW.partialGraph.bind('doubleClickNode', function(e) {
          console.log("===doubleClickNode===");
          console.log("e", e);
        })


        // $('#sigma-example').dblclick(function(event) {// using SelectionEngine
        //     var area = {}
        //
        //     // TODO replace
        //     console.log("customdoubleclick", event)
        //     area.x1 = partialGraph._core.mousecaptor.mouseX;
        //     area.y1 = partialGraph._core.mousecaptor.mouseY;
        //
        //     targeted = SelInst.SelectorEngine_part01({
        //                     cursorsize:cursor_size,
        //                     area:area
        //                 })
        //
        //     if(targeted.length>0) {
        //         var finalSelection = SelInst.SelectorEngine_part02( {
        //                                     addvalue:checkBox ,
        //                                     clicktype:(checkBox)?"simple":"double",
        //                                     prevsels:selections,
        //                                     currsels:targeted
        //                                 });
        //         cancelSelection(false);
        //         SelInst.MultipleSelection2( {nodes:finalSelection} )
        //
        //     } else cancelSelection(false);
        //
        //     partialGraph.draw();
        //     trackMouse(event);
        // });

        // Simple Click
        //  external usage: SelectorEngine()
        // $("#sigma-example")
        //     .mousemove(function(event){
        //         if(!isUndef(partialGraph)) {
        //             if(cursor_size>0) trackMouse(event);
        //         }
        //     })
        //     .contextmenu(function(){
        //         return false;
        //     })
        //     .mousedown(function(e) { // using SelectionEngine
        //         //left click!<- normal click
        //         if(e.which==1){
        //             console.warn('new sigma.js FIX event bindings for downgraph, upgraph')
        //             partialGraph.dispatchEvent(
        //                 e['type'] == 'mousedown' ?
        //                 'downgraph' :
        //                 'upgraph'
        //             );
        //             var area = {}
        //
        //
        //             // new sigma.js: (x,y) from event -- TODO check if convert coords
        //             area.x1 = sigma.utils.getX(e);
        //             area.y1 = sigma.utils.getY(e);
        //
        //             // old version
        //             // area.x1 = partialGraph._core.mousecaptor.mouseX;
        //             // area.y1 = partialGraph._core.mousecaptor.mouseY;
        //
        //             var targeted = SelInst.SelectorEngine( {
        //                                 cursorsize:cursor_size,
        //                                 area:area,
        //                                 addvalue:checkBox,
        //                                 clicktype:"simple",
        //                                 prevsels:selections
        //                             } )
        //             if(targeted.length>0) {
        //                 cancelSelection(false);
        //                 SelInst.MultipleSelection2( {nodes:targeted} )
        //             }
        //             partialGraph.refresh({skipIndexation:true});
        //             trackMouse(e);
        //         }
        //     });



        $("#zoomSlider").slider({
            orientation: "vertical",

            // new sigma.js current zoom ratio
            value: partialGraph.camera.ratio,
            min: sigmaJsMouseProperties.minRatio,
            max: sigmaJsMouseProperties.maxRatio,
            range: "min",
            step: 0.1,
            slide: function( event, ui ) {
                console.log("*******lalala***********")
                console.log(partialGraph.camera.ratio)
                console.log(sigmaJsMouseProperties.minRatio)
                console.log(sigmaJsMouseProperties.maxRatio)
                partialGraph.zoomTo(
                    TW.partialGraph.renderers[0].width / 2,
                    TW.partialGraph.renderers[0].height / 2,
                    ui.value);
            }
        });

        $("#zoomPlusButton").click(function () {
            partialGraph.zoomTo(TW.partialGraph.renderers[0].width / 2, TW.partialGraph.renderers[0].height / 2, partialGraph._core.mousecaptor.ratio * 1.5);
            $("#zoomSlider").slider("value",partialGraph.position().ratio);
            return false;
        });

        $("#zoomMinusButton").click(function () {
            partialGraph.zoomTo(TW.partialGraph.renderers[0].width / 2, TW.partialGraph.renderers[0].height / 2, partialGraph._core.mousecaptor.ratio * 0.5);
            $("#zoomSlider").slider("value",partialGraph.position().ratio);
            return false;
        });

        $("#edgesButton").click(function () {
            fa2enabled=true;
            if(!isUndef(partialGraph.forceatlas2)) {

                if(partialGraph.forceatlas2.active) {
                    partialGraph.stopForceAtlas2();
                    partialGraph.refresh({ skipIndexation: true });
                    return;
                } else {
                    partialGraph.startForceAtlas2();
                    return;
                }

            } else {
                partialGraph.startForceAtlas2();
                return;
            }
        });

        NodeWeightFilter ( categories , "#slidercat0nodesweight" ,  categories[0],  "type" ,"size");

        EdgeWeightFilter("#slidercat0edgesweight", "label" , "nodes1", "weight");

        $("#category1").hide();

        //finished
        $("#slidercat0nodessize").freshslider({
            step:1,
            min:-20,
            max:20,
            value:0,
            bgcolor:"#27c470",
            onchange:function(value){
                $.doTimeout(100,function (){
                   // new sigma.js loop on nodes POSS optimize
                   nds  = TW.partialGraph.graph.nodes()
                   console.log("init: slider resize")
                   for(j=0 ; j<TW.partialGraph.nNodes ; j++){
                       if (nds[j]
                        && nds[j].type == TW.catSoc) {
                            var n = nds[j]
                            var newval = parseFloat(TW.Nodes[n.id].size) + parseFloat((value-1))*0.3
                            n.size = (newval<1.0)?1:newval;
                            sizeMult[TW.catSoc] = parseFloat(value-1)*0.3;
                       }
                   }
                   partialGraph.refresh({skipIndexation:true})
                });
            }
        });

        //finished
        $("#slidercat1nodessize").freshslider({
            step:1,
            min:-20,
            max:20,
            value:0,
            bgcolor:"#FFA500",
            onchange:function(value){
                $.doTimeout(100,function (){
                    // new sigma.js loop on nodes POSS optimize
                    nds  = TW.partialGraph.graph.nodes()
                    console.log("init: slider resize")
                    for(j=0 ; j<TW.partialGraph.nNodes ; j++){
                        if (nds[j]
                         && nds[j].type == TW.catSem) {
                             var n = nds[j]
                             var newval = parseFloat(TW.Nodes[n.id].size) + parseFloat((value-1))*0.3
                             n.size = (newval<1.0)?1:newval;
                             sizeMult[TW.catSem] = parseFloat(value-1)*0.3;
                        }
                    }
                    partialGraph.refresh({skipIndexation:true})
                });
            }
        });

        //Cursor Size slider
        $("#unranged-value").freshslider({
            step: 1,
            min:cursor_size_min,
            max:cursor_size_max,
            value:cursor_size,
            onchange:function(value){
                // console.log("en cursorsize: "+value);
                cursor_size=value;
                if(cursor_size==0) partialGraph.refresh({skipIndexation:true});
            }
        });

    }

};