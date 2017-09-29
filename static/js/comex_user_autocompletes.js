/**
 * @fileoverview
 * Autocompletes
 *  -> local data for countries, jobtitles
 *  -> use ajax /services/api/aggs for the scholars, kws and labs (TODO)
 *
 * @todo
 *    - package.json
 *
 * @version 1
 * @copyright ISCPIF-CNRS 2016
 * @author romain.loth@iscpif.fr
 *
 * @requires comex_user_shared
 */

var countriesList = ["Afghanistan", "Albania", "Algeria", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan",
                    "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina",
                    "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burma (Myanmar)", "Burundi", "Cambodia", "Cameroon", "Canada",
                    "Cape Verde", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo, Rep. of", "Congo, Dem. Rep. of",
                    "Costa Rica", "Côte d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic",
                    "East Timor", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia", "Fiji", "Finland", "France",
                    "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti",
                    "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan",
                    "Kazakhstan", "Kenya", "Kiribati", "Korea, North", "Korea, South", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho",
                    "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Macedonia", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali",
                    "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro",
                    "Morocco", "Mozambique", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "Norway", "Oman",
                    "Pakistan", "Palau", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia",
                    "Rwanda", "St. Kitts and Nevis", "St. Lucia", "St. Vincent and the Grenadines", "Samoa", "São Tomé and Príncipe", "Saudi Arabia",
                    "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa",
                    "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Swaziland", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan",
                    "Tanzania", "Thailand", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine",
                    "United Arab Emirates", "United Kingdom", "USA", "Uruguay", "Uzbekistan", "Vanuatu", "Venezuela", "Vietnam",
                    "Yemen", "Zambia", "Zimbabwe"]

var hontitlesList = ["Mr", "Ms", "Dr.", "Prof.", "Prof. Dr."]

var jobtitlesList = ["Graduate Student", "Post-Graduate Student", "Engineer",
                      "Lecturer", "Associate Professor", "Professor",
                     "PhD Student", "Research Fellow", "Research Director"]

var citiesList = ["Alès", "Amsterdam", "Barcelona", "Birmingham", "Bochum", "Bogotá", "Bologna", "Bondy", "Bordeaux", "Boston", "Brisbane", "Bristol", "Bruxelles", "Budapest", "Cambridge", "Cancún", "Cergy-Pontoise", "Clermont-Ferrand", "Coimbra", "Cranfield", "Créteil", "Dublin", "Evry", "Firenze", "Glasgow", "Göteborg", "Grenoble", "Haifa", "Istanbul", "Italy", "Lausanne", "Le Havre", "Leicester", "Leipzig", "Leuven", "Lille", "Lisboa", "London", "Lorraine", "Los Angeles", "Lyon", "Marseille", "Mexico", "Milano", "Milton Keynes", "Montpellier", "Namur", "Nancy", "Nanterre", "Netherlands", "New York", "Newcastle", "Nice", "Orsay", "Oxford", "Paderborn", "Palaiseau", "Palma de Mallorca", "Paris", "Patras", "Rennes", "Roma", "Rouen", "Saint-Etienne", "San Francisco", "Santa Fe", "São Paulo", "Southampton", "Spain", "Stellenbosch", "Strasbourg", "Sweden", "Talinn", "Torino", "Toulouse", "Trieste", "Valparaiso", "Verona", "Versailles", "Warsaw", "Warwick", "Zaragoza"]

// autocomplete via local list
function localAutocompleteInit(fieldName, seedList) {
  // jquery var for jquery-ui
  var $theInput = $('#'+fieldName)

  if ($theInput.length && seedList && seedList.length) {
    $theInput.autocomplete({
      source: seedList,
      autoFocus: true,
      focus: function () {
          // prevent value inserted on focus
          return false;
      },
      select: function (event, ui) {
        // console.log(ui)
        $theInput[0].style.fontWeight = "bold"
      }
    });
  }
}

// autocomplete via remote aggs api
//   @fieldName : 'keywords' or 'hashtags'
//       => must match the html form input id (eg #keywords)
//       => supposed to also match the REST param
//            (eg services/api/aggs?field=keywords)
function remoteAutocompleteInit(fieldName, hap, altApiName, seedKeys) {
  var nMax = 100
  var hapaxThresh = 1
  if (hap != null) {
      hapaxThresh = hap
  }
  var apiName = fieldName
  if (altApiName != null) {
      apiName = altApiName
  }

  var $theInput = $('#'+fieldName)

  var theValuedArray = []

  if ($theInput.length) {
    $.ajax({
        type: 'GET',
        dataType: 'json',
        url: "/services/api/aggs?field="+apiName+"&hapax="+hapaxThresh,
        success: function(data) {
            // ex data is array like:
            // [{"occs": 1116, "x": null},
            //  {"occs": 100, "x": "complex systems"},
            //  {"occs": 90, "x": "complex networks"},
            //  {"occs": 66, "x": "agent-based models"}]

            for (var i in data) {
                if (data[i].x != null) {
                    var item = data[i].x
                    var occs = data[i].occs || data[i].n

                    if (item && item != null) {
                        theValuedArray.push([item, occs])
                    }
                }
            }

            // sorted couples [[networks, 84], [cooperation, 8], [topology, 4]...]
            // rn sort on vals
            theValuedArray.sort(
              function(a, b) {
                  return  b[1] - a[1]
              }
            )

            // console.log(kwValuedArray)

            // sorted auto completion array by previous freq, with max
            var theArray
            if (seedKeys && seedKeys.length) {
              theArray = seedKeys
            }
            else {
              theArray = []
            }
            for (var i in theValuedArray) {
              theArray.push(theValuedArray[i][0])
              if (i > nMax) {
                  break;
              }
            }

            $theInput.autocomplete({
                source: theArray,
                autoFocus: true,
                focus: function () {
                    // prevent value inserted on focus
                    return false;
                },
                select: function (event, ui) {
                }
            });

        },
        error: function(result) {
            console.warn('jquery ajax error with result', result)
        }
    });
  }
}


// main:
// initialize the most common ones if they exist in the DOM

localAutocompleteInit("country", countriesList)
localAutocompleteInit("hon_title", hontitlesList)
localAutocompleteInit("position", hontitlesList)

// initialize the remote ones
remoteAutocompleteInit('keywords')
remoteAutocompleteInit('hashtags')
remoteAutocompleteInit('lab_label', 1, 'laboratories')
remoteAutocompleteInit('inst_label', 1, 'institutions')

 console.log("autocompletes load OK")
