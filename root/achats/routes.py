from root import database as db
from num2words import num2words
from flask_login import login_required, current_user
from flask import jsonify, url_for, session, render_template,request, redirect, flash
from datetime import datetime
from root.achats.forms import PaiementForm,EntryField, ExitVoucherForm, PurchaseOrderForm, PurchaseReceiptForm
from root.models import UserForCompany, ExitVoucher, Entry, Item, Stock, DeliveryNote, Order, Supplier\
                        , PurchaseReceipt, Client, Invoice, User, Expense, Pay, Company, Warehouse
from root.achats.forms import InvoiceForm, InvoiceEntryField
from root.achats import purchases_bp
from sqlalchemy.sql import func
from flask_weasyprint import render_pdf, HTML
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
    company = UserForCompany.query.filter_by(role="magasiner") \
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


# @purchases_bp.get('/sales/delivery')
# @login_required
# def delivery_notes():
#     return render_template('sales/deliveries.html')


@purchases_bp.get('/orders')
@login_required
def purchases_orders():
    session['endpoint']="orders"
    _orders = Order.query.filter_by(category="achat").filter_by(is_deleted=False) \
        .filter_by(fk_company_id = UserForCompany.query.filter_by(role="magasiner") \
                        .filter_by(fk_user_id = current_user.id) \
                        .first().fk_company_id
            ).all()
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
        flash("Veuillez d'abord ajouter des fournisseurs",'warning')

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
        _q.fk_supplier_id= form.fournisseur.data.id
        _q.fk_client_id = None
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
            sum_amounts += e.total_price
            e.fk_order_id = _q.id
            e.fk_quotation_id, e.fk_exit_voucher_id=None, None
            e.fk_invoice_id, e.fk_delivery_note_id = None, None
            db.session.add(e)
            db.session.commit()
        _q.total = sum_amounts
        db.session.add(_q)
        db.session.commit()
        flash(f'Commande {_q.intern_reference} crée avec succès','success')
        # return redirect(url_for('purchases_bp.new_order'))
        return render_template("purchases/new_order.html", form=form,
                                somme = _q.total,
                               new_command=True,
                               nested=EntryField(),
                               to_print=True)
    return render_template("purchases/new_order.html", form = form, nested=EntryField(), somme = 0)


@purchases_bp.get('/orders/<int:o_id>/receipt')
@login_required
def order_receipt(o_id):
    # print("receipt")
    session['endpoint']="orders"
    order = Order.query.get(o_id)
    if not order:
        return render_template("errors/404.html", blueprint="purchases_bp")

    if order.category != "achat":
        return render_template('errors/404.html', blueprint="purchases_bp")

    company = UserForCompany.query.filter_by(role="magasiner").filter_by(fk_user_id = current_user.id).first().fk_company_id
    if order.fk_company_id != company:
        return render_template('errors/404.html', 
                               blueprint="purchases_bp")

    if order.is_canceled:
        flash('Impossible de créer un bon réception pour une commande annulé','danger')
        return redirect(url_for('purchases_bp.purchases_orders'))
    order.is_delivered = True
    db.session.add(order)
    db.session.commit()
    p_receipt = PurchaseReceipt()
    last_q = PurchaseReceipt.query.filter_by(fk_company_id=company).order_by(
        PurchaseReceipt.created_at.desc()).first()
    if last_q:
        last_intern_ref = last_q.intern_reference.split('-')[1].split('/')[0]
        year = last_q.intern_reference.split('-')[1].split('/')[2]
        if year == datetime.datetime.now().date().year:
            p_receipt.intern_reference = "BR-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
                datetime.datetime.now().date().year)
        else:
            p_receipt.intern_reference = "BR-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
    else:
        p_receipt.intern_reference = "BR-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
    p_receipt.fk_supplier_id = order.fk_supplier_id
    p_receipt.created_by = current_user.id
    p_receipt.total = order.total
    p_receipt.fk_company_id = order.fk_company_id
    p_receipt.fk_order_id = order.id
    db.session.add(p_receipt)
    db.session.commit()
    for e in order.entries:
        e.fk_purchase_receipt_id = p_receipt.id
        stock = Stock.query.filter_by(fk_item_id = e.fk_item_id).first()
        if stock:
            stock.stock_qte += e.quantity
            stock.last_purchase_price = e.unit_price
            db.session.add(stock)
            db.session.commit()
        # else:
            # flash(f'Veuillez rajouter des stock pour le produit {Item.query.get(e.fk_item_id)}','warning')
            # return redirect(url_for('purchases_bp.purchases_receipts'))
        db.session.add(e)
        db.session.commit()
    flash(f'Entrée {p_receipt.intern_reference} sauvegardée','success')
    print('''
    générer un PDF à télécharger par le manager et le magasiner
    ''')
    return redirect(url_for('purchases_bp.purchases_orders'))


