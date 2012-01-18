# -*- coding: utf-8 -*-

from mako.template import Template
import netsvc
import pooler

import report_webkit

from report.report_sxw import *
from tools.translate import _
from osv.osv import except_osv
from osv.orm import except_orm

from lxml import etree as ET
from lxml.builder import E


##
## TODO:
##
## - clean Obj2Xml oe-object xml making process. (remove all rewriting of
## elements ?)
##
##

## XXXvlab: Translation ?

ElementClass = type(E.dummy())


## XXXvlab: yuk ! I would have appreciated to have a common ancestor to
## osv object...
def is_of_browser_interface(obj):
    module_name = obj.__class__.__module__
    return (module_name.startswith('osv')              ## openerp 6.0.3
            or module_name.startswith('openerp.osv'))  ## openerp 6.1


def hash_oe(obj):
    return (obj._table_name, obj._id)


class Obj2Xml():
    """Generic python object to XML converter

    Specificities upon openerp objects where added.

    """

    _attr_keep_fields = ["relation", "type", "help", "name", "string"]

    _dump_dispatcher = [(dict, "_xml_dict"),
                        ((list, tuple), "_xml_list"),
                        (unicode, "_xml_unicode"),
                        (bool, "_xml_bool"),
                        ((int, basestring, float), "_xml_str")
                        ]

    _remove_models = ["ir.ui.menu", "res.groups", "res.currency.rate", "ir.model.access"]
              
    KEEP_FALSE_VALUE = False

    def __init__(self, **kwargs):
        self.meta = {}
        for k, v in kwargs.iteritems():
            self.meta[k] = v

        self.uid = kwargs['uid']
        self.context = kwargs['context']
        self.cr = kwargs['cr']

        self._oe_cache = {}
        self._oe_graph = {}
        self._oe_key_defs = {}
        self._oe_getattr = {}

    def context2xml(self, cache):
        c = self.context.copy()

        ## Removing any active_* keys, as they are active_id(s) and
        ## active_model already in the <requests> element.
        for k in c.keys():
            if k.startswith("active_"):
                del c[k]

        ## Adding user in context
        pool = pooler.get_pool(self.cr.dbname)
        table_obj = pool.get("res.users")
        objs = table_obj.browse(self.cr, self.uid, [self.uid],
                                list_class=None, context=self.context,
                                fields_process=None)
        self._mk_oe_graph(objs[0], deep=0)
        xmlobj = self.obj2xml(objs[0], deep=0, cache=cache)

        user = E.user(table="res.users", **xmlobj.attrib)

        context = self.obj2xml(c)
        context.tag = "context"
        context.append(user)
        return context

    def report(self, objs, additional_data="", max_deep=3):

        self.max_deep = max_deep
        ## Structure:
        ## dump @model
        ##    meta
        ##       context
        ##    element @model @id
        ##       attr @oe-type (@relation)

        cache = {}
        context = self.context2xml(cache=cache)
        #meta = self.meta2xml()
        for obj in objs:
            self._mk_oe_graph(obj, deep=0)

        xmlobjs = [self.obj2xml(obj, deep=0, cache=cache) for obj in objs]

        try:
            additional_data = ET.fromstring(additional_data)
        except (ET.XMLSyntaxError, ValueError):
            additional_data = str(additional_data)

        return E.report(
            additional_data,
            context,
            E.requests(*[E.request(table=c.tag, **c.attrib) for c in xmlobjs]),
            E.data(*cache.values()),
        )

    def get_fields_def(self, obj):
        ## (access to a private member '_table')
        ## pylint: disable=W0212
        return obj._table.fields_get(self.cr, self.uid, None, self.context)

    def oe_subobjs(self, obj, hash_obj):
        self._oe_key_defs[hash_obj] = fields = self.get_fields_def(obj)
        self._oe_getattr[hash_obj] = attr = {}
        objs = []
        for key, field_def in fields.iteritems():
            ftype = field_def["type"]
            if ftype not in ("one2one", "many2one",
                             "many2many", "one2many"):
                continue
            try:
                r = getattr(obj, key)
            except Exception, e:
                continue
            if r.__class__.__name__ == 'browse_null':
                continue  ## element is removed
            if ftype in ("one2one", "many2one"):
                attr[key] = r
                objs.append(r)
            elif ftype in ("one2many", "many2many"):
                attr[key] = r
                objs.extend(r)
        return objs


    def _xml_dict(self, obj, deep, cache):
        elts = []
        for k, v in obj.iteritems():
            try:
                xml = self.obj2xml(v, deep=deep, cache=cache)
            except NotImplementedError:
                continue  ## ignore bad field.
            if xml is None:
                continue
            elts.append(getattr(E, k)(xml))
        if len(elts) == 0:
            return None
        return E.dict(*elts)


    def _mk_oe_graph(self, obj, deep):
        queue = [(deep, obj)]
        count = 1
        while len(queue) != 0:
            deep, obj = queue.pop(0)
            hash_obj = hash_oe(obj)
            self._oe_cache[hash_obj] = (deep, obj)
            subobjs = self.oe_subobjs(obj, hash_obj)
            self._oe_graph[hash_obj] = []
            for subobj in subobjs:
                hash_subobj = hash_oe(subobj)
                self._oe_graph[hash_obj].append(hash_subobj)

                if hash_subobj[0] not in self._remove_models and \
                       hash_subobj not in self._oe_cache and deep <= self.max_deep:
                    queue.append((deep + 1, subobj))
                    count += 1

        print "cache %s elements" % count

    def _xml_list(self, obj, deep, cache):
        elts = []
        for v in obj:
            try:
                xml = self.obj2xml(v, deep=deep, cache=cache)
            except NotImplementedError:
                continue  ## ignore bad field.
            if xml is None:
                continue
            elts.append(E.li(xml))
        if len(elts) == 0:
            return None
        return E.ul(*elts)

    def _xml_str(self, obj, _deep, _cache):
        return str(obj)

    def _xml_unicode(self, obj, _deep, _cache):
        return unicode(obj)

    def _xml_bool(self, obj, _deep, _cache):
        return E.bool(value=str(obj))

    def _xml_oe_object(self, obj, deep, cache):


        ## (access to a private member '_table')
        ## pylint: disable=W0212
        if not hasattr(obj, '_table') or obj._table is None:
            F = getattr(E, "oe-object")
            attrs = {
                "type": obj.__class__.__name__,
                }

            class_name = obj.__class__.__name__
            if class_name == 'browse_record_list':
                assert False
                return F(*(self.obj2xml(o, deep=deep, cache=cache)
                           for i, o in enumerate(obj)))
            if class_name == 'browse_null':
                return None  ## element is removed

            raise NotImplementedError("This oe-object is unknown: %r "
                                      "(type: %r)"
                                      % (obj, type(obj)))


        ## This is the real deepness
        deep = self._oe_cache[hash_oe(obj)][0]

        attrs = {
            "id": str(obj._id),
            "deep": str(deep),
            }

        F = getattr(E, obj._table_name)

        # Using repr as id...
        cached_value = cache.get(str(obj), None)
        if cached_value is not None:
            return F(**attrs)

        res = cache[str(obj)] = F(**attrs)
        hash_obj = hash_oe(obj)
        for key, field_def in self._oe_key_defs[hash_obj].iteritems():
            G = getattr(E, key)

            ## XXXvlab: what should I do of the states ?
            attr = dict((k, unicode(v))
                        for k, v in field_def.iteritems()
                        if k in self._attr_keep_fields)

            oe_attrs = self._oe_getattr[hash_obj]
            if key in oe_attrs:
                raw_value = oe_attrs[key]
            else:
                try:
                    raw_value = getattr(obj, key)
                except Exception, e:
                    attr['cropped'] = "EXCEPTION"
                    attr['exception-type'] = type(e).__name__
                    if isinstance(e, except_orm):
                        attr['exception-name'] = e.name
                        attr['exception-value'] = e.value
                    else:
                        attr['exception-repr'] = repr(e)
                    elt = G(**attr)
                    res.append(elt)
                    continue

            if not self.KEEP_FALSE_VALUE and \
                   field_def['type'] != "boolean" and \
                   raw_value is False:
                attr['undefined'] = "True"
                elt = G(**attr)
                res.append(elt)
                continue

            if "relation" in field_def:
                if deep + 1 >= self.max_deep:
                    attr["table"] = field_def["relation"]
                    attr["cropped"] = "MAX_DEEPNESS_REACHED"
                    elt = G(**attr)
                    res.append(elt)
                    continue
                elif field_def["relation"] in self._remove_models:
                    attr["cropped"] = "MATCHED_IGNORE_MODELS"
                    elt = G(**attr)
                    res.append(elt)
                    continue

            value = self.obj2xml(raw_value, deep=deep + 1, cache=cache)
            if value is None:
                continue

            if not isinstance(value, ElementClass):
                elt = G(value, **attr)
                res.append(elt)
                continue

            if hasattr(raw_value, "_table") and raw_value._table is not None:
                attr["table"] = raw_value._table_name

            elt = G(**attr)
            elt.text = value.text
            elt.attrib.update(dict(value.attrib))

            for child in value.getchildren():
                elt.append(child)

            if field_def['type'] == "many2one":
                if key.endswith("_id"):
                    elt.tag = elt.tag[:-3]
                del elt.attrib['relation']
            if field_def['type'] in ["one2many", "many2many"]:
                if key.endswith("_ids"):
                    elt.tag = elt.tag[:-4]
                elif key.endswith("_id"):
                    elt.tag = elt.tag[:-3]

                if elt.tag.endswith("ss"):
                    sub = elt.tag
                    elt.tag = elt.tag + "es"
                else:
                    if not elt.tag.endswith("s"):
                        elt.tag = elt.tag + "s"
                    sub = elt.tag[:-1]

                for c in elt:
                    c.tag = "%s" % sub
                    c.attrib['table'] = elt.attrib['relation']
                    c.attrib.update(dict(c[0].attrib))
                    for child in c[0].getchildren():
                        c.append(child)
                    c.remove(c[0])

            res.append(elt)

        return F(**attrs)

    def obj2xml(self, obj, deep=0, cache=None):
        cache = {} if cache is None else cache

        for types, fn_name in self._dump_dispatcher:
            if isinstance(obj, types):
                return getattr(self, fn_name, types)(obj, deep, cache)

        if is_of_browser_interface(obj):
            return self._xml_oe_object(obj, deep, cache)

        raise NotImplementedError("Dump not implemented for %r (type: %r)"
                                  % (obj, type(obj)))


