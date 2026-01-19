from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'renovation_work_order',
		"non_standard_fieldnames":{
			'Renovation Work Order Modify Request': 'work_order_no'
		},
		'transactions': [
			{
				'label': _('Fulfillment'),
				'items': ['Sales Invoice']
			},
			{
				'label': _('Reference'),
				'items': ['Quotation', 'Renovation Work Order Modify Request']
			}
		]
	}