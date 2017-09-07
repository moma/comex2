/**
 * @fileoverview
 * Comex Client Module: initialize and expose as *cmxClt* var
 *   -> shared vars for css
 *   -> shared vars and functions for all user forms in *cmxClt.uform* submodule
 *
 * @todo
 *    - package.json
 *
 * @version 1
 * @copyright ISCPIF-CNRS 2016
 * @author romain.loth@iscpif.fr
 *
 */


// initialize and export cmxClt module
var cmxClt = (function() {

    let cC = {}

    // cf corresponding css classes
    cC.colorWhite = '#fff'
    cC.colorRed = '#910'
    cC.colorGreen = '#161'
    cC.colorGrey = '#554'
    cC.colorLGrey = '#ddd'
    cC.colorOrange = '#F96'
    cC.colorDarkerOrange = '#C73'
    cC.colorBlue = '#23A'


    cC.strokeWhite = ".8px .8px #fff, -.8px -.8px #fff, -.8px .8px #fff, .8px -.8px #fff"
    cC.strokeGrey = ".8px .8px #333, -.8px -.8px #333, -.8px .8px #333, .8px -.8px #333"
    cC.strokeBlack = ".5px .5px #000, -.5px -.5px #000, -.5px .5px #000, .5px -.5px #000"
    cC.strokeDeepGrey = "3px 3px 4px #333,-3px 3px 4px #333,-3px -3px 4px #333,3px -3px 4px #333"


    // the target columns in DB: tuple (name, mandatory, group, type, section)
    // at = array of text
    // t = text
    // m = select menu
    // f = blob
    cC.COLS = [
        ["keywords",               true,       "plsfill", "at", "map_infos"],
        // ==> *keywords* table
        ["hashtags",              false,       "plsfill", "at", "map_infos"],
        // ==> *hashtags* table

        ["doors_uid",              true,       "auto"   , "t",  null],
        ["email",                  true,       "plsfill", "t",  "login_infos"],
        ["hon_title",             false,       "plsfill", "t",  "basic_infos"],
        ["first_name",             true,       "plsfill", "t",  "basic_infos"],
        ["middle_name",           false,       "pref",    "t",  "basic_infos"],
        ["last_name",              true,       "plsfill", "t",  "basic_infos"],
        ["country",                true,       "plsfill", "t",  "basic_infos"],
        ["initials",               true,       "pref",    "t",  null],
        ["position",               true,       "pref",    "t",  "org_infos"],
        ["interests_text",        false,       "pref",    "t",  "other_infos"],
        ["gender",                false,       "plsfill", "m",  "other_infos"],
        ["job_looking",           false,       "pref"   , "m",  "map_infos"],
        ["job_looking_date",      false,       "pref"   , "d",  "map_infos"],
        ["home_url",              false,       "plsfill", "t",  "other_infos"],
        ["pic_url",               false,       "pref"   , "t",  "other_infos"],
        ["pic_file",              false,       "pref"   , "f",  "other_infos"],
        // ==> *scholars* table


        // org field
        //   => name, acro in one field "label": #lab_label, #inst_label
        //   => all other fields
        //        - are optional
        //        - if present, should be named: lab|inst + '_' + colname
        //   => TODO org details suggestions
        //      url, loc should have autofill when name or acro is chosen
        //   => POSS org <-> org suggestions
        //      once a lab is filled, we could propose the institution
        ["lab_label",              false,       "plsfill", "t", "org_infos"],
        ["lab_locname",            false,       "pref", "t", "org_infos"],
        ["inst_label",             false,       "pref", "t", "org_infos"],
        ["inst_type",              false,       "pref", "m", "org_infos"],
        // ["lab_code",            false,       "pref", "t", "org_infos"],
        // ["lab_url",             false,       "pref", "t", "org_infos"],
        // ["inst_locname",        false,       "pref"   , "t", "org_infos"],
        // ["inst_url",            false,       "pref"   , "t", "org_infos"],
        // ==> *orgs* table via pretreatment org is inst or org is lab
    ]

    // group "auto"    === filled by controllers
    // group "plsfill" === filled by user, ideally needed for a complete profile
    // group "pref"    === filled by user but not needed at all

    cC.miniSanitize = function(aString) {
        return aString.replace(/[^A-z0-9, :\(\)-]/, ' ').replace(/^ +| +$/, '')
    }

    cC.makeRandomString = function (nChars) {
      var rando = ""
      var possible = "abcdefghijklmnopqrstuvwxyz0123456789";
      var len = possible.length
      for( var i=0; i < nChars; i++ )
          rando += possible.charAt(Math.floor(Math.random() * len));
      return rando
    }

    cC.ulListFromLabelsArray = function (cplArray, ulClassList, message) {
        ulClasses=["minilabels"].concat(ulClassList).join(" ")
        var resultHtml = ""
        if (message) {
            resultHtml = cC.miniSanitize(message)
        }
        resultHtml += '<ul class="'+ulClasses+'">'
        for (var i in cplArray) {
            var fname = cplArray[i][0]
            var flabel = cplArray[i][1]

            // to open any collapsible containing the label and input
            var openFun = 'return cmxClt.uform.gotoField(\''+fname+'\')'

            // debug onclick fun
            // console.log("openFun", openFun)

            // link works if anchorLabels was run
            resultHtml += '<li class="minilabel"><div onclick="'+openFun+'">'+flabel+'</div></li>'
        }
        resultHtml += '</ul>'
        return resultHtml
    }

    // basic inputs get normal on focus
    cC.makeNormal = function (elt) {
        elt.style.fontWeight = "normal"
    }

    // basic inputs get bold on blur
    cC.makeBold = function (elt){
      if (elt.value != "")   elt.style.fontWeight = "bold"
    }

    // insert after
    // cf. stackoverflow.com/questions/4793604
    cC.insertAfter = function(referenceNode, newNode) {
        referenceNode.parentNode.insertBefore(
            newNode, referenceNode.nextSibling
        )
    }

    // find ancestor
    // cf. stackoverflow.com/questions/22119673
    cC.findAncestor = function(elt, cls) {
        // console.log("findAncestor starting from", elt.id)
        while ((elt = elt.parentElement) && !elt.classList.contains(cls) && elt);
        // console.log("findAncestor returning", elt)
        return elt
    }

    // ============================================
    // cmxClt.uform: user forms class and functions
    // ============================================

    cC.uform = {}

    // a class var with all initialized forms on the page
    cC.uform.allForms = {}

    // functions
    cC.uform.initialize
    cC.uform.testFillField
    cC.uform.simpleValidateAndMessage
    cC.uform.gotoField
    cC.uform.multiTextinput
    cC.uform.stampTime  // <= POSS replace by sql stamp

    // dates up to 2049/12/31
    cC.uform.validDate = new RegExp( /^20[0-4][0-9]\/(?:0?[1-9]|1[0-2])\/(?:0?[1-9]|[1-2][0-9]|3[0-1])$/)


    // function definitions
    // =====================

    // multiTextinput
    //
    // A textinput element containing multiple values like keywords
    //   => UI shows input where user enters words one by one
    //   => validated words become removable "boxes"
    //   => result is an array of texts in memory, concatenated at mtiCollect()
    cC.uform.multiTextinput = function (fName, otherMtiParams, aUForm) {
        // console.debug ("multiTextinput args:", fName, otherMtiParams, aUForm)

        var perhapsPreviousValues = otherMtiParams.prevals
        var perhapsColor = otherMtiParams.color
        var perhapsReadonly = otherMtiParams.readonly

        // HTML elt to insert tag boxes around
        var refElt = null

        // new multiTextinput slot in this form, for reference
        aUForm.mti[fName] = {
                             // new array for full result
                             'stock': [],
                             // specified in params or 0
                             'minEntries': typeof otherMtiParams.minEntries != "undefined" ? otherMtiParams.minEntries : 0
                           }

        // there must be a normal text input
        var normalInput = document.getElementById(fName)
        // (and it can use autocomplete)

        // refElt is where we show the boxes and messages
        refElt = normalInput

        refElt.style.marginBottom = 0

        // shows a box and saves the input value in mti.stock
        var pushTagbox = function(event) {
            // debug
            // console.log ('pushTagbox from event' + event.type)

            var asIsValue = normalInput.value

            if (asIsValue != '') {
                // maybe several values from cache (comma is reserved as separator)
                var subValues = asIsValue.split(/,/)
                for (var i in subValues) {
                    var newValue = subValues[i]

                    // "let" so that it's unique for each i
                    // (this unique pointer is useful in newBoxClose)
                    let newBox = document.createElement('div')

                    // move the value
                    normalInput.value = ''
                    newBox.textContent = newValue

                    // and save it
                    var nSaved = aUForm.mti[fName].stock.push(newValue)

                    // normal case gets a close button x
                    if (!perhapsReadonly) {
                        var newBoxClose = document.createElement('div')
                        newBoxClose.classList.add('box-highlight-close')
                        newBoxClose.classList.add('operation')
                        newBoxClose.innerHTML = '<span class="glyphicon glyphicon-remove"></span>'

                        var closeBox = function() {
                            // start transition
                            newBox.style.opacity = 0

                            // remove value from stock
                            var i = 0
                            for (i in aUForm.mti[fName].stock){
                                if (aUForm.mti[fName].stock[i] == newValue) {
                                    break ;
                                }
                            }
                            aUForm.mti[fName].stock.splice(i, 1)

                            // signal form change
                            aUForm.elForm.dispatchEvent(new CustomEvent('change'))

                            // remove box
                            setTimeout(function(){newBox.style.display = 'none'}, 300)

                            // console.debug("droptagbox", aUForm.id aUForm.mti[fName].stock.length, aUForm.mti[fName].stock)
                        }

                        newBox.insertBefore(newBoxClose, newBox.firstChild)
                        newBoxClose.onclick = closeBox
                    }

                    // show the box
                    newBox.classList.add("box-highlight")
                    if (perhapsColor) {
                        newBox.style.backgroundColor = perhapsColor
                    }

                    cC.insertAfter(refElt, newBox)

                    // console.debug("pushTagbox", aUForm.id, aUForm.mti[fName].stock.length, aUForm.mti[fName].stock)
                }
            }
        }

        // when re-entering previously saved values at init
        if (   perhapsPreviousValues
            && perhapsPreviousValues.length) {
            for (var i in perhapsPreviousValues) {
                normalInput.value = perhapsPreviousValues[i]
                pushTagbox()
            }
        }

        // bind it to 'blur', 'change' and ENTER
        normalInput.onblur = pushTagbox
        normalInput.onchange = pushTagbox
        normalInput.onkeydown = function (ev) {

            // perhaps now there's a jquery-ui autocomplete
            var hasAutocomplete = $(normalInput).data('ui-autocomplete')

            if (ev.keyCode == 13) {
                // ENTER
                if ( !hasAutocomplete
                     ||
                     !hasAutocomplete.menu.active) {

                    pushTagbox()
                }
            }
            else if (ev.which == 27) {
                // ESC
                normalInput.value = ""
            }
        }
    }

    // initialize
    // -----------
    // @params:
    //   - mainMessageId
    //   - timestampId
    //   - submitBtnId
    //   - multiTextinputs: [(...multiTextinputsParams...)]

    // exposed members:
    // theForm.id  <=> the HTML #id value
    // theForm.elForm <=> the HTML <form> element
    // theForm.mti.stock <=> all tags entered via multiTextinputs
    // theForm.asFormData() <=> all values asFormData...
    // theForm.preSubmitActions <=> functions to call before sending data

    // NB if you send the data by a classic formElt.submit() or use asFormData(), preSubmitActions will already be called

    cC.uform.Form = function(aFormId, aValidationFun, fParams) {

        // new "obj"
        var myUform = {}

        // keep a ref to it in global scope
        cC.uform.allForms[aFormId] = myUform

        // exposed vars that may be used during the interaction
        myUform.id = aFormId
        myUform.elForm = document.getElementById(aFormId)
        myUform.asFormData = function() {

            // invoke preSubmitActions to collect widget data (captcha, mtis)
            for (var i in myUform.preSubmitActions) {
                myUform.preSubmitActions[i]()
            }
            return new FormData(myUform.elForm)
        }

        // an array of functions to call before sending form (submit or fetch)
        // NB *synchronous* functions only !!
        myUform.preSubmitActions = []

        // events
        if (aValidationFun) {
            myUform.elForm.onkeyup = function(event) {
                // console.info('..elForm '+myUform.id+' event:'+event.type)
                return aValidationFun(myUform)
            }
            myUform.elForm.onchange = myUform.elForm.onkeyup
            myUform.elForm.onblur = myUform.elForm.onkeyup
        }

        // main interaction elements, if present
        // ------------------------
        if (!fParams)        fParams = {}
        var mainMessageId, timestampId, buttonId

        mainMessageId = fParams.mainMessageId || 'main_message'
        timestampId   = fParams.timestampId   || 'form_timestamp'
        submitBtnId   = fParams.submitBtnId   || 'form_submit'

        myUform.elMainMessage = document.getElementById(mainMessageId)
        myUform.elTimestamp = document.getElementById(timestampId)
        myUform.elSubmitBtn = document.getElementById(submitBtnId)

        // optional: init mtis
        if (fParams.multiTextinputs) {
            myUform.mti = {}  // arrays of inputs metadata per fieldName
            for (var i in fParams.multiTextinputs) {
                // creates mti.stock entries and mti elements and events
                cC.uform.multiTextinput(
                    fParams.multiTextinputs[i].id,  // ex "keywords"
                    fParams.multiTextinputs[i],     // ex color, previous values,
                                                    //    and/or min entries
                    myUform
                )
            }

            let mtiCollect = function(field) {
              return function() {
                let exitStatus = true
                let errMsg = ''

                if (myUform.mti[field].stock.length < myUform.mti[field].minEntries) {
                  let exitStatus = false
                  let label = document.querySelectorAll(`label[for=${field}]`) || field
                  errMsg = `Please provide at least ${myUform.mti[field].minEntries} entries for the field ${label}`
                }
                document.getElementById(field).value =  myUform.mti[field].stock.join(',')
                console.debug(`  mti collected field "${field}"
                                 new value = ${document.getElementById(field).value}`)

                console.log('collecting multiTextinputs status:', exitStatus)
                return {'ok': exitStatus, 'errMsg': errMsg}
              }
            }

            // mti collectors: a function per multiTextinput to check out values
            for (var field in myUform.mti) {
              myUform.preSubmitActions.push( mtiCollect(field) )
            }

            // Here we overload the submit() function with preSubmitActions
            // (submit() is more practical to overload than the submit *event*)
            // (preSubmitActions are as evaluated at submit invocation time)

            // NB: for the moment, the only preSubmitActions are mti collectors,
            // but it may become other things in the future -- they just have to
            // return a couple (successBool, errMsg)

            // we keep classicSubmit() as member of the html form
            // (preserves its invocation context)
            myUform.elForm.classicSubmit = myUform.elForm.submit

            myUform.elForm.submit = function() {
                let goodToGo = true
                let errorMsgs = []

                // 1) invoke any (synchronous) preparation functions
                for (var i in myUform.preSubmitActions) {
                    let thisStatus = myUform.preSubmitActions[i]()
                    goodToGo = goodToGo && thisStatus.ok
                    if (! thisStatus.ok) {
                      errorMsgs.push(thisStatus.errMsg)
                    }
                }

                // 2) if everything ok, proceed with normal submit
                if (goodToGo) {
                  console.log("go classicSubmit")
                  myUform.elForm.classicSubmit()
                }
                else {
                  let errorMsg = errorMsgs.join('<br/>')
                  myUform.elMainMessage.innerHTML = `<span class='orange glyphicon glyphicon-exclamation-sign glyphicon-float-left'></span><p>${errorMsg}</p>`
                  myUform.elMainMessage.classList.remove('faded')

                  // unlock the button
                  elSubmitBtn.disabled = false
                }

            }
        }
        return myUform
    }

    // testFillField
    // --------------
    // diagnostic over COLS, good to use in validation funs
    //
    // checks if mandatory fields are filled
    // checks if other plsfill ones are filled
    // highlights labels of missing mandatory fields
    cC.uform.testFillField = function (aUForm, params) {
        // "private" copy
        var wholeFormData = new FormData(aUForm.elForm)

        // our return values
        var valid = true
        var mandatoryMissingFields = []
        var otherMissingFields = []

        // default params
        if (!params)                           params = {}
        // bool
        if (params.doHighlight == undefined)   params.doHighlight = true
        if (params.fixResidue == undefined)    params.fixResidue = false
        // $
        if (!params.filterGroup)               params.filterGroup = "plsfill"
        // @
        if (!params.ignore)                    params.ignore = []
        if (!params.cols)                      params.cols = cC.COLS

        // let's go
        for (var i in params.cols) {
          //   console.info("testFillField COLS["+i+"]", cC.COLS[i])

          var fieldName = params.cols[i][0]
          var mandatory = params.cols[i][1]
          var fieldGroup = params.cols[i][2]
          var fieldType = params.cols[i][3]

          var actualValue = wholeFormData.get(fieldName)

          // python residue ~~~> can correct on the fly
          // --------------
          // POSS better strategy ?
          if (params.fixResidue) {
            // "None" as a string
            if (actualValue == "None") {
                actualValue = null
                document.getElementById(fieldName).value = ""
            }
            // arrays of text: rm brackets and any squotes
            if (fieldType == "at" && actualValue
                  && actualValue.charAt(0) == '['
                  && actualValue.charAt(actualValue.length-1) == "]") {
                actualValue = actualValue.replace(/[\[\]']/g,'')
                document.getElementById(fieldName).value = actualValue
            }
          }

          // filled or not filled
          // --------------------

          // skipping params.ignore and non-filterGroup elements
          var ignoreFlag = false
          for (var j in params.ignore) {
            if (fieldName == params.ignore[j]) {
                ignoreFlag = true
                break
            }
          }
          if (ignoreFlag || fieldGroup != params.filterGroup) continue ;
          //                                                    skip

          // otherwise get a human-readable label
          var labelElt = document.querySelector('label[for='+fieldName+']')
          var fieldLabel = labelElt ? labelElt.innerText : fieldName

          // alternative null values
          if (actualValue == "") {
              actualValue = null
          }

          // filled values from mti lists are handled here during the form use
          // (NB: check before submit is self-handled with a preSubmitAction)
          if (fieldType == "at" && !actualValue
             && aUForm.mti[fieldName].stock.length) {
            actualValue = aUForm.mti[fieldName].stock.join(',')
            // debug
            // console.log('recreated multiTextinput value', actualValue)
          }

          // debug
          // console.log(
          //              "cmxClt.testFillField: field", fieldName,
          //              "actualValue:", actualValue
          //             )

          // test mandatory -----------------
          if (mandatory &&
                (actualValue == null
                  ||
                 (fieldType == 'at'
                  && aUForm.mti[fieldName].stock.length < aUForm.mti[fieldName].minEntries)
                )
              ) {
              mandatoryMissingFields.push([fieldName, fieldLabel])
              valid = false

              if (params.doHighlight && labelElt) {
                  labelElt.style.backgroundColor = cC.colorOrange
              }
          }


          // test benign
          // may be missing but doesn't affect valid
          else if (actualValue == null) {
              otherMissingFields.push([fieldName, fieldLabel])
            //   console.log("otherMissingField", fieldName)
          }

          else if (params.doHighlight && labelElt) {
              labelElt.style.backgroundColor = ""
          }
      } // end for val in params.cols

        // return full form diagnostic and field census
        return [  valid,
                  mandatoryMissingFields,
                  otherMissingFields         ]
    }

    // simple timestamp if needed
    cC.uform.stampTime = function (aUForm) {
        var now = new Date()
        aUForm.elTimestamp.value = now.toISOString()
    }


    // diagnosticParams are optional
    //
    cC.uform.simpleValidateAndMessage = function (aUform, diagnosticParams) {

        var diagnostic = cmxClt.uform.testFillField(aUform,
                                                    diagnosticParams)

        var isValid = diagnostic[0]
        var mandatoryMissingFields = diagnostic[1]
        var optionalMissingFields = diagnostic[2]

        if (isValid) {
            aUform.elMainMessage.innerHTML = "<span class='green glyphicon glyphicon-check glyphicon-float-left' style='float:left;'></span><p>OK thank you! <br/>(we have all the fields needed for the mapping!)<br/>(don't forget to SAVE!)</p>"

            aUform.elMainMessage.classList.add('faded')
        }
        else {
            aUform.elMainMessage.innerHTML = "<span class='orange glyphicon glyphicon-exclamation-sign glyphicon-float-left'></span><p>There are some <br/> important missing fields</p>"

            aUform.elMainMessage.classList.remove('faded')
        }

        // list of missing fields
        aUform.elMainMessage.innerHTML += cmxClt.ulListFromLabelsArray(mandatoryMissingFields, ['orange'])

        if (optionalMissingFields.length) {
            aUform.elMainMessage.innerHTML += cmxClt.ulListFromLabelsArray(
                    optionalMissingFields,
                    ['white'],
                    "You may also want to fill:"
                )
        }
    }


    // gotoField
    // (assumes nothing)
    // (side-effect: opens the corresponding panel)
    cC.uform.gotoField = function (fName) {
        // debug
        // console.log('goto fName', fName)

        var fieldElt = document.getElementById(fName)

        // open panel if it is closed
        var ourPanel = cC.findAncestor(fieldElt, "panel-collapse")
        if (ourPanel && ! ourPanel.classList.contains('in')) {
            // POSS use cols with key/value structure to use cols[fName] instead of looking for i
            var theCol = -1
            for (var i in cC.COLS) {
                if (fName == cC.COLS[i][0]) {
                    theCol = i
                    break
                }
            }
            var ccSection = cC.COLS[i][4]

            // debug
            // console.log('ccSection', ccSection)

            if (ccSection) {
                // click the corresponding toggler
                document.getElementById('ccsection_toggle_'+ccSection).click()
            }
        }
        // now go to the field itself (actually, 120px above)
        // --------------------------------------------------
        fieldElt.scrollIntoView(true)
        window.scrollTo(window.scrollX, window.scrollY - 120)
    }

    // ===================================================================
    // additional controllers for detailed forms like /register, /profile
    // ===================================================================

    // exposed functions and vars
    cC.uform.checkBlob
    cC.uform.checkShowPic
    cC.uform.showPic
    cC.uform.createInitials
    cC.uform.checkJobDateStatus
    cC.uform.fName = document.getElementById('first_name')
    cC.uform.mName = document.getElementById('middle_name')
    cC.uform.lName = document.getElementById('last_name')
    cC.uform.jobLookingDateStatus = false


    // function definitions, private vars and event handlers
    // ======================================================


    // image fileInput ~~~> display image
    // ----------------------------------
    var fileInput = document.getElementById('pic_file')
    var showPicImg = document.getElementById('show_pic')
    var boxShowPicImg = document.getElementById('box_show_pic')
    var picMsg = document.getElementById('picture_message')
    var imgReader = new FileReader();

    cC.uform.showPic = function(aSrc) {
        showPicImg.src = aSrc

        // prepare max size while preserving ratio
        var realValues = window.getComputedStyle(showPicImg)
        var imgW = realValues.getPropertyValue("width")
        var imgH = realValues.getPropertyValue("height")

        // debug
        // console.log("img wid", imgW)
        // console.log("img hei", imgH)

        if (imgW > imgH) {
            showPicImg.style.width  = "100%"
            showPicImg.style.height  = "auto"
        }
        else {
            showPicImg.style.width  = "auto"
            showPicImg.style.height = "100%"
        }

        // now show it
        boxShowPicImg.style.display = 'block'
        // possible re-adjust outerbox ?
    }

    // checkBlob: a generic onchange checker for file inputs
    // ---------
    // returns a couple [successBool, message]
    //
    // optional args:
    //  args.maxSize
    //  args.expectedMime
    //  args.expectedFileExt
    cC.uform.checkBlob = function (aFileInput, args) {
      if (! args)     args = {}
      // 2MB default maxSize for pdf
      let maxSize = 2097152
      if (args.maxSize)    maxSize = args.maxSize

      let theFile = aFileInput.files[0]
      if (!theFile) {
        return [false, 'no file']
      }
      else {
        // check size
        if (theFile.size > maxSize) {
          // human-readable values for message
          let kBMax = parseInt(maxSize/1024)
          let kBReal = parseInt(theFile.size/1024)
          return [false, `file too big (max=${kBMax}kB, actual=${kBReal}kB)`]
        }

        // optional check mime
        if (args.expectedMime) {
          if (theFile.type != args.expectedMime) {
            return [false, `file needs correct mimetype "${args.expectedMime}"`]
          }
        }

        // optional check extension
        if (args.expectedFileExt) {
          let extMatch = theFile.name.match(/\.([^.]{1,6})$/)
          if (!extMatch) {
            return [false, `filename has no extension (expected: "${args.expectedFileExt}")`]
          }
          else {
            let ext = extMatch[1]
            if (ext != args.expectedFileExt) {
              return [false, `file needs correct extension ${args.expectedFileExt}`]
            }
          }
        }
        return [true, "file OK"]
      }
    }

    // POSSible use smaller functions: checkBlob + file read + GUI effects
    cC.uform.checkShowPic = function (aForm, doHighlight) {
        // TEMPORARY initial size already 500 kB, user has to do it himself
        var max_size = 524288

        // TODO  max source image size before resizing
        //       see libs or stackoverflow.com/a/24015367
        // 4 MB
        // var max_size = 4194304

        // always reset style and width/height calculations
        boxShowPicImg.style.display = 'none'
        showPicImg.style.display  = ""
        showPicImg.style.width  = ""
        showPicImg.style.height = ""

        if (fileInput.files) {
            var theFile = fileInput.files[0]

            // debug
            console.log(theFile.name, "size", theFile.size, theFile.lastModifiedDate)

            if (theFile.size > max_size) {
              // msg pb
              picMsg.innerHTML = "The picture is too big (500kB max)!"
              picMsg.style.color = cmxClt.colorRed
            }
            else {
              // msg ok
              picMsg.innerHTML = "Picture ok"
              picMsg.style.color = cmxClt.colorGreen

              // to show the pic when readAsDataURL
              imgReader.onload = function() {
                  cC.uform.showPic(imgReader.result)
              }
              // create fake src url & trigger the onload
              imgReader.readAsDataURL(theFile);
            }
        }
        else {
            console.warn("skipping testPictureBlob called w/o picture in fileInput")
        }
    }

    // first, middle & last name ~~~> initials
    // ----------------------------------------
    var nameInputs = [cC.uform.fName,
                      cC.uform.mName,
                      cC.uform.lName]

    var initialsInput = document.getElementById('initials')

    cC.uform.createInitials = function() {
      var apparentInitials = ""
        nameInputs.forEach ( function(nameInput) {
          var txt = nameInput.value
          if (txt.length) {
            if(/[A-Z]/.test(txt)) {
              var capsArr = txt.match(/[A-Z]/g)
              for (var i in capsArr) {
                apparentInitials += capsArr[i]
              }
            }
            else {
              apparentInitials += txt.charAt(0)
            }
          }
        }) ;
      // update the displayed value
      initialsInput.value = apparentInitials
    }

    // handlers: names to initials
    nameInputs.forEach ( function(nameInput) {
      if (nameInput) {
        nameInput.onkeyup = cC.uform.createInitials
        nameInput.onchange = cC.uform.createInitials
      }
    })

    // handler: show middlename button
    var mnDiv = document.getElementById('group-midname')

    if (mnDiv) {
        var mnLabel = mnDiv.querySelector('label')

        var mnBtn = document.getElementById('btn-midname')
        var mnBtnIcon = document.getElementById('btn-midname-icon')

        if(!mnBtn) {
            console.warn('group-midname without btn-midname')
            mnDiv.style.display = 'block'
        }
        else {
            mnBtn.onclick= function() {

              if (mnDiv.style.display == 'none') {
                mnDiv.style.display = 'table'
                mnLabel.style.color="#23A"
                setTimeout(function(){mnLabel.style.color=""}, 2000)

                mnBtnIcon.classList.remove("glyphicon-plus")
                mnBtnIcon.classList.add("glyphicon-arrow-down")
                mnBtnIcon.style.color="#23A"
                mnBtnIcon.style.textShadow = cC.strokeBlack
              }

              else {
                mnDiv.style.display = 'none'

                mnBtnIcon.classList.remove("glyphicon-arrow-down")
                mnBtnIcon.classList.add("glyphicon-plus")
                mnBtnIcon.style.color=""
                mnBtnIcon.style.textShadow = ""
              }
            }
        }
    }

    cC.uform.displayMidName = function() {
        mnDiv.style.display = 'table'
        mnLabel.style.color="#23A"
        setTimeout(function(){mnLabel.style.color=""}, 2000)

        mnBtnIcon.classList.remove("glyphicon-plus")
        mnBtnIcon.classList.add("glyphicon-arrow-down")
        mnBtnIcon.style.color="#23A"
        mnBtnIcon.style.textShadow = cC.strokeBlack
    }

    cC.uform.hideMidName = function() {
        mnDiv.style.display = 'none'

        mnBtnIcon.classList.remove("glyphicon-arrow-down")
        mnBtnIcon.classList.add("glyphicon-plus")
        mnBtnIcon.style.color=""
        mnBtnIcon.style.textShadow = ""
    }


    // jobLookingDateStatus ~~~> is job date a valid date?
    // ---------------------------------------------------
    var jobBool = document.getElementById('job_looking')
    var jobDate = document.getElementById('job_looking_date')
    var jobDateMsg = document.getElementById('job_date_message')
    var jobLookingDiv = document.getElementById('job_looking_div')

    cC.uform.checkJobDateStatus = function () {
      cC.uform.jobLookingDateStatus = (jobBool.value == "0" || cC.uform.validDate.test(jobDate.value))
      if (!cC.uform.jobLookingDateStatus) {
          jobDateMsg.style.color = "#888"
          jobDateMsg.innerHTML = '<small>format is YYYY/MM/DD</small>'
      }
      else {
          jobDateMsg.style.color = cmxClt.colorGreen
          jobDateMsg.innerHTML = '<small>Ok valid date!</small>'
      }
    }

    // handler: show jobLookingDiv
    if (jobBool && jobDate) {
        jobBool.onchange = function() {
            // shows "Until when"
            if(this.value=='1'){
                jobLookingDiv.style.display = 'block'
            }
            else {
                jobLookingDiv.style.display='none'
                jobDate.value=''
            }
        }
        jobDate.onkeyup = cC.uform.checkJobDateStatus
        jobDate.onchange = cC.uform.checkJobDateStatus
    }


    // ========= end of advanced form controls ===========

    return cC
}()) ;

console.log("user shared load OK")
