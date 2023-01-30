from flask_wtf import FlaskForm, Form
from wtforms.fields import StringField, SubmitField, RadioField, PasswordField, SelectField
from wtforms.validators import DataRequired, ValidationError, EqualTo
from root.models import UserForCompany, Company, User
from flask_login import current_user
from sqlalchemy.sql import and_
from sqlalchemy import func
from root import name_regex, phone_number_regex

class NewItemForm(FlaskForm):
    pass


class EntryForm(Form):
    pass


class OrderForm(FlaskForm):
    pass


class InvoiceForm(FlaskForm):
    pass


class QuotationForm(FlaskForm):
    pass


class TaxesForm(FlaskForm):
    name = StringField('Nom: ',
                        validators=[DataRequired('Ce champs est obligatoire')])

    label = StringField('Abréviation: ',
                        validators=[DataRequired('Ce champs est obligatoire')])

    value = StringField('Valeur: ',
                        validators=[DataRequired('Ce champs est obligatoire')])

    is_fixed = RadioField('', choices=[(True, "Valeur Fixée"), (False, "Pourcentage")],
                          validators=[DataRequired('Champs obligatoire')])

    sign = RadioField("Mode d'application: ", choices=[('+', 'َAdditionner'), ('-', 'Soustraire')],
                      validators=[DataRequired('Champs obligatoire')])

    # sell_or_buy = RadioField('Type: ', choices=[('sell','Pour les ventes'), ('buy','Pour les Achats')],
    #                          validators=[DataRequired('Champs obligatoire')])

    applied_before_TVA = RadioField('', choices=[(True, 'Appliqué avant la TVA'),(False, 'Appliqué après la TVA')],
                                    validators=[DataRequired('Champs obligatoire')])

    on_applied_products = RadioField('Appliquer Sur le produits:', choices=[(True, 'Oui'), (False,'Non')],
                                     validators=[DataRequired('Champs obligatoire')])

    # on_applied_TVA = RadioField('Appliquer sur la TVA',
    #                             choices=[(True,'Oui'), (False,'Non')])
    submit = SubmitField('Ajouter')

    def validate_label(self, label):
        companies = Company.query.join(UserForCompany, UserForCompany.fk_company_id == Company.id) \
            .filter(and_(UserForCompany.role == "manager", UserForCompany.fk_user_id == current_user.id)).all()
        if companies:
            for company in companies:
                if str.lower(label.data) in [str.lower(x.label) for x in company.taxes]:
                    raise ValidationError('Tax déja existe')

    def validate_value(self, value):
        if float(value.data)<=0:
            raise ValidationError('Valeur invalide.')


class EditTaxForm(TaxesForm):
    submit = SubmitField('Executer')
    def validate_label(self, label):
        pass


class WarehouseForm(FlaskForm):
    name = StringField('Nom:', validators=[DataRequired('Champs obligatoire')])
    address = StringField('Adresse: ', validators=[DataRequired('Champs obligatoire')])
    contact = StringField('Contact (Téléphone): ', validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Ajouter')


class EditWarehouseForm(FlaskForm):
    name = StringField('Nom:', validators=[DataRequired('Champs obligatoire')])
    address = StringField('Adresse: ', validators=[DataRequired('Champs obligatoire')])
    contact = StringField('Contact (Téléphone): ', validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Executer')


class EmployeeForm(FlaskForm):
    full_name = StringField('Nom complet: ', validators=[DataRequired('Champs obligatoire')])
    username = StringField('Nom d\'utilisateur:', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired('Champs obligatoire')])
    confirm_password = PasswordField('Confirmer le mot de passe: ', validators=[DataRequired('Champs obligatoire'), EqualTo(password)])
    role = SelectField('Rôle: ', choices=[(1, 'Vendeur'), (2, 'Magasiner')])
    location = SelectField('Lieu: ', coerce=int, validate_choice=False, validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Ajouter')
    def validate_full_name(self, full_name):
        if name_regex.search(full_name.data) is None:
            raise ValidationError('Nom invalide')

        user = User.query.filter(func.lower(full_name)==func.lower(full_name.data)).first()
        if user:
            raise ValidationError('Employer déjà existe')

class StockForm(FlaskForm):
    pass
