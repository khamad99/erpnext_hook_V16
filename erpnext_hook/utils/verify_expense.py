import frappe
from frappe.utils import nowdate
import os

def execute():
    site_path = frappe.get_site_path()
    private_files_path = os.path.join(site_path, "private", "files")
    
    # Ensure directory exists
    os.makedirs(private_files_path, exist_ok=True)
    
    # Create dummy files
    receipt_path = os.path.join(private_files_path, "receipt.pdf")
    malicious_path = os.path.join(private_files_path, "malicious_script.exe")
    
    # Minimal valid PDF structure
    minimal_pdf = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%EOF\n"

    with open(receipt_path, "wb") as f:
        f.write(minimal_pdf)
    with open(malicious_path, "w") as f:
        f.write("dummy script")

    try:
        emp = frappe.get_all("Employee", ['name', 'company'], limit=1)[0]
        company = emp.company
        employee = emp.name
        
        cost_center = frappe.db.get_value("Company", company, "cost_center") or frappe.get_all("Cost Center", filters={"company": company}, limit=1)[0].name

        doc = frappe.get_doc({
            "doctype": "Expense Claim",
            "employee": employee,
            "company": company,
            "cost_center": cost_center,
            "posting_date": nowdate(),
            "workflow_state": "Pending",
            "exchange_rate": 1,
            "expenses": [{
                "expense_type": frappe.db.get_value("Expense Claim Type", {}, "name"),
                "expense_date": nowdate(),
                "amount": 100,
                "sanctioned_amount": 100
            }]
        })
        
        doc.insert(ignore_permissions=True)
        print(f"Created Test Claim: {doc.name}")

        # Simulate attaching a valid file
        frappe.get_doc({
            "doctype": "File",
            "file_name": "receipt.pdf",
            "file_url": "/private/files/receipt.pdf",
            "attached_to_doctype": "Expense Claim",
            "attached_to_name": doc.name,
            "is_private": 1
        }).insert(ignore_permissions=True)
        print("Attached valid receipt.pdf")
        
        # Test 1: Valid Submit
        doc.workflow_state = "Need Review"
        doc.save()
        print("PASS: Valid PDF attachment allowed submission.")
        
        # Add invalid file
        frappe.get_doc({
            "doctype": "File",
            "file_name": "malicious_script.exe",
            "file_url": "/private/files/malicious_script.exe",
            "attached_to_doctype": "Expense Claim",
            "attached_to_name": doc.name,
            "is_private": 1
        }).insert(ignore_permissions=True)
        print("Attached invalid malicious_script.exe")

        # Test 2: Invalid Submit Re-eval (mocking edit->resubmit)
        try:
            doc.save()
            print("FAIL: The document was saved with an invalid .exe attachment!")
        except Exception as e:
            if "Only PDF and Image files" in str(e):
                print("PASS: Successfully blocked submission with invalid attachment extension.")
            else:
                print(f"FAIL: Blocked for a different reason: {e}")
                
        # Cleanup DB
        frappe.db.rollback()
        
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        # Cleanup Files
        if os.path.exists(receipt_path):
            os.remove(receipt_path)
        if os.path.exists(malicious_path):
            os.remove(malicious_path)
