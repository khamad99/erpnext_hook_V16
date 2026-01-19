import frappe

def execute():
    if not frappe.db.has_field('', 'hook_processed'):
        return
    docs = frappe.get_all('Communication', {"communication_medium": "Email", "hook_processed": 0})
    batch_size = 100
    for i in range(0, len(docs), batch_size):
        batch_docs_rows = docs[i:i + batch_size]
        for comm in batch_docs_rows:
            doc = frappe.get_doc('Communication', comm.name)
            doc.save()
        frappe.db.commit()
