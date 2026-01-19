from frappe.utils import flt
from erpnext import get_default_cost_center
from frappe import _, throw


def validate(doc, method):
	calculate_totals_vat(doc)

def calculate_totals_vat(doc):
	vat = 0.0
	for item in doc.expenses:
		vat += flt(item.vat_amount)
		item.base_vat_amount = flt(flt(item.vat_amount) * doc.conversion_rate, doc.precision("base_vat_amount", item))
	doc.total_vat = flt(vat, doc.precision("total_vat"))
	doc.base_total_vat = flt(vat * doc.conversion_rate, doc.precision("base_total_vat"))


def on_submit(doc, method):
	make_gl_entries(doc)

def on_cancel(doc, method):
	make_gl_entries(doc)

def make_gl_entries(doc):
	if not doc.base_total_vat:
		return
	gl_entries = []
	
	cost_center = get_default_cost_center(doc.company)
		
	gl_entries.append(
		doc.get_gl_dict({
			"account": doc.credit_account,
			"against": doc.vat_account,
			"credit": doc.base_total_vat,
			"cost_center": cost_center
		})
	)
	if doc.base_total_vat:
		if not doc.vat_account:
			throw(_("Please select VAT Account"))
		gl_entries.append(
			doc.get_gl_dict({
				"account": doc.vat_account,
				"against": doc.credit_account,
				"debit": doc.base_total_vat,
				"cost_center": cost_center
			})
		)
	
	from erpnext.accounts.general_ledger import make_gl_entries
	make_gl_entries(gl_entries, cancel=(doc.docstatus == 2),
	update_outstanding='Yes', merge_entries=False)