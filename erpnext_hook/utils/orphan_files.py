"""
Utility to fix orphaned private files by creating File records.
"""
import frappe
import os

def fix_orphan_files():
    """Create File records for orphaned private files."""
    site = frappe.local.site
    private_files_path = frappe.get_site_path("private", "files")
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    # Get all files in private directory
    for filename in os.listdir(private_files_path):
        file_path = os.path.join(private_files_path, filename)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
        
        file_url = f"/private/files/{filename}"
        
        # Check if File record exists
        existing = frappe.db.exists("File", {"file_url": file_url})
        
        if existing:
            skipped_count += 1
            continue
        
        try:
            # Create File record via SQL to valid collision logic renaming the file
            # We want to point to the EXISTING file on disk.
            current_time = frappe.utils.now()
            file_name = filename
            file_url = f"/private/files/{filename}"
            
            frappe.db.sql("""
                INSERT INTO tabFile 
                (name, creation, modified, modified_by, owner, docstatus, 
                file_name, file_url, is_private, is_folder, folder)
                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, 1, 0, 'Home/Attachments')
            """, (
                frappe.generate_hash(length=10), 
                current_time, 
                current_time, 
                "Administrator", 
                "Administrator", 
                file_name, 
                file_url
            ))
            
            created_count += 1
            if created_count % 100 == 0:
                frappe.db.commit()
                print(f"Processed {created_count} files...")
            
        except Exception as e:
            error_count += 1
    
    frappe.db.commit()
    return f"Created={created_count}, Skipped={skipped_count}, Errors={error_count}"

def create_specific_orphan_files():
    """Create File records for specific failing files."""
    files_to_create = [
        "20260102_100824.jpg",
        "20260102_100733.jpg",
        "20260102_100712.jpg",
        "Voice 008 2026-01-02 11:01:16.m4a"
    ]
    
    results = []
    for fn in files_to_create:
        file_url = f"/private/files/{fn}"
        if not frappe.db.exists("File", {"file_url": file_url}):
            try:
                doc = frappe.get_doc({
                    "doctype": "File",
                    "file_url": file_url,
                    "file_name": fn,
                    "is_private": 1,
                    "folder": "Home/Attachments"
                })
                doc.insert(ignore_permissions=True)
                results.append(f"Created: {fn}")
            except Exception as e:
                results.append(f"Failed {fn}: {e}")
        else:
            results.append(f"Exists: {fn}")


    frappe.db.commit()
    return "\n".join(results)

def check_get_all():
    file_url = "/private/files/20260102_100824.jpg"
    
    results = []
    results.append(f"Checking as {frappe.session.user}...")
    files = frappe.get_all("File", filters={"file_url": file_url}, fields="*")
    results.append(f"Files found (Admin): {len(files)}")
    
    frappe.set_user("Guest")
    results.append(f"Checking as {frappe.session.user}...")
    files = frappe.get_all("File", filters={"file_url": file_url}, fields="*")
    results.append(f"Files found (Guest): {len(files)}")
    
    files_ignore = frappe.get_all("File", filters={"file_url": file_url}, fields="*", ignore_permissions=True)
    results.append(f"Files found (Guest + ignore_permissions): {len(files_ignore)}")
    

    return "\n".join(results)

def fix_mismatched_urls():
    """Fix File records where file_url doesn't match file_name (due to hash suffix)."""
    mismatched = frappe.db.sql("""
        SELECT name, file_name, file_url 
        FROM tabFile 
        WHERE is_private=1 
        AND file_url NOT LIKE CONCAT('%', file_name)
    """, as_dict=True)
    
    count = 0
    total = len(mismatched)
    print(f"Found {total} mismatched files.")
    
    for file_data in mismatched:
        correct_url = f"/private/files/{file_data.file_name}"
        
        # Update via SQL to avoid any framework "help" re-hashing
        frappe.db.sql("""
            UPDATE tabFile 
            SET file_url = %s, content_hash=NULL
            WHERE name = %s
        """, (correct_url, file_data.name))
        
        count += 1
        if count % 1000 == 0:
            frappe.db.commit()
            print(f"Fixed {count}/{total} files...")

    frappe.db.commit()
    return f"Fixed {count} mismatched file URLs."
