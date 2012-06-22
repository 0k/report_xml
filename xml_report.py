# -*- coding: utf-8 -*-

import logging

import netsvc
import pooler

from tools.safe_eval import safe_eval as eval
from tools.translate import _

import report_webkit

from report.report_sxw import *


from . import mako_tools
from oe2xml import Obj2Xml
from .common import format_last_exception, xml2string, string2xml


class XmlParser(report_webkit.webkit_report.WebKitParser):
    """Custom class that dump data to XML reports

    Code partially taken from report webkit. Thanks guys :)

    """

    def __init__(self, name, table, rml=False, parser=False,
                 header=True, store=False):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.parser_instance = False
        self.localcontext = {}
        super(XmlParser, self).__init__(name, table, rml,
                                        parser, header, store)

    def generate_pdf(self, _comm_path, _report_xml, _header, _footer, _html_list):
        ## should return the raw data of a pdf
        return None

    def _get_additional_data(self, cr, uid, ids, data, report_xml, context=None):
        return report_xml.xml_full_dump_additional_data

    def _create_full_dump_xml(self, cr, uid, ids, data, report_xml, context=None,
                              additional_data=None):

        model = self.table
        pool = pooler.get_pool(cr.dbname)
        table_obj = pool.get(model)
        objs = table_obj.browse(cr, uid, ids, list_class=None,
                                context=context, fields_process=None)
        toXml = Obj2Xml(cr=cr, uid=uid, context=context,
                        remove_models=["ir.ui.menu", "res.groups",
                                       "res.currency.rate", "ir.model.access"])

        max_deep = 3 if report_xml.xml_full_dump_deepness < 3 \
                   else report_xml.xml_full_dump_deepness

        data = additional_data or report_xml.xml_full_dump_additional_data
        outline_string = report_xml.xml_full_dump_unfold_outline or ""
        if outline_string:
            try:
                outline = eval(report_xml.xml_full_dump_unfold_outline) or None
            except Exception, e:
                self._logger.error('unfold outline evaluation failed:\n%s' % e.message)
                raise
        else:
            outline = None

        xml_output = toXml.report(objs,
                                  additional_data=data,
                                  max_deep=max_deep,
                                  outline=outline,
                                  )

        return (xml2string(xml_output), 'xml')

    def _create_mako_xml(self, cr, uid, ids, data, report_xml, context=None):

        model = self.table
        pool = pooler.get_pool(cr.dbname)
        table_obj = pool.get(model)
        objs = table_obj.browse(cr, uid, ids, list_class=None,
                                context=context, fields_process=None)

        content = ""
        for obj in objs:
            content += mako_tools.render(report_xml.xml_template, obj)

        try:
            xml = string2xml(content)
        except:
            exc = format_last_exception()
            raise SyntaxError("Output doesn't seem to be valid XML.\n%s"
                              "\nException Traceback:\n%s"
                              % (content, exc))

        return (xml2string(xml), 'xml')

    # override needed to keep the attachments' storing procedure
    def create_single_pdf(self, cr, uid, ids, data, report_xml, context=None):
        """Override of inherited function to divert it and generate the XML
        instead of PDF if report_type is 'xml'."""

        if context is None:
            context = {}

        if report_xml.report_type != 'xml':
            return super(XmlParser, self).create_single_pdf(cr, uid, ids,
                                                           data, report_xml,
                                                           context=context)

        return self.create_single_xml(cr, uid, ids, data, report_xml, context)

    def create_single_xml(self, cr, uid, ids, data, report_xml, context=None,
                          additional_data=None):
        """generate the XML"""

        if context is None:
            context = {}

        if report_xml.xml_full_dump:
            return self._create_full_dump_xml(cr, uid, ids, data,
                                              report_xml, context,
                                              additional_data)

        return self._create_mako_xml(cr, uid, ids, data, report_xml, context)

    def create(self, cr, uid, ids, data, context=None):
        """We override the create function in order to handle generator

        Code taken from report webkit. Thanks guys :)

        """

        pool = pooler.get_pool(cr.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_obj.search(cr, uid,
                [('report_name', '=', self.name[7:])], context=context)
        if report_xml_ids:
            report_xml = ir_obj.browse(cr, uid, report_xml_ids[0],
                                       context=context)
            report_xml.report_rml = None
            report_xml.report_rml_content = None
            report_xml.report_sxw_content_data = None
            report_xml.report_sxw_content = None
            report_xml.report_sxw = None
        else:
            return super(XmlParser, self).create(cr, uid, ids, data, context)
        if report_xml.report_type != 'xml':
            return super(XmlParser, self).create(cr, uid, ids, data, context)
        result = self.create_source_pdf(cr, uid, ids, data, report_xml, context)
        if not result:
            return (False, False)
        return result
