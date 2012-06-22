# -*- coding: utf-8 -*-

{
    "name" : "Xml Report Engine",
    "description" : """This module adds a new Report Engine to output XML.
The module structure and some code is inspired by the report_webkit module.
""",
    "version" : "%%short-version%%",
    "depends" : ["base"],
    "author" : "Valentin LAB -- Simplee",
    "category": "Reports/Xml",
    "url": "http://www.simplee.fr",
    "data": [ "security/ir.model.access.csv",
              "ir_report_add_button_view.xml",
              "ir_report_view.xml",
    ],
    "installable" : True,
    "active" : False,
}
