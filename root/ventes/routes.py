import datetime

from flask import url_for, redirect, render_template, session, flash
from root import database as db
from flask_login import login_required, current_user
from root.ventes import sales_bp
from root.models import UserForCompany, Quotation, Entry, Item, Order, Invoice, Client, DeliveryNote
from root.ventes.forms import QuotationForm, EntryField, OrderForm
@sales_bp.before_request
def sales_before_request():
    session['role']="Vendeur"


@sales_bp.get('/')
# @login_required
def index():
    if 'endpoint' in session:
        del session['endpoint']
    return render_template('sales/index.html')


@sales_bp.get('/quotations')
# @login_required
def quotations():
    session['endpoint']='sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role=="vendeur").first()
    _quotations = Quotation.query.filter_by(fk_company_id =user_for_company.fk_company_id) \
                                    .filter_by(created_by=current_user.id).filter_by(is_deleted=False) \
                                    .order_by(Quotation.created_at.desc()).all()
    liste = list()
    if _quotations:
        indexe = 1
        for quotation in _quotations:
            _dict = quotation.repr()
            _dict.update({'index':indexe})
            liste.append(_dict)
            indexe += 1
    return render_template("sales/quotations.html", liste = liste)


@sales_bp.get('/quotations/<int:q_id>/delete')
# @login_required
def delete_quotation(q_id):
    session['endpoint'] = 'sales'
    quotation = Quotation.query.get(q_id)
    if not quotation:
        return render_template('errors/404.html', blueprint="sales_bp")

    user_for_company = UserForCompany.query.filter_by(fk_user_id = current_user.id).filter_by(role="vendeur").first()
    if quotation.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="sales_bp")
    for e in quotation.entries:
        if not e.fk_order_id and not e.fk_invoice_id and not e.fk_delivery_note_id:
            db.session.delete(e)
            db.session.commit()
    quotation.is_deleted = True
    db.session.add(quotation)
    db.session.commit()
    flash('Objet Supprimé avec succès','success')
    return redirect(url_for('sales_bp.quotations'))


@sales_bp.get('/quotations/<int:q_id>/get')
# @login_required
def get_quotation(q_id):
    session['endpoint'] = 'sales'
    quotation = Quotation.query.get(q_id)

    if not quotation:
        return render_template('errors/404.html', bluebript="sales_bp")

    user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id).filter_by(role="vendeur").first()
    if quotation.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="sales_bp")

    return render_template("sales/quotation_info.html", quotation=quotation.repr())


