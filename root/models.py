from root import login_manager, database as db
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import and_
@login_manager.user_loader
def user_loader(user_id):
    return User.query.get_or_404(user_id)

class TVA(db.Model):
    __tablename__="tva"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(500))
    value = db.Column(db.Float, default=0)
    sign = db.Column(db.String(1), default='+')
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))


class Company(db.Model):
    __tablename__="company"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    site = db.Column(db.String(100))
    # manager = db.Column(db.Integer, db.ForeignKey('user.id'))
    currency = db.Column(db.String(10))
    # taxes = db.relationship('Tax', backref="company_taxes", lazy = "subquery")
    activity_sector = db.Column(db.String(100))
    users = db.relationship('User', secondary="user_for_company",viewonly=True,
                            primaryjoin="Company.id == foreign(UserForCompany.fk_company_id)",
                            secondaryjoin="and_(User.id == foreign(UserForCompany.fk_user_id), UserForCompany.role!='manager')")
    warehouses = db.relationship('Warehouse', backref="company_warehouses", lazy="subquery")
    stores = db.relationship('Store', backref="company_stores", lazy="subquery")
    def __repr__(self):
        return f'<Company:{self.id}, {self.name}>'

class Tax(db.Model):
    __tablename__="tax"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    label = db.Column(db.String(100))
    value = db.Column(db.Float, default=0)
    sign = db.Column(db.String(1), default='+')
    is_fixed = db.Column(db.Boolean, default=False)
    is_percent = db.Column(db.Boolean, default=False)
    applied_before_TVA = db.Column(db.Boolean, default=False)
    applied_after_TVA = db.Column(db.Boolean, default=False)
    on_applied_products = db.Column(db.Boolean, default=False)
    # on_applied_TVA = db.Column(db.Boolean, default=False)
    fk_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'{self.label}-{self.sign}{self.value}'

    def repr(self, columns=None):
        _dict = dict(
             id=self.id,
             name = self.name,
             label = self.label,
             value = self.value,
             signe = self.sign,
             v_status = "Fixée" if self.is_fixed else "Pourcentage",
             for_sell = "Pour les ventes" if self.for_sell else "Pour les achats",
             applied_before_TVA = "Appliqué sur TVA" if self.applied_after_TVA else "Appliqué sans TVA"
         )
        if columns:
            return {key:_dict[key] for key in columns}
        return _dict


class Address(db.Model):
    __tablename__="address"
    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(100))
    zip_code = db.Column(db.Integer)
    description = db.Column(db.String(1500))
    address_type = db.Column(db.String(50))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))


class BankAccount(db.Model):
    __tablename__="bank_account"
    id = db.Column(db.Integer, primary_key=True)
    bank = db.Column(db.String(100))
    label = db.Column(db.String(100))
    account_number = db.Column(db.String(100))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))


class Aspect(db.Model):
    __tablename__="aspect"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'{self.id}  -  {self.label}'


class Format(db.Model):
    __tablename__="format"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'{self.id}  -  {self.label}'

    def repr(self):
        return dict(
            id = self.id,
            label = self.label
        )


# class Utilisation(db.Model):
#     __tablename__="utilisation"
#     id = db.Column(db.Integer, primary_key=True)
#     label = db.Column(db.String(500))
#     created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
#
#     def __repr__(self):
#         return f'{self.id}  -  {self.label}'


class Client(db.Model):
    __tablename__="client"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    site = db.Column(db.String(100))
    category = db.Column(db.String(20))
    nif = db.Column(db.String(100))
    civility = db.Column(db.String(10))


class ClientCompany(db.Model):
    __tablename__="client_company"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))


class Contact(db.Model):
    __tablename__="contact"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50))
    value = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))


class DeliveryNote(db.Model):
    __tablename__="delivery_note"
    id = db.Column(db.Integer, primary_key=True)
    intern_reference = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))


class Entry(db.Model):
    __tablename__="entry"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    quantity = db.Column(db.Float, default=0)
    tva = db.Column(db.Integer, db.ForeignKey('tva.id'))
    unit_price = db.Column(db.Float, default=0)
    total_price = db.Column(db.Float, default=0)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotation.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    delivery_note_id = db.Column(db.Integer, db.ForeignKey('delivery_note.id'))


class Fund(db.Model):
    __tablename__="fund"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100))
    total = db.Column(db.Float, default=0)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))


class Invoice(db.Model):
    __tablename__="invoice"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    inv_type = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    total = db.Column(db.Float, default=0)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    is_delivered = db.Column(db.Boolean, default=False)
    is_canceled = db.Column(db.Boolean, default=False)
    is_valid = db.Column(db.Boolean, default=False)
    taxes = db.relationship('Tax', secondary="invoice_tax",
                            primaryjoin="Invoice.id == foreign(InvoiceTax.fk_invoice_id)",
                            secondaryjoin="Tax.id == foreign(InvoiceTax.fk_tax_id)",
                            viewonly=True)


