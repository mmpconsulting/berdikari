# -*- coding: utf-8 -*-
# from odoo import http


# class YmKasbon(http.Controller):
#     @http.route('/ym_kasbon/ym_kasbon', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ym_kasbon/ym_kasbon/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ym_kasbon.listing', {
#             'root': '/ym_kasbon/ym_kasbon',
#             'objects': http.request.env['ym_kasbon.ym_kasbon'].search([]),
#         })

#     @http.route('/ym_kasbon/ym_kasbon/objects/<model("ym_kasbon.ym_kasbon"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ym_kasbon.object', {
#             'object': obj
#         })
