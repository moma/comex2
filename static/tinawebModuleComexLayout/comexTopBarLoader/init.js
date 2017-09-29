// topbar module for comex
// =======================
// Allows loading special topbar

// POSS: works well but would be more efficient with an explorer template
//       (an html version just for comex: not as modular but lighter)

// Our module_name is simultaneously 3 things:
//   - a DivsFlag for settings_explorerjs
//   - our current dir for this module's files (and this init.js)
//   - the class of module's html elements
module_name="comexTopBarLoader"
// ---- INIT main part -------- (listing all things to load)

// 1 - load dependencies (paths assume we are within comex project)
loadCSS("/static/css/topbar_bootstrap_retrocompatibility.css") ;
loadCSS("/static/js/jquery-ui-1.12.1/jquery-ui.min.css") ;
loadCSS("/static/css/whoswho.css") ;
loadCSS("/static/css/comex_user.css") ;
loadCSS("/static/css/comex.css") ;
loadJS("/static/js/comex_user_shared.js") ;
loadJS("/static/js/comex_lib_elts.js") ;
loadJS("/static/js/whoswho.js") ;

// 2 - make room

// remove ProjectExplorer logo
document.getElementById('mainlogo').remove()

// move maplabel to toolbar
let ml = document.getElementById('maplabel').parentElement.parentElement
let le = document.getElementById('left')
ml.style.fontSize = "150%"
ml.style.float = "right"
le.appendChild(ml)

// 3 - recreate user params
//     (whoswho filters recreated from cache by whoswhojs)
var uinfo = null
if (sessionStorage.hasOwnProperty("uinfo")) {
  try {
    uinfo = JSON.parse(sessionStorage.uinfo)
  }
  catch(e) {}
}

// 4 - replace traditional ProjectExplorer's topbar
let newHtml = cmxClt.elts.topbar.prepare(uinfo ? uinfo.luid : null, {'classicLogin': true})
document.getElementById('topbar').outerHTML = newHtml

// initialize the 2 not-automatic dropdowns (refine is self-contained)
new Dropdown( document.getElementById('user-dropdown') );
new Dropdown( document.getElementById('jobs-dropdown') );

// 5 - add onresize to adjust page to topbar
var topB = document.querySelector("#comex-top > .topbar-inner")

var cTools = document.getElementById("toolbar")
var cSigmaBox = document.getElementById("sigma-contnr")
var cSidebar = document.getElementById("sidebar")
var cLeftBox = document.getElementById("lefttopbox")

let topResize = function() {
  if (topB) {
    let subline = topB.offsetHeight - 5
    let midline = topB.offsetHeight + 65

    // move main containers accordingly
    if (cTools)
      cTools.style.top = subline + "px"

    if (cSigmaBox)
      cSigmaBox.style.top = midline + "px"

    if (cLeftBox)
      cLeftBox.style.top = (midline + 30) + "px"

    if (cSidebar) {
      if (window.innerWidth > 768) {
        cSidebar.style.top = midline + "px"
      }
      else {
        cSidebar.style.top = ''
      }
    }
  }
}

// schedule for next resizes
var winResizeTopbarTimeout = null
window.addEventListener('resize', function(ev){
  if (winResizeTopbarTimeout) {
    clearTimeout(winResizeTopbarTimeout)
  }
  winResizeTopbarTimeout = setTimeout(topResize, 300)
}, true)

// replace whoswho's shiftPage
if (whoswho && whoswho.shiftPage) {
  whoswho.shiftPage = topResize
}

console.log("OK LOADED " + module_name) ;
