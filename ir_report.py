# -*- coding: utf-8 -*-

import openerp
from openerp.osv import osv, fields
from openerp.report.report_sxw import rml_parse

from .xml_report import XmlParser


class ReportXML(osv.osv):


    _report_parser = XmlParser

    _name = 'ir.actions.report.xml'
    _inherit = 'ir.actions.report.xml'
    _columns = {

        'xml_debug': fields.boolean(
            'reportXML debug',
            help="Enable the xml report engine debugger"),

        'xml_full_dump': fields.boolean(
            'Full dump',
            help="Enable the full dump of the current object."),

        'xml_full_dump_deepness': fields.integer(
            'Full dump deepness',
            help="Deepness of the full dump."),

        'xml_full_dump_additional_data': fields.text(
            'Additional data',
            help="Data to be included in the XML full dump."),

        'xml_full_dump_unfold_outline': fields.text(
            'Unfold Outline',
            help="Python dictionnary to draw the unfold outline of the dump"),

        'xml_template': fields.text(
            'XML Template', help="Mako XML Template."),
    }

    _defaults = {
        'xml_debug': lambda *a: False,
        'xml_full_dump': lambda *a: True,
        'xml_full_dump_deepness': lambda *a: 3,
        'xml_full_dump_additional_data': lambda *a: "<prefix></prefix>",
    }

    def _lookup_report(self, cr, name):
        """
        Look up a report definition.
        """
        import operator
        import os
        opj = os.path.join

        # First lookup in the deprecated place, because if the report definition
        # has not been updated, it is more likely the correct definition is there.
        # Only reports with custom parser specified in Python are still there.
        if 'report.' + name in openerp.report.interface.report_int._reports:
            new_report = openerp.report.interface.report_int._reports['report.' + name]
            if not isinstance(new_report, self._report_parser):
                new_report = None
        else:
            cr.execute("SELECT * FROM ir_act_report_xml WHERE report_name=%s", (name, ))
            r = cr.dictfetchone()
            if r:
                if r['parser']:
                    parser = operator.attrgetter(r['parser'])(openerp.addons)
                    kwargs = { 'parser': parser }
                else:
                    kwargs = {}

                new_report = self._report_parser('report.'+r['report_name'],
                    r['model'], opj('addons',r['report_rml'] or '/'),
                    header=r['header'], register=False, **kwargs)
            else:
                new_report = None

        if new_report:
            return new_report
        else:
            return super(ReportXML, self)._lookup_report(cr, name)

