/**
 * @fileoverview
 * Shows an array of jsons with jsgrid
 * We assume the data in the global var jobsTable
 *
 * @version 1
 * @copyright ISCPIF-CNRS 2017
 * @author romain.loth@iscpif.fr
 *
 * @requires jsgrid.js
 */


let myController = {
  loadData: function(someFilter) {
    console.log('type of filter', typeof someFilter)
    console.log('filter', someFilter)

    // filter object example:
    // {email: "", job_valid_date: "", mission_text: "blabla some query"}

    return jobsTable.filter(function(record){
      for (key in someFilter) {
        if (someFilter[key].length) {
          if (record[key].indexOf(someFilter[key]) == -1) {
            return false
          }
        }
      }
      return true
    })
  }
}

let gridFields = [
   {
     name: "mission_text",
     title:"Mission",
     type: "text",
     width: 100,
     css:"mission",
     itemTemplate: function(value, item) {
       console.log('item', item)
       return value
     }
   },
   {
     name: "recruiter_org_text",
     title:"Organization",
     type: "text",
     width: 100,
     align: "center",
     css:"recr-org"
   },
   {
     name: "email",
     title:"Contact",
     type: "text",
     width: 80,
     align: "center",
     css:"email"
   },
   {
     name: "job_valid_date",
     title:"Valid until",
     type: "text",
     width: 60,
     align: "center",
     css:"jobdate"
   }
]

let isAdminView = false
if (isAdminView) {
  gridFields.push({type:'control'})
}

$("#jobsgrid").jsGrid({
    width: "80%",
    height: "700px",

    filtering: true,
    sorting: true,
    paging: true,

    editing: false,
    inserting: false,

    data: jobsTable,
    controller: myController,

    fields: gridFields
});


console.log("job-board controllers load OK")
