/*global: openerp,window,QWeb,_,mySettings,$,navigator */


openerp.report_xml = function (instance) {

    var QWeb = instance.web.qweb,
    _t  = instance.web._t,
    _lt = instance.web._lt;

    instance.web.form.widgets.add('report_xml_template', 'instance.report_xml.FieldTextReportXMLTemplate');

    function escapeRegExp(string) {
        return string.replace(/([.*+?^=!:${}()|\[\]\/\\])/g, "\\$1");
    }

    String.prototype.replaceAll = function (find, replace) {
        return this.replace(new RegExp(escapeRegExp(find), 'g'), replace);
    };

    function escape_html_chars(string) {
        return string.replaceAll('&','&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;');
    }


    instance.report_xml.FieldTextReportTemplateReadOnly = instance.web.form.FieldText.extend({
        template: 'FieldTextReportTemplateReadOnly',

        render_value: function() {
            var self = this;
            debugger;  // XXXvlab: display the content of the template and don't compute anything
            if (! this.get("effective_readonly")) {
                return this._super.apply(this, arguments);
            } else {
                // XXXvlab: put a loading symbol
                this.rpc('/report_xml/rst2html', {
                    'source': this.get('value'),
                    'theme': 'nature'
                }).then(function(html_content) {
                    self._set_preview_html(html_content);
                });
            }
        }
    });


    /**
     * @class
     * @extends instance.web.ListView
     */
    instance.report_xml.Many2ManyVirtualListView = instance.web.ListView.extend({
        init: function (parent, dataset, view_id, options) {
            this._super(parent, dataset, view_id, _.extend(options || {}, {
                ListType: instance.report_xml.Many2ManyList,
            }));
        },
        do_add_record: function () {
            var pop = new instance.web.form.SelectCreatePopup(this);
            pop.select_element(
                this.model,
                {
                    title: _t("Add: ")
                },
                new instance.web.CompoundDomain(["!", ["id", "in", this.dataset.ids]]),
                this.dataset.get_context()
            );
            var self = this;
            pop.on("elements_selected", self, function(element_ids) {
                var reload = false;
                _(element_ids).each(function (id) {
                    if (! _.detect(self.dataset.ids, function(x) {return x == id;})) {
                        self.dataset.set_ids(self.dataset.ids.concat([id]));
                        self.dataset.trigger("dataset_changed");
                        reload = true;
                    }
                });
                if (reload) {
                    self.reload_content();
                }
            });
        },
        do_activate_record: function(index, id) {
            var self = this;
            var pop = new instance.web.form.FormOpenPopup(this);
            pop.show_element(this.dataset.model, id, this.dataset.get_context(), {
                title: _t("Open: ") + this.name,
                readonly: this.getParent().get("effective_readonly")
            });
            pop.on('write_completed', self, self.reload_content);
        },
        do_button_action: function(name, id, callback) {
            var self = this;
            new instance.web.Dialog(this, {
                size: 'large',
                title: "OpenERP Error",
                buttons: [{
                    text: _t("Ok"),
                    click: function() {
                        this.parents('.modal').modal('hide');
                    }}],
            }, $('<div>Action not implemented yet. ' +
                 'Please contact your administrator.</div>')).open();
            // var _sup = _.bind(this._super, this);
            // if (! this.m2m_field.options.reload_on_button) {
            //     return _sup(name, id, callback);
            // } else {
            //     return this.m2m_field.view.save().then(function() {
            //         return _sup(name, id, function() {
            //             self.m2m_field.view.reload();
            //         });
            //     });
            // }
        },
        is_action_enabled: function () { return true; },
    });
    instance.report_xml.Many2ManyList = instance.web.form.AddAnItemList.extend({
        _add_row_class: 'oe_form_field_many2many_list_row_add',
        is_readonly: function () {
            try {
                res = this.view.getParent().get('effective_readonly');
            } catch(e) {
                // XXXvlab: should probably catch why we get here
            }
            return res;
        }
    });


    instance.report_xml.FieldTextReportXMLTemplate = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {

        template: 'FieldReportXMLTemplate',
        display_name: _lt('ReportXmlTemplate'),
        widget_class: 'oe_form_field_report_xml_template',
        events: {
            'change input': 'store_dom_value'
        },
        init: function (field_manager, node) {
            this._super(field_manager, node);
            this.$txt = false;
            this.old_value = null;
            this.old_source = null;

            this.object_ids = [];
            this.dataset = null;                // M2M memory dataset
            this.objects_select_widget = null;  // M2M list view


        },
        on_field_multi_changed: function () {
            this.render_value();
        },
        on_field_model_changed: function() {
            if (this.get("effective_readonly")) return;
            var self = this;
            this.select_objects_reinit().then(function() {
                self.render_value();
            });
        },
        on_field_xml_full_dump_changed: function() {
            if (this.get("effective_readonly")) return;
            this.reinitialize();
        },
        initialize_content: function() {
            // Gets called at each redraw of widget
            //  - at .start() which occurs in ``.init_fields`` for parent form start
            //    and just after render.
            //  - switching between read-only mode and edit mode (after renderElement())
            //  - BUT NOT when switching to next object.

            // So you shouldn't have to worry about double binding some event as the
            // in any case, the elements are new.

            console.log("INIT " + (this.get("effective_readonly") ?
                                  "READ ONLY" : "READ WRITE"));

            this.$txt = this.$el.find('textarea[name="' + this.name + '"]');
            this.setupFocus(this.$txt);

            if (this.get('effective_readonly')) return; // Nothing more to do in read-only.

            // These elements are rendered (or used) only on edit mode

            this.$split = this.$el.find('div.oe_report_xml_split');
            this.$select_objects = this.$el.find('div.report_xml_select_objects');
            this.$select_objects_title = this.$el.find('h4.select_preview_title');
            this.$select_objects_area = this.$el.find('div.report_xml_select_objects_area');
            this.$select_area = this.$el.find('div.report_xml_select_area');
            this.$preview_pane = this.$el.find('.oe_preview_pane');
            this.$preview = this.$el.find('div.oe_form_field_preview');
            this.$no_preview_message = this.$el.find('div.no_preview_message');

            this.$txt.attr('readonly', false);

            // Events

            var self = this;

            this.$select_objects_title.click(function() {
                self.select_widget_toggle();
            });


            // this.$txt.reportxml(
            //     $.extend(mySettings, {
            //         resizeHandle: false,
            //     }));

            this.$editor = $('<div />');
            this.$editor.appendTo(this.$el.find('div.report_xml_edit_ace_editor'));
            this.$txt.remove();

            this.editor = ace.edit(this.$editor[0]);
            this.editor.setTheme("ace/theme/" + this.theme);
            this.editor.getSession().setMode("ace/mode/" + this.mode);
            this.editor.setValue();
            this.$editor.height("520px");
            this.$editor.data('editor', this.editor);

            this.view.fields.multi.on("changed_value", this, this.on_field_multi_changed);
            this.view.fields.model.on("changed_value", this, this.on_field_model_changed);

            this.init_splitter();

            this.$el.find("div.report_xml_edit_ace_editor div").on("scroll", function() {
                self.sync_scroll_position();
            });

            this.editor.on('change', function() {
                self._gen_preview_html();
            });

            this.old_value = null; // will trigger a redraw
            this.old_source = null; // will trigger saving of value if any.

            this.view.fields.xml_full_dump.on(
                "changed_value",
                this, this.on_field_xml_full_dump_changed);

        },
        init_splitter: function () {
            // In forms, we could be hidden in a notebook. Thus we couldn't
            // render correctly the splitter so we try to detect when we are
            // not visible to wait for when we will be visible.

            // This is a bug that can't really be fixed: http://bugs.jquery.com/ticket/14685
            // we must wait for the div to show.

            var self = this;
            var def = $.Deferred();

            console.log("INIT NEW SPLITTER");

            if (this.$split.is(':visible'))  {
                def.resolve();
            } else {
                this.$split.parents(".ui-tabs").on('tabsactivate', function() {
                    if (self.$split.is(':visible')) {
                        def.resolve();
                    }
                });
            }
            $.when(def).then(function() {
                self.$split.splitter({
                    type: "v",
                    dock: "rightDock",
                    minRight: 250,
                    dockSpeed: 200,
                    resizeToWidth: true,
                });
                self.$split.on('move resize', function() {
                    self.editor.resize();
                });
                self.$split.trigger('resize');
            });
            return def;
        },
        destroy_select: function() {
            console.log("MY DESTROY SELECT");
            if (this.objects_select_widget) {
                console.log(" -- EFFECTIVE DESTROY");
                this.objects_select_widget.destroy();
                this.objects_select_widget = undefined;
                this.dataset.destroy();
                this.dataset = null;
                this.object_ids = [];
            }
            if (this.$select_objects_area) {
                // this will remove any message or widget
                this.$select_objects_area.empty();
            }
        },
        destroy_content: function () {
            // Called by reinitialize from ReinitializeFieldMixin upon
            //   - readonly change
            console.log("MY DESTROY CONTENT");
            if (this.$split && this.$split.data('splitter'))
                this.$split.splitter('destroy');
            if (this.$editor && this.editor)
                this.editor.destroy();
            this.destroy_select();
            this.view.fields.multi.off("changed_value", this, this.on_field_multi_changed);
            this.view.fields.model.off("changed_value", this, this.on_field_model_changed);
            this.view.fields.xml_full_dump.off(
                "changed_value",
                this, this.on_field_xml_full_dump_changed);

        },
        select_widget_toggle: function (duration) {
            var $sot = this.$select_objects_title;
            var $soa = this.$select_objects_area;
            var def = $.Deferred();
            duration = duration || 150;
            if ($sot.hasClass('open')) {
                $sot.removeClass('open');
                $sot.addClass('closed');
                $soa.slideUp(duration, function() { def.resolve(); });
            } else {
                $sot.removeClass('closed');
                $sot.addClass('open');
                $soa.slideDown(duration, function() { def.resolve(); });
            }
            return def;
        },
        select_objects_reinit: function() {
            // Take care of previous widget/dataset already present if present.
            // returns a deferred that ends when all animation and html is finished.

            var self = this;
            var def = $.Deferred();
            var model = this.view.fields.model.get_value();
            var was_select_open = this.$select_objects_title.hasClass('open');
            var previous_model = this.dataset ? this.dataset.model : null;

            if (previous_model === model) return; // nothing to be done

            var my_token = _.uniqueId('report_xml_');
            this._priority_token = my_token; // Take precedence.

            (was_select_open ? this.select_widget_toggle(50) : $.when()).then(function() {
                if (self._priority_token !== my_token) return;
                self.destroy_select(); // clean database and widget for selection
                self._select_create(model, my_token).then(function() {
                    (was_select_open ? self.select_widget_toggle(50): $.when())
                        .then(function() {
                            def.resolve();
                        });
                });
            });
            return def;
        },
        _select_create: function(model, token) {
            // Should only be called by select_objects_reinit().
            // Starts with an object that don't have any database/widget set.
            // And our responsibility is to create the widget/dataset on given model.
            //   we are ment to fill this.$select_objects_area

            var self = this;
            var def = $.Deferred();

            if (this._priority_token !== token) {
                console.log("Canceled running creation of m2m select box for model " + model);
                return def.resolve();
            }

            // var defaults = {};
            // _.each($.extend({}, this.data_template, data), function(val, field_name) {
            //     defaults['default_' + field_name] = val;
            // });

            var context = this.view.dataset.get_context();

            // check if given model is valid

            var query_models = (new instance.web.Model("ir.model")).query(["name"]);
            query_models.filter([['model', '=', model]]).first().then(function(data) {
                // Warning: this part could actually be run just after a change to readonly
                // occured. So in the body of the function it was edit mode, and suddenly
                // now it's not anymore this mode. In this latter case, we must quit as
                // there are no more widget to fill.
                if (self.get('effective_readonly')) {
                    console.log("Canceled running creation of m2m select box for model " +
                                model + " -- we are now in read-only");
                    return def.resolve();
                }
                if (self._priority_token !== token) {
                    console.log("Canceled running creation of m2m select box for model " +
                                model);
                    return def.resolve();
                }
                if (!data) {
                    self.$select_objects_area.html(
                        '<div class="error_wrong_model">The given model ' +
                            model + ' is not found in OpenERP.</div>');
                    return def.resolve();
                }

                console.log("MY CREATE SELECT");
                self.dataset = new instance.web.DataSetStatic(
                    self, model, context, self.ids);

                self.objects_select_widget = new instance.report_xml.Many2ManyVirtualListView(
                    self, self.dataset, false, {
                        'addable': null,
                        'deletable': true,
                        'selectable': false,
                        'sortable': true,
                        'reorderable': true,
                        'import_enabled': false,
                        'confirm_deletion': false,
                    });

                self.objects_select_widget.on("list_view_loaded", self, function() {
                    if (self._priority_token !== token) {
                        console.log("Possible leaking event listener");
                        debugger;
                    } else {
                        self.objects_select_widget.reload_content();
                    }
                    def.resolve();
                });
                self.objects_select_widget.dataset.on(
                    'dataset_changed unlink',
                    self, function() {
                        if (self._priority_token !== token) {
                            console.log("Possible leaking event listener");
                            debugger;
                            return;
                        }
                        self.object_ids = self.objects_select_widget.dataset.ids;
                        self._gen_preview_html();
                    });
                self.objects_select_widget.appendTo(self.$select_objects_area);
            });
            return def;
        },
        _get_raw_value: function() {
            if (_.isUndefined(this.editor))
                return '';
            return this.editor.getValue();
        },
        _set_rendering_status: function(data, $el) {
            var out;
            var $pre = $el.find("pre");
            if ($pre.length === 0) {
                $pre = $("<pre/>");
                $el.append($pre);
            }
            if (data.status === 'ok') {
                $pre.addClass("ok");
                $pre.removeClass("warning");
                out = data.output;
            } else {
                $pre.addClass("warning");
                $pre.removeClass("ok");
                if (data.error === 'XML Syntax') {
                    out = data.message + "\n\n-- Source:\n\n" + data.source;
                } else {
                    out = data.message;
                }
            }

            $pre.html(escape_html_chars(out));
        },
        do_print_record: function(active_ids, active_model) {
            var self = this;
            var action = {
                context: {
                    active_id: active_ids[0],
                    active_ids: active_ids,
                    active_model: active_model
                },
                report_type: this.view.fields.report_type.get_value(),
                report_name: this.view.fields.report_name.get_value(),
                name: this.view.fields.name.get_value()
            };

            instance.web.blockUI();

            var c = instance.webclient.crashmanager;
            return $.Deferred(function (d) {
                self.session.get_file({
                    url: '/web/report',
                    data: {action: JSON.stringify(action)},
                    complete: instance.web.unblockUI,
                    success: function(){
                        d.resolve();
                    },
                    error: function (options) {
                        options = options.orig_body ?
                            JSON.parse(options.orig_body.childNodes[2]
                                       .textContent) : options;
                        if (options.data.exception_type === "except_osv") {
                            // Handle the error ourselves as 8.0 is broken
                            var error = _.extend({}, options, {
                                data: _.extend({}, options.data, {
                                    message: options.data.arguments[0]})});
                            var dialog = new instance.web.Dialog(this, {
                                size: 'large',
                                title: "OpenERP Error",
                                buttons: [{
                                    text: _t("Ok"),
                                    click: function() {
                                        dialog.close();
                                    }}],
                            }, $('<div>' + QWeb.render('ReportError',
                                                       {error: error}) +
                                 '</div>')).open();
                        } else if (options.data.exception_type === "except_orm") {
                            debugger;
                        } else {
                            c.rpc_error.apply(c, [options]);
                        }
                        d.reject();
                    }
                });
            });
        },
        no_preview_message: function (msg) {
            this.$no_preview_message.html(
                "<span class='no_preview_object'>" + msg + "</span>");
            this.$no_preview_message.show();
            this.$preview.fadeOut();
        },
        add_check_for_report: function (value, id) {
            var self = this;

            if (id !== 0) {
                value = _.clone(value);
                value.active_ids = [id];
                value.id = id;
            }

            var $el = this.$preview.find("div.check#check-" + id);
            if ($el.length === 0) {
                var title = id === 0 ? "Multi-Object Report" : "Single Object Report";
                $el = $("<div class='check' id='check-" + id  +"'>" +
                        "<button type='button' class='btn btn-default btn-lg get-report'>" +
                        "<span class='glyphicon glyphicon-download'></span>" +
                        "</button>" +
                        "<div class='indicator'></div>" +
                        "<div class='message'></div>" +
                        "<h3>" + title + "</h3>" +
                        "<div class='content' style='display: none;'></div>" +
                            "</div>").hide();
                this.$preview.append($el);
                $el.find("button.get-report").click(function() {
                    var active_ids = $(this).data("active_ids");
                    var active_model = $(this).data("active_model");
                    self.view.save().done(function () {
                        self.do_print_record(active_ids, active_model);
                    });
                });
                if (navigator.userAgent.toLowerCase().indexOf('firefox') > -1) {
                    $el.find(".glyphicon.glyphicon-download").css('top', '-1px');
                }

                $el.find("h3").click(function() {
                    $(this).toggleClass("open");
                    $el.find(".content").slideToggle(100);
                });
                $el.slideDown(150);

            }

            $el.find("button.get-report")
                .data("active_ids", value.active_ids)
                .data("active_model", value.active_model);

            var $content = $el.find(".content");
            var $indicator = $el.find(".indicator");
            var $message = $el.find(".message");

            $indicator.html("<i class='fa fa-cog fa-spin fa-2x'></i>");
            $indicator.addClass("loading");
            $indicator.removeClass("warning");
            $indicator.removeClass("ok");

            if ($content.css('display') !== "none") {
                $content.find("pre").animate({
                    backgroundColor: "#e0e0e0",
                    color: "#888",
                }, 1000 );
            }

            this.rpc('/report_xml/check_mako_rendering', value, {shadow: true}).then(
                function(data) {
                    $indicator.removeClass("loading");
                    $content.find("pre").stop();

                    if (data.status === 'ok') {
                        $message.fadeOut();
                        $indicator.addClass("ok");
                        $indicator.html("<i class='fa fa-check-circle fa-2x'></i>");
                        if ($content.css('display') !== "none") {
                            $content.find("pre").animate({
                                backgroundColor: "#f8f8f8",
                                color: "#222"
                            }, 300 );
                        }
                    } else {
                        $indicator.addClass("warning");
                        $indicator.html("<i class='fa fa-warning fa-2x'></i>");
                        $message.fadeIn();
                        $message.html(data.error);
                        if ($content.css('display') !== "none") {
                            $content.find("pre").animate({
                                backgroundColor: "#f8f8f8",
                                color: "#422"
                            }, 300 );
                        }

                    }
                    $indicator.addClass(data.status);
                    self._set_rendering_status(data, $content);
                    self.sync_scroll_position();
                });
        },
        _gen_preview_html: function() {

            var self = this;
            var preview = this.objects_select_widget;
            var active_ids = preview ? preview.dataset.ids : [];
            var active_model = this.view.fields.model.get_value();


            var source = this._get_raw_value();
            if (source !== this.old_source) {
                // Triggers store_dom_value and dirty state.
                // ``internal`` is required to stop rerendering which
                // would reset textarea view position to top.
                this.internal_set_value(source);
                this.old_source = source;
            }

            if (source.length === 0) {
                return this.no_preview_message("No content to render.");
            }

            if (active_ids.length === 0) {
                return this.no_preview_message(
                    "Please select at least one preview object to enable preview.");
            }

            this.$preview.fadeIn(400, function() {
                self.$no_preview_message.hide();
            });

            if (this.$preview_pane.css('display') == "none")
                return;

            var multi = this.view.fields.multi.get_value();
            // XXXvlab: put a loading symbol in the preview window and remove the
            // global application loading symbol and blockade !
            var value = {'id': this.view.datarecord.id,
                         'active_ids': active_ids,
                         'source': source,
                         'active_model': active_model};
            if (_.isEqual(value, this.old_value) &&
                (multi === this.old_multi))
                return;

            this.old_value = value;
            this.old_multi = multi;

            var ids = multi ? [0] : active_ids;
            // Remove all boxes for previous checks (but not the one to be redrawn)
            this.$preview.find("div.check").each(function () {
                var id = parseInt(this.id.split("-")[1], 10);
                if (!_.contains(ids, id)) {
                    $(this).slideUp(500, function() {
                        $(this).remove();
                    });
                }
            });
            _(ids).each(function(id) {
                // trigger addition or redraw of all boxes
                self.add_check_for_report(value, id);
            });

        },

        store_dom_value: function () {
            if (!this.get('effective_readonly') &&
                this._get_raw_value() !== '' &&
                this.is_syntax_valid()) {
                // We use internal_set_value because we were called by
                // ``.commit_value()`` which is called by a ``.set_value()``
                // itself called because of a ``onchange`` event
                this.internal_set_value(
                    this.parse_value(
                        this._get_raw_value()));
            }
        },

        commit_value: function () {
            this.store_dom_value();
            return this._super();
        },

        sync_scroll_position: function () {

            var editorScrollRange = (
                (this.editor.getSession().getScreenLength() *
                 this.editor.renderer.lineHeight) -
                    this.$editor.innerHeight());
            var previewScrollRange = (this.$preview_pane[0].scrollHeight -
                                      this.$preview_pane.innerHeight());

            // Find how far along the editor is (0 means it is scrolled to the top, 1
            // means it is at the bottom).
            var scrollFactor = this.editor.getSession().getScrollTop() / editorScrollRange;

            // Set the scroll position of the preview pane to match.  jQuery will
            // gracefully handle out-of-bounds values.
            this.$preview_pane.scrollTop(scrollFactor * previewScrollRange);
        },

        render_value: function() {
            if (this.view.fields.xml_full_dump.get_value()) return;

            // Gets called at each redraw/save of widget
            //  - at start
            //  - switching between read-only mode and edit mode
            //  - when switching to next object.
            console.log("RENDER " +
                        (this.get("effective_readonly") ?
                         "READ ONLY" : "READ WRITE"));
            var show_value = this.format_value(this.get('value'), '');
            var readonly = this.get("effective_readonly");

            if (readonly) {
                this.$txt.attr("readonly", readonly);
                this.$txt.val(show_value);
                this.destroy_content();
                return;
            }
            this.editor.setValue(show_value);
            this.editor.clearSelection();
            this.editor.moveCursorTo(0,0);

            if (this.dataset) this.dataset.set_ids(this.object_ids);
            this.select_objects_reinit();
            this._gen_preview_html();
            this.$split.trigger('resize');
        },

        is_syntax_valid: function() {
            if (!this.get("effective_readonly") && this._get_raw_value().length > 0) {
                try {
                    this.parse_value(this._get_raw_value(), '');
                    return true;
                } catch(e) {
                    return false;
                }
            }
            return true;
        },

        parse_value: function(val, def) {
            return instance.web.parse_value(val, this, def);
        },

        format_value: function(val, def) {
            return instance.web.format_value(val, this, def);
        },

        is_false: function() {
            return this.get('value') === '' || this._super();
        },

        // XXXvlab: how to test ?
        focus: function() {
            this.$('textarea:first')[0].focus();
        },

        set_dimensions: function (height, width) {
            this._super(height, width);
            this.$('textareat').css({
                height: height,
                width: width
            });
        }
    });
};
