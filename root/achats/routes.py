from root import database as db
from flask_login import login_required, current_user
from flask import url_for, session, render_template, redirect, jsonify, flash
from datetime import datetime
from root.achats.forms import EntryField, ExitVoucherForm, PurchaseOrderForm
from root.models import UserForCompany, ExitVoucher, Entry, Item, Stock, DeliveryNote, Order, Supplier
from root.achats import purchases_bp
import datetime
@purchases_bp.before_request
def purchases_before_request():
    session['role'] = "Magasiner"


@purchases_bp.get('/')
@login_required
def index():
    if 'endpoint' in session:
        del session['endpoint']
    return render_template('purchases/index.html')


@purchases_bp.get('/sales/exit_voucher/add')
@purchases_bp.post('/sales/exit_voucher/add')
@login_required
def add_exit_voucher():
    session['endpoint']="stocks"
    # form = ExitVoucherForm()
    # return render_template('sales/add_exit_voucher.html', form = form)
    session['endpoint'] = 'sales'
    form = ExitVoucherForm()
    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    # clients = Client.query.filter_by(fk_company_id=company)
    # if not clients:
    #     flash("Veuillez d'abord ajouter des clients", 'warning')

    if form.validate_on_submit():
        entities = list()
        _q = ExitVoucher()
        # sum_amounts = 0
        if enumerate(form.entities):
            for _index, entry in enumerate(form.entities):
                if entry.quantity.data:
                    entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    # sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    return render_template("sales/new_quotation.html",
                                           form=form, nested=EntryField(),
                                           # somme=sum_amounts
                                           )
                _ = Entry()
                _.fk_item_id = entry.item.data.id
                _.purchase_price = entry.purchase_price.data
                _.quantity = entry.quantity.data
                _.total_price = entry.amount.data
                entities.append(_)
        if form.add.data:
            if enumerate(form.entities):
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.purchase_price.data * entry.quantity.data
                    # sum_amounts += entry.amount.data
            form.entities.append_entry({
                'label': Item.query.filter_by(is_disabled=False) \
                    .filter_by(fk_company_id=UserForCompany.query.filter_by(role="vendeur") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                'unit_price': 0,
                'quantity': 1,
                'amount': 0
            })
            return render_template('purchases/add_exit_voucher.html', form=form, nested=EntryField(),
                                   # somme=sum_amounts
                                   )
        if form.fin.data:
            if enumerate(form.entities):
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.purchase_price.data * entry.quantity.data
                    # sum_amounts += entry.amount.data
            return render_template('purchases/add_exit_voucher.html', form=form, nested=EntryField(),
                                   # somme=sum_amounts
                                   )

        # if form.exit_date.data:
        #     _q.created_at = form.exit_date.data
        _q.created_by = current_user.id
        # _q.fk_company_id = company
        # _q.fk_client_id = form.client.data.id
        # _q.total = sum_amounts
        # db.session.add(_q)
        # db.session.commit()
        last_q = ExitVoucher.query.filter_by(fk_company_id=company).order_by(ExitVoucher.created_at.desc()).first()
        # print(last_q)
        if last_q:
            last_intern_ref = last_q.intern_reference.split('-')[1].split('/')[0]
            year = last_q.intern_reference.split('-')[1].split('/')[2]
            if year == datetime.datetime.now().date().year:
                _q.intern_reference = "BS-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
                    datetime.datetime.now().date().year)
            else:
                _q.intern_reference = "BS-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
        else:
            _q.intern_reference = "BS-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
        db.session.add(_q)
        db.session.commit()
        for e in entities:
            # sum_amounts += e.total_price
            e.fk_order_id = _q.id
            db.session.add(e)
            db.session.commit()
            item = Item.query.get(e.fk_item_id)
            item.stock_quantity -= e.quantity
            db.session.add(item)
            db.session.commit()
            stock = Stock.query.filter_by(fk_item_id=e.fk_item_id).first()
            stock.stock_qte -= e.quantity
            db.session.add(stock)
            db.session.commit()
        # _q.total = sum_amounts
        db.session.add(_q)
        db.session.commit()
        flash('Bon de sortie crée avec succès', 'success')
        # return redirect(url_for('sales_bp.add_quotation'))
        return render_template("purchases/add_exit_voucher.html", form=form,
                               nested=EntryField(),
                               to_approve=True,
                               to_print=True)
    return render_template("purchases/add_exit_voucher.html", form=form, nested=EntryField())


@purchases_bp.get('/sales/delivery/<int:bl_id>/approve')
@login_required
def approve_delivery(bl_id):
    d_note = DeliveryNote.query.get(bl_id)
    if not d_note:
        return render_template('errors/404.html', blueprint="sales_bp")

    # company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if d_note.created_by != current_user.id:
        return render_template('errors/404.html', blueprint="sales_bp")
    query = Order.query.get(d_note.fk_order_id)
    if query.is_delivered:
        flash(f'Livraison { d_note.intern_reference } déjà validée')
        return redirect(url_for('sales_bp.delivery_notes'))

    delivered_quantity=0
    for entry in d_note.entities:
        delivered_quantity += entry.quantity

    ordered_quantity = 0
    _order=Order.query.get(d_note.fk_order_id)
    for entry in _order:
        ordered_quantity += entry.quantity

    if delivered_quantity == ordered_quantity:
        flash(f'Document {d_note.intern_reference} approuvé','success')
        return redirect(url_for('sales_bp.delivery_notes'))
    flash(f'Impossible d\'approuver le document {d_note.intern_reference}','warning')
    return redirect(url_for('sales_bp.delivery_notes'))


