/**
 * @fileoverview
 * Can add a comex (communityexplorer.org) job ad form
 * Provides a function to validates the form
 *                     and prepare DB save into cmxClt.job.COLS
 *
 * @todo
 *    - package.json
 *
 * @version 1
 * @copyright ISCPIF-CNRS 2017
 * @author romain.loth@iscpif.fr
 *
 * @requires comex_user_shared
 */


jobCols = [
     ["mission_text",           true,       "plsfill", "t",     null    ],
     ["keywords",               true,       "plsfill", "at",    null    ],
     ["recruiter_org_text",     true,       "plsfill", "t",     null    ],
     ["email",                  true,       "plsfill", "t",     null    ],
     ["job_valid_date",         true,       "plsfill", "d",     null    ]
   ]


// args has 4 optional slots:
//   'user': a uinfo object
//   'job': a job as jsgrid item
//   'can_edit': a boolean
//   'alt_submit': an optional alternate submit button id
function createJobForm(containerId, args) {
  let tgtElt = document.getElementById(containerId)
  if (! tgtElt) {
    console.error(`createJobForm: couldn't find target element ${containerId}`)
    return false
  }

  let rw = args.can_edit ? '' : 'readonly'
  console.log("createJobForm rw:", rw)
  console.log("createJobForm args:", args)

  let optionalSubmit = ''

  if (args.can_edit && ! args.alt_submit) {
    optionalSubmit = `
        <!-- == S U B M I T == -->
        <!-- button instead of input.submit to validate before real submit action -->
        <!-- also remember stackoverflow.com/a/3315016/2489184 -->
        <div class="question">
            <button class="btn btn-lg btn-success" style="float:right"
                    id="form_submit" type=button disabled
                    onclick="validateJobForm('comex_job_form')">
                    Submit your form
            </button>
        </div>
        `
  }

  let pdfSection = ''
  // previous pdf => add link to it
  if (args.job && args.job.pdf_fname && args.job.pdf_fname.length) {
    pdfSection = `
    <div class="question">
      <p id="previous-pdf" class="mega-legend">
        <span class="glyphicon glyphicon-file"></span>
        Consult the
        <a href="/data/shared_user_files/${args.job.pdf_fname}" target="_blank">
          provided job description
        </a> (pdf).
      </p>
    </div>
    `
  }
  // can edit => add pdf file input
  if (args.can_edit) {
    pdfSection += `
        <div class="question">
          <div class="input-group">
            <label for="pdf_attachment" class="smlabel input-group-addon"><small>Job description (PDF)</small></label>
            <input id="pdf_attachment" name="pdf_attachment" maxlength="10" ${rw}
                   type="file" class="form-control" onchange="customOnChangePdf()">
          </div>
          <p class="legend">
            You can ${(args.job && args.job.pdf_fname && args.job.pdf_fname.length) ? "<b>replace</b> the pdf" : "add an optional pdf"} document here.
          </p>
        </div>`
  }

  let jobHtml = `
    <form id="comex_job_form" enctype="multipart/form-data"
          method="post" onsubmit="console.info('submitted')">

        <!-- MISSION & KEYWORDS -->
        <h3 class="formcat">Missions and keywords</h3>

        <div class="question">
         <div class="input-group">
           <label for="mission_text" class="input-group-addon">
             Job mission
           </label>

           <textarea id="mission_text" name="mission_text" maxlength="2400"
                     rows="7" style="resize:none"
                     class="form-control" placeholder="Describe the job here, along with main mission or tasks and required skills"
                     onblur="cmxClt.makeBold(this)" onfocus="cmxClt.makeNormal(this)" ${rw}
                     >${args.job ? args.job.mission_text : ''}</textarea>
         </div>
         <p class="legend">~30 lines max (2400 chars)</p>
        </div>

        <div class="question">
         <div class="input-group tagbox-container">
           <label for="keywords" class="smlabel input-group-addon tagbox-label">Key subjects</label>

           <input id="keywords" name="keywords" maxlength="350" ${rw} ${args.can_edit ? '' : 'style="display:none"'}
                  type="text" class="form-control autocomp" placeholder="Add a keyword here">
         </div>
        </div>


        <!-- ORG DESCRIPTION & CONTACT MAIL -->
        <h3 class="formcat">Organization and contact</h3>


        <div class="question">
         <div class="input-group">
           <label for="recruiter_org_text" class="input-group-addon">
             About the<br>recruiting<br>organization
           </label>

           <textarea id="recruiter_org_text" name="recruiter_org_text" maxlength="2400"
                     rows="7" style="resize:none" ${rw}
                     class="form-control" placeholder="Describe the recruiting company or organization"
                     onblur="cmxClt.makeBold(this)" onfocus="cmxClt.makeNormal(this)"
                     >${args.job ? args.job.recruiter_org_text : ''}</textarea>
         </div>
         <p class="legend">Optional, ~30 lines max (2400 chars)</p>
        </div>

        <div class="question">
         <div class="input-group">
           <label for="email" class="smlabel input-group-addon">
             Contact Email
           </label>
           <input id="email" name="email" maxlength="255"
                  type="text" class="form-control" ${rw}
                  value="${args.job ? args.job.email : (args.user ? args.user.email : '')}">
          </div>
          <p class="legend">Your email or any other contact email for the job.</p>
        </div>

        <div class="question">
          <div class="input-group">
            <label for="job_valid_date" class="smlabel input-group-addon"><small>Job available until ?</small></label>
            <input id="job_valid_date" name="job_valid_date" maxlength="10" ${rw}
                   type="text" class="form-control" placeholder="ex: 2017/09/30"
                   value="${args.job ? args.job.job_valid_date.replace(/-/g,'/') : ''}">
          </div>
          <p class="legend">You can always remove the job manually before this date.</p>
        </div>

        ${pdfSection}

        <!-- hidden input for associated user id -->
        <input id="uid" name="uid" type="text" hidden
              value="${args.user ? args.user.luid : ''}">
        </input>

        <!-- hidden input for current job id (if edit) -->
        <input id="jobid" name="jobid" type="text" hidden
              value="${args.job ? args.job.jobid : ''}">
        </input>

        ${optionalSubmit}
    </form>
  `

  // replace in DOM
  tgtElt.innerHTML = jobHtml

  // initialize form controllers
  let jobadForm = cmxClt.uform.Form(
    "comex_job_form",
    function(){},   // onchange
    { 'submitBtnId': args.alt_submit || 'form_submit',
      'multiTextinputs':[{
        'id':'keywords',
        'readonly': ! args.can_edit,
        'prevals': args.job && args.job.keywords ? args.job.keywords.split(/,/) : null
      }]
    }
  )

  if (args.can_edit) {
    jobadForm.elSubmitBtn.disabled = false
  }

  // initialize autocomplete on keywords
  remoteAutocompleteInit('keywords')

  return jobadForm
}