@sales_bp.get('/quotations/add')
@sales_bp.post('/quotations/add')
# @login_required
def add_quotation():
    session['endpoint'] = 'sales'
    form = QuotationForm()
    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    clients = Client.query.filter_by(fk_company_id=company)
    if not clients:
        flash("Veuillez d'abord ajouter des clients",'warning')

    if form.validate_on_submit():
        entities = list()
        _q = Quotation()
        sum_amounts=0
        if enumerate(form.entities):
            for _index, entry in enumerate(form.entities):
                if entry.quantity.data:
                    entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    return render_template("sales/new_quotation.html",
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
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.unit_price.data * entry.quantity.data
                    sum_amounts += entry.amount.data
            form.entities.append_entry({
                'label': Item.query.filter_by(is_disabled=False) \
                    .filter_by(fk_company_id=UserForCompany.query.filter_by(role="vendeur") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                'unit_price': 0,
                'quantity': 1,
                'amount': 0
            })
            return render_template('sales/new_quotation.html', form=form, nested=EntryField(), somme=sum_amounts)
        if form.fin.data:
            if enumerate(form.entities):
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.unit_price.data * entry.quantity.data
                    sum_amounts += entry.amount.data
            return render_template('sales/new_quotation.html', form=form, nested=EntryField(), somme=sum_amounts)

        if form.quotation_date.data:
            _q.created_at = form.quotation_date.data
        _q.created_by = current_user.id
        _q.fk_company_id = company
        _q.fk_client_id= form.client.data.id
        _q.total = sum_amounts
        # db.session.add(_q)
        # db.session.commit()
        last_q = Quotation.query.filter_by(fk_company_id = company).order_by(Quotation.created_at.desc()).first()
        print(last_q)
        if last_q:
            last_intern_ref = last_q.intern_reference.split('-')[1].split('/')[0]
            year = last_q.intern_reference.split('-')[1].split('/')[2]
            if year == datetime.datetime.now().date().year :
                _q.intern_reference = "DEV-"+(last_intern_ref+1)+"/"+str(company)+"/"+str(datetime.datetime.now().date().year)
            else:
                _q.intern_reference = "DEV-1/"+str(company)+"/"+str(datetime.datetime.now().date().year)
        else:
            _q.intern_reference = "DEV-1/"+str(company)+"/"+str(datetime.datetime.now().date().year)
        db.session.add(_q)
        db.session.commit()
        for e in entities:
            sum_amounts += e.total_price
            e.fk_quotation_id = _q.id
            db.session.add(e)
            db.session.commit()
        _q.total = sum_amounts
        db.session.add(_q)
        db.session.commit()
        flash('Devis crée avec succès','success')
        # return redirect(url_for('sales_bp.add_quotation'))
        return render_template("sales/new_quotation.html", form=form,
                                somme = _q.total,
                               nested=EntryField(),
                               to_approve=True,
                               to_print=True)
    return render_template("sales/new_quotation.html", form = form, nested=EntryField(), somme = 0)


@sales_bp.get('/quotation/<int:q_id>/approve')
@login_required
def approve_quotation(q_id):
    session['endpoint']='sales'
    quotation = Quotation.query.get(q_id)
    if not quotation:
        return render_template('errors/404.html', blueprint="sales_bp")

    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if quotation.is_deleted or quotation.fk_company_id != company:
        return render_template('errors/404.html', blueprint="sales_bp")

    if quotation.is_approved:
        flash('Devis déjà approuvé','warning')
        return redirect(url_for('sales_bp.quotations'))

    quotation.is_approved=True
    db.session.add(quotation)
    db.session.commit()
    flash(f'Devis {quotation.intern_reference} est approuvé','success')
    return redirect(url_for('sales_bp.quotations'))


@sales_bp.get('/quotations/<int:q_id>/get/order')
@login_required
def quotation_order(q_id):
    session['endpoint']="sales"
    quotation = Quotation.query.get(q_id)
    if not quotation:
        return render_template('errors/404.html', blueprint="sales_bp")

    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if quotation.is_deleted or quotation.fk_company_id != company:
        return render_template('errors/404.html', blueprint="sales_bp")

    entities = quotation.entries
    order = Order()
    last_o = Order.query.filter_by(fk_company_id=company).order_by(Order.created_at.desc()).first()
    if last_o and last_o.intern_reference.split('/')[1] == str(datetime.datetime.now().date().year):
        last_intern_ref = last_o.intern_reference.split('-').split('/')[0]
        order.intern_reference = "BC-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
            datetime.datetime.now().date().year)
    else:
        order.intern_reference = "BC-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
    order.fk_client_id = quotation.fk_client_id
    order.category="vente"
    order.total = quotation.total
    order.fk_quotation_id = quotation.id
    order.created_by = current_user.id
    db.session.add(order)
    db.session.commit()
    for entry in entities:
        # _ = Entry()
        entry.fk_order_id = order.id
        # _.fk_item_id = entry.fk_item_id
        # _.quantity = entry.quantity
        # _.total_price = entry.total_price
        # _.unit_price = entry.unit_price
        db.session.add(entry)
        db.session.commit()
    flash(f'Commande {order.intern_reference} ajoutée', 'success')
    return redirect(url_for('sales_bp.quotations'))


@sales_bp.get('/quotations/<int:q_id>/get/invoice')
@login_required
def quotation_invoice(q_id):
    session['endpoint']="sales"
    quotation = Quotation.query.get(q_id)
    if not quotation:
        return render_template('errors/404.html', blueprint="sales_bp")

    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if quotation.is_deleted or quotation.fk_company_id != company:
        return render_template('errors/404.html', blueprint="sales_bp")

    entities = quotation.entries
    invoice = Invoice()
    last_o = Order.query.filter_by(fk_company_id=company).order_by(Order.created_at.desc()).first()
    if last_o and last_o.intern_reference.split('/')[1] == str(datetime.datetime.now().date().year):
        last_intern_ref = last_o.intern_reference.split('-').split('/')[0]
        invoice.intern_reference = "BL-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
            datetime.datetime.now().date().year)
    else:
        invoice.intern_reference = "BL-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
    invoice.fk_client_id = quotation.fk_client_id
    invoice.total = quotation.total
    invoice.fk_quotation_id = quotation.id
    invoice.created_by = current_user.id
    db.session.add(invoice)
    db.session.commit()
    for entry in entities:
        entry.fk_invoice_id = invoice.id
        # entry.fk_item_id = entry.fk_item_id
        # entry.quantity = entry.quantity
        # entry.total_price = entry.total_price
        # entry.unit_price = entry.unit_price
        db.session.add(entry)
        db.session.commit()
    flash(f'Facture {invoice.intern_reference} ajoutée', 'success')
    return redirect(url_for('sales_bp.quotations'))


