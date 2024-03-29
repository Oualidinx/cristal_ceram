from datetime import datetime

from flask_wtf import FlaskForm, Form
from wtforms.fields import StringField, SubmitField, RadioField, PasswordField, SelectField, DecimalField, DateField,FloatField
from wtforms.fields import FloatField, FieldList, FormField
from wtforms.validators import DataRequired, ValidationError, EqualTo, Optional
from root.models import UserForCompany, Company, User, Item, Warehouse, Store, Format, Aspect, ExpenseCategory
from root.models import Supplier, Client, Order, Contact
from flask_login import current_user
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
import sqlalchemy as sa
from root import name_regex, phone_number_regex

class NewItemForm(FlaskForm):
    label = StringField('Désignation du produit: ', validators=[DataRequired('Champs obligatoire')],
                        render_kw={'placeholder':'Désignation du produit'})
    serie = StringField('Série: ', validators=[DataRequired('Champs obligatoire')],
                        render_kw={'placeholder':'Série du produit'})
    format = QuerySelectField('Format ',blank_text="Séléctionner le format...",allow_blank =True, query_factory=lambda : Format.query.filter_by(
                                fk_company_id=UserForCompany.query.filter_by(role='manager').filter_by(fk_user_id=current_user.id)\
                                                                                            .first().fk_company_id).all(),
                              validators=[Optional()],
                              render_kw={'data-placeholder': 'Séléctionner le format...'})
    aspect = QuerySelectField('Aspect ', validators=[Optional()],
                              render_kw={'data-placeholder':'Séléctionner l\'aspect du produit...'},
                              allow_blank=True,blank_text="Séléctionner l'aspect...",
                              query_factory=lambda: Aspect.query.filter_by(
                                  fk_company_id=UserForCompany.query.filter_by(role='manager').filter_by(
                                      fk_user_id=current_user.id) \
                                      .first().fk_company_id).all())
    utilisation=SelectField('Utilisation ', choices=[('Carreaux-de-mur','Carreaux-de-mur'),
                                                        ('Carreaux-de-sol','Carreaux-de-sol'),
                                                        ('Carreaux-de-pierre','Carreaux-de-pierre'),
                                                        ('Carreaux-de-parquet','Carreaux-de-parquet'), ('Autres','Autres')],
                            render_kw={'data-placeholder':'Produit utilisé Pour...'},
                            validators=[DataRequired('Champs obligatoire')])
    intern_reference = StringField('Référence interne:',
                                   render_kw={'placeholder':"La référence interne du produit..."})
    manufacturer=StringField('Produit Par:',
                             render_kw={'placeholder':'Usine de production'}, validators=[Optional()])
    unit = StringField('Unité', render_kw={'placeholder':'Unité de stock de produit'},
                       validators=[Optional()])
    sale_price = StringField('Prix de vente',validators=[Optional()])
    piece_per_unit=FloatField('Pièce par unité: ',
                               render_kw={'placeholder':'Pièce ou poids par unité'}, default='1')
    expired_at = DateField('Date d\'expiration:', validators=[Optional()],
                               render_kw={'placeholder':'La date d\'expiration'})
    stock_sec = FloatField('Stock de sécurité',validators=[DataRequired('Champs obligatoire')], render_kw={'placeholder':'Le stock de sécurité...'})
    submit = SubmitField('Ajouter')
    def validate_stock_sec(self, stock_sec):
        if stock_sec.data <= 0:
            raise ValidationError('Valeur invalide !')
    def validate_label(self, label):
        c_id=UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id = current_user.id).first().fk_company_id
        item = Item.query.filter_by(fk_company_id = c_id) \
            .filter(sa.func.lower(label.data) == sa.func.lower(Item.label)).first()
        if item:
            raise ValidationError('Désignation déjà existe')

    def validate_intern_reference(self, intern_reference):
        c_id = UserForCompany.query.filter_by(role="manager").filter_by(
            fk_user_id=current_user.id).first().fk_company_id
        item = Item.query.filter_by(fk_company_id=c_id) \
            .filter(sa.func.lower(str(intern_reference.data)) == sa.func.lower(Item.intern_reference)).first()
        if item:
            raise ValidationError('Référence interne ne peut être répéter')

    def validate_expired_at(self, expired_at):
        if expired_at.data :
            if expired_at.data <= datetime.utcnow().date():
                raise ValidationError('Date d\'expiration non valide')

