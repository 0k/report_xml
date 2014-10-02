# -*- coding: utf-8 -*-

{
    "name": "Xml Report Engine",
    "description": """This module adds a new Report Engine to output XML.
The module structure and some code is inspired by the report_webkit module.
""",
    "version": "%%short-version%%",
    "depends": [
        "base",
        "report_webkit",
        "web",
        "web_ace_editor",
    ],
    "author": "Valentin LAB -- Simplee",
    "category": "Reports/Xml",
    "url": "http://www.simplee.fr",
    "data": [
	"view.xml",
        "security/ir.model.access.csv",
        "ir_report_view.xml",
    ],
    "qweb": [
        "static/src/xml/report_xml_template.xml",
        ],
    "installable": True,
    "active": False,
}
