from __future__ import unicode_literals

from frappe import _


def get_data():
    return {
        'heatmap': False,
        'heatmap_message': _('This is based on the Time Sheets created against this project'),
        'fieldname': 'master_project',
        'transactions': [
            {
                'label': _('Project'),
                'items': ['Project', 'Expense Claim', 'Issue', 'Project Update', 'Correspondence']
            },
            {
                'label': _('Material'),
                'items': ['Material Request', 'Stock Entry']
            },
            {
                'label': _('Sales'),
                'items': ['Sales Order', 'Delivery Note', 'Sales Invoice', 'Quotation', 'Contract']
            },
            {
                'label': _('Purchase'),
                'items': ['Purchase Order', 'Purchase Receipt', 'Purchase Invoice']
            },
        ]
    }
