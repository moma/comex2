/**
 * @fileoverview
 * Validates the comex (communityexplorer.org) job ad form
 *  + prepares DB save into cmxClt.job.COLS
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


// initialize form controllers
let jobadForm = cmxClt.uform.Form(
  "comex_job_form",
  function(){},   // onchange
  {'multiTextinputs':[{'id':'keywords'}]}
)

jobadForm.elSubmitBtn.disabled = false

// initialize autocomplete on keywords
remoteAutocompleteInit('keywords')


// submit function
function submitJobForm() {

  // presubmit "is it filled ?" testing
  jobadForm.elMainMessage.style.display = "block"

  console.log(">> custom validate and message on ", jobadForm.id)

  var diagnostic = cmxClt.uform.testFillField(jobadForm,{'cols': jobCols})

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

  if (isFilled && dateValid) {
      jobadForm.elMainMessage.innerHTML = "<span class='green glyphicon glyphicon-check glyphicon-float-left' style='float:left;'></span><p>OK thank you!</p>"

      // preSubmitActions + classicSubmit
      jobadForm.elForm.submit()
  }
  else {
      jobadForm.elMainMessage.innerHTML = "<span class='orange glyphicon glyphicon-exclamation-sign glyphicon-float-left'></span>"

      if (! isFilled) {
        jobadForm.elMainMessage.innerHTML = "<p>There are some <br/> important missing fields</p>"
        jobadForm.elMainMessage.innerHTML += cmxClt.ulListFromLabelsArray(
          missingFields,
          ['orange']
        )
      }
      if (! dateValid) {
        jobadForm.elMainMessage.innerHTML += '<br><p>The <a class="minilabel orange" onclick="return cmxClt.uform.gotoField(\'job_valid_date\')">date</a> needs to be<br>in YYYY/MM/DD format!</p>'
        dateLabel.style.backgroundColor = cmxClt.colorOrange
      }

      jobadForm.elMainMessage.classList.remove('faded')
  }
}


console.log("jobad controllers load OK")
