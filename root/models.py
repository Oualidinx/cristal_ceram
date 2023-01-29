from root import login_manager, database as db
from datetime import datetime
from flask_login import UserMixin

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


class Brand(db.Model):
    __tablename__="brand"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(500))


class Category(db.Model):
    __tablename__="category"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(500))


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


class Item(db.Model):
    __tablename__="item"
    id = db.Column(db.Integer, primary_key=True)
    intern_reference = db.Column(db.String(100))
    series = db.Column(db.String(100))
    label = db.Column(db.String(100))
    item_type = db.Column(db.String(20))
    bar_code = db.Column(db.String(512))
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    dim_x = db.Column(db.Float, default=0)
    dim_y = db.Column(db.Float, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    expired_at = db.Column(db.DateTime, default=datetime.utcnow())
    is_disabled = db.Column(db.Boolean, default=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))


class ItemBrandCategory(db.Model):
    __tablename__="item_brand_category"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))


class Order(db.Model):
    __tablename__="order"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
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
    label = db.Column(db.String(100))
    fk_item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    fk_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    stock_qte = db.Column(db.Float, default=0)
    stock_min = db.Column(db.Float, default=0)
    stock_max = db.Column(db.Float, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_purchase = db.Column(db.DateTime, default=datetime.utcnow())
    last_buy_price = db.Column(db.Float, default=0)


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
    # created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_verified = db.Column(db.Boolean, default=0)
    is_disabled = db.Column(db.Boolean, default=0)
    taxes = db.relationship('Tax', backref="user_taxes", lazy="subquery")
    companies = db.relationship('Company', secondary="user_for_company",
                                primaryjoin="foreign(UserForCompany.fk_company_id) == Company.id",
                                secondaryjoin="and_(User.id==foreign(UserForCompany.fk_user_id), UserForCompany.role=='manager')",
                                viewonly=True)
    fk_store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable = True)
    fk_warehouse_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable = True)


class UserForCompany(db.Model):
    __tablename__="user_for_company"
    id=db.Column(db.Integer, primary_key=True)
    fk_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    fk_company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    role = db.Column(db.String(10))
    start_from = db.Column(db.DateTime, default = datetime.utcnow())

class Warehouse(db.Model):
    __tablename__="warehouse"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10))
    address = db.Column(db.String(100))
    contact = db.Column(db.String(10))
    fk_company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    stocks = db.relationship('Stock', backref="warehouse_stocks", lazy="subquery")

    def __repr__(self):
        return f'Entrepôt: {self.name}, {self.address}'

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
    name = db.Column(db.String(10))
    address = db.Column(db.String(100))
    contact = db.Column(db.String(10))
    fk_company_id=db.Column(db.Integer, db.ForeignKey('company.id'))

    def __repr__(self):
        return f'magasin: {self.name}, {self.address}'