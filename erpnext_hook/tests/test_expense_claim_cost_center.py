"""A draft Expense Claim takes its cost centre from its project.

The rule is `utils/expense_claim.set_cost_center_from_project`. The tests run on
the dev site's demo company. That site has no Expense Claim workflow, so
`workflow_state` is not a field there and `validate_attachment` fails on every
save. Each save sets it by hand, as the workflow does on production.

Labels: CD is the company default. P and R are projects with their own cost
centres. N has none, PD has a disabled one, PO has one of another company. X is
a cost centre a user picks by hand.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from erpnext_hook.utils import expense_claim

COMPANY = "almaidana (Demo)"
PAYABLE = "Trade Payable - AD"
VAT_ACCOUNT = "VAT 5% - AD"
EXPENSE_TYPE = "Travel"


class TestExpenseClaimCostCenter(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		tag = frappe.generate_hash(length=6)
		cls.cd = frappe.get_cached_value("Company", COMPANY, "cost_center")
		cls.p_cc, cls.r_cc, cls.x, cls.d = (_cost_center(f"ECCC {k} {tag}") for k in "PRXD")
		cls.p = _project(f"ECCC P {tag}", cls.p_cc)
		cls.r = _project(f"ECCC R {tag}", cls.r_cc)
		cls.n = _project(f"ECCC N {tag}", cls.cd, stored=None)
		other_company_cc = frappe.db.get_value(
			"Cost Center", {"company": ("!=", COMPANY), "is_group": 0, "disabled": 0}
		)
		cls.po = _project(f"ECCC PO {tag}", cls.cd, stored=other_company_cc)
		cls.pd = _project(f"ECCC PD {tag}", cls.d)
		frappe.db.set_value("Cost Center", cls.d, "disabled", 1)
		cls.employee = _employee()
		_give_expense_type_an_account()

	def _claim(self, project, cost_center, lines=(None,)):
		"""Insert a draft the way the portal, REST and Data Import send one."""
		doc = frappe.get_doc({
			"doctype": "Expense Claim",
			"employee": self.employee,
			"company": COMPANY,
			"project": project,
			"cost_center": cost_center,
			"payable_account": PAYABLE,
			"expenses": [_line(cc) for cc in lines],
		})
		return _save(doc)

	def assertCostCenters(self, doc, header, lines):
		doc.reload()
		self.assertEqual((header, lines), (doc.cost_center, [r.cost_center for r in doc.expenses]))

	def test_portal_insert_takes_project_cost_center(self):
		"""A header on CD and empty lines take P's cost centre."""
		doc = self._claim(self.p, self.cd, [None, None])
		self.assertCostCenters(doc, self.p_cc, [self.p_cc, self.p_cc])

	def test_insert_without_cost_center_takes_project_cost_center(self):
		"""No header is sent. The fetch puts CD there first."""
		doc = self._claim(self.p, None)
		self.assertCostCenters(doc, self.p_cc, [self.p_cc])

	def test_project_added_on_later_save(self):
		"""No project gives CD. Then P, set on a later save, gives P's."""
		doc = self._claim(None, self.cd)
		self.assertCostCenters(doc, self.cd, [self.cd])
		doc.project = self.p
		self.assertCostCenters(_save(doc), self.p_cc, [self.p_cc])

	def test_company_default_set_again_on_later_save_is_kept(self):
		"""CD picked again with the same project stays."""
		doc = self._claim(self.p, self.cd)
		doc.cost_center = self.cd
		self.assertCostCenters(_save(doc), self.cd, [self.cd])

	def test_user_pick_on_new_claim_is_kept(self):
		"""X picked by hand on a new claim with P stays."""
		doc = self._claim(self.p, self.x)
		self.assertCostCenters(doc, self.x, [self.x])

	def test_project_without_cost_center_keeps_company_default(self):
		"""A project with no cost centre leaves CD in place."""
		doc = self._claim(self.n, self.cd)
		self.assertCostCenters(doc, self.cd, [self.cd])

	def test_line_on_company_default_follows_header(self):
		"""The expense type put CD on the line in Desk. The line follows the header."""
		doc = self._claim(self.p, self.p_cc, [self.cd])
		self.assertCostCenters(doc, self.p_cc, [self.p_cc])

	def test_line_with_own_value_is_kept(self):
		"""Lines on CD, X and empty give P's, X and P's."""
		doc = self._claim(self.p, self.p_cc, [self.cd, self.x, None])
		self.assertCostCenters(doc, self.p_cc, [self.p_cc, self.x, self.p_cc])

	def test_line_on_previous_header_follows_new_header(self):
		"""The header moves from X to R's with the project unchanged. The line follows."""
		doc = self._claim(self.p, self.x)
		doc.cost_center = self.r_cc
		self.assertCostCenters(_save(doc), self.r_cc, [self.r_cc])

	def test_project_change_moves_header_from_old_project(self):
		"""The project changes from P to R while the portal still sends P's header."""
		doc = self._claim(self.p, self.cd)
		doc.project = self.r
		self.assertCostCenters(_save(doc), self.r_cc, [self.r_cc])

	def test_project_change_moves_lines_when_desk_sent_the_new_header(self):
		"""The Desk helper already put R's on the header. The lines follow it."""
		doc = self._claim(self.p, self.cd)
		doc.project, doc.cost_center = self.r, self.r_cc
		self.assertCostCenters(_save(doc), self.r_cc, [self.r_cc])

	def test_project_change_keeps_user_pick(self):
		"""X picked by hand stays when the project changes."""
		doc = self._claim(self.p, self.x)
		doc.project = self.r
		self.assertCostCenters(_save(doc), self.x, [self.x])

	def test_project_cleared_returns_to_company_default(self):
		"""Clearing the project puts CD back."""
		doc = self._claim(self.p, self.cd)
		doc.project = None
		self.assertCostCenters(_save(doc), self.cd, [self.cd])

	def test_project_without_cost_center_returns_to_company_default(self):
		"""A change to a project with no cost centre puts CD back."""
		doc = self._claim(self.p, self.cd)
		doc.project = self.n
		self.assertCostCenters(_save(doc), self.cd, [self.cd])

	def test_amended_claim_follows_the_rule(self):
		"""A cancelled claim on CD is amended onto P's. The original is not changed."""
		original = self._claim(self.p, self.cd)
		_store(original, self.cd, self.cd, docstatus=2)
		original.reload()
		amended = frappe.copy_doc(original)
		amended.amended_from, amended.docstatus = original.name, 0
		self.assertCostCenters(_save(amended), self.p_cc, [self.p_cc])
		self.assertCostCenters(original, self.cd, [self.cd])

	def test_disabled_project_cost_center_is_skipped(self):
		"""A project whose cost centre is disabled leaves CD in place."""
		doc = self._claim(self.pd, self.cd)
		self.assertCostCenters(doc, self.cd, [self.cd])

	def test_other_company_project_cost_center_is_skipped(self):
		"""A project whose cost centre belongs to another company leaves CD in place."""
		doc = self._claim(self.po, self.cd)
		self.assertCostCenters(doc, self.cd, [self.cd])

	def test_desk_helper_gives_the_server_answer(self):
		"""As a user with only the Employee role."""
		self._act_as(self._single_role_user("Employee"))
		ask = expense_claim.get_header_cost_center
		self.assertEqual(self.p_cc, ask(COMPANY, self.p, None, self.cd))
		self.assertEqual(self.r_cc, ask(COMPANY, self.r, self.p, self.p_cc))
		self.assertEqual(self.cd, ask(COMPANY, None, self.p, self.p_cc))
		self.assertEqual(self.x, ask(COMPANY, self.r, self.p, self.x))

	def test_desk_helper_needs_project_select(self):
		"""A User Permission on P, and a Site Engineer of R only."""
		ask = expense_claim.get_header_cost_center
		limited = self._single_role_user("Employee")
		frappe.get_doc({
			"doctype": "User Permission", "user": limited, "allow": "Project", "for_value": self.p,
		}).insert()
		self._act_as(limited)
		self.assertEqual(self.p_cc, ask(COMPANY, self.p))
		self.assertRaises(frappe.PermissionError, ask, COMPANY, self.r)

		if not frappe.db.exists("Role", "CMS Site Engineer"):
			self.skipTest("erpnext_contracting is not installed: no project-scoped role")
		frappe.set_user("Administrator")
		engineer = self._single_role_user("CMS Site Engineer")
		project = frappe.get_doc("Project", self.r)
		project.append("users", {"user": engineer, "welcome_email_sent": 1})
		project.flags.ignore_mandatory = True
		project.save()
		self._act_as(engineer)
		self.assertEqual(self.r_cc, ask(COMPANY, self.r))
		self.assertRaises(frappe.PermissionError, ask, COMPANY, self.p)

	def test_submitted_claim_is_not_changed(self):
		"""A submitted claim on CD whose project is edited."""
		doc = self._claim(self.p, self.cd)
		_store(doc, self.cd, self.cd, docstatus=1)
		doc.reload()
		doc.project = self.r
		expense_claim.set_cost_center_from_project(doc)
		self.assertEqual((self.cd, [self.cd]), (doc.cost_center, [r.cost_center for r in doc.expenses]))

	def test_submit_books_on_project_cost_center(self):
		"""The expense, payable and erpnext_hook VAT rows are on P's."""
		doc = self._submit_with_vat([None])
		rows = _gl_rows(doc)
		self.assertIn((_expense_account(), self.p_cc, 400, 0), rows)
		self.assertIn((PAYABLE, self.p_cc, 0, 400), rows)
		self.assertIn((VAT_ACCOUNT, self.p_cc, 20, 0), rows)

	def test_line_pick_is_booked_and_payment_follows_header(self):
		"""A line on X is booked on X. The Payment Entry takes the header."""
		doc = self._submit_with_vat([None, self.x])
		rows = _gl_rows(doc)
		self.assertIn((_expense_account(), self.p_cc, 400, 0), rows)
		self.assertIn((_expense_account(), self.x, 400, 0), rows)
		self.assertIn((VAT_ACCOUNT, self.p_cc, 40, 0), rows)
		payment = expense_claim.get_payment_entry("Expense Claim", doc.name)
		self.assertEqual(self.p_cc, payment.cost_center)

	def test_existing_draft_at_its_next_save(self):
		"""Drafts as stored before the deploy: at the next save the header stays and the lines follow it."""
		on_default = self._claim(self.p, self.cd)
		_store(on_default, self.cd, None)
		picked = self._claim(self.p, self.p_cc)
		_store(picked, self.p_cc, self.cd)
		self.assertCostCenters(_save(frappe.get_doc("Expense Claim", on_default.name)), self.cd, [self.cd])
		self.assertCostCenters(_save(frappe.get_doc("Expense Claim", picked.name)), self.p_cc, [self.p_cc])

	def test_portal_insert_as_self_service_user(self):
		"""frappe.client.insert as an Employee Self Service user."""
		if not frappe.db.exists("User Type", "Employee Self Service"):
			self.skipTest("this site has no Employee Self Service user type")
		user = _user(user_type="Employee Self Service")
		employee = _employee(user)
		frappe.get_doc("User", user).save()  # the user type gives its role once an employee links it
		self.assertEqual(["Employee Self Service"], [r.role for r in frappe.get_doc("User", user).roles])
		self._act_as(user)
		saved = frappe.client.insert({
			"doctype": "Expense Claim", "employee": employee, "company": COMPANY,
			"project": self.p, "cost_center": self.cd, "workflow_state": "Pending",
			"expenses": [_line(None)],
		})
		frappe.set_user("Administrator")
		self.assertCostCenters(frappe.get_doc("Expense Claim", saved.name), self.p_cc, [self.p_cc])

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

	def _submit_with_vat(self, lines):
		"""A claim on P with VAT 20 a line and a PDF receipt, approved and submitted."""
		doc = self._claim(self.p, self.cd, lines)
		for row in doc.expenses:
			row.vat_amount = row.sanctioned_vat_amount = 20
		doc.vat_account = VAT_ACCOUNT
		doc.total_vat_amount = doc.total_sanctioned_vat_amount = 20 * len(lines)
		_save(doc)
		frappe.get_doc({
			"doctype": "File", "file_name": "receipt.pdf", "file_url": "https://example.com/receipt.pdf",
			"attached_to_doctype": "Expense Claim", "attached_to_name": doc.name,
		}).insert()
		doc.approval_status, doc.workflow_state = "Approved", "Approved"
		doc.submit()
		return doc


