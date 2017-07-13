/**
 * @fileoverview
 * Shows an array of jsons with jsgrid
 * We assume the data in the global var params.jobsTable
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
     name: "mission_text",
     title:"Mission",
     type: "text",
     width: 110,
     css:"mission",
     itemTemplate: function(value, item) {
       return value
     }
   },
   {
     name: "keywords",
     title:"Keywords",
     type: "text",
     width: 80,
     align: "center",
     css:"keywords"
   },
   {
     name: "recruiter_org_text",
     title:"Organization",
     type: "text",
     width: 80,
     align: "center",
     css:"recr-org"
   },
   {
     name: "email",
     title:"Contact",
     type: "text",
     width: 60,
     align: "center",
     css:"email"
   },
   {
     name: "job_valid_date",
     title:"Valid until",
     type: "text",
     width: 40,
     align: "center",
     css:"jobdate"
   }
]


if (params.isAdmin) {
  gridFields.push({
    title: "Delete",
    type:'control',
    itemTemplate: function(value, item) {
        return [this._createDeleteButton(item)];
    }
  })
}

$("#jobsgrid").jsGrid({
    width: "80%",
    height: "700px",

    filtering: true,
    sorting: true,
    paging: true,

    editing: false,
    inserting: false,

    noDataContent: "<div class=my-centering-box><p class=stamp style=\"width:50%;background-color:#222;text-align:center;\">There are no currently available jobs for this request.<br><br>If you're registered, you can add jobs <a href='/services/jobad/'>here</a></p></div>",

    data: params.jobsTable,
    controller: myController,

    fields: gridFields
});


console.log("job-board controllers load OK")
