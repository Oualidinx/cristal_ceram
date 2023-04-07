from flask_wtf import FlaskForm, Form
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.fields import SubmitField, FieldList, FormField, DateField, DecimalField, StringField
from datetime import datetime
from wtforms.validators import ValidationError, Optional, DataRequired
from root.models import Client, UserForCompany, Item, Supplier, Order, ExpenseCategory, Warehouse, DeliveryNote
from flask_login import current_user


class EntryField(Form):
    item = QuerySelectField('Désignation ', query_factory=lambda : Item.query \
                                .filter_by(is_disabled=False) \
                             .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                             allow_blank=True, blank_text="Sélectionner le produit...",
                             render_kw={'data-placeholder':'Article ...'}, validators=[DataRequired('Champs obligatoire')])

    unit_price = DecimalField('Prix unitaire', validators=[DataRequired('Champs obligatoire')])
    # purchase_price = DecimalField('Prix unitaire', validators=[DataRequired('Champs obligatoire')])
    unit = StringField('', render_kw={'readonly':True}, default="")
    quantity = DecimalField('Quantité',default=1, validators=[DataRequired('Champs obligatoire')])
    amount = DecimalField('Montant', default=0, render_kw={'readonly':True})
    # delete_entry = SubmitField('-', render_kw={'class':'btn btn-sm btn-outline-danger fa-solid fa-trash-can'})
    delete_entry = SubmitField('Supprimer')

    def validate_quantity(self, quantity):
        if float(quantity.data) < 0:
            raise ValidationError('Valeur invalide')

    def validate_unit_price(self, unit_price):
        if float(unit_price.data) < 0:
            raise ValidationError('Valeur invalide')

class PurchaseField(EntryField):
    unit_price = DecimalField('Prix unitaire', render_kw={'readonly':True})

class PurchaseOrderForm(FlaskForm):
    fournisseur = QuerySelectField('Fournisseur ', query_factory=lambda: Supplier.query \
                              .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                              allow_blank=True, blank_text='Sélectionner un bénéficiaire ...',
                              validators=[Optional()])

    order_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(PurchaseField), min_entries=1)
    add = SubmitField('Ajouter produit')
    fin = SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')



class ExitVoucherEntryField(Form):
    item = QuerySelectField('Désignation ', query_factory=lambda: Item.query \
                            .filter_by(is_disabled=False) \
                            .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                                       .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                            allow_blank=True, blank_text="Sélectionner le produit...",
                            render_kw={'data-placeholder': 'Article ...'},
                            validators=[DataRequired('Champs obligatoire')])

    quantity = DecimalField('Quantité',default=1, validators=[DataRequired('Champs obligatoire')])
    available_stock = StringField('', render_kw={'readonly': True})
    delete_entry = SubmitField('Supprimer')

    def validate_quuantity(self, quantity):
        if float(quantity.data) < 0:
            raise ValidationError('Valeur invalide')

from sqlalchemy.sql import and_

class ExitVoucherForm(FlaskForm):
    motif = QuerySelectField('Motif ',
                 allow_blank=True,
                 blank_text="Sélectionner le motif ...",
                 query_factory=lambda :Order.query.filter(and_(Order.is_deleted==False,Order.category=='vente')) \
                     .filter(Order.is_canceled == None) \
                     .filter( Order.fk_company_id == UserForCompany.query.filter_by(role="magasiner") \
                            .filter_by(fk_user_id=current_user.id) \
                                .first().fk_company_id).all()+
                     DeliveryNote.query.join(Order, Order.id == DeliveryNote.fk_order_id) \
                                        .filter(Order.category=='vente').filter(
                         Order.fk_company_id == UserForCompany.query.filter_by(role="magasiner") \
                         .filter_by(fk_user_id=current_user.id) \
                         .first().fk_company_id
                     ).all(),
                 validators=[DataRequired('Champs obligatoire')])
    warehouse=QuerySelectField('Dépôt',
                    allow_blank=True,
                   blank_text="Sélectionner le dépôt ...",
                   query_factory=lambda : Warehouse.query.join(UserForCompany,
                                                        UserForCompany.fk_warehouse_id == Warehouse.id) \
                                                    .filter(UserForCompany.role=="magasiner") \
                                                    .filter(UserForCompany.fk_user_id == current_user.id).all(),
                   validators=[DataRequired('Champs obligatoire')]
                   )
    exit_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(ExitVoucherEntryField), min_entries=1)

    add = SubmitField('Ajouter produit')
    # fin = SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')

    def validate_exit_date(self, exit_date):
        if exit_date.data < datetime.utcnow().date():
            raise ValidationError('Date invalide!')

from sqlalchemy.sql import or_
class PurchaseReceiptForm(FlaskForm):
    recipient = QuerySelectField('Bénéficiaire: ',query_factory=lambda :Client.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="magasiner").first().fk_company_id).all()+
                                        Supplier.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="magasiner").first().fk_company_id).all(),
                            validators=[Optional()])
    command_reference = QuerySelectField('Code commande:',allow_blank=True,
                                 query_factory=lambda : Order.query.filter_by(category="achat") \
                                         .filter(Order.is_deleted == False) \
                                         .filter(Order.is_canceled == None) \
                                         .filter(Order.is_delivered==None) \
                                         .filter_by(fk_company_id =UserForCompany.query \
                                                   .filter_by(role="magasiner").first().fk_company_id)\
                                                    .all(),
                                validators=[DataRequired('Champs obligatoire')])
    order_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(PurchaseField), min_entries=1)
    add = SubmitField('Ajouter produit')
    fin = SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')

class InvoiceEntryField(EntryField):
    item = QuerySelectField('Désignation ', query_factory=lambda: Item.query \
                            .filter_by(is_disabled=False) \
                            .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                                       .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                            allow_blank=True, blank_text="Sélectionner le produit...",
                            render_kw={'data-placeholder': 'Article ...', 'readonly': True},
                            )

    unit_price = DecimalField('Prix unitaire', render_kw={'readonly': True})
    # purchase_price = DecimalField('Prix unitaire', validators=[DataRequired('Champs obligatoire')])
    unit = StringField('', render_kw={'readonly': True}, default="")
    quantity = DecimalField('Quantité', default=1, render_kw={'readonly': True})
    amount = DecimalField('Montant', default=0, render_kw={'readonly': True})
    # delete_entry = SubmitField('-', render_kw={'class':'btn btn-sm btn-outline-danger fa-solid fa-trash-can'})
    delete_entry = SubmitField('Supprimer')


class InvoiceForm(FlaskForm):
    recipient = QuerySelectField('Bénéficiaire ',allow_blank=True,
                                 query_factory=lambda :Client.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="magasiner").first().fk_company_id).all()+
                                        Supplier.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="magasiner").first().fk_company_id).all(),
                            validators=[Optional()])

    reference_supplier_invoice = StringField('Référence ',validators=[Optional()])
    order_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(InvoiceEntryField))
    submit = SubmitField('Sauvegarder')


class PaiementForm(FlaskForm):
    expense_category = QuerySelectField('Dépenses',
                        validators=[DataRequired('Champs obligatoire')],
                        query_factory=lambda : ExpenseCategory.query.filter_by(fk_company_id=UserForCompany \
                                                   .query.filter_by(role="magasiner") \
                                                    .filter_by(fk_user_id=current_user.id) \
                                                       .first().fk_company_id).all(),
                        render_kw={'data-placeholder':'La catégorie de dépense pour le réglement de cette facture'}
                        )
    amount = StringField('Montant', validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Payer')