@purchases_bp.get('/sales/delivery')
@login_required
def delivery_notes():
    return render_template('sales/deliveries.html')


@purchases_bp.get('/orders')
@login_required
def purchases_orders():
    session['endpoint']="orders"
    _orders = Order.query.filter_by(category="achat").filter_by(
        fk_company_id = UserForCompany.query.filter_by(role="magasiner") \
                        .filter_by(fk_user_id = current_user.id) \
                        .first().fk_company_id
        )
    liste = list()
    if _orders:
        indexe = 1
        for order in _orders:
            _dict = order.repr()
            _dict.update({'index':indexe})
            indexe += 1
            liste.append(_dict)
    return render_template('purchases/purchases_orders.html', liste = liste)


@purchases_bp.get("/orders/add")
@purchases_bp.post('/orders/add')
@login_required
def new_order():
    session['endpoint'] = 'orders'
    form = PurchaseOrderForm()
    company = UserForCompany.query.filter_by(role="magasiner") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    _suppliers = Supplier.query.filter_by(fk_company_id=company)
    if not _suppliers:
        flash("Veuillez d'abord ajouter des clients",'warning')

    if form.validate_on_submit():
        entities = list()
        _q = Order()
        _q.category="achat"
        sum_amounts=0
        if enumerate(form.entities):
            sum_amounts = 0
            for _index, entry in enumerate(form.entities):
                sum_amounts += entry.amount.data
                if entry.quantity.data:
                    entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    return render_template("purchases/new_order.html",
                                           form = form, nested=EntryField(),
                                           somme = sum_amounts)
                _ = Entry()
                _.fk_item_id = entry.item.data.id
                _.unit_price = entry.unit_price.data
                _.quantity = entry.quantity.data
                _.total_price = entry.amount.data
                entities.append(_)
        if form.add.data:
            if enumerate(form.entities):
                sum_amounts = 0
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.unit_price.data * entry.quantity.data
                    sum_amounts += entry.amount.data
            form.entities.append_entry({
                'label': Item.query.filter_by(is_disabled=False) \
                    .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                'unit_price': 0,
                'quantity': 1,
                'amount': 0
            })
            return render_template('purchases/new_order.html',
                                   form=form,
                                   nested=EntryField(),
                                   somme=sum_amounts)
        if form.fin.data:
            if enumerate(form.entities):
                sum_amounts = 0
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.unit_price.data * entry.quantity.data
                    sum_amounts += entry.amount.data
            return render_template('purchases/new_order.html',
                                   form=form,
                                   nested=EntryField(),
                                   somme=sum_amounts)

        if form.order_date.data:
            _q.created_at = form.order_date.data
        _q.created_by = current_user.id
        _q.fk_company_id = company
        _q.fk_client_id= form.supplier.data.id
        _q.total = sum_amounts
        last_q = Order.query.filter_by(category="achat").filter_by(fk_company_id = company).order_by(Order.created_at.desc()).first()
        if last_q:
            last_intern_ref = last_q.intern_reference.split('-')[1].split('/')[0]
            year = last_q.intern_reference.split('-')[1].split('/')[2]
            if year == datetime.datetime.now().date().year :
                _q.intern_reference = "BC-"+(last_intern_ref+1)+"/"+str(company)+"/"+str(datetime.datetime.now().date().year)
            else:
                _q.intern_reference = "BC-1/"+str(company)+"/"+str(datetime.datetime.now().date().year)
        else:
            _q.intern_reference = "BC-1/"+str(company)+"/"+str(datetime.datetime.now().date().year)
        db.session.add(_q)
        db.session.commit()
        sum_amounts = 0
        for e in entities:
            sum_amounts = e.total_price
            e.fk_quotation_id = _q.id
            db.session.add(e)
            db.session.commit()
        _q.total = sum_amounts
        db.session.add(_q)
        db.session.commit()
        flash('Commande crée avec succès','success')
        return render_template("purchases/new_order.html", form=form,
                                somme = _q.total,
                               nested=EntryField(),
                               to_approve=True,
                               to_print=True)
    return render_template("purchases/new_order.html", form = form, nested=EntryField(), somme = 0)


@purchases_bp.get('/orders/<int:o_id>/receipt')
@login_required
def order_receipt(o_id):
    session['endpoint']="orders"
    order = Order.query.get(o_id)
    if not order:
        return render_template("errors/404.html", blueprint="purchases_bp")

    if order.category != "achat":
        return render_template('errors/404.html', blueprint="purchases_bp")

    company = UserForCompany.query.filter_by(role="magasiner").filter_by(fk_user_id = current_user.id).first().fk_company_id
    if order.fk_company_id != company:
        return render_template('errors/404.html', blueprint="purchases_bp")

    if order.is_canceled:
        flash('Impossible de créer un bon réception pour une commande annulé','danger')
        return redirect(url_for('purchases_bp.purchases_orders'))


    return redirect(url_for('purchases_bp.purchases_orders'))

@purchases_bp.get('/invoices')
@login_required
def purchases_invoices():
    session['endpoint']="orders"
    return render_template("purchases/invoices.html")


@purchases_bp.get('/orders/receipts')
@login_required
def purchases_receipts():
    session['endpoint']="orders"
    return render_template("purchases/purchases_receipts.html")


@purchases_bp.get('/stocks')
@login_required
def stocks():
    return "Stocks"