class EditItemForm(NewItemForm):
    submit = SubmitField('Executer')

    def validate_intern_reference(self, intern_reference):
        pass

    def validate_label(self, label):
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
            .filter(sa.and_(UserForCompany.role == "manager", UserForCompany.fk_user_id == current_user.id)).all()
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
    name = StringField('Nom:', validators=[DataRequired('Champs obligatoire')], render_kw={'placeholder':"Nome du dépôt"})
    address = StringField('Adresse: ', validators=[DataRequired('Champs obligatoire')], render_kw={'placeholder':"L'adresse du dépôt"})
    contact = StringField('Contact (Téléphone): ', validators=[DataRequired('Champs obligatoire')], render_kw={'placeholder':"Contact(Téléphone)"})
    submit = SubmitField('Valider')


class StoreForm(FlaskForm):
    name = StringField('Nom:', validators=[DataRequired('Champs obligatoire')],
                       render_kw={'placeholder':"Nom du magasin"})
    address = StringField('Adresse: ', validators=[DataRequired('Champs obligatoire')],
                          render_kw={'placeholder':"L'adresse du magasin"})
    contact = StringField('Contact (Téléphone): ', validators=[DataRequired('Champs obligatoire')],
                          render_kw={'placeholder':"Contact(téléphone)"})
    # seller = QuerySelectField('Vendeur', render_kw={'data-placeholder':"Séléctionner le vendeur ..."})
    submit = SubmitField('Ajouter')

    def validate_contact(self, contact):
        if phone_number_regex.search(contact.data) is None:
            raise ValidationError('Numéro de téléphone invalide')


class EditStoreForm(StoreForm):
    submit = SubmitField('Valider')


