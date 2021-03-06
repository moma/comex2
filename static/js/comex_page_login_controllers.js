/**
 * @fileoverview
 * Login via Doors
 * @todo
 *    - package.json
 *
 * @version 1
 * @copyright ISCPIF-CNRS 2016
 * @author romain.loth@iscpif.fr
 *
 * @requires comex_user_shared
 * @requires comex_user_shared_auth
 */

 // initialize auth with doors
var loginForm = cmxClt.uauth.AuthForm(
                    "comex_login_form",
                    loginValidate,
                    {'type': "login",
                     'validateCaptcha': true}
                     // element ids are default so unspecified
                )

var submitButton = document.getElementById('form_submit')

// bind our overloaded submit() function
submitButton.onclick = loginForm.elForm.submit

// trigger changes (useful if browser completed from cache)
loginForm.elEmail.dispatchEvent(new CustomEvent('change'))
loginForm.elPass.dispatchEvent(new CustomEvent('change'))
loginForm.elCaptcha.dispatchEvent(new CustomEvent('change'))

// done when anything in the form changes
function loginValidate(myForm) {
  // console.log("loginValidate Go")

  if (myForm.emailStatus
      && myForm.passStatus
      && myForm.captchaStatus) {
      submitButton.disabled = false
  }
  else {
      submitButton.disabled = true
  }
}


console.log("login controllers load OK")
