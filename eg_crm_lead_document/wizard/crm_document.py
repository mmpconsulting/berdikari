from odoo import models, fields, api


class CRMDocument(models.TransientModel):
    _name = "crm.document"

    file = fields.Binary(string='File')
    file_name = fields.Char(string='File Name')


    def add_document(self):
        lead_id = self.env["crm.lead"].browse(self._context.get("active_id"))
        attachment_id = self.env["ir.attachment"].create({
            "datas": self.file,
            "name": self.file_name,
            "res_model": lead_id._name,
            "res_id": lead_id.id,
        })
        lead_id.attachment_ids = [(4, attachment_id.id)]