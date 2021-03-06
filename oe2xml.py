# -*- coding: utf-8 -*-
"""OpenERP objects to XML

This code needs to be cleaned and simplified.

"""

import logging
import pooler

from lxml import etree as ET
from lxml.builder import E

from osv.orm import except_orm
from .common import format_last_exception


## XXXvlab: any better way to get ``ElementClass`` ?
ElementClass = type(E.dummy())


def hash_oe(obj):
    """Return a unique identifier for an OpenERP object"""
    return (obj._table_name, obj._id)


## XXXvlab: yuck ! I would have appreciated to have a common ancestor to
## osv objects...
def is_openerp_object(obj):
    """Return boolean wether the given object is a recognized OpenERP object"""
    module_name = obj.__class__.__module__
    return (module_name.startswith('osv')              ## openerp 6.0.3
            or module_name.startswith('openerp.osv'))  ## openerp 6.1

##
## TODO:
##
## - clean Obj2Xml oe-object xml making process. (remove all rewriting of
## elements ?)
##

class Obj2Xml():
    """Python/OpenERP object to XML converter

    """

    _attr_keep_fields = ["relation", "type", "help", "name", "string"]

    _dump_dispatcher = [(dict, "_xml_dict"),
                        ((list, tuple), "_xml_list"),
                        (unicode, "_xml_unicode"),
                        (bool, "_xml_bool"),
                        ((int, basestring, float), "_xml_str")
                        ]

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
        self._outlines = {}
        self._oe_key_defs = {}
        self._oe_getattr = {}
        self._logger = logging.getLogger(self.__class__.__name__)

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
        self._mk_oe_graph(objs[0], deep=0, outline=['*'])
        xmlobj = self.obj2xml(objs[0], deep=0, cache=cache, outline=["*"])

        user = E.user(table="res.users", **xmlobj.attrib)

        context = self.obj2xml(c)
        context.tag = "context"
        context.append(user)
        return context

    def report(self, objs, additional_data="", avoid_models=None,
               max_deep=3, outline=None):

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
            self._mk_oe_graph(obj, deep=0, outline=outline)

        xmlobjs = [self.obj2xml(obj, deep=0, cache=cache, outline=outline)
                   for obj in objs]

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

    def _outline_hash(self, outline):
        if isinstance(outline, dict):
            h = hash(
                tuple((k, self._outline_hash(v))
                      for k, v in sorted(outline.items(),
                                         key=(lambda t: t[0]))))
        elif isinstance(outline, list):
            h = hash(tuple(outline))
        else:
            h = outline
        self._outlines[h] = outline
        return h

    def oe_subobjs(self, obj, hash_obj, outline):
        self._oe_key_defs[hash_obj] = fields = self.get_fields_def(obj)
        self._oe_getattr[hash_obj] = attr = {}
        objs = set()
        for key, field_def in fields.iteritems():
            ftype = field_def["type"]
            if ftype not in ("one2one", "many2one",
                             "many2many", "one2many"):
                continue
            new_outline = self._check_outline(outline, obj, key, field_def)
            if new_outline is False:
                continue
            new_outline_hash = self._outline_hash(new_outline)
            try:
                r = getattr(obj, key)
            except Exception, e:
                formated = format_last_exception()
                self._logger.error("CACHE FAILED: Exception received while "
                                   "getattr object %r on attribute %r:\n%s"
                                   % (obj, key, formated))
                continue
            if r.__class__.__name__ == 'browse_null':
                continue  ## element is removed
            if ftype in ("one2one", "many2one"):
                attr[key] = r
                objs.add((r, new_outline_hash))
            elif ftype in ("one2many", "many2many"):
                attr[key] = r
                objs.update((elt, new_outline_hash) for elt in r)
        return objs

    def _mk_oe_graph(self, obj, deep, outline):
        queue = [(deep, obj, self._outline_hash(outline))]
        count = 1
        parse = 1
        while len(queue) != 0:
            deep, obj, outline_hash = queue.pop(0)
            hash_obj = hash_oe(obj)
            ## XXXvlab: first outline has precedence on the following.
            ## This can be bogus.
            if hash_obj in self._oe_cache:
                ## then outline has to be augmented.
                if outline_hash in self._oe_cache[hash_obj][2]:
                    ## forget this object with this outline has already been
                    ## parsed.
                    continue
                self._oe_cache[hash_obj][2].append(outline_hash)
            else:
                self._oe_cache[hash_obj] = (deep, obj, [outline_hash])
            count += 1
            subobjs = self.oe_subobjs(obj, hash_obj, self._outlines[outline_hash])
            self._oe_graph[hash_obj] = set()
            for subobj, suboutline_hash in subobjs:
                hash_subobj = hash_oe(subobj)
                self._oe_graph[hash_obj].add(hash_subobj)

                if hash_subobj[0] not in self.meta.get("ignore_models",[]) and \
                       ((hash_subobj not in self._oe_cache) or
                        ## This suboutline is not already stored
                        suboutline_hash not in self._oe_cache[hash_subobj][2]) and \
                       deep <= self.max_deep:
                    print "obj %r adds %r of deepness %r" % (obj, subobj, deep)
                    queue.append((deep + 1, subobj, suboutline_hash))
                    parse += 1

        print "cache %s elements and parsed %r." % (count, parse)

    def _xml_dict(self, obj, deep, cache, outline=None):
        elts = []
        for k, v in obj.iteritems():
            try:
                xml = self.obj2xml(v, deep=deep, cache=cache, outline=outline)
            except NotImplementedError:
                continue  ## ignore bad field.
            if xml is None:
                continue
            elts.append(getattr(E, k)(xml))
        if len(elts) == 0:
            return None
        return E.dict(*elts)

    def _xml_list(self, obj, deep, cache, outline=None):
        elts = []
        for v in obj:
            try:
                xml = self.obj2xml(v, deep=deep, cache=cache, outline=outline)
            except NotImplementedError:
                continue  ## ignore bad field.
            if xml is None:
                continue
            elts.append(E.li(xml))
        if len(elts) == 0:
            return None
        return E.ul(*elts)

    def _xml_str(self, obj, _deep, _cache, outline=None):
        return str(obj)

    def _xml_unicode(self, obj, _deep, _cache, outline=None):
        return unicode(obj)

    def _xml_bool(self, obj, _deep, _cache, outline=None):
        return E.bool(value=str(obj))

    def _check_outline(self, outline, obj, key, field_def):
        """Returns False if outline forbids to continue, and a new_outline to
        provide to the child if outline allows to go deeper.

        """

        if outline is None:
            return None

        if key not in outline and '*' not in outline:
            return False

        is_complex = field_def['type'] in ["one2many", "many2many",
                                           "many2one", "one2one"]

        if isinstance(outline, list):
            if is_complex:
                if key in outline:
                    ## You're are doing it wrong
                    self._logger.warn("Object %r outline %r is not a dict. "
                                      "Thus it should list only simple fields. "
                                      "But field %r is complex and was listed: "
                                      "this is incoherent. Ignoring this field."
                                      % (obj, outline, key))
                return False  ## No complex fields through list form.
            return []  ## Empty outline for simple form

        if isinstance(outline, dict):
            if key in outline:
                return outline[key]
            ## then '*' in outline
            if is_complex:
                return False  ## no complex fields can be selected with '*'
            return []

        self._logger.warn("Object %r outline %r is not a dict, a list, "
                          "nor value None. Ignoring all fields. field %r"
                          % (obj, outline, key, ))
        return False

    def _xml_oe_object(self, obj, deep, cache, outline=None):

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
                return F(*(self.obj2xml(o, deep=deep, cache=cache,
                                        outline=outline)
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

            ## Outline checking
            field_outline = self._check_outline(outline, obj, key, field_def)
            if field_outline is False:
                continue

            G = getattr(E, key)

            ## XXXvlab: what should I do of the states ?
            attr = dict((k, v if isinstance(v, unicode) else \
                                  unicode(v, 'utf-8'))
                        for k, v in field_def.iteritems()
                        if k in self._attr_keep_fields and
                           ## it has happened that ``v`` was False.
                           isinstance(v, basestring))

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
                elif field_def["relation"] in self.meta.get("ignore_models", []):
                    attr["cropped"] = "MATCHED_IGNORE_MODELS"
                    elt = G(**attr)
                    res.append(elt)
                    continue

            value = self.obj2xml(raw_value, deep=deep + 1, cache=cache,
                                 outline=field_outline)
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

    def obj2xml(self, obj, deep=0, cache=None, outline=None):
        cache = {} if cache is None else cache

        for types, fn_name in self._dump_dispatcher:
            if isinstance(obj, types):
                return getattr(self, fn_name, types)(obj, deep, cache,
                                                     outline=outline)

        if is_openerp_object(obj):
            return self._xml_oe_object(obj, deep, cache, outline=outline)

        raise NotImplementedError("Dump not implemented for %r (type: %r)"
                                  % (obj, type(obj)))