class Bunch(dict):
    def __init__(self, d):
        b = dict((k, Bunch(v) if isinstance(v, dict) else v)
                 for k, v in d.iteritems())
        dict.__init__(self, b)
        self.__dict__.update(b)


## Simple wrapper for browser object
class MakoParsable(object):

    NULL = {}

    def __init__(self, browser):
        self._browser = browser
        fields_def = {}
        if hasattr(browser, "_table") and \
               browser._table is not None: ## browse_null class will by pass this
            fields_def = browser._table.fields_get(
                browser._cr, browser._uid, None, browser._context)
        self._fields = Bunch(fields_def)

    def __getitem__(self, label):

        if label not in self._fields and \
           ("%s_id" % label) in self._fields:
            return self["%s_id"]

        return self._browser.__getitem__(label)

    def __getattr__(self, label):

        if label not in self._fields and \
           ("%s_id" % label) in self._fields:
            return getattr(self, "%s_id" % label)

        val = getattr(self._browser, label)

        if is_of_browser_interface(val):
            class_name = val.__class__.__name__
            if hasattr(val, "_table") or \
               class_name == 'browse_null':
                return MakoParsable(val)
            if class_name == 'browse_record_list':
                return [MakoParsable(v) for v in val]

        return val


def mako_template(text):
    """Build a Mako template.

    This template uses UTF-8 encoding
    """
    # default_filters=['unicode', 'h'] can be used to set global filters
    return Template(text, input_encoding='utf-8', output_encoding='utf-8')


