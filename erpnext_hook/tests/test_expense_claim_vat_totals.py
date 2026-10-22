"""The header VAT totals of an Expense Claim are the sums of its lines.

The rules are `utils/expense_claim.set_vat_totals` and
`utils/expense_claim.validate_sanctioned_vat`. The tests run on the dev site's
demo company. That site has no Expense Claim workflow, so each save sets
`workflow_state` by hand, as `test_expense_claim_cost_center` does.

Every line has an amount of 400 and a sanctioned amount of 400. Each test
gives the VAT. "a / b" is Total VAT Amount a, Total Sanctioned VAT Amount b.
"""

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from frappe.tests import IntegrationTestCase

from erpnext_hook.tests.test_expense_claim_cost_center import (
	COMPANY,
	PAYABLE,
	VAT_ACCOUNT,
	_employee,
	_give_expense_type_an_account,
	_gl_rows,
	_line,
	_save,
	_user,
)
from erpnext_hook.utils import expense_claim

CASH = "Cash"


class TestExpenseClaimVatTotals(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.employee = _employee()
		_give_expense_type_an_account()

	def test_insert_without_header_totals_takes_line_sums(self):
		"""REST or Data Import sends the lines only. The totals sum two different fields."""
		user = self._single_role_user("Employee")
		employee = frappe.db.get_value("Employee", {"user_id": user})
		self._act_as(user)
		saved = frappe.client.insert(self._payload(employee, [(10.10, 10.10), (20.20, 15.00)]))
		self.assertEqual((30.30, 25.10), (saved.total_vat_amount, saved.total_sanctioned_vat_amount))
		self.assertStoredTotals(saved.name, 30.30, 25.10)

	def test_wrong_header_sent_is_replaced(self):
		"""A header of 999 / 999 with lines 20 and 30, at insert and at save."""
		user = self._single_role_user("Employee")
		employee = frappe.db.get_value("Employee", {"user_id": user})
		self._act_as(user)
		payload = self._payload(employee, [(20, 20), (30, 30)], header=(999, 999))
		saved = frappe.client.insert(payload)
		self.assertStoredTotals(saved.name, 50, 50)

		sent = frappe.get_doc("Expense Claim", saved.name).as_dict()
		sent.update({"total_vat_amount": 999, "total_sanctioned_vat_amount": 999, "workflow_state": "Pending"})
		frappe.client.save(sent)
		self.assertStoredTotals(saved.name, 50, 50)

	def test_deleted_line_vat_leaves_the_header(self):
		"""As an HR User on the Desk: line 2 is deleted and the screen still sends 50 / 50."""
		self._act_as(self._single_role_user("HR User"))
		doc = self._claim([(20, 20), (30, 30)])
		self.assertStoredTotals(doc.name, 50, 50)
		doc.expenses.pop()
		doc.total_vat_amount = doc.total_sanctioned_vat_amount = 50
		_save(doc)
		self.assertStoredTotals(doc.name, 20, 20)

	def test_empty_vat_cell_counts_as_zero(self):
		"""As an HR User on the Desk: line 2 has no VAT, and the header is sent empty."""
		self._act_as(self._single_role_user("HR User"))
		doc = self._claim([(20, 20), (None, None), (15, 15)], header=(None, None))
		self.assertStoredTotals(doc.name, 35, 35)

	def test_submit_books_the_line_sums(self):
		"""A draft stored with 50 / 50 whose only line has VAT 20 books 20."""
		doc = self._claim([(20, 20)])
		frappe.db.set_value("Expense Claim", doc.name, {"total_vat_amount": 50, "total_sanctioned_vat_amount": 50})
		doc = self._submit(frappe.get_doc("Expense Claim", doc.name))
		self.assertStoredTotals(doc.name, 20, 20)
		self.assertIn((VAT_ACCOUNT, doc.cost_center, 20, 0), _gl_rows(doc))
		self.assertEqual(-420, _ledger(doc.name, is_cancelled=0)[PAYABLE])  # expense 400 + VAT 20
		self.assertNotIn(50, _amounts(doc.name))

	def test_paid_claim_books_and_reverses_the_line_vat(self):
		"""Is Paid, stored 50 / 50, one line VAT 20. Submit books 20. Cancel reverses every row."""
		doc = self._claim([(20, 20)], is_paid=1, mode_of_payment=CASH)
		frappe.db.set_value("Expense Claim", doc.name, {"total_vat_amount": 50, "total_sanctioned_vat_amount": 50})
		doc = self._submit(frappe.get_doc("Expense Claim", doc.name))
		self.assertStoredTotals(doc.name, 20, 20)

		cash = get_bank_cash_account(CASH, COMPANY)["account"]
		booked = _ledger(doc.name, is_cancelled=0)
		self.assertEqual(20, booked[VAT_ACCOUNT])
		self.assertEqual(-420, booked[cash])
		self.assertEqual(0, booked[PAYABLE])
		self.assertNotIn(50, _amounts(doc.name))

		doc.cancel()
		self.assertEqual([], [r for r in _rows(doc.name) if not r.is_cancelled])
		self.assertEqual({0}, set(_ledger(doc.name).values()))

	def test_submitted_claim_is_not_changed(self):
		"""A submitted claim with line VAT 20 stored as 0 / 0, saved (Update after Submit) and cancelled."""
		doc = self._submit(self._claim([(20, 20)]))
		frappe.db.set_value("Expense Claim", doc.name, {"total_vat_amount": 0, "total_sanctioned_vat_amount": 0})
		doc = frappe.get_doc("Expense Claim", doc.name)
		doc.save()
		self.assertStoredTotals(doc.name, 0, 0)
		doc.cancel()
		self.assertStoredTotals(doc.name, 0, 0)
		self.assertEqual(2, frappe.db.get_value("Expense Claim", doc.name, "docstatus"))

	def test_amended_claim_takes_line_sums(self):
		"""A cancelled claim stored with 50 / 50 and line VAT 20 is amended. The original keeps 50 / 50."""
		original = self._claim([(20, 20)])
		frappe.db.set_value(
			"Expense Claim", original.name,
			{"total_vat_amount": 50, "total_sanctioned_vat_amount": 50, "docstatus": 2},
		)
		for row in original.expenses:
			frappe.db.set_value("Expense Claim Detail", row.name, "docstatus", 2)
		original.reload()
		amended = frappe.copy_doc(original)
		amended.amended_from, amended.docstatus = original.name, 0
		_save(amended)
		self.assertStoredTotals(amended.name, 20, 20)
		self.assertStoredTotals(original.name, 50, 50)

	def test_portal_insert_keeps_its_sums(self):
		"""frappe.client.insert as an Employee Self Service user, with the portal's own sums."""
		if not frappe.db.exists("User Type", "Employee Self Service"):
			self.skipTest("this site has no Employee Self Service user type")
		user = _user(user_type="Employee Self Service")
		employee = _employee(user)
		frappe.get_doc("User", user).save()  # the user type gives its role once an employee links it
		self.assertEqual(["Employee Self Service"], [r.role for r in frappe.get_doc("User", user).roles])
		self._act_as(user)
		saved = frappe.client.insert(self._payload(employee, [(5.25, 5.25), (0, 0)], header=(5.25, 5.25)))
		self.assertStoredTotals(saved.name, 5.25, 5.25)

	def test_sanctioned_vat_above_vat_is_refused(self):
		"""As an HR User: line 2 has VAT 30 and sanctioned VAT 30.01. Nothing is saved."""
		self._act_as(self._single_role_user("HR User"))
		doc = self._new_claim([(20, 20), (30, 30.01)])
		with self.assertRaisesRegex(
			frappe.ValidationError, r"Sanctioned VAT Amount cannot be greater than VAT Amount in Row 2\."
		):
			_save(doc)
		self.assertFalse(doc.name and frappe.db.exists("Expense Claim", doc.name))

	def test_sanctioned_vat_equal_to_vat_is_saved(self):
		"""Equal values pass, also when float noise puts sanctioned VAT a hair above VAT."""
		self._act_as(self._single_role_user("HR User"))
		doc = self._claim([(20, 20), (30, 10)])
		self.assertStoredTotals(doc.name, 50, 30)

		noisy = self._new_claim([(0.3, 0.1 + 0.2)])
		self.assertGreater(noisy.expenses[0].sanctioned_vat_amount, noisy.expenses[0].vat_amount)
		expense_claim.validate_sanctioned_vat(noisy)

	def assertStoredTotals(self, name, total_vat, total_sanctioned_vat):
		stored = frappe.db.get_value(
			"Expense Claim", name, ["total_vat_amount", "total_sanctioned_vat_amount"], as_dict=True
		)
		self.assertEqual((total_vat, total_sanctioned_vat), (stored.total_vat_amount, stored.total_sanctioned_vat_amount))

	def _new_claim(self, vat_lines, header=None, **values):
		"""A Desk draft: the header holds the lines' sums unless `header` is given."""
		sums = tuple(sum(line[i] or 0 for line in vat_lines) for i in (0, 1))
		doc = frappe.get_doc(self._payload(self.employee, vat_lines, header or sums))
		doc.update(values)
		return doc

	def _claim(self, vat_lines, header=None, **values):
		return _save(self._new_claim(vat_lines, header, **values))

	def _payload(self, employee, vat_lines, header=None):
		"""The dict a client sends. No `header` sends no header totals at all."""
		payload = {
			"doctype": "Expense Claim", "employee": employee, "company": COMPANY,
			"payable_account": PAYABLE, "vat_account": VAT_ACCOUNT, "workflow_state": "Pending",
			"expenses": [_line(None) | {"vat_amount": vat, "sanctioned_vat_amount": sanctioned} for vat, sanctioned in vat_lines],
		}
		if header:
			payload["total_vat_amount"], payload["total_sanctioned_vat_amount"] = header
		return payload

	def _submit(self, doc):
		"""Attach a PDF receipt, approve and submit, as the workflow's Approve does."""
		frappe.get_doc({
			"doctype": "File", "file_name": "receipt.pdf", "file_url": "https://example.com/receipt.pdf",
			"attached_to_doctype": "Expense Claim", "attached_to_name": doc.name,
		}).insert()
		doc.approval_status, doc.workflow_state = "Approved", "Approved"
		doc.submit()
		return doc

	def _single_role_user(self, role):
		"""ERPNext gives the Employee role only to a user linked to an employee."""
		user = _user() if role == "Employee" else _user(role)
		if role == "Employee":
			_employee(user)
		self.assertEqual([role], [r.role for r in frappe.get_doc("User", user).roles])
		return user

	def _act_as(self, user):
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user)


def _rows(name):
	return frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Expense Claim", "voucher_no": name},
		fields=["account", "debit", "credit", "is_cancelled"],
	)


def _ledger(name, **filters):
	"""Debit minus credit per account, over the claim's GL rows."""
	totals = {}
	for row in _rows(name):
		if all(row[k] == v for k, v in filters.items()):
			totals[row.account] = totals.get(row.account, 0) + row.debit - row.credit
	return totals


def _amounts(name):
	return {amount for row in _rows(name) for amount in (row.debit, row.credit)}