@purchases_bp.route('/invoices',methods=['GET','POST'])
@login_required
def purchases_invoices():
    session['endpoint']="orders"
    form = PaiementForm()
    company = UserForCompany.query.filter_by(role="magasiner") \
        .filter_by(fk_user_id=current_user.id) \
        .first().fk_company_id
    _invoices = Invoice.query.filter_by(fk_company_id=company
                                        ).all()
    liste = list()
    if _invoices:
        indexe = 1
        for receipt in _invoices:
            _dict = receipt.repr()
            _dict.update({'index': indexe})
            indexe += 1
            liste.append(_dict)

    if form.validate_on_submit():
        code = request.form.get('code')
        invoice = Invoice.query.filter_by(intern_reference=code).first()
        if not invoice:
            flash('Facture introuvable', 'danger')
            return redirect(url_for('purchases_bp.purchases_invoices'))
        expense = Expense()
        expense.fk_company_id = company
        expense.fk_category_id = form.expense_category.data.id
        expense.created_by = current_user.id
        expense.amount = invoice.total
        expense.label = f"paiement de la facture  {invoice.intern_reference}"
        expense.fk_invoice_id = invoice.id
        expense.description=f"Paiement d'une facture d'où de code = {invoice.intern_reference} générée par {User.query.get(current_user.id).full_name} avec total de {invoice.total}, le {invoice.created_at.date()}"
        db.session.add(expense)
        db.session.commit()
        flash(f'{form.data.get("code")} a été payée','success')
        return redirect(url_for('purchases_bp.purchases_invoices'))
    return render_template("purchases/invoices.html", liste = liste, form=form)


@purchases_bp.get('/receipts')
@login_required
def purchases_receipts():
    session['endpoint']="orders"
    _receipts = PurchaseReceipt.query.filter_by(is_deleted=False) \
        .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                   .filter_by(fk_user_id=current_user.id) \
                   .first().fk_company_id
                   ).all()
    liste = list()
    if _receipts:
        indexe = 1
        for receipt in _receipts:
            _dict = receipt.repr_()
            _dict.update({'index': indexe})
            indexe += 1
            liste.append(_dict)
    return render_template("purchases/purchases_receipts.html", liste = liste)


@purchases_bp.get('/orders/<int:o_id>/get')
@login_required
def get_order(o_id):
    session['endpoint'] = 'purchases'
    order = Order.query.filter_by(category="achat").filter_by(id = o_id).first()

    if not order:
        return render_template('errors/404.html', bluebript="purchases_bp")

    user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id) \
        .filter_by(role="magasiner").first()
    if order.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="purchases_bp")
    return render_template("purchases/order_info.html", order=order.repr())


@purchases_bp.get('/orders/<int:o_id>/delete')
@login_required
def delete_order(o_id):
    session['endpoint'] = 'purchases'
    order = Order.query.filter_by(category="achat").filter_by(id = o_id).first()

    if not order:
        return render_template('errors/404.html', blueprint="purchases_bp")

    user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id) \
                                            .filter_by(role="magasiner").first()

    if order.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="purchases_bp")

    for e in order.entries:
        db.session.delete(e)
        db.session.commit()
    order.is_deleted = True
    db.session.add(order)
    db.session.commit()
    flash('Objet Supprimé avec succès', 'success')
    return redirect(url_for('purchases_bp.purchases_orders'))