def xml2string(content):
    """Render a ElementTree to a string with some default options

    """
    return ET.tostring(content,
                       pretty_print=True,
                       xml_declaration=True,
                       encoding="utf-8")


class XmlParser(report_webkit.webkit_report.WebKitParser):
    """Custom class that dump data to XML reports
       Code partially taken from report webkit. Thanks guys :)
    """

    def __init__(self, name, table, rml=False, parser=False,
        header=True, store=False):
        self.parser_instance = False
        self.localcontext={}
        super(XmlParser, self).__init__(name, table, rml,
                                        parser, header, store)

    def generate_pdf(self, comm_path, report_xml, header, footer, html_list):
        ## should return the raw data of a pdf
        return None

    def _get_additional_data(self, cr, uid, ids, data, report_xml, context=None):
        return report_xml.xml_full_dump_additional_data

    def _create_full_dump_xml(self, cr, uid, ids, data, report_xml, context=None,
                              additional_data=None):

        model = self.table
        pool = pooler.get_pool(cr.dbname)
        table_obj = pool.get(model)
        objs = table_obj.browse(cr, uid, ids, list_class=None, context=context, fields_process=None)
        toXml = Obj2Xml(cr=cr, uid=uid, context=context)

        max_deep = 3 if report_xml.xml_full_dump_deepness < 3 \
                   else report_xml.xml_full_dump_deepness

        data = additional_data or report_xml.xml_full_dump_additional_data

        xml_output = toXml.report(objs,
                                  additional_data=data,
                                  max_deep=max_deep)

        return (xml2string(xml_output), 'xml')

    def _create_mako_xml(self, cr, uid, ids, data, report_xml, context=None):
        tpl = mako_template(report_xml.xml_template)

        model = self.table
        pool = pooler.get_pool(cr.dbname)
        table_obj = pooler.pool.get(model)
        objs = table_obj.browse(cr, uid, ids, list_class=None, context=context, fields_process=None)

        content = ""
        for obj in objs:
            obj = MakoParsable(obj) #, cr, uid, None, context)
            fields = obj._table.fields_get(cr, uid, None, context)
            content += tpl.render(fields=fields, obj=obj)

        xml = E.data(ET.fromstring(content))

        return (xml2string(xml), 'xml')

    # override needed to keep the attachments' storing procedure
    def create_single_pdf(self, cr, uid, ids, data, report_xml, context=None):
        """Override of inherited function to divert it and generate the XML
        instead of PDF if report_type is 'xml'."""

        if context is None:
            context={}

        if report_xml.report_type != 'xml':
            return super(XmlParser,self).create_single_pdf(cr, uid, ids, data, report_xml, context=context)

        return self.create_single_xml(cr, uid, ids, data, report_xml, context)

    def create_single_xml(self, cr, uid, ids, data, report_xml, context=None):
        """generate the XML"""

        if context is None:
            context={}

        if report_xml.report_type != 'xml':
            return super(XmlParser,self).create_single_pdf(cr, uid, ids, data, report_xml, context=context)

        if report_xml.xml_full_dump:
            return self._create_full_dump_xml(cr, uid, ids, data, report_xml, context)

        return self._create_mako_xml(cr, uid, ids, data, report_xml, context)

    def create(self, cr, uid, ids, data, context=None):
        """We override the create function in order to handle generator
           Code taken from report webkit. Thanks guys :) """

        pool = pooler.get_pool(cr.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_obj.search(cr, uid,
                [('report_name', '=', self.name[7:])], context=context)
        if report_xml_ids:
            report_xml = ir_obj.browse(
                                        cr,
                                        uid,
                                        report_xml_ids[0],
                                        context=context
                                    )
            report_xml.report_rml = None
            report_xml.report_rml_content = None
            report_xml.report_sxw_content_data = None
            report_rml.report_sxw_content = None
            report_rml.report_sxw = None
        else:
            return super(XmlParser, self).create(cr, uid, ids, data, context)
        if report_xml.report_type != 'xml' :
            return super(XmlParser, self).create(cr, uid, ids, data, context)
        result = self.create_source_pdf(cr, uid, ids, data, report_xml, context)
        if not result:
            return (False,False)
        return result