class InvoiceTax(db.Model):
    __tablename__='invoice_tax'
    id = db.Column(db.Integer, primary_key=True)
    fk_invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    fk_tax_id = db.Column(db.Integer, db.ForeignKey('tax.id'))


class ItemAspectFormat(db.Model):
    __tablename__="item_aspect_format"
    id = db.Column(db.Integer, primary_key=True)
    fk_format_id = db.Column(db.Integer, db.ForeignKey('format.id'))
    fk_aspect_id = db.Column(db.Integer, db.ForeignKey('aspect.id'))
    # fk_utilisation_id = db.Column(db.Integer, db.ForeignKey('utilisation.id'))
    utilisation = db.Column(db.String(50))
    fk_item_id = db.Column(db.Integer, db.ForeignKey('item.id'))


class Item(db.Model):
    __tablename__="item"
    id = db.Column(db.Integer, primary_key=True)
    serie = db.Column(db.String(100), nullable=True)
    intern_reference = db.Column(db.String(100))
    label = db.Column(db.String(1500))
    # use_for = db.Column(db.String(20))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    expired_at = db.Column(db.DateTime, default=datetime.utcnow())
    is_disabled = db.Column(db.Boolean, default=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))

    def __repr__(self):
        return f'{self.label}, ' \
               f'{Format.query.get(ItemAspectFormat.query.filter(fk_item_id = self.id).fk_format_id).label}, ' \
               f'{Aspect.query.get(ItemAspectFormat.query.filter(fk_item_id = self.id).fk_aspect_id).label}'


class Order(db.Model):
    __tablename__="order"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    delivery_date = db.Column(db.DateTime, default=datetime.utcnow())
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    total = db.Column(db.Float, default=0)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotation.id'))
    is_delivered = db.Column(db.Boolean, default=0)
    is_canceled = db.Column(db.Boolean, default=0)
    taxes = db.relationship('Tax', secondary="order_tax",
                            primaryjoin="Order.id == foreign(OrderTax.fk_order_id)",
                            secondaryjoin="Tax.id == foreign(OrderTax.fk_tax_id)",
                            viewonly=True)

class OrderTax(db.Model):
    __tablename__="order_tax"
    id = db.Column(db.Integer, primary_key=True)
    fk_order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    fk_tax_id = db.Column(db.Integer, db.ForeignKey('tax.id'))


class Pay(db.Model):
    __tablename__="pay"
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, default=0)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow())
    create_at = db.Column(db.DateTime, default=datetime.utcnow())
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    expiry_date = db.Column(db.DateTime, default=datetime.utcnow())
    is_cheque = db.Column(db.Boolean, default=0)
    is_in_cash = db.Column(db.Boolean, default=0)
    is_by_bank_transfer = db.Column(db.Boolean, default=0)
    holder_full_name = db.Column(db.String(150))
    bank = db.Column(db.String(10))
    cheque_number = db.Column(db.String(10))
    pay_information = db.Column(db.String(1500))
    receiving_account = db.Column(db.String(10))
    recv_crate = db.Column(db.String(10))
    fk_company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    fk_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'))
    fk_invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))


class Quotation(db.Model):
    __tablename__="quotation"
    id = db.Column(db.Integer, primary_key=True)
    intern_reference = db.Column(db.String(10))
    fk_client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))


class Stock(db.Model):
    __tablename__="stock"
    id = db.Column(db.Integer, primary_key=True)
    # label = db.Column(db.String(100))
    fk_item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    fk_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    stock_qte = db.Column(db.Float, default=0)
    stock_sec = db.Column(db.Float, default=0)
    # stock_max = db.Column(db.Float, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_purchase = db.Column(db.DateTime, default=datetime.utcnow())
    last_purchase_price = db.Column(db.Float, default=0)

    def __repr__(self):
        return f'{self.id}, ' \
               f'{Item.query.get(self.fk_item_id).label}, ' \
               f'{Warehouse.query.get(self.fk_warehouse_id).name}'

    def repr(self, columns=None):
        _dict = dict(
            id = self.id,
            warehouse = Warehouse.query.get(self.fk_warehouse_id).name,
            item = Item.query.get(self.fk_item_id).label,
            quantity = self.stock_qte,
            last_purchase = self.last_purchase.date(),
            last_purchase_price = '{:20,.2f}'.format(self.last_purchase_price),
            status = "#004D33" if (self.stock_sec/self.stock_qte)<0.5 else "#A6001A" if (self.stock_sec/self.stock_qte) in [0.51,1] else "#E06000",
            stock_sec = self.stock_sec
        )
        if columns:
            return {key:_dict[key] for key in columns}
        return _dict


class Subscription(db.Model):
    __tablename__="subscription"
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.DateTime, default=datetime.utcnow())
    end_date = db.Column(db.DateTime, default=datetime.utcnow())
    expire_in = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    users_number = db.Column(db.Integer, default=0)
    sms_number = db.Column(db.Integer, default=0)
    per_mounth = db.Column(db.Boolean, default=False)
    per_year = db.Column(db.Boolean, default=False)
    fk_company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    fk_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Supplier(db.Model):
    __tablename__="supplier"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(10))
    site = db.Column(db.String(10))
    category = db.Column(db.String(20))
    nif = db.Column(db.String(10))
    civility = db.Column(db.String(10))


