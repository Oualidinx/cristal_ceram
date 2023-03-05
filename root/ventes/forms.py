from flask_wtf import FlaskForm, Form
from flask_login import current_user
from wtforms.validators import ValidationError, DataRequired, Optional, EqualTo
from wtforms.fields import FormField, FieldList, StringField, FloatField, DateField, SubmitField, DecimalField
from wtforms_sqlalchemy.fields import QuerySelectField
from root.models import Client, UserForCompany, Item
from datetime import datetime
class EntryField(Form):
    item = QuerySelectField('Désignation ', query_factory=lambda : Item.query \
                                .filter_by(is_disabled=False) \
                             .filter_by(fk_company_id=UserForCompany.query.filter_by(role="vendeur") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                             allow_blank=True, blank_text="Sélectionner le produit...",
                             render_kw={'data-placeholder':'Article ...'}, validators=[DataRequired('Champs obligatoire')])

    unit_price = DecimalField('Prix unitaire', validators=[DataRequired('Champs obligatoire')])
    unit = StringField('', render_kw={'readonly':True}, default="")
    quantity = DecimalField('Quantité',default=1, validators=[DataRequired('Champs obligatoire')])
    amount = DecimalField('Montant', default=0, render_kw={'readonly':True})
    # delete_entry = SubmitField('-', render_kw={'class':'btn btn-sm btn-outline-danger fa-solid fa-trash-can'})
    delete_entry = SubmitField('Supprimer')


class QuotationForm(FlaskForm):
    client = QuerySelectField('Client: ', query_factory=lambda : Client.query \
                                .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id = UserForCompany.query.filter_by(role="vendeur") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                                allow_blank =True, blank_text='Sélectionner Un client...',
                              validators=[DataRequired('Champ obligatoire')])
    quotation_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()] )
    entities = FieldList(FormField(EntryField), min_entries=1)
    # add = SubmitField('+', render_kw={'class':''})
    add = SubmitField('Ajouter produit')
    fin=SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')
    def validate_quotation_date(self, quotation_date):
        if quotation_date.data < datetime.utcnow().date():
            raise ValidationError('Date invalide!')


class ExitVoucherForm(FlaskForm):
    client = QuerySelectField('Client: ', query_factory=lambda: Client.query \
                              .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id=UserForCompany.query.filter_by(role="vendeur") \
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


class OrderForm(FlaskForm):
    client = QuerySelectField('Client: ', query_factory=lambda : Client.query \
                                .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id = UserForCompany.query.filter_by(role="vendeur") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                                allow_blank =True, blank_text='Sélectionner Un client...',
                              validators=[DataRequired('Champ obligatoire')])
    quotation_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()] )
    entities = FieldList(FormField(EntryField), min_entries=1)
    # add = SubmitField('+', render_kw={'class':''})
    add = SubmitField('Ajouter produit')
    fin=SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')
    def validate_quotation_date(self, quotation_date):
        if quotation_date.data < datetime.utcnow().date():
            raise ValidationError('Date invalide!')