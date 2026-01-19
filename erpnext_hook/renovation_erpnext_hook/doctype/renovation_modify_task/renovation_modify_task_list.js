frappe.listview_settings['Renovation Modify Task'] = {
	get_indicator: function(doc) {
		if (doc.state=="Draft") {
			return [__("Draft"), "orange", "state,=,Draft"];
		} else if (doc.state=="In Progress") {
			return [__("In Progress"), "yellow", "state,=,In Progress"];
		} else if (doc.state=="Failed") {
			return [__("Failed"), "red", "state,=,Failed"];
		} else if (doc.state=="Submitted") {
			return [__("Submitted"), "green", "state,=,Submitted"];
		}
	},
	onload: $lsit => {
		locals.DocType[$lsit.doctype].is_submittable = 0
	}
}