class SupplierCompany(db.Model):
    __tablename__="supplier_company"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))


class User(UserMixin, db.Model):
    __tablename__="user"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(256))
    username = db.Column(db.String(256))
    # role = db.Column(db.String(10))
    password_hash = db.Column(db.String(256))
    email = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_verified = db.Column(db.Boolean, default=False)
    is_disabled = db.Column(db.Boolean, default=False)
    taxes = db.relationship('Tax', backref="user_taxes", lazy="subquery")
    companies = db.relationship('Company', secondary="user_for_company",
                                primaryjoin="foreign(UserForCompany.fk_company_id) == Company.id",
                                secondaryjoin="and_(User.id==foreign(UserForCompany.fk_user_id), UserForCompany.role=='manager')",
                                viewonly=True)
    fk_store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable = True)
    def __repr__(self):
        return f'{self.id} - {self.full_name}'
    def repr(self, columns=None):
        _dict = {
            'id':self.id,
            'full_name' : self.full_name,
            'username' : self.username,
            'role': 'vendeur' if self.fk_store_id and Store.query.get(self.fk_store_id) else 'magasiner' if UserForCompany.query.filter(and_(
                UserForCompany.fk_warehouse_id is not None, UserForCompany.role == 'magasiner')) \
                .filter_by(fk_user_id=self.id).all() else '',
            'status': ('A6001A', "Suspendu(e)") if not self.fk_store_id and not UserForCompany.query.filter(and_(
                UserForCompany.fk_warehouse_id is not None, UserForCompany.role == 'magasiner')) \
                .filter_by(fk_user_id=self.id).all() else ("#004D33", "Affecté(e)"),
            '_session' : ("#004D33","Activé") if not self.is_disabled else ('A6001A',"Désactivé"),
            'location' : Store.query.get(self.fk_store_id) if self.fk_store_id else "Autres...",
            'locations': [str(wh) for wh in Warehouse.query.join(UserForCompany, Warehouse.id == UserForCompany.fk_warehouse_id)\
                                .filter(UserForCompany.fk_user_id == self.id).all()]
        }
        return  {key : _dict[key] for key in columns} if columns else _dict


class UserForCompany(db.Model):
    __tablename__="user_for_company"
    id=db.Column(db.Integer, primary_key=True)
    fk_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    fk_company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    fk_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)
    role = db.Column(db.String(10))
    start_from = db.Column(db.DateTime, default = datetime.utcnow())
    end_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'UserForCompany: {User.query.get(self.fk_user_id).full_name}, {self.role}, dans {Warehouse.query.get(self.fk_warehouse_id)}'

    def repr(self, columns = None):
        user = User.query.get(self.fk_user_id)
        _dict={
            'id': user.id,
            'full_name': user.full_name,
            'username': user.username,
            'role':self.role,
            'status': ('A6001A', "Suspendu(e)") if not user.fk_store_id and not UserForCompany.query.filter(and_(
                UserForCompany.fk_warehouse_id is not None, UserForCompany.role == 'magasiner')) \
                .filter_by(fk_user_id=user.id).all() else ("#004D33", "Affecté(e)"),
            '_session': ("#004D33", "Activé") if not user.is_disabled else ('A6001A', "Désactivé"),
            'location': Store.query.get(self.fk_store_id) if user.fk_store_id else "Autres...",
            'locations': Warehouse.query.join(UserForCompany, Warehouse.id == UserForCompany.fk_warehouse_id) \
                .filter(UserForCompany.fk_user_id == user.id).all()

        }
        return {key:_dict[key] for key in columns} if columns else _dict


class Warehouse(db.Model):
    __tablename__="warehouse"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10))
    address = db.Column(db.String(100))
    contact = db.Column(db.String(10))
    fk_company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    stocks = db.relationship('Stock', backref="warehouse_stocks", lazy="subquery")

    def __repr__(self):
        return f'\n{self.name}, {self.address}'

    def repr(self, columns = None):
        _dict = dict(
            id = self.id,
            name = self.name,
            address = self.address,
            contact = self.contact
        )
        if columns:
            return {key:_dict[key] for key in columns}
        return _dict


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    address = db.Column(db.String(100))
    contact = db.Column(db.String(10))
    is_disabled = db.Column(db.Boolean, default = False)
    fk_company_id=db.Column(db.Integer, db.ForeignKey('company.id'))
    sellers = db.relationship('User', backref="stores_sellers", lazy ="subquery")

    def __repr__(self):
        return f'Magasin: {self.name}, {self.address}'

    def repr(self):
        return dict(
            id= self.id,
            name = self.name,
            address = self.address,
            contact = self.contact,
        )