/**
 * @fileoverview
 *  Prepares cmxClt.uauth.box HTML elements (mail, pass inputs) in a modal
 *  (use case: enter login credentials client-side without changing page)
 *
 * @todo
 *    - package.json
 *
 * @version 1
 * @copyright ISCPIF-CNRS 2016
 * @author romain.loth@iscpif.fr
 *
 * @requires comex_user_shared
 *
 *
 * cmxClt.elts: A module to create dom elements handled by comex client
 * -----------
 *  - .elts.box is a loginbox
 *    currently need set up menu login box before rest to provide elts to uauth
 */


var cmxClt = (function(cC) {

    cC.elts = {}

    cC.elts.elBody = document.querySelector('body')
    cC.elts.elPage = document.querySelector('.page')

    // a topbar creation function from template
    //   ------
    cC.elts.topbar = {}
    cC.elts.topbar.prepare
    cC.elts.topbar.create

    // a tagcloud-like div with proportional labels
    //   ------
    cC.elts.tagcloud = {}
    cC.elts.tagcloud.xhrSync
    cC.elts.tagcloud.prepare

    // an optional modal box for login/register credentials
    //            -----------
    cC.elts.box = {}
    cC.elts.box.toggleBox
    cC.elts.box.addGenericBox
    cC.elts.box.addAuthBox
    cC.elts.box.postAuthBox
    cC.elts.box.authBox = null

    // generate html content for a new topbar
    cC.elts.topbar.prepare = function(luid, args = {'empty': false}) {
      let baseMenus = ''

      // for active users that are not empty
      if (luid && !args.empty) {
        baseMenus = `
          <li class="comex-nav-item">
              <a class="topbarlink" href='/explorerjs.html?type="uid"&amp;nodeidparam="${luid}"'> Your Map </a>
          </li>
          <li class="comex-nav-item">
              <a class="topbarlink" href='/print_scholar_directory.php?query=${luid}&user=${luid}'> Your Directory </a>
          </li>
          <li class="dropdown">
            <a id="jobs-dropdown" href="#" class="navlink dropdown-toggle"
               data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">
               <span class="glyphicon glyphicon-briefcase"></span>
               Jobs
               <span class="caret"></span>
           </a>
            <ul class="dropdown-menu">
              <li>
                  <a href='/services/addjob/'>Add a new job</a>
              </li>
              <li>
                  <a href='/services/user/myjobs/'>Your posted jobs</a>
              </li>
              <li>
                <a href='/services/jobboard/'>Job Market</a>
              </li>
            </ul>
          </li>
        `
      }
      // for anonymous and empty users
      else {
        baseMenus = `
          <li class="dropdown">
            <a id="jobs-dropdown" href="#" class="navlink dropdown-toggle"
               data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">
               <span class="glyphicon glyphicon-briefcase"></span>
               Jobs
               <span class="caret"></span>
           </a>
            <ul class="dropdown-menu">
              <li>
                <a href='/services/jobboard/'> Job Market </a>
              </li>
            </ul>
          </li>
        `
      }

      let dropDownContent = ''
      if (luid) {
        if (args.empty) {
          // special case for returning users
          dropDownContent = `
            <li>
                <a href="/services/user/profile"> Create your Profile !</a>
            </li>
            <li>
                <a onclick="sessionStorage.removeItem('uinfo')" href='/services/user/logout/'> Logout </a>
            </li>
          `
        }
        // normal logged in case
        else {
          dropDownContent = `
            <li>
                <a href="/services/user/profile"> Your Profile </a>
            </li>
            <li>
                <a onclick="sessionStorage.removeItem('uinfo')" href='/services/user/logout/'> Logout </a>
            </li>
          `
        }
      }
      // unlogged case
      else {
        if (args.classicLogin) {
          dropDownContent = `
            <li>
                <a href="/services/user/login"> Login </a>
            </li>
            <li>
                <a href="/services/user/register"> Register </a>
            </li>
          `
        }
        else {
          dropDownContent = `
            <li>
                <div class="dropdown-a-like" id="poplogin"
                  data-toggle="dropdown"
                  onclick="cmxClt.elts.box.toggleBox('auth_modal')">
                  Login </div>
            </li>
            <li>
                <a href="/services/user/register"> Register </a>
            </li>
          `
        }
      }

      let topbarHtml = `
        <div class="topbar" style="opacity: 0.9;" id="comex-top">
            <div class="topbar-inner">
                <div class="container-fluid">
                    <ul class="white nav navbar-nav navbar-left">
                        <li>
                            <a class="brand" href="https://iscpif.fr/">
                              <img height="25px" src="/static/img/logo_m_bleu-header.png">
                            </a>
                        </li>
                        <li>
                            <a class="brand" href="/">
                              <span class="glyphicon glyphicon-home white"></span>&nbsp;&nbsp;
                              Community Explorer
                            </a>
                        </li>


                      <!-- MAIN SEARCH/REFINE NAVBAR -->
                      <li id="mapping" class="comex-nav-item">
                          <p class='topbarlink'>
                              <strong>SELECT Keywords AND Scholars</strong>
                          </p>
                      </li>
                      <li id="refine" class="dropdown comex-nav-item">
                          <a class="btn-default nav-inline-selectable"
                             style="padding-top: 1em"
                             onclick='$(this).next(".dropdown-menu").toggle();'
                             >refine<i class="caret"></i></a>
                          <ul class="dropdown-menu">
                              <li>
                                  <a id="addfiltercountry" href="#"
                                      onclick='$(this).parents(".dropdown-menu").toggle();'>
                                      Filter by country</a>
                              </li>
                              <li>
                                  <a id="addfilterkeyword" href="#"
                                     onclick='$(this).parents(".dropdown-menu").toggle();'>
                                     Filter by keyword</a>
                              </li>
                              <li>
                                  <a id="addfiltertag" href="#"
                                     onclick='$(this).parents(".dropdown-menu").toggle();'>
                                     Filter by community tags</a>
                              </li>
                              <li>
                                  <a id="addfilterlaboratory" href="#"
                                     onclick='$(this).parents(".dropdown-menu").toggle();'>
                                     Filter by laboratory</a>
                              </li>
                              <li>
                                  <a id="addfilterinstitution" href="#"
                                     onclick='$(this).parents(".dropdown-menu").toggle();'>
                                     Filter by organization</a>
                              </li>
                          </ul>
                      </li>
                      <li class="comex-nav-item">
                          <a class="topbarlink" id="print" href="#"> <i class="icon-arrow-right icon-white"></i> <strong>CREATE DIRECTORY</strong></a>
                      </li>
                      <li class="comex-nav-item">
                          <p class="topbarlink">
                              <strong>&nbsp;OR&nbsp;</strong>
                          </p>
                      </li>
                      <li class="comex-nav-item">
                          <a class="topbarlink" id="generate" href="#"> <i class="icon-arrow-right icon-white"></i> <strong>MAP</strong></a>
                      </li>
                    </ul>


                    <ul class="white nav navbar-nav navbar-right">
                      ${baseMenus}

                      <!-- USER TOOLBARS (LOGIN/REGISTER/PROFILE/ETC) -->
                      <li class="dropdown">
                        <a id="user-dropdown" href="#" class="navlink dropdown-toggle"
                           data-toggle="dropdown" role="button"
                           aria-haspopup="true" aria-expanded="false">
                           <span class="glyphicon glyphicon-user"></span>
                           User
                           <span class="caret"></span>
                       </a>
                        <ul class="dropdown-menu">
                          ${dropDownContent}
                        </ul>
                      </li>
                    </ul>
                </div>
            </div>
        </div>
      `

      return topbarHtml
    }

    // create in dom
    cC.elts.topbar.create = function(luid, args) {
      let topbarHtml = cmxClt.elts.topbar.prepare(luid, args)

      // append as body's first child
      let topbar = document.createElement('div')
      topbar.innerHTML = topbarHtml
      document.body.insertBefore(topbar, document.body.firstChild)

      // initialize the 2 not-automatic dropdowns (refine is self-contained)
      new Dropdown( document.getElementById('user-dropdown') );
      new Dropdown( document.getElementById('jobs-dropdown') );
    }


    cC.elts.tagcloud.xhrSync = function(fieldName, theCallback) {
      let thresh = 0
      $.ajax({
          type: 'GET',
          dataType: 'json',
          url: "/services/api/aggs?field="+fieldName+"&hapax="+thresh,
          success: theCallback,
          error: function(result) {
              console.warn('tagcloud.xhrSync ('+fieldName+'): jquery ajax error with result', result)
          }
      });
    }

    cC.elts.tagcloud.update = function(tgtDivId, aggFieldName, args) {

      let tgtDiv = document.getElementById(tgtDivId)
      if (! tgtDiv) return false

      if (! args)   args = {}

      var limit = args.limit || 200
      var tagcloudFontsizeMin = args.fontMin ||  1
      var tagcloudFontsizeMax = args.fontMax || 4

      cmxClt.elts.tagcloud.xhrSync( aggFieldName,

        // cb inspired from ProjectExplorer htmlProportionalLabels
        function(elems){
          if(elems.length==0){
            tgtDiv.innerHTML = ""
            return false;
          }
          let resHtml=[]

          let fontSize   // <-- normalized for display

          // we assume already sorted, and we skip 0 which is null
          let frecMax = elems[1].occs
          let frecMin = elems.slice(-1)[0].occs

          let sourceRange = frecMax - frecMin
          let targetRange = tagcloudFontsizeMax - tagcloudFontsizeMin

          for(var i in elems){
              if(i==limit)
                  break
              let labl=elems[i].x
              let frec=elems[i].occs
              if (! labl)
                continue

              if (sourceRange) {
                fontSize = ((frec - frecMin) * (targetRange) / (sourceRange)) + tagcloudFontsizeMin
                fontSize = parseInt(100000 * fontSize)/100000
              }
              else {
                // 1em when all elements have the same freq
                fontSize = 1
              }

              // debug
              // console.log('htmlfied_tagcloud (',labl') freq',frec,' fontSize', fontSize)

              if(typeof labl == "string"){
                  let explorerParam = (aggFieldName == "hashtags") ? "tags" : aggFieldName
                  let explorerFilter = {}
                  explorerFilter[explorerParam] = [labl]
                  let encodedFilter = escape(encodeURIComponent(JSON.stringify(explorerFilter)))
                  let jspart = "onclick=window.open('/explorerjs.html?sourcemode=\"api\"&type=\"filter\"&nodeidparam=\"" + encodedFilter +"\"')"

                  // using em instead of px to allow global x% resize at css box level
                  let htmlLabel = '<span title="'+labl+' ['+frec+']" class="tagcloud-item-front" style="font-size:'+fontSize+'em; line-height:'+fontSize/6+'em; padding:'+2.5*fontSize+'px" '+jspart+'>'+ labl+ '</span>';
                  resHtml.push(htmlLabel)
              }
          }

          tgtDiv.innerHTML = resHtml
          return true;
        })
    }


    // function to login via ajax
    cC.elts.box.postAuthBox = function(formId) {
        var formObj = cmxClt.uform.allForms[formId]

        // inputs should already have correct names: 'email', 'password'
        var formdat = formObj.asFormData();
        // + real captcha value has also been collected by asFormData()

        var nextLocation = '/services/user/profile'

        if (   document.getElementById('auth_modal')
            && document.getElementById('auth_modal').dataset
            && document.getElementById('auth_modal').dataset.next
          ) {
            nextLocation = document.getElementById('auth_modal').dataset.next
          }

        // new-style ajax
        if (window.fetch) {
            fetch('/services/user/login/', {
                method: 'POST',
                headers: {'X-Requested-With': 'MyFetchRequest'},
                body: formdat,
                credentials: "same-origin"  // <= this allows response's Set-Cookie
            })
            // 1st then() over promise
            .then(function(response) {
                // NB 2 promises to unwrap for Fetch to complete which allows the cookie to be set in the OK case
                if (response.ok) {
                  // unwraps the promise => 2nd then()
                  response.text().then( function(bodyText) {
                    // cookie should be set now !
                    console.log("Login was OK, redirecting to profile...")
                    window.location = nextLocation
                  })
                }
                else {
                   // also unwraps the promise => 2nd then()
                   // (we want to use the bodyText as message)
                   // cf. github.com/github/fetch/issues/203
                  response.text().then( function(bodyText) {
                    console.log("Login failed, aborting and showing message")
                    formObj.elMainMessage.innerHTML = bodyText

                    // TODO factorize CSS with old #main_message as a class
                    formObj.elMainMessage.style.color = cmxClt.colorRed
                    formObj.elMainMessage.style.fontSize = "150%"
                    formObj.elMainMessage.style.lineHeight = "130%"
                    formObj.elMainMessage.style.textAlign = "center"
                  })
                }
            })
            .catch(function(error) {
                console.warn('fetch error:'+error.message);
            });
        }

        // also possible using old-style jquery ajax
        else {
            $.ajax({
                contentType: false,  // <=> multipart
                processData: false,  // <=> multipart
                data: formdat,
                type: 'POST',
                url: "/services/user/login/",
                success: function(data) {
                    // console.log('JQUERY got return', data, 'and login cookie should be set')
                    window.location = nextLocation
                },
                error: function(result) {
                    console.warn('jquery ajax error with result', result)
                }
            });
        }
    }

    // our self-made modal open/close function
    // optional params:
    //      nextPage        (default null)
    //      dontOpacifyPage (default false)
    cC.elts.box.toggleBox = function(boxId, params) {
        if (typeof params == 'undefined') params = {}

        var laBox = document.getElementById(boxId)
        if (laBox) {
            if (laBox.style.display == 'none') {
                // show box
                laBox.style.display = 'block'
                laBox.style.opacity = 1

                // optional set data
                if (params.nextPage) laBox.dataset.next = params.nextPage

                // opacify .page element
                if (cC.elts.elPage && !params.dontOpacifyPage) cC.elts.elPage.style.opacity = .2
            }
            else {
                // remove box
                laBox.style.opacity = 0
                setTimeout(function(){laBox.style.display = 'none'}, 300)

                // show .page
                if (cC.elts.elPage && !params.dontOpacifyPage) cC.elts.elPage.style.opacity = ''
            }
        }
        else {
            console.warn("Can't find box with id '"+$boxId+"'")
        }
    }


    // to create an html modal with doors auth (reg or login)
    cC.elts.box.addAuthBox = function(boxParams) {

        // --- default params
        if (!boxParams)                        boxParams = {}
        // mode <=> 'login' or 'register'
        if (boxParams.mode == undefined)       boxParams.mode = 'login'
        // for prefilled values
        if (boxParams.email == undefined)      boxParams.email = ""

        // add a captcha (requires jquery)?
        if (boxParams.insertCaptcha == undefined)
            boxParams.insertCaptcha = false


        var title, preEmail, emailLegend, passLegend, confirmPass, captchaBlock
        // --- template fragments
        if (boxParams.mode == 'register') {
            title = "Register your email"
            preEmail = ""
            emailLegend = "Your email will also be your login for the ISC services."
            passPlaceholder = "Create a password"
            passLegend = "Please make your password difficult to predict."
            confirmPass = `
            <div class="question">
              <div class="input-group">
                <label for="menu_password2" class="smlabel input-group-addon">Password</label>
                <input id="menu_password2" name="password2" maxlength="30"
                       type="password" class="form-control" placeholder="Repeat the password">
              </div>
              <p class="umessage legend red" style="font-weight:bold"></p>
            </div>
            `
        }
        else if (boxParams.mode == 'login') {
            title = "Login"
            preEmail = boxParams.email
            emailLegend = "This email is your login for community explorer"
            passPlaceholder = "Your password"
            passLegend = `Forgot your password ? You can reset it on <a href="${cmxClt.uauth.doorsParam.htscheme}//${cmxClt.uauth.doorsParam.connect}" target="_blank">Doors</a> (our external authentication portal).`
            confirmPass = ""
        }
        else {
            console.error("Unrecognized mode:", boxParams.mode)
        }

        // also perhaps captcha
        if (boxParams.insertCaptcha) {

            captchaBlock = `
                <input id="menu_captcha_hash" name="my-captchaHash" type="text" hidden></input>
                <!--pseudo captcha using realperson from http://keith-wood.name/realPerson.html -->
                <div class="question input-group">
                    <label for="menu_captcha" class="smlabel input-group-addon">Verification</label>
                    <input id="menu_captcha" name="my-captcha"
                           type="text" class="form-control input-lg" placeholder="Enter the 5 letters beside =>"
                           onblur="cmxClt.makeBold(this)" onfocus="cmxClt.makeNormal(this)">
                    <p class="legend legend-float">(A challenge for spam bots)</p>
                </div>
            `
        }
        else {
            captchaBlock=''
        }

        // --- insert it all into a new div
        var myDiv = document.createElement('div')
        myDiv.innerHTML = `
            <div class="modal fade self-made" id="auth_modal" role="dialog" aria-labelledby="authTitle" aria-hidden="true" style="display:none">
              <div class="modal-dialog" role="document">
                <div class="modal-content">
                  <form id="auth_box" enctype="multipart/form-data">
                      <div class="modal-header">
                        <button type="button" class="close" onclick="cmxClt.elts.box.toggleBox('auth_modal')" aria-label="Close">
                          <span aria-hidden="true">&times;</span>
                        </button>
                        <h5 class="modal-title" id="authTitle">${title}</h5>
                      </div>
                      <div class="modal-body">
                        <div class="question">
                          <p class="legend">${emailLegend}</p>
                          <div class="input-group">
                            <!-- email validation onblur/onchange is done by cmxClt.uauth.box.testMailFormatAndExistence -->
                            <label for="menu_email" class="smlabel input-group-addon">Email</label>
                            <input id="menu_email" name="email" maxlength="255"
                                   type="text" class="form-control" placeholder="Your email" value="${preEmail}">

                            <!-- doors return value icon -->
                            <div class="input-group-addon"
                                 title="The email will be checked in our DB after you type and leave the box.">
                              <span class="uicon glyphicon glyphicon-question-sign grey"></span>
                            </div>
                          </div>
                          <!-- doors return value message -->
                          <p class="umessage legend"></p>
                        </div>

                        <div class="question">
                          <div class="input-group">
                            <label for="menu_password" class="smlabel input-group-addon">Password</label>
                            <input id="menu_password" name="password" maxlength="30"
                                   type="password" class="form-control" placeholder="${passPlaceholder}">
                          </div>
                          <p class="legend">${passLegend}</p>
                        </div>
                        <br/>
                        ${confirmPass}
                        <br/>
                        ${captchaBlock}
                        <br/>
                        <div id="menu_message" class="legend"></div>
                      </div>
                      <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="cmxClt.elts.box.toggleBox('auth_modal')">
                            Cancel
                        </button>
                        <!-- submit -->
                        <button type="button" id="menu_form_submit"
                                onclick="cmxClt.elts.box.postAuthBox('auth_box')"
                                class="btn btn-primary">
                            Submit
                        </button>
                      </div>
                  </form>
                </div>
              </div>
            </div>`


        // append on body (no positioning now: it's a fixed overlay anyway)
        var body = document.querySelector('body')
        body.insertBefore(myDiv, body.lastChild)

        // add an enter action like classic submit but ignored when email is focused (because email often has browser's own completion)
        myDiv.onkeydown = function(evt) {
            if (evt.keyCode == 13 && evt.target.id != 'menu_email')
                cmxClt.elts.box.postAuthBox('auth_box')
        }

        // save a ref to it
        cC.elts.box.authBox = document.getElementById('auth_modal')
    }


    // /login box ----------------------------------------------------------


    // generic message box -------------------------------------------------

    // to create an html message modal with doors auth (reg or login)
    // @params
    //    boxId: string
    //    boxTitle: any html
    //    boxContent: any html content
    //    onOK: optional function to perform on clicking the 'OK' button
    //          (apart from closing the box)
    cC.elts.box.addGenericBox = function(boxId, boxTitle, boxContent, onOK) {

        // in a new div
        var myDiv = document.createElement('div')
        myDiv.innerHTML = `
            <div class="modal fade self-made" id="${boxId}" role="dialog" aria-labelledby="${boxId}-title" aria-hidden="true" style="display:none">
              <div class="modal-dialog" role="document">
                <div class="modal-content">
                  <form id="auth_box" enctype="multipart/form-data">
                      <div class="modal-header">
                        <button type="button" class="close" onclick="cmxClt.elts.box.toggleBox('${boxId}')" aria-label="Close">
                          <span aria-hidden="true">&times;</span>
                        </button>
                        <h5 class="modal-title" id="${boxId}-title">
                            <span class="glyphicon glyphicon-comment glyphicon-float-left"></span>&nbsp;&nbsp;
                            ${boxTitle}
                        </h5>
                      </div>
                      <div class="modal-body mini-hero">
                        ${boxContent}
                      </div>
                      <div class="modal-footer">
                        <button type="button" class="btn btn-primary">
                            Ok
                        </button>
                      </div>
                  </form>
                </div>
              </div>
            </div>`


        // append on body (no positioning now: it's a fixed overlay anyway)
        var body = document.querySelector('body')
        body.insertBefore(myDiv, body.lastChild)

        // tie in the custom onclick function
        var functionOnOk
        if (onOK) {
            functionOnOk = function() {
                onOK()
                cmxClt.elts.box.toggleBox(boxId)
            }
        }
        else {
            functionOnOk = function() {
                cmxClt.elts.box.toggleBox(boxId)
            }
        }
        // we assume there's only one .btn
        var okBtn = document.getElementById(boxId).querySelector('.btn')
        okBtn.onclick = functionOnOk
    }

    // cookie warning ------------------------------------------------------

    // NB we use localStorage (kept "forever") to not re-display to same browser
    // POSS use sessionStorage instead

    cC.elts.box.closeCookieOnceForAll = function () {
        cmxClt.elts.box.toggleBox('cookie-div', {'dontOpacifyPage': true})
        localStorage['comex_cookie_warning_done'] = 1
    }

    // to create an html message panel with the legal cookie warning
    // no params (FIXME div id is hard-coded)
    //
    cC.elts.box.addCookieBox = function() {

        // in a new div
        var myDiv = document.createElement('div')
        myDiv.innerHTML = `
        <div id="cookie-div" class="panel panel-success cookie-panel" role="dialog">
            <div class="panel-body">
              <h4 class="center">
                This website uses cookies to adapt the display to your navigation.
              </h4>
              <p class="center">
                Press <span class="framed-text">SPACE</span> to accept or click here:
                <button type="button" class="btn btn-primary"
                        onclick="cmxClt.elts.box.closeCookieOnceForAll()">
                    OK
                </button>
              </p>
            </div>
        </div>`

        // append on body (no positioning: fixed overlay)
        var body = document.querySelector('body')
        body.insertBefore(myDiv, body.lastChild)

        // add a closing action to spacebar
        window.onkeydown = function(evt) {
            if (!localStorage['comex_cookie_warning_done']) {
                if (evt.keyCode == 32) {
                    cmxClt.elts.box.closeCookieOnceForAll()
                    // console.log('space toggleBox')
                }
            }
        }
    }

    return cC

})(cmxClt) ;


console.log("uform related html elements lib load OK")