@purchases_bp.get('/receipts/add')
@purchases_bp.post('/receipts/add')
@login_required
def new_purchase_receipt():
    session['endpoint'] = 'orders'
    company=UserForCompany.query.filter_by(role="magasiner") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    _suppliers = Supplier.query.filter_by(fk_company_id=company)
    if not _suppliers:
        flash("Veuillez d'abord ajouter des fournisseurs", 'warning')
    form = PurchaseReceiptForm()

    if form.validate_on_submit():
        entities = list()
        _q = PurchaseReceipt()
        sum_amounts = 0
        if enumerate(form.entities):
            sum_amounts = 0
            for _index, entry in enumerate(form.entities):
                sum_amounts += entry.amount.data
                if entry.quantity.data:
                    entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    return render_template("purchases/new_receipt.html",
                                           form=form, nested=EntryField())
                _ = Entry()
                _.fk_item_id = entry.item.data.id
                _.unit_price = entry.unit_price.data
                _entry = Entry.query.filter(Entry.fk_order_id != None).filter_by(fk_order_id=form.command_reference.data.id).first()
                if _entry:
                    if _entry.quantity > entry.quantity.data:
                        flash(f"La quantity du {Item.query.get(entry.fk_item_id).label} est suppérieur à la quantity commandée","warning")
                        return render_template("purchases/new_receipt.html",
                                               form=form, nested=EntryField(),
                                               somme=sum_amounts)

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

            if form.command_reference.data:
                form.entities.append_entry({
                    'item':Item.query.join(Entry, Entry.fk_item_id == Item.id)\
                                        .filter(Item.fk_company_id==company) \
                                            .filter(Item.is_disabled==False) \
                                                .filter(Entry.fk_order_id==form.command_reference.data.id).all(),
                    'unit_price': 0,
                    'quantity': 1,
                    'amount': 0
                })
                return render_template('purchases/new_receipt.html',
                                       form=form,
                                       somme=sum_amounts,
                                       nested=EntryField())
            else:
                form.entities.append_entry({
                    'item': Item.query.filter_by(is_disabled=False) \
                        .filter_by(fk_company_id=UserForCompany.query.filter_by(role="magasiner") \
                                   .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                    'unit_price': 0,
                    'quantity': 1,
                    'amount': 0
                })
                return render_template('purchases/new_receipt.html',
                                       form=form,
                                       somme=sum_amounts,
                                       nested=EntryField())
        if form.fin.data:
            if enumerate(form.entities):
                sum_amounts = 0
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.unit_price.data * entry.quantity.data
                    sum_amounts += entry.amount.data
            return render_template('purchases/new_receipt.html',
                                   form=form,
                                   somme=sum_amounts,
                                   nested=EntryField())
        if form.order_date.data:
            _q.created_at = form.order_date.data
        _q.created_by = current_user.id
        _q.fk_company_id = company

        if form.command_reference.data.fk_supplier_id:
            _q.fk_supplier_id = form.command_reference.data.fk_supplier_id
            _q.fk_client_id = None
        else:
            _q.fk_client_id = form.command_reference.data.fk_client_id
            _q.fk_supplier_id = None

        _q.total = sum_amounts
        last_q = Order.query.filter_by(category="achat").filter_by(fk_company_id=company).order_by(
            Order.created_at.desc()).first()
        if last_q:
            last_intern_ref = last_q.intern_reference.split('-')[1].split('/')[0]
            year = last_q.intern_reference.split('-')[1].split('/')[2]
            if year == datetime.datetime.now().date().year:
                _q.intern_reference = "BR-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
                    datetime.datetime.now().date().year)
            else:
                _q.intern_reference = "BR-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
        else:
            _q.intern_reference = "BR-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
        sum_amounts = 0
        for e in entities:
            sum_amounts = e.total_price
            e.fk_order_id = None
            e.fk_quotation_id, e.fk_exit_voucher_id = None, None
            e.fk_invoice_id, e.fk_delivery_note_id = None, None
            warhouses = Warehouse.query.join(UserForCompany, UserForCompany.fk_warehouse_id == Warehouse.id) \
                                        .filter_by(fk_user_id = current_user.id)
            stock = Stock.query.filter_by(fk_item_id=e.fk_item_id).first()
            if not stock:
                db.session.rollback()
                flash(f"Article {Item.query.get(e.fk_item_id).label} n'a pas de stock",'warning')
                return render_template("purchases/new_receipt.html",
                                       form = form,nested=EntryField(),
                                       somme = sum_amounts)
            db.session.add(e)
            db.session.commit()

            stock.stock_qte += e.quantity
            item = Item.query.filter_by(id = e.fk_item_id).first()
            item.stock_quantity += e.quantity
            db.session.add(item)
            db.session.commit()
            stock.last_purchase_price = e.unit_price
            db.session.add(stock)
            db.session.commit()
        _q.total = sum_amounts
        db.session.add(_q)
        db.session.commit()
        flash(f'Bon {_q.intern_reference} crée avec succès', 'success')
        return render_template("purchases/new_receipt.html", form=form,
                               somme=_q.total,
                               new_command=True,
                               nested=EntryField(),
                               to_print=True)

    return render_template("purchases/new_receipt.html", form=form, nested=EntryField(), somme=0)


