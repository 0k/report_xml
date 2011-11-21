# -*- coding: utf-8 -*-

import netsvc
import ir

from osv import osv, fields
from xml_report import XmlParser
from report.report_sxw import rml_parse


def register_report(name, model, tmpl_path, parser=rml_parse):
    "Register the report into the services"
    name = 'report.%s' % name
    if netsvc.Service._services.get(name, False):
        service = netsvc.Service._services[name]
        if isinstance(service, XmlParser):
            #already instantiated properly, skip it
            return
        if hasattr(service, 'parser'):
            parser = service.parser
        del netsvc.Service._services[name]
    XmlParser(name, model, tmpl_path, parser=parser)


class ReportXML(osv.osv):

    def __init__(self, pool, cr):
        super(ReportXML, self).__init__(pool, cr)

    def _add_print_button_exists(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        ir_values = self.pool.get('ir.values')

        for id in ids:
            report = self.browse(cr, uid, id, context=context)
            domain = [('value', '=', '%s,%s' % (report.type, report.id))]
            res[id] = True if ir_values.search(cr, uid, domain) else False
        return res

    def register_all(self,cursor):
        value = super(ReportXML, self).register_all(cursor)
        cursor.execute("SELECT * FROM ir_act_report_xml WHERE report_type = 'xml'")
        records = cursor.dictfetchall()
        for record in records:
            register_report(record['report_name'], record['model'], record['report_rml'])
        return value

    def unlink(self, cursor, user, ids, context=None):
        """Delete report and unregister it"""
        trans_obj = self.pool.get('ir.translation')
        trans_ids = trans_obj.search(
            cursor,
            user,
            [('type', '=', 'report'), ('res_id', 'in', ids)]
        )
        trans_obj.unlink(cursor, user, trans_ids)

        # Warning: we cannot unregister the services at the moment
        # because they are shared across databases. Calling a deleted
        # report will fail so it's ok.

        res = super(ReportXML, self).unlink(
                                            cursor,
                                            user,
                                            ids,
                                            context
                                        )
        return res

    def create(self, cursor, user, vals, context=None):
        "Create report and register it"
        res = super(ReportXML, self).create(cursor, user, vals, context)
        if vals.get('report_type','') == 'xml':
            # I really look forward to virtual functions :S
            register_report(
                        vals['report_name'],
                        vals['model'],
                        vals.get('report_rml', False)
                        )
        return res

    def write(self, cr, uid, ids, vals, context=None):
        "Edit report and manage it registration"
        if isinstance(ids, (int, long)):
            ids = [ids,]
        for rep in self.browse(cr, uid, ids, context=context):
            if rep.report_type != 'xml':
                continue
            if vals.get('report_name', False) and \
                vals['report_name'] != rep.report_name:
                report_name = vals['report_name']
            else:
                report_name = rep.report_name

            register_report(
                        report_name,
                        vals.get('model', rep.model),
                        vals.get('report_rml', rep.report_rml)
                        )
        res = super(ReportXML, self).write(cr, uid, ids, vals, context)
        return res

    def add_print_button(self, cr, uid, ids, context):

        report = self.browse(cr, uid, ids[0], context=context)

        action_id = '%s,%d' % (report.type, report.id)
        models = [report.model]

        res = ir.ir_set(cr, uid, 'action', 'client_print_multi',
                        report.report_name, models,
                        action_id, isobject=True)

        return True

    def remove_print_button(self, cr, uid, ids, context):

        report = self.browse(cr, uid, ids[0], context=context)

        action_id = '%s,%d' % (report.type, report.id)

        ir_values = self.pool.get('ir.values')
        domain = [('value', '=', action_id)]
        res =  ir_values.search(cr, uid, domain)

        if len(res):
            for id in res:
                res = ir.ir_del(cr, uid, id)

        return True


    _name = 'ir.actions.report.xml'
    _inherit = 'ir.actions.report.xml'
    _columns = {
        'xml_debug' : fields.boolean('reportXML debug', help="Enable the xml report engine debugger"),
        'xml_full_dump' : fields.boolean('Full dump', help="Enable the full dump of the current object."),
        'xml_full_dump_deepness' : fields.integer('Full dump deepness', help="Deepness of the full dump."),
        'xml_full_dump_additional_data' : fields.text('Additional data', help="Data to be included in the XML full dump."),

        'xml_add_print_button_exists': fields.function(_add_print_button_exists,
                                                            type="boolean", method=True),

        'xml_template' : fields.text('XML Template', help="Mako XML Template."),
    }

    _defaults = {
        'xml_debug': lambda *a: False,
        'xml_full_dump': lambda *a: True,
        'xml_full_dump_deepness': lambda *a: "3",
    }

ReportXML()
