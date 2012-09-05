XML Report module for OpenERP
=============================

**Please consider as pre-Alpha software** ;)

This module provides a new report type in OpenERP which can:

  - deliver a full XML dump of OpenERP_ database, including linked object to a
    configurable depth

  - use a `Mako template`_ to create any type of XML dumps.


.. _Mako template: http://www.makotemplates.org/
.. _OpenERP: http://www.openerp.com/


Usage
=====

This module is intended to be plugged to other modules that would use this
output to generate any kind of GED publishing.

For instance, this module was used in conjunction with `report_graphane`_ to
send XML to a `graphane server`_.

.. _report_graphane: https://github.com/simplee/report_graphane
.. _graphane server: http://www.callidoc.com


Installation
============

Once the code downloaded, don't forget to run ``./autogen.sh`` which will
generate the correct version number.

This is an openerp module, working with OpenERP 6.0, 6.1 and greater. So please
install as any other openerp module.

Once installed, you can create reports (Customization > Low Level Object >
Actions > Reports) of "Report Type" ``xml``, which should give you a new "XML"
tab.


Maturity
========

While this code is in full production in real GED environment, the code and
interface is not finished and the release was done in intent to share what
we are working on.

**Please consider this code as pre-Alpha software**.

Any contribution, idea, comments are welcome.


Roadmap
=======

Towards 1.0.0:

  - Complete examples of templates and XML

  - Openerp security permissions.

  - Full translations.

  - provide or use a real UI widget to display previews.

  - provide real help for the mako template dissociating mako parsing errors,
    python errors, xml validation errors.

  - write a doc on HOW TO install and use this code.

  - write a doc on XML full dump outlines.
