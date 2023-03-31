from flask_wtf import FlaskForm, Form
from flask_login import current_user
from wtforms.validators import ValidationError, DataRequired, Optional
from wtforms.fields import FormField, FieldList, StringField,  DateField, SubmitField, DecimalField, SelectField
from wtforms_sqlalchemy.fields import QuerySelectField
from root.models import Client, UserForCompany, Item, Order, Warehouse,DeliveryNote
from datetime import datetime


class EntryField(Form):
    item = QuerySelectField('Désignation ', query_factory=lambda : Item.query \
                                .filter_by(is_disabled=False) \
                             .filter_by(fk_company_id=UserForCompany.query.filter_by(role="vendeur") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                             allow_blank=True, blank_text="Sélectionner le produit...",
                             render_kw={'data-placeholder':'Article ...'}, validators=[DataRequired('Champs obligatoire')])

    unit_price = DecimalField('Prix unitaire', validators=[DataRequired('Champs obligatoire')])
    unit = StringField('', render_kw={'disabled':True}, default="")
    quantity = DecimalField('Quantité',default=1, validators=[DataRequired('Champs obligatoire')])
    amount = DecimalField('Montant', default=0, render_kw={'readonly':True})
    delete_entry = SubmitField('Supprimer')

    def validate_quantity(self, quantity):
        if float(quantity.data)<=0:
            raise ValidationError('Valeur de qunatité invalide')

    def validate_unit_price(self, unit_price):
        if float(unit_price.data) <= 0:
            raise ValidationError('Valeur de prix invalide')


class QuotationForm(FlaskForm):
    client = QuerySelectField('Client: ', query_factory=lambda : Client.query \
                                .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id = UserForCompany.query.filter_by(role="vendeur") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                                allow_blank =True, blank_text='Sélectionner Un client...',
                              validators=[DataRequired('Champ obligatoire')])
    quotation_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()], render_kw={'readonly':True} )
    entities = FieldList(FormField(EntryField), min_entries=1)
    # add = SubmitField('+', render_kw={'class':''})
    add = SubmitField('Ajouter produit')
    fin=SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')
    def validate_quotation_date(self, quotation_date):
        if quotation_date.data < datetime.utcnow().date():
            raise ValidationError('Date invalide!')


class OrderForm(FlaskForm):
    client = QuerySelectField('Client: ', query_factory=lambda : Client.query \
                                .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id = UserForCompany.query.filter_by(role="vendeur") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                                allow_blank =True, blank_text='Sélectionner Un client...',
                              validators=[DataRequired('Champ obligatoire')])
    quotation_date = DateField('Date: ', default=datetime.utcnow().date(), render_kw={'readonly':True},
                               validators=[Optional()] )
    entities = FieldList(FormField(EntryField), min_entries=1)
    # add = SubmitField('+', render_kw={'class':''})
    add = SubmitField('Ajouter produit')
    fin=SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')
    def validate_quotation_date(self, quotation_date):
        if quotation_date.data < datetime.utcnow().date():
            raise ValidationError('Date invalide!')



class ExitVoucherEntryField(Form):
    item = QuerySelectField('Désignation ', query_factory=lambda: Item.query \
                            .filter_by(is_disabled=False) \
                            .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                                       .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                            allow_blank=True, blank_text="Sélectionner le produit...",
                            render_kw={'data-placeholder': 'Article ...'},
                            validators=[DataRequired('Champs obligatoire')])

    quantity = DecimalField('Quantité',default=1, validators=[DataRequired('Champs obligatoire')])
    delete_entry = SubmitField('Supprimer')


class ExitVoucherForm(FlaskForm):
    motif = QuerySelectField('Motif ',
                             query_factory=lambda :Order.query.filter(Order.category=='vente').filter(
                                    Order.fk_company_id == UserForCompany.query.filter_by(role="magasiner") \
                                                                                .filter_by(fk_user_id=current_user.id) \
                                                                                    .first().fk_company_id).all()+
                             DeliveryNote.query.join(Order, Order.id == DeliveryNote.fk_order_id) \
                                                .filter(Order.category=='vente').filter(
                                 Order.fk_company_id == UserForCompany.query.filter_by(role="magasiner") \
                                 .filter_by(fk_user_id=current_user.id) \
                                 .first().fk_company_id
                             ).all(),
                             validators=[DataRequired('Champs obligatoire')])
    warehouse=QuerySelectField('Dépôt', query_factory=lambda : Warehouse.query.join(UserForCompany,
                                                                    UserForCompany.fk_warehouse_id == Warehouse.id) \
                                                                .filter(UserForCompany.role=="magasiner") \
                                                                .filter(UserForCompany.fk_user_id == current_user.id).all(),
                               validators=[DataRequired('Champs obligatoire')]
                               )
    exit_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(EntryField), min_entries=1)
    add = SubmitField('Ajouter produit')
    # fin = SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')

    def validate_exit_date(self, exit_date):
        if exit_date.data < datetime.utcnow().date():
            raise ValidationError('Date invalide!')


class PaiementForm(FlaskForm):
    # expense_category = QuerySelectField('Dépenses',
    #                     validators=[DataRequired('Champs obligatoire')],
    #                     query_factory=lambda : ExpenseCategory.query.filter_by(fk_company_id=UserForCompany \
    #                                                .query.filter_by(role="magasiner") \
    #                                                 .filter_by(fk_user_id=current_user.id) \
    #                                                    .first().fk_company_id).all(),
    #                     render_kw={'data-placeholder':'La catégorie de dépense pour le réglement de cette facture'}
    #                     )
    amount = StringField('Montant', validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Payer')

class ClientForm(FlaskForm):
    full_name = StringField('Nom complet: ',
                            validators=[DataRequired('Champs obligatoire')],
                            render_kw={'placeholder': 'Nom complet du client'})
    category = SelectField('Catégorie', validators=[DataRequired('Champs obligatoire')],
                           choices=[('', ''), ('Particulier', 'Particulier'),
                                    ('Professionel', 'Professionel')],
                           render_kw={'data-placeholder': 'La catégorie du client'})
    contacts = StringField('Contact(Téléphone)',
                           validators=[DataRequired('Champs obligatoire')],
                           render_kw={'placeholder': 'Contact(Téléphone)'})
    submit = SubmitField('Ajouter')