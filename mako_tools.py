"""Questionnable wrapping object and function to ease writing of mako templates

Note that you can run the doctest with:

    python -m doctest mako_tools.py

"""

from mako.template import Template

from babel.dates import format_date as babel_format_date
from datetime import datetime, date
import time

## This global dictionary will be added to mako environment
env = {}


def register(f):
    """Decorator helper to register function in the Mako environment"""
    env[f.__name__] = f
    return f


@register
def format_date(mp, locale):
    """Format a MakoParsable object as a date in provided locale

    This function is provided as a convenience shortcut for mako template
    writers.

    Usage
    =====

    Let's create two MakoParsable date:

        >>> epoch_datetime = MakoParsable(datetime.utcfromtimestamp(0))
        >>> epoch_string = MakoParsable("2000-10-10")

    ``format_date`` should convert to the accurate human local representation
    of these date:

        >>> format_date(epoch_datetime, "fr")
        u'1 janvier 1970'
        >>> format_date(epoch_string, "fr")
        u'10 octobre 2000'

    Acceptance of both format is required for conveniency as OOOP object and
    OpenERP object do not behave the same way when accessing datetime objects.

    Please note that providing a non-string / date object will result by
    returning a MakoParsable(None):

        >>> format_date(MakoParsable(2), "fr")
        None
        >>> type(format_date(MakoParsable(2), "fr"))  # doctest: +ELLIPSIS
        <class '...MakoParsable'>

    Please note that other languages are supported:

        >>> format_date(epoch_string, "en")
        u'October 10, 2000'
        >>> format_date(epoch_string, "de")
        u'10. Oktober 2000'

    """
    if not isinstance(mp, MakoParsable):
        raise TypeError("Argument %r is not a MakoParsable.")

    raw = getattr(mp, "_obj")

    if isinstance(raw, basestring):
        dt = datetime.strptime(raw, "%Y-%m-%d")
    elif isinstance(raw, datetime) or isinstance(raw, date):
        dt = raw
    else:
        return MakoParsable(None)
    return MakoParsable(babel_format_date(dt,
                                          format="long",
                                          locale=locale))


@register
def strftime(mp, fmt):
    """Format a MakoParsable date as a date in time.strftime provided format

    This function is provided as a convenience shortcut for mako template
    writers.

    Usage
    =====

    Let's create two MakoParsable date:

        >>> epoch_datetime = MakoParsable(datetime.utcfromtimestamp(0))
        >>> epoch_string = MakoParsable("2000-10-10")

    ``format_date`` should convert to the accurate human local representation
    of these date:

        >>> format_date(epoch_datetime, "fr")
        u'1 janvier 1970'
        >>> format_date(epoch_string, "fr")
        u'10 octobre 2000'

    Acceptance of both format is required for conveniency as OOOP object and
    OpenERP object do not behave the same way when accessing datetime objects.

    Please note that other languages are supported:

        >>> format_date(epoch_string, "en")
        u'October 10, 2000'
        >>> format_date(epoch_string, "de")
        u'10. Oktober 2000'

    """
    if not isinstance(mp, MakoParsable):
        raise TypeError("Argument %r is not a MakoParsable.")

    raw = getattr(mp, "_obj")

    if not raw:
        return MakoParsable(None)
    return MakoParsable(time.strftime(raw, fmt))


class MakoParsable(object):
    """Risky attempt to make a mako "user friendly" object.

    This is a general python object wrapper. Any python object can be wrapped:

        >>> two = MakoParsable(2)
        >>> an_object = MakoParsable(object())
        >>> a_list = MakoParsable([1, 2])
        >>> a_dict = MakoParsable({'a': 2})
        >>> a_string = MakoParsable("Hello World!")

    Any wrapped object should behave as if it wasn't wrapped:

        >>> two, an_object, a_list, a_dict, a_string  # doctest: +ELLIPSIS
        (2, <object object at ...>, [1, 2], {'a': 2}, 'Hello World!')

    For the exception of some behavior that would have casted exceptions, as
    AttributeErrors, where the MakoParsable(None) value will be returned...

        >>> two.foo
        None
        >>> type(two.foo)  # doctest: +ELLIPSIS
        <class '...MakoParsable'>

    These specifications will allow chaining attributes without having to check
    for existence of subattribute:

        >>> an_object.partner_id.user_id.name
        None

    And hopefully will reveal itself useful in mako templates more than it is
    cumbersome to have this strange magic.

    Note that callable can be wrapped:

        >>> my_fun = MakoParsable(lambda *args, **kwargs: (args, kwargs))

    And that the MakoParsable(None) can be called (and returns
    MakoParsable(None)).

        >>> MakoParsable(None)(1, 2, 3)
        None
        >>> type(MakoParsable(None)(1, 2, 3))  # doctest: +ELLIPSIS
        <class '...MakoParsable'>

    This is needed to complete the attribute defaulting coverage:

        >>> a_string.split()
        ['Hello', 'World!']
        >>> type(a_string.split())  # doctest: +ELLIPSIS
        <class '...MakoParsable'>

    And on object that do not support this method will then default to
    returning MakoParsable(None):

        >>> two.split()
        None

    There's a lot missing to impersonate a real object, but this is sufficient
    to test wether this is a really good idea or not.

    """

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
            def w(*args, **kwargs):
                return MakoParsable(val(*args, **kwargs))
            return w
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


def mako_template(text):
    """Build a Mako template from provided string

    This template uses UTF-8 encoding

    """
    return Template(text, input_encoding='utf-8', output_encoding='utf-8')


def render(tpl, obj):
    """Render mako template provided as string in tpl with object as 'object'

    Usage
    =====

    Here is a quick sample:

        >>> render('hello ${object}!', 'World')
        'hello World!'

    Please note that any registered function can be called:

        >>> render('current date: ${format_date(object, "en")}!', '2010-10-10')
        'current date: October 10, 2010!'

    """

    tpl_obj = mako_template(tpl)
    wrapped_obj = MakoParsable(obj)
    return tpl_obj.render(object=wrapped_obj, **env)