@purchases_bp.get('/receipt/<int:r_id>/get')
@login_required
def get_receipt(r_id):
    session['endpoint'] = 'purchases'
    order = PurchaseReceipt.query.filter_by(id=r_id).first()

    if not order:
        return render_template('errors/404.html', bluebript="purchases_bp")
    if order.is_deleted:
        return render_template('errors/404.html', blueprint="purchases_bp")

    user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id) \
        .filter_by(role="magasiner").first()
    if order.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="purchases_bp")
    return render_template("purchases/receipt_info.html", order=order.repr_())


# @purchases_bp.get('/receipt/<int:r_id>/delete')
# @login_required
# def delete_receipt(r_id):
#     pass


@purchases_bp.get('/receipt/<int:r_id>/invoice')
@purchases_bp.post('/receipt/<int:r_id>/invoice')
@login_required
def receipt_invoice(r_id):
    receipt=PurchaseReceipt.query.get(r_id)
    if not receipt:
        return render_template('errors/404.html', blueprint="purchases_bp")
    company =  UserForCompany.query.filter_by(role="magasiner") \
                                    .filter_by(fk_user_id=current_user.id) \
                                        .first().fk_company_id
    if receipt.fk_company_id != company:
        return render_template('errors/404.html', blueprint="purchases_bp")

    invoice = Invoice.query.filter_by(fk_receipt_id=receipt.id).first()
    if invoice:
        flash('Bon déjà facturé','warning')
        return redirect(url_for('purchases_bp.purchases_receipts'))
    form = InvoiceForm()
    sum_amounts = 0
    if request.method=="GET":
        form.recipient.data = Supplier.query.get(receipt.fk_supplier_id)
        form.order_date.data = receipt.created_at.date()
        for entry in receipt.entries:
            sum_amounts += entry.quantity*entry.unit_price
            form.entities.append_entry({
                    'item': Item.query.get(entry.fk_item_id),
                    'unit_price': entry.unit_price,
                    'quantity': entry.quantity,
                    'amount': entry.quantity*entry.unit_price
                })

    if form.validate_on_submit():
        invoice = Invoice()
        invoice.fk_company_id = company
        invoice.fk_supplier_id = form.recipient.data.id
        invoice.total = receipt.total
        invoice.created_by=current_user.id
        invoice.fk_receipt_id = receipt.id
        invoice.is_valid = True
        invoice.inv_type = "achat"
        invoice.reference_supplier_invoice = None
        if form.reference_supplier_invoice.data:
            invoice.reference_supplier_invoice = form.reference_supplier_invoice.data
        last_q = Invoice.query.filter_by(inv_type="achat").filter_by(fk_company_id=company).order_by(
            Invoice.created_at.desc()).first()
        if last_q:
            last_intern_ref = last_q.intern_reference.split('-')[1].split('/')[0]
            year = last_q.intern_reference.split('-')[1].split('/')[2]
            if year == datetime.datetime.now().date().year:
                invoice.intern_reference = "FAC-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
                    datetime.datetime.now().date().year)
            else:
                invoice.intern_reference = "FAC-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
        else:
            invoice.intern_reference = "FAC-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)

        invoice.fk_order_id = PurchaseReceipt.query.get(invoice.fk_receipt_id).fk_order_id
        db.session.add(invoice)
        db.session.commit()
        for entry in receipt.entries:
            entry.fk_invoice_id = invoice.id
            db.session.add(entry)
            db.session.commit()
        flash('Document sauvegardée','success')
        return redirect(url_for("purchases_bp.purchases_receipts"))
    return render_template('purchases/new_invoice.html',somme=sum_amounts,
                           nested=InvoiceEntryField(), form=form)


