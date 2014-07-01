# -*- coding: utf-8 -*-

from mako import exceptions

import traceback


from openerp.http import Controller, route
from openerp.http import request
from openerp.addons.web.controllers.main import Reports, content_disposition, serialize_exception
from ..mako_tools import render
from ..common import format_last_exception, xml2string, string2xml
from lxml.etree import XMLSyntaxError


from openerp import pooler
import openerp.modules.registry

from openerp.tools.safe_eval import safe_eval


class Home(Controller):

    @route(['/report_xml/check_mako_rendering/'], type='json', auth="public")
    def check_mako_rendering(self, id=None, active_ids=None, active_model=None,
                             source=None):
        s = request.session
	if not source:
            return ""

        registry = openerp.modules.registry.RegistryManager.get(request.session._db)
        objs = registry.get(active_model).browse(request.cr, s.uid, active_ids, s.context)
        base_env = {"_uid": s.uid, "_cr": request.cr, "_pool": pooler.get_pool(s.db),
                    "_context": s.context}

        results = []
        try:
            output = render(source, objects=objs, object=objs[0], **base_env)
        except exceptions.SyntaxException, e:
            return {'status': 'ko',
                    'error': 'Mako Syntax Error',
                    'line': e.lineno,
                    'col': e.pos,
                    'results': results,
                    'message': e.message,
                    'more': None}
        except Exception, e:
            tb = exceptions.RichTraceback()
            output = ""
            prevent = True
            first = True
            for (filename, lineno, function, line) in tb.traceback:
                if filename.startswith('memory:'):
                    prevent = False
                if prevent:
                    continue
                if filename.startswith('memory:'):
                    first = False
                    output += "  Line %s, in template:\n" % (lineno, )
                else:
                    output += "  File %s, line %s, in %s\n" \
                              % (filename, lineno, function)
                output += "    %s\n" % line
            output += "%s: %s\n" % (str(tb.error.__class__.__name__), tb.error)
            return {'status': 'ko',
                    'error': 'Mako Runtime Error',
                    'line': tb.lineno,
                    'results': results,
                    'message': e.message,
                    'more': output}

        ## XXXvlab: translation please !
        results.append({'type': 'text',
                        'content': output,
                        'title': 'Mako render',
                        })
        ## Should move this to another method. Ideally the first part should
        ## be in a report_mako module, and this second in a report_xml module

        try:
            output = string2xml(output)
        except XMLSyntaxError, e:
            message_lines = []
            errors = []
            for line in str(e.error_log).split("\n"):
                fields = line.split(":", 7)
                line = fields[1]
                col = fields[2]
                msg = fields[6]
                errors.append({'line': line, 'col': col, 'msg': msg})
                message_lines.append("Line %s, Column %s: %s"
                                     % (line, col, msg))
            return {'status': 'ko',
                    'error': 'XML Syntax',
                    'line': line,
                    'col': col,
                    'source': output,
                    'results': results,
                    'errors': errors,
                    'message': "\n".join(message_lines)}
        except Exception, e:
            exc = format_last_exception()
            return {'status': 'ko',
                    'error': 'Unrecognised XML Issue',
                    'line': -1,
                    'message': exc}
        else:
            output = xml2string(output)
        ## XXXvlab: translation please !
        results.append({'type': 'xml',
                        'content': output,
                        'title': 'XML',
                        })

        return {'status': 'ok',
                'results': results}
