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


def validate_attachment(doc, method=None):
	if doc.workflow_state in ["Need Review", "Reviewed", "Approved"] or doc.docstatus == 1:
		attachments = frappe.db.get_all("File", 
			filters={
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name
			},
			fields=["file_name", "file_url"]
		)
		
		if not attachments:
			frappe.throw(_("An attachment is compulsory before submitting an Expense Claim."))

		allowed_extensions = ('.pdf', '.png', '.jpg', '.jpeg')
		
		for file in attachments:
			# Check either file_name or file_url (if hosted externally)
			name_to_check = (file.file_name or file.file_url or "").lower()
			if not name_to_check.endswith(allowed_extensions):
				frappe.throw(_("Invalid attachment format: {0}. Only PDF and Image files (.pdf, .png, .jpg, .jpeg) are allowed for Expense Claims.").format(name_to_check))


def set_cost_center_from_project(doc, method=None):
	"""Pre-fill a draft claim's cost centre from its project (validate).

	Header: on a new claim, or the save where the project changes, a header that
	is empty, the company default or the old project's cost centre is not the
	user's choice. It takes the project's Default Cost Center, else the company
	default. Lines: a line that is empty, on the company default or on the
	header's previous value follows the header. Any other value stays.

	Drafts only. Submit runs validate with docstatus 1, and a change on a
	submitted claim would re-post its ledger and drop the VAT rows that
	on_event_for_expense_claim books.
	"""
	if doc.docstatus != 0 or not doc.company:
		return

	sent = doc.cost_center
	if doc.has_value_changed("project"):
		doc.cost_center = pick_header_cost_center(
			doc.company, doc.project, doc.get_value_before_save("project"), doc.cost_center
		)
	if not doc.cost_center:
		return

	company_cc = frappe.get_cached_value("Company", doc.company, "cost_center")
	follow = {None, "", company_cc, sent, doc.get_value_before_save("cost_center")}
	for row in doc.expenses:
		if row.cost_center in follow:
			row.cost_center = doc.cost_center


@frappe.whitelist()
def get_header_cost_center(
	company: str, project: str | None = None, old_project: str | None = None, cost_center: str | None = None
):
	"""The Desk form's header after a project change: the same rule as the save."""
	if project:
		frappe.has_permission("Project", "select", project, throw=True)
	return pick_header_cost_center(company, project, old_project, cost_center)


def pick_header_cost_center(company, project, old_project, cost_center):
	"""The header for a claim whose project is new or changed.

	A header that is set and is neither the company default nor the old
	project's cost centre is the user's choice and stays. Otherwise: the
	project's cost centre, if it is enabled and of this company, else the
	company default.
	"""
	company_cc = frappe.get_cached_value("Company", company, "cost_center")
	old_project_cc = frappe.db.get_value("Project", old_project, "cost_center") if old_project else None
	if cost_center and cost_center not in (company_cc, old_project_cc):
		return cost_center
	return _usable_project_cost_center(company, project) or company_cc or cost_center


def _usable_project_cost_center(company, project):
	cost_center = project and frappe.db.get_value("Project", project, "cost_center")
	if not cost_center:
		return None
	disabled, cc_company = frappe.db.get_value("Cost Center", cost_center, ["disabled", "company"])
	if disabled or cc_company != company:
		return None
	return cost_center
