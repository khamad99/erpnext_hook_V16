import frappe
from frappe.utils import flt, nowdate
from frappe import _, scrub
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account


def on_event_for_expense_claim(doc, method):
	make_gl_entry_expense(doc, cancel=True if method=="on_cancel" else False)


def make_gl_entry_expense(doc, cancel=False):
	if not flt(doc.total_sanctioned_vat_amount):
		return
	if not doc.vat_account:
		frappe.throw(_("Please Set VAT Account"))
	
	entries = get_entries(doc)
	make_gl_entries(entries, cancel=cancel)


def get_entries(doc):
	gl_entry = []
	gl_entry.append(
			doc.get_gl_dict({
				"account": doc.payable_account,
				"credit": doc.total_sanctioned_vat_amount,
				"credit_in_account_currency": doc.total_sanctioned_vat_amount,
				"against": doc.vat_account,
				"party_type": "Employee",
				"party": doc.employee,
				"against_voucher_type": doc.doctype,
				"against_voucher": doc.name
			})
		)
	gl_entry.append(
			doc.get_gl_dict({
					"account": doc.vat_account,
					"debit": doc.total_sanctioned_vat_amount,
					"debit_in_account_currency": doc.total_sanctioned_vat_amount,
					"against": doc.employee,
					"cost_center": doc.cost_center
			})
		)
	if doc.is_paid and doc.total_sanctioned_vat_amount:
		# payment entry
		payment_account = get_bank_cash_account(doc.mode_of_payment, doc.company).get("account")
		gl_entry.append(
			doc.get_gl_dict({
				"account": payment_account,
				"credit": doc.total_sanctioned_vat_amount,
				"credit_in_account_currency": doc.total_sanctioned_vat_amount,
				"against": doc.employee
			})
		)

		gl_entry.append(
			doc.get_gl_dict({
				"account": doc.payable_account,
				"party_type": "Employee",
				"party": doc.employee,
				"against": payment_account,
				"debit": doc.total_sanctioned_vat_amount,
				"debit_in_account_currency": doc.total_sanctioned_vat_amount,
				"against_voucher": doc.name,
				"against_voucher_type": doc.doctype,
			})
		)
	return gl_entry



@frappe.whitelist()
def get_payment_entry(dt, dn, party_amount=None, bank_account=None, bank_amount=None):
	doc = frappe.get_doc(dt, dn)

	# party account
	party_type = "Employee"
	party_account = doc.payable_account

	party_account_currency = doc.get("party_account_currency") or get_account_currency(party_account)

	# payment type
	payment_type = "Pay"

	# amounts
	grand_total = outstanding_amount = 0
	if dt in ("Expense Claim"):
		grand_total = (flt(doc.total_sanctioned_amount) + flt(doc.total_sanctioned_vat_amount))
		outstanding_amount = grand_total - doc.total_amount_reimbursed - flt(doc.total_advance_amount)

	# bank or cash
	bank = get_default_bank_cash_account(doc.company, "Bank", mode_of_payment=doc.get("mode_of_payment"),
		account=bank_account)

	paid_amount = received_amount = 0
	if party_account_currency == bank.account_currency:
		paid_amount = received_amount = abs(flt(outstanding_amount))
	else:
		received_amount = abs(flt(outstanding_amount))
		if bank_amount:
			paid_amount = bank_amount

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = payment_type
	pe.company = doc.company
	pe.cost_center = doc.get("cost_center")
	pe.posting_date = nowdate()
	pe.mode_of_payment = doc.get("mode_of_payment")
	pe.party_type = party_type
	pe.party = doc.get(scrub(party_type))
	pe.contact_person = doc.get("contact_person")
	pe.contact_email = doc.get("contact_email")
	pe.ensure_supplier_is_not_blocked()

	pe.paid_from = bank.account
	pe.paid_to = party_account
	pe.paid_from_account_currency =  bank.account_currency
	pe.paid_to_account_currency = party_account_currency
	pe.paid_amount = paid_amount
	pe.received_amount = received_amount
	pe.allocate_payment_amount = 1
	pe.letter_head = doc.get("letter_head")
	
	pe.append("references", {
		'reference_doctype': dt,
		'reference_name': dn,
		"bill_no": doc.get("bill_no"),
		"due_date": doc.get("due_date"),
		'total_amount': grand_total,
		'outstanding_amount': outstanding_amount,
		'allocated_amount': outstanding_amount
	})

	pe.setup_party_account_field()
	pe.set_missing_values()
	if party_account and bank:
		pe.set_exchange_rate()
		pe.set_amounts()
	return pe