def _save(doc):
	doc.workflow_state = "Pending"
	doc.save()
	return doc


def _store(doc, header, lines, **values):
	"""Put stored values in place, as a claim saved before this rule holds them."""
	frappe.db.set_value("Expense Claim", doc.name, {"cost_center": header, **values})
	for row in doc.expenses:
		frappe.db.set_value("Expense Claim Detail", row.name, {"cost_center": lines, **values})


def _line(cost_center):
	return {
		"expense_type": EXPENSE_TYPE, "expense_date": today(), "amount": 400,
		"sanctioned_amount": 400, "cost_center": cost_center,
	}


def _gl_rows(doc):
	rows = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Expense Claim", "voucher_no": doc.name, "is_cancelled": 0},
		fields=["account", "cost_center", "debit", "credit"],
	)
	return [(r.account, r.cost_center, r.debit, r.credit) for r in rows]


def _cost_center(name):
	root = frappe.db.get_value("Cost Center", {"company": COMPANY, "is_group": 1}, order_by="lft")
	return frappe.get_doc({
		"doctype": "Cost Center", "cost_center_name": name, "parent_cost_center": root,
		"company": COMPANY, "is_group": 0,
	}).insert().name


def _project(name, cost_center, **kwargs):
	"""A project on `cost_center`. `stored` overwrites it after insert, for a
	value the Project form refuses (none, or another company's). The fields
	other apps make mandatory on a project do not matter here."""
	project = frappe.get_doc({
		"doctype": "Project", "project_name": name, "company": COMPANY, "cost_center": cost_center,
	}).insert(ignore_mandatory=True).name
	if "stored" in kwargs:
		frappe.db.set_value("Project", project, "cost_center", kwargs["stored"])
	return project


def _employee(user=None):
	return frappe.get_doc({
		"doctype": "Employee", "first_name": "ECCC Test", "company": COMPANY, "status": "Active",
		"gender": "Male", "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
		"user_id": user,
	}).insert().name


def _user(*roles, user_type=None):
	return frappe.get_doc({
		"doctype": "User", "email": f"eccc-{frappe.generate_hash(length=8)}@example.com",
		"first_name": "ECCC Test", "send_welcome_email": 0, "cms_welcome_sent": 1,
		"user_type": user_type, "roles": [{"role": role} for role in roles],
	}).insert().name


def _expense_account():
	return frappe.db.get_value(
		"Account",
		{"company": COMPANY, "root_type": "Expense", "is_group": 0, "account_type": ("is", "not set")},
		order_by="lft",
	)


def _give_expense_type_an_account():
	"""The dev site's expense types have no account for the demo company."""
	expense_type = frappe.get_doc("Expense Claim Type", EXPENSE_TYPE)
	if not any(row.company == COMPANY for row in expense_type.accounts):
		expense_type.append("accounts", {"company": COMPANY, "default_account": _expense_account()})
		expense_type.save()