class EditWarehouseForm(FlaskForm):
    name = StringField('Nom:', validators=[DataRequired('Champs obligatoire')])
    address = StringField('Adresse: ', validators=[DataRequired('Champs obligatoire')])
    contact = StringField('Contact (Téléphone): ', validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Executer')


class EmployeeForm(FlaskForm):
    full_name = StringField('Nom complet: ', validators=[DataRequired('Champs obligatoire')],
                            render_kw={'placeholder':'Nom complet: '})
    username = StringField('Nom d\'utilisateur:', validators=[DataRequired()],
                           render_kw={'placeholder':'Nom d\'utilisateur:'})
    password = PasswordField('Mot de passe', validators=[EqualTo('confirm_password','mot de passe erroné'),DataRequired('Champs obligatoire')],
                             render_kw={'placeholder':'Mot de passe'})
    confirm_password = PasswordField('Confirmer le mot de passe: ', validators=[DataRequired('Champs obligatoire'), EqualTo('password','mot de passe erroné')],
                                     render_kw={'placeholder':'Confirmer le mot de passe: '})
    role = SelectField('Rôle: ', choices=[(0,'Sélectionner le rôle...'),(1, 'Vendeur'), (2, 'Magasiner')], validate_choice=False, coerce=int)
    location = SelectField('Lieu: ', validate_choice=False, coerce=int,choices=[(0,'Aucune location')])
    submit = SubmitField('Ajouter')

    def validate_full_name(self, full_name):
        if name_regex.search(full_name.data) is None:
            raise ValidationError('Nom invalide')

        user = User.query.filter(sa.func.lower(User.full_name)==sa.func.lower(full_name.data)).filter(User.is_disabled ==False).first()
        if user and not user.is_disabled:
            raise ValidationError('Employer déjà existe')

    def validate_username(self, username):
        user = User.query.filter(sa.func.lower(User.username)==sa.func.lower(username.data)).filter(User.is_disabled ==False).first()
        if user and not user.is_disabled:
            raise ValidationError('Employer déjà existe')


class StockForm(FlaskForm):
    item = QuerySelectField('Produit: ', validators=[DataRequired('Champs obligatoire')])
    warehouse = QuerySelectField("Dépôt: ", validators=[DataRequired('Champs Obligatoire')])
    stock_qte = StringField('Quantité: ')
    stock_sec = StringField('Quantité de Sécurité (Stock de sécurité): ', validators=[DataRequired('Champs obligatoire')])
    # stock_max = db.Column(db.Float, default=0)
    submit = SubmitField('Ajouter')

    def validate_stock_qte(self, stock_qte):
        if stock_qte.data and float(stock_qte.data) < 0:
            raise ValidationError('La quantité doit être supérieur à 0')

    def validate_stock_sec(self, stock_sec):
        if stock_sec.data and float(stock_sec.data) <= 0:
            raise ValidationError('La quantité doit être supérieur à 0')


class UpdateUserForm(FlaskForm):
    full_name = StringField('Nom complet: ', validators=[DataRequired('Champs obligatoire')])
    username = StringField('Nom d\'utilisateur:', validators=[DataRequired()])
    role = SelectField('Rôle: ', coerce=int, choices=[(0,''), (1, 'vendeur'), (2, 'magasiner')])
    # location = SelectField('Lieu: ', coerce=int, validate_choice=False,
    #                         render_kw={'data-placeholder':'Rôle..'},
    #                        validators=[DataRequired('Champs obligatoire')])
    warehouses = QuerySelectMultipleField('Les dépôts', allow_blank=True, blank_text="Pas encore affecté",
                                          query_factory=lambda : Warehouse.query.all(),
                                          render_kw={'data-placeholder': "Sélectionner un/des dépôt(s)"})
    stores = QuerySelectField('Le magasin', allow_blank=True, blank_text='Pas encore affecté',
                              query_factory=lambda : Store.query.filter_by(
                                                fk_company_id=UserForCompany.query.filter_by(role="manager") \
                                                    .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                                           render_kw={'data-placeholder': "Sélectionner un magasin"})


    submit = SubmitField('Executer')


class UpdatePasswordForm(FlaskForm):
    user_password = PasswordField('Mot de passe', validators=[DataRequired('Champs obligatoire')])
    new_password = PasswordField('Nouveau Mot de passe', validators=[DataRequired('Champs obligatoire')])
    confirm_password = PasswordField('Confirmer le Mot de passe', validators=[DataRequired('Champs obligatoire'), EqualTo(new_password, "Mots de passe doivent être identiques")])
    submit = SubmitField('Mise à jour')


class FormatForm(FlaskForm):
    label = StringField('Nom du Format:', validators=[DataRequired('Champs obligatoire')], render_kw={'data-placeholder':'Nom de format'})
    submit = SubmitField('Ajouter')


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


# class ExpenseForm(FlaskForm):
#     expense_category = QuerySelectField('Dépenses',
#                         validators=[DataRequired('Champs obligatoire')],
#                         query_factory=lambda : ExpenseCategory.query.filter_by(fk_company_id=UserForCompany \
#                                                    .query.filter_by(role="magasiner") \
#                                                     .filter_by(fk_user_id=current_user.id) \
#                                                        .first().fk_company_id).all(),
#                         render_kw={'data-placeholder':'La catégorie de dépense pour le réglement de cette facture'}
#                         )
#     amount = StringField('Montant', validators=[DataRequired('Champs obligatoire')])
#     submit = SubmitField('Payer')


class AspectForm(FlaskForm):
    label = StringField("Nom de l'aspect: ", validators=[DataRequired('Champs obligatoire')], render_kw={'data-placeholder':'Nom de l\'aspect'})
    submit = SubmitField('Valider')


class EditFormatForm(FlaskForm):
    label = StringField("Nom du Format: ", validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Executer')


class EditAspectForm(FlaskForm):
    label = StringField("Nom de l'aspect: ", validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Executer')


class AttachWareHouseForm(FlaskForm):
    warehouse = QuerySelectField("Dépôt: ", validators=[DataRequired('Champs Obligatoire')])
    stock_qte = StringField('Quantité: ')
    stock_sec = StringField('Quantité de Sécurité (Stock de sécurité): ',
                            validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Valider')


class ClientForm(FlaskForm):
    full_name=StringField('Nom complet: ',
                            validators=[DataRequired('Champs obligatoire')],
                          render_kw={'placeholder':'Nom complet du client'})
    category=SelectField('Catégorie', validators=[DataRequired('Champs obligatoire')],
                        choices=[('',''),('Particulier','Particulier'),
                                 ('Professionel', 'Professionel')],
                         render_kw={'data-placeholder':'La catégorie du client'})
    contacts=StringField('Contact(Téléphone)', validators=[DataRequired('Champs obligatoire')],
                         render_kw={'placeholder':'Contact(Téléphone)'})
    submit = SubmitField('Ajouter')
    def validate_full_name(self, full_name):
        client = Client.query.filter(sa.func.lower(Client.full_name) == sa.func.lower(full_name.data)).first()
        if client and not client.is_deleted:
            raise ValidationError('Client déjà existe')

    def validate_contacts(self, contacts):
        client = Contact.query.filter_by(value = contacts.data).first()
        if client:
            raise ValidationError('Contact existe déjà')
        
class EditClientForm(ClientForm):
    def validate_full_name(self, full_name):
        pass
    def validate_contacts(self, contacts):
        pass


class SupplierForm(FlaskForm):
    full_name=StringField('Nom complet: ',
                            validators=[DataRequired('Champs obligatoire')],
                          render_kw={'placeholder':'Nom complet du fournisseur'})
    category=SelectField('Catégorie', validators=[Optional()],
                        choices=[('',''),('Particulier','Particulier'),
                                 ('Professionel', 'Professionel')],
                         render_kw={'data-placeholder':'La catégorie du fournisseur'})
    contacts=StringField('Contact(Téléphone)', validators=[DataRequired('Champs obligatoire')],
                         render_kw={'placeholder':'Contact(Téléphone)'})
    submit = SubmitField('Ajouter')

    def validate_full_name(self, full_name):
        supplier = Supplier.query.filter(sa.func.lower(Supplier.full_name) == sa.func.lower(full_name.data)).first()
        if supplier and not supplier.is_deleted:
            raise ValidationError('Fournisseur déjà existe')

    def validate_contacts(self, contacts):
        supplier = Contact.query.filter_by(value=contacts.data).first()
        if supplier:
            raise ValidationError('Contact existe déjà')
        
class EditSupplierForm(SupplierForm):
    def validate_contacts(self, contacts):
        pass

    def validate_full_name(self, full_name):
        pass


class InventoryForm(FlaskForm):
    item = QuerySelectField('Produit', validators=[DataRequired('Champs Obligatoire')], query_factory=lambda : Item.query.filter_by(fk_company_id =
                                                                    UserForCompany.query.filter_by(role="manager") \
                                                                    .filter_by(fk_user_id=current_user.id) \
                                                                                   .first().fk_company_id).all(),
                            allow_blank=True,
                            blank_text='Sélectionner un produit...'
                            )
    warehouse = QuerySelectField('Dépôt', validators=[DataRequired('Champs obligatoire')],
                                 query_factory=lambda : Warehouse.query.filter_by(fk_company_id =
                                                                    UserForCompany.query.filter_by(role="manager") \
                                                                    .filter_by(fk_user_id=current_user.id) \
                                                                                   .first().fk_company_id).all(),
                                 allow_blank=True,
                                 blank_text='Sélectionner un dépôt...'
                                 )
    quantity = DecimalField('Quantité de stock', validators=[DataRequired('Champs obligatoire')])
    purchase_price = DecimalField('Prix d\'achat', validators=[DataRequired('Champs obligatoire')])
    sale_price = DecimalField('Prix de vente', validators=[DataRequired('Champs obligatoire')])
    purchase_date = DateField('Date d\'achat', validators = [DataRequired('Champs obligatoire')])
    submit = SubmitField('Sauvegarder')


class ExpenseForm(FlaskForm):
    label = StringField('Titre: ', validators=[DataRequired('Champs obligatoire')])
    description = StringField('Description: ', validators=[Optional('Champs optionel')])
    amount = DecimalField('Montant: ', validators=[DataRequired('Champs obligatoire')])
    expense_category=QuerySelectField('Catégorie de dépense: ',
                      query_factory= lambda : ExpenseCategory.query. \
                            filter_by(fk_company_id = UserForCompany.query
                                .filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
                                                        ).all(),
                      validators=[DataRequired('Champs obligatoire')],
                      allow_blank=True,
                      blank_text="Sélectionner la catégorie")
    submit = SubmitField('Valider')

    def validate_amount(self, amount):
        if float(amount.data)<=0:
            raise ValidationError('Valeur du montant est invalide')


class ExpenseCategoryForm(FlaskForm):
    label = StringField('Titre: ', validators=[DataRequired('Champs obligatoire')])
    submit = SubmitField('Valider')

class EntryField(Form):
    item = QuerySelectField('Désignation ', query_factory=lambda : Item.query \
                                .filter_by(is_disabled=False) \
                             .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
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
    unit_price = DecimalField('Prix d\'achat')
    sale_price = DecimalField('Prix de vente')
class PurchaseReceiptForm(FlaskForm):
    recipient = QuerySelectField('Bénéficiaire: ',query_factory=lambda :Client.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="manager").first().fk_company_id).all()+
                                        Supplier.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="manager").first().fk_company_id).all(),
                            validators=[Optional()])
    command_reference = QuerySelectField('Code commande:',query_factory=lambda : Order.query.filter_by(category="achat") \
                                         .filter(Order.is_deleted == False) \
                                         .filter(Order.is_canceled == None) \
                                         .filter(Order.is_delivered==None) \
                                         .filter_by(fk_company_id =UserForCompany.query \
                                                   .filter_by(role="manager").first().fk_company_id)\
                                                    .all(),
                                         allow_blank=True,
                                         blank_text="Sélectionner une référence...",
                                validators=[DataRequired('Champs obligatoire')])
    order_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(PurchaseField), min_entries=1)
    add = SubmitField('Ajouter produit')
    fin = SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')


class PurchaseOrderForm(FlaskForm):
    fournisseur = QuerySelectField('Fournisseur ', query_factory=lambda: Supplier.query \
                              .filter_by(is_deleted=False) \
                              .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
                                         .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                              allow_blank=True, blank_text='Sélectionner un bénéficiaire ...',
                              validators=[Optional()])

    order_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(EntryField), min_entries=1)
    add = SubmitField('Ajouter produit')
    fin = SubmitField('Terminer')
    submit = SubmitField('Sauvegarder')

class InvoiceEntryField(EntryField):
    item = QuerySelectField('Désignation ', query_factory=lambda: Item.query \
                            .filter_by(is_disabled=False) \
                            .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
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
                                            .filter_by(role="manager").first().fk_company_id).all()+
                                        Supplier.query \
                                        .filter_by(fk_company_id = UserForCompany.query\
                                            .filter_by(role="manager").first().fk_company_id).all(),
                            validators=[Optional()])

    reference_supplier_invoice = StringField('Référence ',validators=[Optional()])
    order_date = DateField('Date: ', default=datetime.utcnow().date(), validators=[Optional()])
    entities = FieldList(FormField(InvoiceEntryField))
    submit = SubmitField('Sauvegarder')