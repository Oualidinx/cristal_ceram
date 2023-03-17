from flask_wtf import FlaskForm, Form
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.fields import SubmitField, FieldList, FormField, DateField, DecimalField, StringField
from datetime import datetime
from wtforms.validators import ValidationError, Optional, DataRequired
from root.models import Client, UserForCompany, Item, Supplier, Order, ExpenseCategory
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


class ExitVoucherForm(FlaskForm):
    client = QuerySelectField('Client: ', query_factory=lambda: Client.query \
                              .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                              allow_blank=True, blank_text='Sélectionner Un client...',
                              validators=[Optional()])
    exit_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(EntryField), min_entries=1)
    # add = SubmitField('+', render_kw={'class':''})
    add = SubmitField('Ajouter produit')
    fin = SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')

    def validate_exit_date(self, exit_date):
        if exit_date.data < datetime.utcnow().date():
            raise ValidationError('Date invalide!')


class PurchaseOrderForm(FlaskForm):
    fournisseur = QuerySelectField('Fournisseur ', query_factory=lambda: Supplier.query \
                              .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                              allow_blank=True, blank_text='Sélectionner un bénéficiaire ...',
                              validators=[Optional()])

    order_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(EntryField), min_entries=1)
    add = SubmitField('Ajouter produit')
    fin = SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')


class PurchaseReceiptForm(FlaskForm):
    recipient = QuerySelectField('Bénéficiaire: ',query_factory=lambda :Client.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="magasiner").first().fk_company_id).all()+
                                        Supplier.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="magasiner").first().fk_company_id).all(),
                            validators=[Optional()])
    command_reference = QuerySelectField('Code commande:',allow_blank=True,
                                         query_factory=lambda : Order.query \
                                                        .filter_by(fk_company_id =UserForCompany.query \
                                                                   .filter_by(role="magasiner").first().fk_company_id)\
                                                                    .all(),
                                    validators=[DataRequired('Champs obligatoire')])
    order_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(EntryField), min_entries=1)
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