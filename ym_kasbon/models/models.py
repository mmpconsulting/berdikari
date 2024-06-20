# -*- coding: utf-8 -*-

from num2words import num2words
from odoo import api, Command, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext


from odoo.osv import expression
from odoo.tools.float_utils import float_is_zero
from bisect import bisect_left
from collections import defaultdict
import re


class AccountAccount(models.Model):
    _inherit='account.account'

    sequence_code = fields.Char('Sequnce Code')

class AccountAnayticAccount(models.Model):
    _inherit='account.analytic.account'

    property_account_payable_id = fields.Many2one('account.account',
        string="Account Payable",
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used instead of the default one as the payable account for the current partner")
    property_account_receivable_id = fields.Many2one('account.account', 
        string="Account Receivable",
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used instead of the default one as the receivable account for the current partner")

class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'Account Move'
    
    lpj_kasbon_operasional_id = fields.Many2one('lpj.kasbon.operasional', string='LPJ Kasbon Operasional', compute='_compute_reference')
    kasbon_operasional_id = fields.Many2one('kasbon.operasional', string='Kasbon Operasional', compute='_compute_reference')
    cek_bg_no = fields.Char('Cek/BG No.')
    is_kasbon = fields.Boolean(compute='_compute_is_kasbon', string='Is Kasbon')
    terbilang = fields.Char('Terbilang', compute='amount_to_words')
    dibayarkan_kpd_id = fields.Many2one('hr.employee', string='Dibayarkan Kepada')
    lampiran = fields.Char('Lampiran')
    analytic_distribution = fields.Json(string='Proyek')
    analytic_precision = fields.Integer(string='Analytic Precision', store=False, default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"))
    analytic_distribution_convert_to_char = fields.Char('Analytic Distribution Convert to Char', compute='_compute_convert_chart')
    
    @api.model_create_multi
    def create(self, vals_list):       
        result = super(AccountMove, self).create(vals_list)        
        for res in result:
            if res.analytic_distribution:
                distibution_ids = []
                for distibution in list(res.analytic_distribution):
                    distibution_ids.append(int(distibution))
                anlytic_id = self.env['account.analytic.account'].browse(distibution_ids)[0]
                if anlytic_id and res.move_type != 'entry':
                    if res.move_type == 'in_invoice':
                        ar_account_id = res.line_ids.filtered(lambda line: line.account_id == res.partner_id.property_account_payable_id)
                        acount = anlytic_id.property_account_payable_id
    
                    else:
                        ar_account_id = res.line_ids.filtered(lambda line: line.account_id == res.partner_id.property_account_receivable_id)
                        acount = anlytic_id.property_account_receivable_id
                    
                    if acount:
                        ar_account_id.write({
                            'account_id' : acount.id,
                            'name': anlytic_id.name
                        })
        return result

    def get_roman(self, input):
        ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
        nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
         
        result = ""
        for i in range(len(ints)):
            count = int(input / ints[i])
            result += nums[i] * count
            input -= ints[i] * count
        return result
    
    def action_post(self):
        account_sequence = self.line_ids.filtered(lambda line: line.account_id.sequence_code)
        if self.name == '/' and account_sequence and not self.partner_id and self.move_type == 'entry':
            number = 1
            year = self[self._sequence_date_field].year 
            month = self.get_roman(self[self._sequence_date_field].month)
            sequence_format = '/' + self.journal_id.code + '/' + account_sequence[0].account_id.sequence_code + '/' + month +'/' + str(year)[-2:]
            query = """ SELECT sequence_number FROM account_move where sequence_prefix = %s ORDER BY id DESC
                LIMIT 1 """
            self.env.cr.execute(query, ([sequence_format]))
            number_tuple = self.env.cr.fetchone()
            if number_tuple:
                number = 1 + int(''.join(map(str, number_tuple)))
            while(True):
                query = """ SELECT sequence_number FROM account_move where name = %s ORDER BY id DESC
                LIMIT 1 """
                self.env.cr.execute(query, ([f'{number:03}' + sequence_format]))
                cek_name = self.env.cr.fetchone()
                if cek_name:
                    number = number + 1
                else:
                    break
            self.name = f'{number:03}' + sequence_format
        else:
            sequence_format = self.sequence_prefix
            number = self.sequence_number

        res = super(AccountMove, self).action_post()
        if not self.partner_id and self.move_type == 'entry': 
            self.sequence_prefix = sequence_format 
            self.sequence_number = number
        return res
    
    def button_draft(self):
        sequence_format = self.sequence_prefix
        number = self.sequence_number
        res = super(AccountMove, self).button_draft()
        self.sequence_prefix = sequence_format 
        self.sequence_number = number
        return res


    @api.depends('analytic_distribution')
    def _compute_convert_chart(self):
        for record in self:
            analytic_distribution = ''
            if record.analytic_distribution:
                distibution_ids = []
                for distibution in list(record.analytic_distribution):
                    distibution_ids.append(int(distibution))
                
                anlytic = self.env['account.analytic.account'].browse(distibution_ids).mapped('name')
                if anlytic:
                    analytic_distribution = " / ".join(anlytic)
            record.analytic_distribution_convert_to_char = analytic_distribution
    
    @api.depends('journal_id', 'journal_id.is_kasbon', 'journal_id.is_lpj_kasbon' )
    def _compute_is_kasbon(self):
        for move in self:
            is_kasbon = False
            if move.journal_id:
                if move.journal_id.is_kasbon == True or move.journal_id.is_lpj_kasbon == True:
                    is_kasbon = True
            move.is_kasbon = is_kasbon

    @api.depends('line_ids', 'line_ids.credit', 'line_ids.debit')
    def amount_to_words(self):
        for move in self:
            terbilang = 0
            for line in move.line_ids:
                if move.journal_id:
                    if move.journal_id.opsi_print == 'debit':
                        if line.debit != 0.00:
                            terbilang = terbilang + line.debit
                    elif move.journal_id.opsi_print == 'credit':
                        if line.credit != 0.00:
                            terbilang = terbilang + line.credit

            move.terbilang = num2words(int(terbilang), to='currency', lang='id')
    
    
    @api.depends('ref', 'name')
    def _compute_reference(self):
        for move in self:
            lpj_kasbon_operasional_id = False
            kasbon_operasional_id = False
            lpj_kasbon_operasional = self.env['lpj.kasbon.operasional'].search(['|', ('name', '=', move.ref), ('move_id', '=', move.id)], limit=1)
            if lpj_kasbon_operasional:
                lpj_kasbon_operasional_id = lpj_kasbon_operasional.id
            kasbon_operasional = self.env['kasbon.operasional'].search(['|', ('name', '=', move.ref), ('move_id', '=', move.id)], limit=1)
            if kasbon_operasional:
                kasbon_operasional_id = kasbon_operasional.id
            move.lpj_kasbon_operasional_id = lpj_kasbon_operasional_id
            move.kasbon_operasional_id = kasbon_operasional_id


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    _description = 'Account Journal'
    

    is_kasbon = fields.Boolean('Is Kasbon Operaional')
    is_lpj_kasbon = fields.Boolean('Is LPJ Kasbon Operaional')
    account_debit_kasbon_id = fields.Many2one('account.account', string='Account Debit Kasbon', ondelete='restrict')
    account_credit_kasbon_id = fields.Many2one('account.account', string='Account Credit Kasbon', ondelete='restrict')
    account_credit_lpj_kasbon_id = fields.Many2one('account.account', string='Account Credit LPJ Kasbon', ondelete='restrict')
    judul_report = fields.Char('Judul Report')
    opsi_print = fields.Selection([
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ], string='Opsi Print')

    @api.onchange('account_debit_kasbon_id')
    def _onchange_account_debit_kasbon_id(self):
        account_credit_lpj_kasbon_id = False
        if self.account_debit_kasbon_id:
            account_credit_lpj_kasbon_id = self.account_debit_kasbon_id.id
        self.account_credit_lpj_kasbon_id = account_credit_lpj_kasbon_id



class KasbonOperasional(models.Model):
    _name = 'kasbon.operasional'
    _description = 'Kasbon Operasional'

    def default_diterima(self):
        diterima = False
        if self.env.user.employee_id:
            diterima = self.env.user.employee_id.id
        return diterima
    
    def default_journal(self):
        journal = False
        journal_id = self.env['account.journal'].search([('is_kasbon', '=', True)], limit =1)
        if journal_id:
            journal = journal_id.id
        return journal
    
    def default_account_credit(self):
        account_credit_kasbon_id = False
        journal_id = self.env['account.journal'].search([('is_kasbon', '=', True)], limit =1)
        if journal_id:
            account_credit_kasbon_id = journal_id.account_credit_kasbon_id.id
        return account_credit_kasbon_id
    
    account_credit_kasbon_id = fields.Many2one('account.account', string='Akun Kas/Bank', ondelete='restrict', default=default_account_credit)
    date = fields.Date('Tanggal', default=fields.Date.today())
    name = fields.Char('Nomor', default="/", copy=False)
    bisnis_unit_id = fields.Many2one('res.company', string='Bisnis Unit', default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Departemen')
    analytic_id = fields.Many2one('account.analytic.account', string='Proyek')
    analytic_distribution = fields.Json(string='Proyek')
    analytic_precision = fields.Integer(string='Analytic Precision', store=False, default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"))
    kasbon_operasional_ids = fields.One2many('kasbon.operasional.line', 'kasbon_id', string='Kasbon Operasional Line')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submission', 'Submission'),
        ('approved_1', 'Approved 1'),
        ('approved_2', 'Approved 2'),
        ('done', 'Done'),
        ('not_approved', 'Not Approved'),
    ], string='state', default="draft")
    analytic_distribution_convert_to_char = fields.Char('Analytic Distribution Convert to Char', compute='_compute_convert_chart')
    
    company_id = fields.Many2one('res.company', string='Bisnis Unit', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Curenncy', compute='_compute_currency_id', store=True)
    journal_id = fields.Many2one('account.journal', string='Journal', default=default_journal, domain=[('is_kasbon', '=', True)], ondelete='restrict')
    move_id = fields.Many2one('account.move', string='Joutnal Entries', ondelete='restrict')
    
    terbilang = fields.Char('Terbilang :', compute="amount_to_words", readonly=True)
    note = fields.Text('Note')
    total = fields.Float('Total :', compute="amount_to_words", readonly=True, store=True)

    diketahui_id = fields.Many2one('hr.employee', string='Diketahui oleh')
    disetujui_id = fields.Many2one('hr.employee', string='Disetujui oleh')
    diserahkan_id = fields.Many2one('hr.employee', string='Diserahkan oleh', default=default_diterima)
    diterima_id = fields.Many2one('hr.employee', string='Diterima oleh', default=default_diterima)

    @api.depends('analytic_distribution')
    def _compute_convert_chart(self):
        for record in self:
            analytic_distribution = ''
            if record.analytic_distribution:
                distibution_ids = []
                for distibution in list(record.analytic_distribution):
                    distibution_ids.append(int(distibution))
                
                anlytic = self.env['account.analytic.account'].browse(distibution_ids).mapped('name')
                if anlytic:
                    analytic_distribution = " / ".join(anlytic)
            record.analytic_distribution_convert_to_char = analytic_distribution


    @api.depends('journal_id.currency_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.journal_id.currency_id or rec.company_id.currency_id

    @api.depends('kasbon_operasional_ids', 'kasbon_operasional_ids.jumlah')
    def amount_to_words(self):
        for rec in self:
            total = sum([x.jumlah for x in rec.kasbon_operasional_ids])
            rec.terbilang = num2words(int(total), to='currency', lang='id')
            rec.total = total

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('kasbon.operasional')
        res = super(KasbonOperasional, self).create(vals_list)
        return res
    
    def set_to_submission(self):
        self.write({'state': 'submission'})

    def set_to_approved_1(self):
        self.write({'state': 'approved_1'})


    def set_to_approved_2(self):
        self.write({'state': 'approved_2'})

    def set_to_done(self):
        self.write({'state': 'done'})
        create_journal_entries = self.env['account.move'].create({
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'move_type': 'entry',
        })
        if create_journal_entries:
            res = [(0,0, {
                'account_id': self.journal_id.account_debit_kasbon_id.id,
                'currency_id': self.currency_id.id,
                'name': "Kasbon %s %s - %s - %s" % (self.currency_id.symbol, str(self.total), self.diterima_id.name, str(self.date)),
                'analytic_distribution': self.analytic_distribution,
                'debit': self.total,
                'credit': 0,
            }), (0,0, {
                'account_id': self.account_credit_kasbon_id.id,
                'currency_id': self.currency_id.id,
                'name': "Kasbon %s %s - %s - %s" % (self.currency_id.symbol, str(self.total), self.diterima_id.name, str(self.date)),
                'analytic_distribution': self.analytic_distribution,
                'debit': 0,
                'credit': self.total,
            })]
            create_journal_entries.write({'line_ids': res})
            self.move_id = create_journal_entries.id
            create_journal_entries.action_post()


    def set_to_not_approved(self):
        self.write({'state': 'not_approved'})



class KasbonOperasionalLine(models.Model):
    _name = 'kasbon.operasional.line'
    _description = 'Kasbon Operasional Line'
    
    kasbon_id = fields.Many2one('kasbon.operasional', string='kasbon', ondelete='cascade')
    name = fields.Char('Uraian')
    jumlah = fields.Float('Jumlah')
    


class LpjKasbonOperasional(models.Model):
    _name = 'lpj.kasbon.operasional'
    _description = 'Lpj Kasbon Operasional'

    def default_diterima(self):
        diterima = False
        if self.env.user.employee_id:
            diterima = self.env.user.employee_id.id
        return diterima
    
    def default_journal(self):
        journal = False
        journal_id = self.env['account.journal'].search([('is_lpj_kasbon', '=', True)], limit =1)
        if journal_id:
            journal = journal_id.id
        return journal
    
    name = fields.Char('Name', default="Draft", copy=False)
    date = fields.Date('Tanggal', default=fields.Date.today())
    kasbon_id = fields.Many2one('kasbon.operasional', string='No. Kasbon', domain=[('state', '=', 'done')], ondelete='restrict')
    bisnis_unit_id = fields.Many2one('res.company', string='Bisnis Unit', default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Departemen')
    analytic_id = fields.Many2one('account.analytic.account', string='Proyek')
    analytic_distribution = fields.Json(string='Proyek')
    analytic_precision = fields.Integer(string='Analytic Precision', store=False, default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"))
    lpj_line_ids = fields.One2many('lpj.kasbon.operasional.line', 'lpj_id', string='LPJ Line')
    move_ids = fields.One2many('account.move', 'lpj_kasbon_operasional_id', string='Move Line')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submission', 'Submission'),
        ('approved_1', 'Approved 1'),
        ('approved_2', 'Approved 2'),
        ('done', 'Done'),
        ('not_approved', 'Not Approved'),
    ], string='state', default="draft")
    analytic_distribution_convert_to_char = fields.Char('Analytic Distribution Convert to Char', compute='_compute_convert_chart')

    note = fields.Text('Note')
    jumlah_kasbon = fields.Float('Jumlah Kasbon', related='kasbon_id.total')
    total_pertanggungjawaban = fields.Float('Total Pertanggungjawaban', readonly=True, store=True, compute="amount_to_words")
    lebih_kurang_bayar = fields.Float('Lebih/(Kurang) Bayar', readonly=True, store=True, compute="amount_to_words")

    company_id = fields.Many2one('res.company', string='Bisnis Unit', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Curenncy', compute='_compute_currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal', default=default_journal, domain=[('is_lpj_kasbon', '=', True)], ondelete='restrict')
    move_id = fields.Many2one('account.move', string='Joutnal Entries', ondelete='restrict')

    diserahkan_id = fields.Many2one('hr.employee', string='Diserahkan oleh', default=default_diterima)
    diperiksa_id = fields.Many2one('hr.employee', string='Diperikasa oleh')
    disetujui_id = fields.Many2one('hr.employee', string='Disetujui oleh')
    dibukukan_id = fields.Many2one('hr.employee', string='Dibukukan oleh')

    @api.depends('analytic_distribution')
    def _compute_convert_chart(self):
        for record in self:
            analytic_distribution = ''
            if record.analytic_distribution:
                distibution_ids = []
                for distibution in list(record.analytic_distribution):
                    distibution_ids.append(int(distibution))
                
                anlytic = self.env['account.analytic.account'].browse(distibution_ids).mapped('name')
                if anlytic:
                    analytic_distribution = " / ".join(anlytic)
            record.analytic_distribution_convert_to_char = analytic_distribution
    
    @api.depends('journal_id.currency_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.journal_id.currency_id.id or rec.company_id.currency_id.id

    @api.onchange('kasbon_id')
    def _onchange_kasbon_id(self):
        if self.kasbon_id:
            bisnis_unit_id = False
            department_id = False
            analytic_id = False
            analytic_distribution = False
            analytic_precision = False
            if self.kasbon_id.bisnis_unit_id:
                bisnis_unit_id = self.kasbon_id.bisnis_unit_id.id
            if self.kasbon_id.department_id:
                department_id = self.kasbon_id.department_id.id
            if self.kasbon_id.analytic_id:
                department_id = self.kasbon_id.analytic_id.id
            if self.kasbon_id.analytic_distribution:
                analytic_distribution = self.kasbon_id.analytic_distribution
            if self.kasbon_id.analytic_precision:
                analytic_precision = self.kasbon_id.analytic_precision
            self.bisnis_unit_id = bisnis_unit_id
            self.department_id = department_id
            self.analytic_id = analytic_id
            self.analytic_distribution = analytic_distribution
            self.analytic_precision = analytic_precision

    @api.depends('lpj_line_ids', 'lpj_line_ids.jumlah')
    def amount_to_words(self):
        for rec in self:
            total = sum([x.jumlah for x in rec.lpj_line_ids])
            rec.total_pertanggungjawaban = total
            rec.lebih_kurang_bayar = rec.jumlah_kasbon - total

    def set_to_submission(self):
        self.write({'state': 'submission'})
        self.name = self.env['ir.sequence'].next_by_code('lpj.kasbon.operasional')

    def set_to_approved_1(self):
        self.write({'state': 'approved_1'})


    def set_to_approved_2(self):
        self.write({'state': 'approved_2'})

    def set_to_done(self):
        self.write({'state': 'done'})
        create_journal_entries = self.env['account.move'].create({
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'move_type': 'entry',
        })
        if create_journal_entries:
            lines = []
            for rec in self.lpj_line_ids:
                lines.append((0, 0, {
                    'account_id': rec.account_id.id,
                    'currency_id': rec.currency_id.id,
                    'name': "LPJ Kasbon %s %s %s - %s - %s" % (rec.ket, rec.currency_id.symbol, str(rec.jumlah), rec.diserahkan_id.name, str(rec.date)),
                    'analytic_distribution': self.analytic_distribution,
                    'debit': rec.jumlah,
                    'credit': 0,
                }))
            lines.append((0, 0, {
                'account_id': self.journal_id.account_credit_lpj_kasbon_id.id,
                'currency_id': self.currency_id.id,
                'name': "LPJ Kasbon Operasional %s %s - %s - %s" % (self.currency_id.symbol, str(self.total_pertanggungjawaban), self.diserahkan_id.name, str(self.date)),
                'analytic_distribution': self.analytic_distribution,
                'debit': 0,
                'credit': self.total_pertanggungjawaban,
            }))
            print("=========", lines)
            create_journal_entries.write({'line_ids': lines})
            self.move_id = create_journal_entries.id
            create_journal_entries.action_post()


    def set_to_not_approved(self):
        self.write({'state': 'not_approved'})



class LpjKasbonOperasionalLine(models.Model):
    _name = 'lpj.kasbon.operasional.line'
    _description = 'Lpj Kasbon Operasional Line'
    
    lpj_id = fields.Many2one('lpj.kasbon.operasional', string='LPJ', ondelete='cascade')
    no_sequence = fields.Integer('No.', compute="_sequence_ref", readonly=True)
    date = fields.Date('Tanggal', default=fields.Date.today())
    ket = fields.Char('Keterangan')
    account_id = fields.Many2one('account.account', string='Akun', ondelete='restrict')
    jumlah = fields.Float('Jumlah')
    currency_id = fields.Many2one('res.currency', string='Curenncy', compute='_compute_currency_id', store=True)
    diserahkan_id = fields.Many2one('hr.employee', string='Diserahkan oleh', compute='_compute_currency_id')

    @api.depends('lpj_id.currency_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.lpj_id.currency_id or rec.lpj_id.company_id.currency_id
            diserahkan_id = False
            if rec.lpj_id.diserahkan_id:
                diserahkan_id = rec.lpj_id.diserahkan_id
            rec.diserahkan_id = diserahkan_id


    @api.depends('lpj_id.lpj_line_ids', 'lpj_id.lpj_line_ids.date')
    def _sequence_ref(self):
        for line in self:
            no = 0
            for l in line.lpj_id.lpj_line_ids:
                no += 1
                l.no_sequence = no
    
class SequenceMixin(models.AbstractModel):
    _inherit = 'sequence.mixin'
    # _description = "Automatic sequence"

    def _sequence_matches_date(self):
        self.ensure_one()
        date = fields.Date.to_date(self[self._sequence_date_field])
        sequence = self[self._sequence_field]

        if not sequence or not date:
            return True

        format_values = self._get_sequence_format_param(sequence)[1]
        year_match = (
            not format_values["year"]
            or format_values["year"] == date.year % 10 ** len(str(format_values["year"]))
        )
        month_match = not format_values['month'] or format_values['month'] == date.month
        return True and month_match
        # return True and True

class AccountMoveReversalInherit(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'
    
    def reverse_moves(self):
        self.ensure_one()
        moves = self.move_ids

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = default_vals.get('auto_post') != 'no'
            is_cancel_needed = not is_auto_post and self.refund_method in ('cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            if moves.analytic_distribution and moves.move_type == 'entry' and moves.name:
                number = int(moves.name[:3]) + 1
                default_values_list[0]['name'] = f'{number:03}' + moves.name[3:]
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)

            if self.refund_method == 'modify':
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({'date': self.date if self.date_mode == 'custom' else move.date})[0])
                new_moves = self.env['account.move'].create(moves_vals_list)

            moves_to_redirect |= new_moves

        self.new_move_ids = moves_to_redirect

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
                'context': {'default_move_type':  moves_to_redirect.move_type},
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
            if len(set(moves_to_redirect.mapped('move_type'))) == 1:
                action['context'] = {'default_move_type':  moves_to_redirect.mapped('move_type').pop()}
        return action

