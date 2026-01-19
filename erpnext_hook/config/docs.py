"""
Configuration for docs
"""
from __future__ import unicode_literals

source_link = "https://github.com/MalikZu/erpnext_hook"
docs_base_url = "/docs"
headline = "App that does everything"
sub_heading = "Yes, you got that right the first time, everything"

def get_context(context):
	context.brand_html = "Erpnext Hook"