// custom eye candy: strikeout previous pdf if new one
function customOnChangePdf() {
  let fileEl = document.getElementById('pdf_attachment')
  let todoEl = document.getElementById('previous-pdf')
  if (todoEl && fileEl) {
    if (fileEl.files[0])
      todoEl.classList.add('strikeout')
    else
      todoEl.classList.remove('strikeout')
  }
}

// validate and submit function
// theJobFormId is a mandatory id for a cmxClt.uform.Form object
// altSubmitFun is an optional arg with an alternative function to submit
//              it has to take as only argument a FormData object
function validateJobForm(theJobFormId, altSubmitFun) {

  let theJobForm = cmxClt.uform.allForms[theJobFormId]

  if (! theJobForm) {
    console.error("validateJobForm error: absent Form object: ", + theJobFormId)
  }

  // presubmit "is it filled ?" testing
  theJobForm.elMainMessage.style.display = "block"

  console.log(">> custom validate and message on ", theJobForm.id)

  var diagnostic = cmxClt.uform.testFillField(theJobForm,{'cols': jobCols})

  console.log(">> diagnostic ", diagnostic)

  var isFilled = diagnostic[0]
  var missingFields = diagnostic[1]

  // additional date test
  var dateValid = false
  let dateInput = document.getElementById('job_valid_date')
  let dateLabel = document.querySelector('label[for=job_valid_date]')
  if (dateInput.value) {
    if (/20[12][0-9]\/(?:0?[0-9]|1[0-2])\/(?:[0-2]?[0-9]|3[01])/.test(dateInput.value)) {
      dateValid = true
    }
  }

  // additional file input 2097152,test
  let pdfInput = document.getElementById('pdf_attachment')
  let [pdfOk, pdfMessage] = cmxClt.uform.checkBlob(pdfInput, {
    maxSize: 2097152,
    expectedFileExt: 'pdf'
  })

  // in our case an empty pdf is acceptable, but not a failed file
  let pdfAcceptable = pdfOk || (pdfMessage == 'no file')

  if (isFilled && dateValid && pdfAcceptable) {
      theJobForm.elMainMessage.innerHTML = "<span class='green glyphicon glyphicon-check glyphicon-float-left' style='float:left;'></span><p>OK thank you!</p>"

      if (altSubmitFun
          && typeof altSubmitFun == 'function') {
        // preSubmitActions + custom submit
        altSubmitFun(theJobForm.asFormData())
      }
      else {
        // preSubmitActions + classicSubmit
        theJobForm.elForm.submit()
      }
  }
  else {
      theJobForm.elMainMessage.innerHTML = "<span class='orange glyphicon glyphicon-exclamation-sign glyphicon-float-left'></span>"

      if (! isFilled) {
        theJobForm.elMainMessage.innerHTML = "<p>There are some <br/> important missing fields</p>"
        theJobForm.elMainMessage.innerHTML += cmxClt.ulListFromLabelsArray(
          missingFields,
          ['orange']
        )
      }
      if (! dateValid) {
        theJobForm.elMainMessage.innerHTML += '<br><p>The <a class="minilabel orange" onclick="return cmxClt.uform.gotoField(\'job_valid_date\')">date</a> needs to be<br>in YYYY/MM/DD format!</p>'
        dateLabel.style.backgroundColor = cmxClt.colorOrange
      }
      if (! pdfAcceptable) {
        theJobForm.elMainMessage.innerHTML += `<br><p>Problem with <a class="minilabel orange" onclick="return cmxClt.uform.gotoField('pdf_attachment')">your pdf file</a>: ${pdfMessage}</p>`
        document.querySelector('label[for=pdf_attachment]').style.backgroundColor = cmxClt.colorOrange
      }

      theJobForm.elMainMessage.classList.remove('faded')
  }
}


console.log("jobad elements load OK")
