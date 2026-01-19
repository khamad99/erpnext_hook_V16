frappe.listview_settings['Renovation Work Order'] = {
	onload: list=>{
		list.setup_columns = function() {
			// setup columns for list view
			this.columns = [];
	
			const get_df = frappe.meta.get_docfield.bind(null, this.doctype);
	
			// 1st column: title_field or name
			if (this.meta.title_field) {
				this.columns.push({
					type: 'Subject',
					df: get_df(this.meta.title_field)
				});
			} else {
				this.columns.push({
					type: 'Subject',
					df: {
						label: __('Name'),
						fieldname: 'name'
					}
				});
			}
	
			// 2nd column: Status indicator
			if (frappe.has_indicator(this.doctype)) {
				// indicator
				this.columns.push({
					type: 'Status'
				});
			}
	
			const fields_in_list_view = this.get_fields_in_list_view();
			// Add rest from in_list_view docfields
			this.columns = this.columns.concat(
				fields_in_list_view
					.filter(df => {
						if (frappe.has_indicator(this.doctype) && df.fieldname === 'status') {
							return false;
						}
						if (!df.in_list_view) {
							return false;
						}
						return df.fieldname !== this.meta.title_field;
					})
					.map(df => ({
						type: 'Field',
						df
					}))
			);

		}
		list.render_header = function() {
			this.$result.find('.list-row-head').remove()
			if (this.$result.find('.list-row-head').length === 0) {
				// append header once
				this.$result.prepend(this.get_header_html());
			}
		}
		list.setup_columns()
		list.render_header()
	}
}