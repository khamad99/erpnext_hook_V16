// Copyright (c) 2021, Leam Technology Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on('Correspondence', {

    to: function (frm) {
        if (frm.doc.to && frm.doc.to !== '') {
            frappe.model.get_value("Contact", {"name": frm.doc.to}, ["email_id", "address"], (data) => {
                frm.set_value("email", data.email_id);
                frm.set_value("address", data.address);
            });
        }
    },

    client: function (frm) {
        if (frm.doc.client && frm.doc.client !== '') {
            frappe.model.get_value("Customer", {"name": frm.doc.client}, ["customer_name"], (data) => {
                const nameSegments = data.customer_name.split(" ");
                let shortName = '';
                for (const nameSegment of nameSegments) {
                    shortName += nameSegment[0];
                }
                shortName = shortName.toUpperCase();
                frm.set_value("client_abbrv", shortName);
            });
        } else {
            frm.set_value("client_abbrv", "");
        }
    },
    project: function (frm) {
        if (!frm.doc.project || frm.doc.project === '') {
          frm.set_value("project_name", "");
          frm.set_value("master_project", "");
          frm.set_value("master_project_name", "");
        }
    },

    setup: function (frm) {
        frm.set_query('project', function (doc) {
            return {
                filters: {
                    'customer': doc.client,
                }
            }
        })


        frm.set_query('master_project', function (doc) {
            return {
                filters: {
                    'customer': doc.client,
                }
            }
        })
    }
});
