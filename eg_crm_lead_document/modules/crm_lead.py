from odoo import models, fields, _


class CrmLead(models.Model):
    _inherit = "crm.lead"

    attachment_ids = fields.Many2many(comodel_name="ir.attachment", string="Attachment")
    attachment_count = fields.Integer(string="Attachment Count", compute="_compute_attachment_count")

    def _compute_attachment_count(self):
        for lead_id in self:
            lead_id.attachment_count = len(lead_id.attachment_ids.ids) if lead_id.attachment_ids else 0

    def action_add_document(self):
        return {
            'name': _('Add Document'),
            'res_model': 'crm.document',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_view_document(self):
        action = self.env.ref('base.action_attachment').read()[0]
        attachments = self.attachment_ids
        if len(attachments) > 1:
            action['domain'] = [('id', 'in', attachments.ids)]
        elif attachments:
            action['views'] = [(self.env.ref('base.view_attachment_form').id, 'form')]
            action['res_id'] = attachments.id
        return action