@purchases_bp.get('/recipients')
@login_required
def get_recipients():
    company = UserForCompany.query.filter_by(role="magasiner").filter_by(fk_user_id = current_user.id) \
                                    .first().fk_company_id
    clients = Client.query.filter_by(fk_company_id=company).filter_by(is_deleted=False)
    suppliers = Supplier.query.filter_by(fk_company_id=company).filter_by(is_deleted=False)
    data = list()
    if not clients.all() and not suppliers.all():
        return jsonify(total_count=0,
                       items = []),200
    if "q" in request.args:
        clients = clients.filter(Client.full_name.like(func.lower(f'%{request.args.get("q")}%'))) if clients.all() else None
        suppliers = suppliers.filter(Supplier.full_name.like(func.lower(f'%{request.args.get("q")}%'))) if suppliers.all() else None
    if clients.all():
        for client in clients.all():
            data.append({
                'id':client.id,
                'text':'Client: '+str.upper(client.full_name)
            })

    if suppliers.all():
        for supplier in suppliers.all():
            data.append({
                    'id':supplier.id,
                    'text':'Fournisseur: '+str.upper(supplier.full_name)
                })
    return jsonify(total_count=len(data),
                   items = data), 200



@purchases_bp.get('/commands')
@login_required
def get_commands():
    company = UserForCompany.query.filter_by(role="magasiner") \
                                    .filter_by(fk_user_id=current_user.id).first().fk_company_id
    commands = Order.query.filter(Order.is_deleted == False).filter_by(fk_company_id = company)
    if "q" in request.args:
        commands = commands.filter(Order.is_canceled == None) \
            .filter(Order.intern_reference.like(func.lower(f'%{request.args["q"]}%')))
    data = list()
    if commands.all():
        for command in commands.all():
            b = Client.query.get(command.fk_client_id) if command.fk_client_id else None
            if b:
                data.append({
                    'id': command.id,
                    'text': str.upper(Client.query.get(command.fk_client_id).full_name)+","+command.intern_reference
                            +' ,Le '+str(command.created_at.date())
                })
            else:
                data.append({
                    'id': command.id,
                    'text': str.upper(Supplier.query.get(
                        command.fk_supplier_id).full_name) + ", " + command.intern_reference + ' ,Le ' + str(
                        command.created_at.date())
                })
        return jsonify(total_count=len(data),
                       items = data), 200
    return jsonify(total_count=0,
                   items = []), 404


@purchases_bp.get('/command_items')
@login_required
def get_command_items():
    if 'q' not in request.args:
        return '', 400
    command = Order.query.get(int(request.args.get('q')))
    data = list()
    if command:
        for entry in command.entries:
            data.append({
                'id':entry.fk_item_id,
                'text':str(Item.query.get(entry.fk_item_id))
            })
        return jsonify(
            total_count = len(data),
            items = data
        ),200
    return jsonify(
        total_count = 0,
        items = list()
    ),404


@purchases_bp.post('/price')
@login_required
def get_purchase_price():
    data = request.json
    print(data)
    if not data:
        return jsonify(
            message='Demande annulé'
        ), 400
    if 'cmd_id' not in data or 'product' not in data:
        return jsonify(
            text="Demande annulé"
        ), 400
    if data['cmd_id']=='__None':
        return jsonify(
            text="Demande annulé: vous devez fournir une référence commande"
        ), 400
    order = Order.query.get(data['cmd_id'])
    if not order:
        return jsonify(
            text="Commande introuvable"
        ), 404
    if order.is_canceled or order.is_deleted:
        return jsonify(
            text="Commande annulé ou supprimée"
        ),404
    company = UserForCompany.query.filter_by(role="magasiner").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if order.fk_company_id != company:
        return jsonify(
            text="Erreur inattendue"
        ), 404
    for entry in order.entries:
        if entry.fk_item_id == int(data['product']):
            return jsonify(
                price=entry.unit_price,
                quantity = entry.quantity,
                amount=entry.unit_price*entry.quantity,
                sum=float(data['sum'])+float(entry.quantity * entry.unit_price)
            ), 200
    return jsonify(text=f"Article ne se trouve pas dans la commande {Order.query.get(data['cmd_id']).intern_reference}"),404


