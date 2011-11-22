import ir

from osv import osv, fields

class AddReportButton(osv.osv):

    def _add_print_button_exists(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        ir_values = self.pool.get('ir.values')

        for id in ids:
            report = self.browse(cr, uid, id, context=context)
            domain = [('value', '=', '%s,%s' % (report.type, report.id))]
            res[id] = True if ir_values.search(cr, uid, domain) else False
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
        'add_print_button_exists': fields.function(_add_print_button_exists,
                                                   type="boolean", method=True),
    }
    _defaults = {
    }

AddReportButton()
