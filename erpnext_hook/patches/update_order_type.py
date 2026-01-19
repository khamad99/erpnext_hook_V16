import frappe
from bs4 import BeautifulSoup
from frappe.utils import get_site_path

def execute():
    if not frappe.db.exists('DocTYpe', "Renovation Job Order"):
        return
    for job in frappe.get_all("Renovation Job Order", {"order_type": "Contractual Order", "file": ("!=", "")}, ['name', 'file']):
        #ToDo Parse HTML and update job no
        """Update Tenant, Building, Others Related Docs."""
        with open(get_site_path(job.file), "r") as f:
            page = f.read()
        soup = BeautifulSoup(page, 'html.parser')
        top_left_side_b_section = soup.find_all('td', {"class": "e f-s9 brd-top brd-right span3-5"})
        doc = frappe.get_doc("Renovation Job Order", job.name)
        order_type = top_left_side_b_section[4].text.strip()
        if order_type and not frappe.db.exists("Renovation Sales  Order Type", order_type):
            order_type_doc = frappe.new_doc("Renovation Sales  Order Type")
            order_type_doc.set('title', order_type)
            order_type_doc.insert(ignore_permissions=True)
            frappe.db.commit()
        doc.db_set('order_type', order_type, False)