# @sales_bp.get('/sales/delivery/<int:bl_id>/get')
# @login_required
# def get_delivery_note(bl_id):
#     return render_template("sales/delivery_note.html")


@sales_bp.get('/sales/delivery/<int:bl_id>/approve')
@login_required
def approve_delivery(bl_id):
    session['endpoint']="sales"
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


# @sales_bp.get('/sales/delivery')
# @login_required
# def delivery_notes():
#     return render_template('sales/deliveries.html')

@sales_bp.get('/orders/add')
@sales_bp.post('/orders/add')
@login_required
def add_order():
    session['endpoint'] = 'sales'
    form = OrderForm()
    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    clients = Client.query.filter_by(fk_company_id=company)
    if not clients:
        flash("Veuillez d'abord ajouter des clients",'warning')

    if form.validate_on_submit():
        entities = list()
        _q = Order()
        sum_amounts=0
        if enumerate(form.entities):
            for _index, entry in enumerate(form.entities):
                if entry.quantity.data:
                    entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    return render_template("sales/new_order.html",
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
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.unit_price.data * entry.quantity.data
                    sum_amounts += entry.amount.data
            form.entities.append_entry({
                'label': Item.query.filter_by(is_disabled=False) \
                    .filter_by(fk_company_id=UserForCompany.query.filter_by(role="vendeur") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                'unit_price': 0,
                'quantity': 1,
                'amount': 0
            })
            return render_template('sales/new_order.html', form=form, nested=EntryField(), somme=sum_amounts)
        if form.fin.data:
            if enumerate(form.entities):
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.unit_price.data * entry.quantity.data
                    sum_amounts += entry.amount.data
            return render_template('sales/new_order.html', form=form, nested=EntryField(), somme=sum_amounts)

        if form.quotation_date.data:
            _q.created_at = form.quotation_date.data
        _q.created_by = current_user.id
        _q.fk_company_id = company
        _q.fk_client_id= form.client.data.id
        _q.total = sum_amounts
        # db.session.add(_q)
        # db.session.commit()
        last_q = Quotation.query.filter_by(fk_company_id = company).order_by(Quotation.created_at.desc()).first()
        print(last_q)
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
        for e in entities:
            sum_amounts += e.total_price
            e.fk_quotation_id = _q.id
            db.session.add(e)
            db.session.commit()
        _q.total = sum_amounts
        db.session.add(_q)
        db.session.commit()
        flash('Commande crée avec succès','success')
        return render_template("sales/new_order.html", form=form,
                                somme = _q.total,
                               nested=EntryField(),
                               to_approve=True,
                               to_print=True)
    return render_template("sales/new_order.html", form = form, nested=EntryField(), somme = 0)



@sales_bp.get('/orders')
@login_required
def orders():
    session['endpoint']='sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role=="vendeur").first()
    _orders = Order.query.filter_by(fk_company_id =user_for_company.fk_company_id) \
                                    .filter_by(created_by=current_user.id).filter_by(is_deleted=False) \
                                    .order_by(Order.created_at.desc()).all()
    liste = list()
    if _orders:
        indexe = 1
        for quotation in _orders:
            _dict = quotation.repr()
            _dict.update({'index':indexe})
            liste.append(_dict)
            indexe += 1
    return render_template("sales/orders.html", liste = liste)


@sales_bp.get('/invoices')
@login_required
def invoices():
    session['endpoint']='sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role=="vendeur").first()
    _orders = Order.query.filter_by(fk_company_id =user_for_company.fk_company_id) \
                                    .filter_by(created_by=current_user.id).filter_by(is_deleted=False) \
                                    .order_by(Order.created_at.desc()).all()
    liste = list()
    if _orders:
        indexe = 1
        for quotation in _orders:
            _dict = quotation.repr()
            _dict.update({'index':indexe})
            liste.append(_dict)
            indexe += 1
    return render_template("sales/invoices.html", liste = liste)

