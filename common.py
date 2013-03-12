# -*- coding: utf-8 -*-
"""Various common functions

"""

from lxml import etree as ET
import traceback


def format_last_exception():
    """Format the last exception for display it in tests."""

    return '\n'.join(
        ["  | " + line for line in traceback.format_exc().strip().split('\n')]
    )


def xml2string(content):
    """Render a ElementTree to a string with some default options

    """
    return ET.tostring(content,
                       pretty_print=True,
                       xml_declaration=True,
                       encoding="utf-8")


def string2xml(content):
    return ET.fromstring(content)
