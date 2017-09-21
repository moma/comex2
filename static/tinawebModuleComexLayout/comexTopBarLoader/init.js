// topbar module for comex
// =======================
// Allows loading special topbar

// Our module_name is simultaneously 3 things:
//   - a DivsFlag for settings_explorerjs
//   - our current dir for this module's files (and this init.js)
//   - the class of module's html elements
module_name="comexTopBarLoader"

// ---- INIT main part -------- (listing all things to load)

// 1 - load dependencies (paths assume we are within comex project)
loadCSS("/static/css/topbar_bootstrap_retrocompatibility.css") ;
// loadCSS("/static/css/whoswho.css") ;
// loadCSS("/static/css/comex.css") ;
loadJS("/static/js/comex_user_shared.js") ;
loadJS("/static/js/comex_lib_elts.js") ;
// loadCSS("/static/tinawebJS/twlibs/css/twjs.css") ;
// loadCSS("/static/tinawebJS/twlibs/css/twjs-mobile.css") ;
// loadCSS("/static/tinawebJS/twlibs/css/selection-panels.css") ;
// loadCSS("/static/tinawebJS/twlibs/css/selection-panels-mobile.css") ;

// 2 - make room

// remove ProjectExplorer logo
document.getElementById('mainlogo').remove()

// move maplabel to toolbar
let ml = document.getElementById('maplabel').parentElement.parentElement
let le = document.getElementById('left')
le.appendChild(ml)

// replace traditional ProjectExplorer's topbar
let newHtml = cmxClt.elts.topbar.prepare(4206)
document.getElementById('topbar').outerHTML = newHtml

// initialize the 2 not-automatic dropdowns (refine is self-contained)
new Dropdown( document.getElementById('user-dropdown') );
new Dropdown( document.getElementById('jobs-dropdown') );


// initialize a global var with the user id for whoswho filters
var uinfo = {'luid': 4206}

// load whoswho
loadJS("/static/js/whoswho.js") ;

console.log("OK LOADED " + module_name) ;