@purchases_bp.get('/stocks')
@login_required
def stocks():
    return "Stocks"


@purchases_bp.post('/info')
@login_required
def get_info():
    data = request.json
    if 'invoice_id' not in data:
        return '', 400

    if len(data) != 1:
        return '', 400

    invoice = Invoice.query.filter_by(intern_reference = data['invoice_id']).first()
    if not invoice:
        return '', 404
    total=Expense.query.filter_by(fk_invoice_id = invoice.id).all()
    total = sum([t.amount for t in total])
    return jsonify(
                code=invoice.intern_reference,
                montant='{:,.2f}'.format(invoice.total),
                reste='{:,.2f}'.format(invoice.total - total)),200


@purchases_bp.get('/invoices/<int:i_id>/print')
@login_required
def print_invoice(i_id):
    invoice = Invoice.query.filter_by(inv_type='achat').filter_by(id=i_id).first()
    if not invoice:
        return render_template('errors/404.html', blueprint='purchases_bp')
    company = UserForCompany.query.filter_by(role="magasiner").filter_by(fk_user_id=current_user.id).first()
    if not company:
        return render_template('errors/401.html')
    if invoice.fk_company_id != company.fk_company_id:
        return render_template('errors/401.html')
    company = Company.query.get(company.fk_company_id)
    total_letters = num2words(invoice.total, lang='fr') + " dinars algérien"
    virgule = invoice.total - float(int(invoice.total))
    if virgule > 0:
        total_letters += f' et {int(round(virgule, 2))} centimes'
    html = render_template('printouts/printable_template.html',
                           company=company.repr(),
                           object=invoice.repr(),
                           titre="Facture d'achat",
                           total_letters=str.upper(total_letters))

    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'factur d\'achat_{invoice.intern_reference}.pdf',
                      automatic_download=False)

@purchases_bp.get('/receipt/<int:r_id>/print')
@login_required
def print_receipt(r_id):
    receipt = PurchaseReceipt.query.filter_by(id=r_id).first()
    if not receipt:
        return render_template('errors/404.html', blueprint='purchases_bp')
    company = UserForCompany.query.filter_by(role="magasiner").filter_by(fk_user_id=current_user.id).first()
    if not company:
        return render_template('errors/401.html')
    if receipt.fk_company_id != company.fk_company_id:
        return render_template('errors/401.html')
    company = Company.query.get(company.fk_company_id)
    total_letters = num2words(receipt.total, lang='fr')+" dinars algérien"
    virgule = receipt.total - float(int(receipt.total))
    if virgule>0:
        total_letters += f' et {int(round(virgule, 2))} centimes'
    html = render_template('printouts/printable_template.html',
                    company = company.repr(),
                    object=receipt.repr_(),
                    titre="Bon de réception",
                    total_letters=str.upper(total_letters))

    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'bon de réception_{receipt.intern_reference}.pdf',
                      automatic_download=False)


@purchases_bp.get('/order/<int:o_id>/print')
@login_required
def print_order(o_id):
    order = Order.query.filter_by(category='achat').filter_by(id=o_id).first()
    if not order:
        return render_template('errors/404.html', blueprint='purchases_bp')
    company = UserForCompany.query.filter_by(role="magasiner").filter_by(fk_user_id=13).first()
    if not company:
        return render_template('errors/401.html')
    if order.fk_company_id != company.fk_company_id:
        return render_template('errors/401.html')
    company = Company.query.get(company.fk_company_id)
    total_letters = num2words(order.total, lang='fr') + " dinars algérien"
    virgule = order.total - float(int(order.total))
    if virgule > 0:
        total_letters += f' et {int(round(virgule, 2))} centimes'
    html = render_template('printouts/printable_template.html',
                    company = company.repr(),
                    titre="Bon d'achat",
                    object=order.repr(),
                    total_letters=str.upper(total_letters))
    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'bon de achat_{order.intern_reference}.pdf',
                      automatic_download=False)
