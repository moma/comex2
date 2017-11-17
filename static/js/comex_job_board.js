/**
 * @fileoverview
 * Shows an array of jsons with jsgrid
 * We assume the data in the global var params.jobsTable
 *
 * @version 1
 * @copyright ISCPIF-CNRS 2017
 * @author romain.loth@iscpif.fr
 *
 * @requires jsgrid.js, comex_jobad_elements.js
 */

let myController = {
  loadData: function(someFilter) {
    // filter object example:
    // {email: "", job_valid_date: "", mission_text: "blabla some query"}

    return params.jobsTable.filter(function(record){
      for (key in someFilter) {
        if (someFilter[key].length) {
          if (!record[key] || record[key].indexOf(someFilter[key]) == -1) {
            return false
          }
        }
      }
      return true
    })
  },
  deleteItem: function(item){
    console.log("DELETE", item, params.user)
    if (params.isAdmin
     && params.user && params.user.luid
     && item.uid == params.user.luid ) {
      $.ajax({
          type: 'DELETE',
          url: "/services/api/jobs/"+`?jobid=${item.jobid}&author=${params.user.luid}`,
          success: function(data) {
              console.log('jquery got return', data)
          },
          error: function(result) {
              console.warn('jquery ajax error with result', result)
          }
      });
    }
  }
}

let gridFields = [
   {
     name: "jtitle",
     title:"Title",
     type: "text",
     width: 80,
     css:"jtitle"
   },
   {
     name: "keywords",
     title:"Keywords",
     type: "text",
     width: 65,
     align: "center",
     css:"keywords",
     itemTemplate: function(value) {
       let html = ''
       if (value) {
         let kws = value.split(/,/)
         for (var k in kws) {
           if (k.length) {
             html += makeTagBox(kws[k]).outerHTML
           }
         }
       }
       return html
     }
   },
   {
     name: "country",
     title:"Country",
     type: "text",
     width: 45,
     align: "center",
     css:"job-country"
   },
   {
     name: "locname",
     title:"Location",
     type: "text",
     width: 45,
     align: "center",
     css:"locname"
   },
   {
     name: "job_valid_date",
     title:"Deadline",
     type: "text",
     width: 30,
     align: "center",
     css:"jobdate"
   },
   {
     name: "job_type",
     title:"Type",
     type: "text",
     width: 30,
     align: "center",
     css:"jobtype"
   },
   {
     name: "pdf_fname",
     title:"PDF",
     type: "text",
     width: 15,
     align: "center",
     css:"pdf_fname",
     itemTemplate: function(value) {
       if (value) {
         return `<a class="norowclick"
                    href="${value}" target="_blank">
                  <span class="glyphicon glyphicon-file norowclick"></span>
                </a>`
       }
     }
   }
]

if (params.isAdmin) {
  // adds edit and delete buttons
  gridFields.push({type:'control'})
}


// to create a tag box
function makeTagBox(textValue) {
  let newBox = document.createElement('div')
  newBox.textContent = textValue
  newBox.classList.add("box-highlight", "minibox")
  return newBox
}

// to create a job edit modal
var jobeditModal = new Modal(
    document.getElementById('job-details'),
    {backdrop: 'static', keyboard: false}
);

// to edit a job in the modal (using globals: uinfo, params)
function editJob(jobinfo) {
  // re-create the form element + init form controllers and autocomplete
  createJobForm( 'edit-job-container', {
      'user': uinfo,
      'job': jobinfo,
      'can_edit': params.isAdmin,
      'alt_submit': 'save-modified-job'
  })
  // show the modal
  jobeditModal.open();
}

// to use as a callback for the jobForm onclick validateJobForm action
function saveModifiedJob(aFormData) {
  $.ajax({
      type: 'POST',
      url: "/services/api/jobs/",
      data: aFormData,
      processData: false,
      contentType: false,
      success: function(data) {
          console.log('job update got return', data)
          jobeditModal.close();
          window.location.reload()
      },
      error: function(result) {
          console.warn('job update ajax error with result', result)
      }
  });
}

// redefine jsGrid's default edit button action accordingly
jsGrid.ControlField.prototype._createEditButton = function(item) {
    return this._createGridButton(
      this.editButtonClass,
      this.editButtonTooltip,
      function(grid, e) {
        editJob(item)
        e.stopPropagation();
    });
}

let jobGrid = $("#jobsgrid").jsGrid({
    width: "80%",
    height: "700px",

    filtering: true,
    sorting: true,
    paging: true,

    editing: false,  // default editing behavior is off (we add our own instead)
    inserting: false,
    deleteConfirm: "This will delete the job.\nAre you sure ?",

    noDataContent: "<div class=my-centering-box><p class=stamp style=\"width:50%;background-color:#222;text-align:center;\">There are no currently available jobs for this request.<br><br>If you're registered, you can add jobs <a href='/services/addjob/'>here</a></p></div>",

    data: params.jobsTable,
    controller: myController,

    fields: gridFields,

    // open full form instead of inline editing
    rowClick: function(rowargs) {
      if (rowargs && rowargs.event && rowargs.event.target) {
        let tgt = rowargs.event.target
        if (! tgt.classList.contains("norowclick")) {
          editJob(rowargs.item)
        }
      }
    }
})

console.log("job-board controllers load OK")
