"""Creates a Questionnable Wrapping Object to ease writing of mako templates

"""

from babel.dates import format_date as babel_format_date
from datetime import datetime, date

env = {}


def register(f):
    env[f.__name__] = f
    return f


@register
def format_date(s, locale):
    if isinstance(s._obj, basestring):
        dt = datetime.strptime(s._obj, "%Y-%m-%d")
    elif isinstance(s._obj, datetime) or isinstance(s._obj, date):
        dt = s._obj
    else:
        return MakoParsable(None)
    return babel_format_date(dt,
                             format="long",
                             locale=locale)

@register
def custom_format_date(s, format):
    if not s._obj:
        return s
    return time.strftime(s._obj, format)


class MakoParsable(object):

    NULL = {}

    def __init__(self, obj):
        self._obj = obj

    def __getattr__(self, label):
        try:
            val = getattr(self._obj, label)
        except (AttributeError, NameError):
            val = None
        if isinstance(val, basestring):
            val = val.strip()
        if callable(val):
            return val
        return MakoParsable(val)

    def __call__(self, *args, **kwargs):
        if self._obj is None:
            return MakoParsable(None)
        return self._obj(*args, **kwargs)

    def __len__(self):

        if self._obj is None:
            return 0

        try:
            res = len(self._obj)
        except TypeError:
            return 1
        return res

    def __str__(self):
        if self._obj is False or \
           self._obj is None:
            return ""
        return unicode(self._obj)

    def __iter__(self):
        try:
            res = iter(self._obj)
        except ValueError:
            return ()
        return (MakoParsable(o) for o in res)

    def __repr__(self):
        return repr(self._obj)

    def __getitem__(self, value):
        try:
            res = self._obj.__getitem__(value)
        except (TypeError, AttributeError):
            return MakoParsable(None)
        return MakoParsable(res)

    def __mul__(self, value):
        try:
            res = self._obj.__mul__(value)
        except (TypeError, AttributeError):
            return MakoParsable(None)
        return MakoParsable(res)

