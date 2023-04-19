import datetime

from flask import url_for, redirect, render_template, session, flash, request, jsonify
from root import database as db
from flask_login import login_required, current_user, logout_user
from root.ventes import sales_bp
from root.models import UserForCompany, Quotation, Entry, Item, Order, Invoice, Client, DeliveryNote
from root.models import ExitVoucher, Stock, Company, Pay, Contact, Supplier
from root.ventes.forms import QuotationForm, EntryField, OrderForm, ExitVoucherEntryField, ExitVoucherForm
from root.ventes.forms import PaiementForm, ClientForm
from sqlalchemy import or_, func
from flask_weasyprint import HTML, render_pdf
from num2words import num2words


@sales_bp.before_request
def sales_before_request():
    session['role']="Vendeur"
    if current_user.is_authenticated:
        user = UserForCompany.query.filter_by(role='vendeur').filter_by(fk_user_id = current_user.id).first()
        if not user:
            return render_template('errors/401.html')
        print(f'{current_user.full_name} is log in ')



@sales_bp.get('/')
@login_required
def index():
    if 'endpoint' in session:
        del session['endpoint']
    
    return render_template('sales/index.html')


@sales_bp.get('/quotations')
@login_required
def quotations():
    session['endpoint']='sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role=="vendeur").first()
    _quotations = Quotation.query.filter_by(fk_company_id =user_for_company.fk_company_id) \
                                    .filter_by(created_by=current_user.id).filter_by(is_deleted=False) \
                                    .order_by(Quotation.created_at.desc()).all()
    items = Item.query.filter_by(fk_company_id=user_for_company.fk_company_id).all()
    for item in items:
        if item.stock_quantity is None:
            flash('Certain produit n\'ont pas de stock','danger')
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
@login_required
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




# @sales_bp.get('/quotations/<int:q_id>/get')
# @login_required
# def get_quotation(q_id):
#     session['endpoint'] = 'sales'
#     quotation = Quotation.query.get(q_id)
#
#     if not quotation:
#         return render_template('errors/404.html', bluebript="sales_bp")
#
#     user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id).filter_by(role="vendeur").first()
#     if quotation.fk_company_id != user_for_company.fk_company_id:
#         return render_template('errors/404.html', blueprint="sales_bp")
#
#     return render_template("sales/quotation_info.html", quotation=quotation.repr())



@sales_bp.get('/quotations/<int:q_id>/print')
@login_required
def get_quotation(q_id):
    quote = Quotation.query.filter_by(id=q_id).first()
    if not quote:
        return render_template('errors/404.html', blueprint='sales_bp')
    company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id=current_user.id).first()
    if not company:
        return render_template('errors/401.html')
    if quote.fk_company_id != company.fk_company_id:
        return render_template('errors/401.html')
    company = Company.query.get(company.fk_company_id)
    total_letters = num2words(quote.total, lang='fr') + " dinars algérien"
    virgule = quote.total - float(int(quote.total))
    if virgule > 0:
        total_letters += f' et {int(round(virgule, 2))} centimes'
    html = render_template('printouts/printable_template.html',
                           company=company.repr(),
                           object=quote.repr(),
                           titre="Devis",
                           total_letters=str.upper(total_letters))

    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'devis_{quote.intern_reference}.pdf',
                      automatic_download=False)


@sales_bp.get('/quotations/add')
@sales_bp.post('/quotations/add')
@login_required
def add_quotation():
    session['endpoint'] = 'sales'
    form = QuotationForm()
    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    _clients = Client.query.filter_by(fk_company_id=company).all()
    items = Item.query.filter_by(fk_company_id=company).all()
    for item in items:
        if item.stock_quantity is None:
            flash('Certain produit n\'ont pas de stock', 'danger')
            return redirect(url_for('sales_bp.quotations'))
    if not _clients:
        flash("Veuillez d'abord ajouter des clients",'warning')
    if form.validate_on_submit():
        entities = list()
        last_q = Quotation.query.filter_by(fk_company_id=company).order_by(Quotation.id.desc()).first()
        _q = Quotation()
        _q.created_by = current_user.id
        sum_amounts=0
        if enumerate(form.entities):
            for _index, entry in enumerate(form.entities):
                entry.unit.data = Item.query.get(entry.item.data.id).unit
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

        # if form.quotation_date.data:
        #     _q.created_at = form.quotation_date.data
        _q.created_by = current_user.id
        _q.fk_company_id = company
        _q.fk_client_id= form.client.data.id
        _q.total = sum_amounts
        _q.intern_reference = "DEV-1/" + str(datetime.datetime.now().date().year)
        if last_q:
            last_intern_ref = int(last_q.intern_reference.split('-')[1].split('/')[0])
            year = int(last_q.intern_reference.split('-')[1].split('/')[1])
            if year == datetime.datetime.now().date().year :
                _q.intern_reference = "DEV-"+str(last_intern_ref+1)+"/"+str(datetime.datetime.now().date().year)
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
    for entry in quotation.entries:
        item = Item.query.get(entry.fk_item_id)
        if item.stock_quantity < entry.quantity:
            flash(f'Le stock du produit {item.label} est insuffisant pour ce devis','danger')
            return redirect(url_for('sales_bp.quotations'))
    quotation.is_approved=True
    db.session.add(quotation)
    db.session.commit()
    flash(f'Devis {quotation.intern_reference} est approuvé','success')
    return redirect(url_for('sales_bp.quotations'))


@sales_bp.get('/order/<int:o_id>/delete')
@login_required
def delete_order(o_id):
    company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id = current_user.id).first()
    _order = Order.query.get(o_id)
    if not _order:
        return render_template('errors/404.html', blueprint="sales_bp")


    if _order.fk_company_id != company.fk_company_id:
        return render_template('errors/404.html', blueprint='sales_bp')

    dl = DeliveryNote.query.filter_by(is_validated = True).filter_by(fk_order_id = _order.id).first()
    if dl:
        flash('Impossible de supprimer cette commande: Commande déjà livrée','danger')
        return redirect(url_for('sales_bp.orders'))

    ev = ExitVoucher.query.filter_by(fk_order_id = o_id).first()
    if ev:
        flash('Impossible de supprimer cette commande: un produit de cette commande est sortie de stock', 'danger')
        return redirect(url_for('sales_bp.orders'))


    for entry in _order.entries:
        '''
        entry.fk_exit_voucher_id is None \
                and 
        '''

        item = Item.query.get(entry.fk_item_id)
        print(f'{item.stock_quantity}, entry = {entry.quantity}')
        item.stock_quantity += entry.quantity
        db.session.add(item)
        db.session.commit()
        if entry.fk_invoice_id == None \
                and entry.fk_quotation_id == None :
            db.session.delete(entry)
            db.session.commit()
    _order.is_deleted = True
    db.session.add(_order)
    db.session.commit()
    flash(f'Object code = {_order.intern_reference} a été supprimé avec succès','success')
    return redirect(url_for('sales_bp.orders'))



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
    if not quotation.is_approved:
        flash('Vous devez d\'abord approuver ce devis avant cette opération','warning')
        return redirect(url_for('sales_bp.quotations'))
    _ = Order.query.filter_by(is_deleted = False).filter_by(fk_quotation_id = quotation.id).first()

    if _:
        flash(f'Devis {quotation.intern_reference} déjà approuver et convertie en commande','warning')
        return redirect(url_for('sales_bp.quotations'))

    for entry in quotation.entries:
        item = Item.query.get(entry.fk_item_id)
        if item.stock_quantity < entry.quantity:
            flash(f'Le stock du produit {item.label} est insuffisant pour ce devis','danger')
            return redirect(url_for('sales_bp.quotations'))

    last_o = Order.query.filter_by(fk_company_id=company).order_by(Order.id.desc()).first()
    order = Order()
    # order.intern_reference = "BC-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
    order.intern_reference = "BC-1/" + str(datetime.datetime.now().date().year)
    if last_o:
        last_intern_ref = int(last_o.intern_reference.split('-')[1].split('/')[0])
        year = int(last_o.intern_reference.split('-')[1].split('/')[1])
        if year == datetime.datetime.now().date().year:
            order.intern_reference = "BC-" + str(last_intern_ref + 1) + "/" + str(datetime.datetime.now().date().year)

    order.fk_client_id = quotation.fk_client_id
    order.category="vente"
    order.total = quotation.total
    order.fk_quotation_id = quotation.id
    order.fk_company_id = company
    order.created_by = current_user.id
    db.session.add(order)
    db.session.commit()
    for entry in quotation.entries:
        e = entry
        item = Item.query.get(entry.fk_item_id)
        e.total_price = entry.total_price
        e.unit_price = item.sale_price
        entry.fk_quotation_id = quotation.id
        if entry.quantity > item.stock_quantity:
            flash(
                f"La quantity du {Item.query.get(entry.item.data.id).label} est suppérieur à la quantity commandée",
                "warning")
            return redirect(url_for('sales_bp.quotations'))
        e.quantity=entry.quantity
        # e.delivered_quantity = entry.quantity
        e.in_stock = item.stock_quantity
        e.fk_order_id = order.id
        item.stock_quantity -= entry.quantity
        db.session.add(e)
        db.session.commit()
        db.session.add(item)
        db.session.commit()
        db.session.add(entry)
        db.session.commit()
    flash(f'Commande {order.intern_reference} ajoutée', 'success')
    return redirect(url_for('sales_bp.quotations'))


@sales_bp.get('/quotations/<int:o_id>/get/invoice')
@login_required
def order_invoice(o_id):
    session['endpoint']="sales"
    order = Order.query.filter_by(id=o_id).first()
    if not order:
        return render_template('errors/404.html', blueprint="sales_bp")

    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if order.is_deleted or order.fk_company_id != company:
        return render_template('errors/404.html', blueprint="sales_bp")

    if order.is_canceled == None:
        print(order.repr())
        flash('Vous devez d\'abord approuver ce devis avant cette opération','warning')
        return redirect(url_for('sales_bp.orders'))

    invoice = Invoice.query.filter_by(fk_order_id = order.id).first()
    if invoice:
        flash(f'Commande {order.intern_reference} déjà facturée','warning')
        return redirect(url_for('sales_bp.orders'))

    entities = order.entries
    last_o = Invoice.query.filter_by(fk_company_id=company).order_by(Invoice.id.desc()).first()
    invoice = Invoice()
    invoice.inv_type="vente"
    invoice.fk_order_id = order.id
    invoice.fk_company_id = company
    invoice.intern_reference = "FAC-1/" + str(datetime.datetime.now().date().year)
    # invoice.intern_reference = "FAC-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
    if last_o:
        last_intern_ref = int(last_o.intern_reference.split('-')[1].split('/')[0])
        year = int(last_o.intern_reference.split('/')[1])
        if year == datetime.datetime.now().date().year:
            invoice.intern_reference = "FAC-" + str(last_intern_ref + 1) + "/" + str(
            datetime.datetime.now().date().year)

    invoice.fk_client_id = order.fk_client_id
    invoice.total = order.total
    invoice.created_by = current_user.id
    db.session.add(invoice)
    db.session.commit()
    order.is_canceled = False
    db.session.add(order)
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
    return redirect(url_for('sales_bp.orders'))


@sales_bp.get('/sales/delivery/<int:bl_id>/approve')
@login_required
def approve_delivery(bl_id):
    session['endpoint']="sales"
    d_note = DeliveryNote.query.get(bl_id)
    if not d_note:
        return render_template('errors/404.html', blueprint="sales_bp")
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


@sales_bp.get('/orders/add')
@sales_bp.post('/orders/add')
@login_required
def add_order():
    session['endpoint'] = 'sales'
    form = OrderForm()
    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    _clients = Client.query.filter_by(is_deleted = False).filter_by(fk_company_id=company).all()
    items = Item.query.filter_by(fk_company_id=company).all()
    for item in items:
        if item.stock_quantity is None:
            flash('Certain produit n\'ont pas de stock', 'danger')
            return redirect(url_for('sales_bp.orders'))
    if not _clients:
        flash("Veuillez d'abord ajouter des clients",'warning')

    if form.validate_on_submit():
        entities = list()
        last_q = Order.query.filter_by(fk_company_id = company).order_by(Order.created_at.desc()).first()
        _q = Order()
        _q.category = "vente"
        sum_amounts=0
        if enumerate(form.entities):
            for _index, entry in enumerate(form.entities):
                entry.unit.data = Item.query.get(entry.item.data.id).unit
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
                item = Item.query.get(entry.item.data.id)
                if item.stock_quantity < entry.quantity.data or entry.quantity.data >= item.stock_sec:
                    flash(f'Le stock du produit {item.label} est insuffisant pour cette commande', 'danger')
                    # return redirect(url_for('sales_bp.quotations'))
                    return render_template("sales/new_order.html",
                                           form=form, nested=EntryField(),
                                           somme=sum_amounts)
                _.in_stock = entry.item.data.stock_quantity
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

        _q.created_by = current_user.id
        _q.fk_company_id = company
        _q.fk_client_id= form.client.data.id
        _q.total = sum_amounts
        # _q.intern_reference = "BC-1/" + str(company) + "/" + str(datetime.datetime.now().date().year)
        _q.intern_reference = "BC-1/" + str(datetime.datetime.now().date().year)
        if last_q:
            last_intern_ref = int(last_q.intern_reference.split('-')[1].split('/')[0])
            year = int(last_q.intern_reference.split('-')[1].split('/')[1])

            _q.intern_reference = "BC-1/" + str(datetime.datetime.now().date().year)
            if year == datetime.datetime.now().date().year :
                _q.intern_reference = "BC-"+str(last_intern_ref+1)+"/"+str(datetime.datetime.now().date().year)
        db.session.add(_q)
        db.session.commit()
        for e in entities:
            sum_amounts += e.total_price
            e.fk_order_id = _q.id
            
            item = Item.query.get(e.fk_item_id)
            e.in_stock = item.stock_quantity
            db.session.add(e)
            db.session.commit()
            item.stock_quantity -= e.quantity
            db.session.add(item)
            db.session.commit()
        _q.total = sum_amounts
        db.session.add(_q)
        db.session.commit()
        flash('Commande crée avec succès','success')
        return render_template("sales/new_order.html", form=form,
                                somme = _q.total,
                               nested=EntryField(),
                               to_approve=True,
                               doc = _q.id,
                               to_print=True)
    return render_template("sales/new_order.html", form = form, nested=EntryField(), somme = 0)


@sales_bp.get('/orders')
@login_required
def orders():
    session['endpoint']='sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role=="vendeur").first()
    _orders = Order.query.filter_by(category='vente').filter_by(fk_company_id =user_for_company.fk_company_id).filter_by(is_deleted=False) \
                                    .order_by(Order.id.desc()).all()
    liste = list()
    if _orders:
        indexe = 1
        for quotation in _orders:
            _dict = quotation.repr()
            _dict.update({'index':indexe})
            liste.append(_dict)
            indexe += 1
    return render_template("sales/orders.html", liste = liste)

from root.models import User
@sales_bp.get('/invoices')
@sales_bp.post('/invoices')
@login_required
def invoices():
    session['endpoint']='sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role=="vendeur").first()
    """\.filter_by(is_deleted=False)"""
    _orders = Invoice.query.filter_by(inv_type="vente").filter_by(fk_company_id =user_for_company.fk_company_id) \
                                    .filter_by(created_by=current_user.id) \
                                    .order_by(Invoice.id.desc()).all()
    liste = list()
    form = PaiementForm()
    if _orders:
        indexe = 1
        for quotation in _orders:
            _dict = quotation.repr()
            _dict.update({'index':indexe})
            liste.append(_dict)
            indexe += 1
    if form.validate_on_submit():
        code = request.form.get('code')
        invoice = Invoice.query.filter_by(intern_reference=code).first()
        if not invoice:
            flash('Facture introuvable', 'danger')
            return redirect(url_for('sales_bp.invoices'))
        pay = Pay()
        pay.fk_company_id = user_for_company.fk_company_id
        pay.fk_invoice_id = invoice.id
        pay.created_by = current_user.id
        pay.amount = float(form.amount.data)
        pay.is_in_cash = True
        pay.label = f"paiement de la facture  {invoice.intern_reference}"
        pay.pay_information=f"Paiement d'une facture d'où de code = {invoice.intern_reference} générée par {User.query.get(invoice.created_by).full_name} avec total de {invoice.total}, le {invoice.created_at.date()}"
        db.session.add(pay)
        db.session.commit()
        flash(f'{form.data.get("code")} a été payée','success')
        return redirect(url_for('sales_bp.invoices'))
    return render_template("sales/invoices.html", form = form, liste = liste)


@sales_bp.get('/commands')
@login_required
def get_commands():
    company = UserForCompany.query.filter_by(role="vendeur") \
                                    .filter_by(fk_user_id=current_user.id).first().fk_company_id
    commands = Order.query.join(Client, Client.id == Order.fk_client_id).filter(Client.is_deleted == False) \
        .filter(Order.is_deleted == False) \
        .filter(Order.is_canceled == None) \
        .filter(Order.category == 'vente').filter(Order.fk_company_id == company)
    if "search" in request.args:
        commands = commands.filter(or_(
            Order.intern_reference.like(func.lower(f'%{request.args["search"]}%')),
            Client.full_name.like(func.lower(f'%{request.args["search"]}%'))
        )).order_by(Order.created_at.desc())
    data = list()
    if commands.all():
        for command in commands.all():
            b = Client.query.get(command.fk_client_id) if command.fk_client_id else None

            data.append({
                'id': command.id,
                'title':'Bon de commande',
                'client': str.upper(Client.query.get(command.fk_client_id).full_name),
                'code':command.intern_reference,
                'date':str(command.created_at.date())
            })
            # else:
            #     data.append({
            #         'id': command.id,
            #         'text': str.upper(Supplier.query.get(
            #             command.fk_supplier_id).full_name) + ", " + command.intern_reference + ' ,Le ' + str(
            #             command.created_at.date())
            #     })
        return jsonify(total_count=len(data),
                       items = data), 200
    return jsonify(total_count=0,
                   items = []), 404



@sales_bp.get('/invoices/<int:i_id>/print')
@login_required
def print_invoice(i_id):
    invoice = Invoice.query.filter_by(inv_type='vente').filter_by(id=i_id).first()
    if not invoice:
        return render_template('errors/404.html', blueprint='sales_bp')
    company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id=current_user.id).first()
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
                           titre="Facture",
                           total_letters=str.upper(total_letters))

    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'facture_{invoice.intern_reference}.pdf',
                      automatic_download=False)


@sales_bp.get('/delivery/<int:bl_id>/print')
@login_required
def print_delivery_note(bl_id):
    company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id=current_user.id).first()
    if not company:
        return render_template('errors/401.html')
    delivery_note = DeliveryNote.query.join(Order, Order.id==DeliveryNote.fk_order_id) \
                                        .filter(Order.fk_company_id==company.fk_company_id) \
                                            .filter(DeliveryNote.is_canceled == None) \
                                                .filter(DeliveryNote.id==bl_id).first()
    print(delivery_note)
    # delivery_note = DeliveryNote.query.get(bl_id)
    if not delivery_note:
        return render_template('errors/404.html', blueprint='sales_bp')
    _order = Order.query.get(delivery_note.fk_order_id)
    if _order.fk_company_id != company.fk_company_id:
        logout_user()
        return render_template('errors/401.html')
    company = Company.query.get(company.fk_company_id)
    total_letters = num2words(_order.total, lang='fr') + " dinars algérien"
    virgule = _order.total - float(int(_order.total))
    if virgule > 0:
        total_letters += f' et {int(round(virgule, 2))} centimes'
    html = render_template('printouts/printable_template.html',
                           company=company.repr(),
                           object=delivery_note.repr(),
                           titre="Bon de livraison",
                           total_letters=str.upper(total_letters)
                           )
    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'{delivery_note.intern_reference}.pdf',
                      automatic_download=False)


@sales_bp.post('/item_unit')
@login_required
def get_unit():
    data = request.json
    item = Item.query.get(int(data['item_id']))
    if not item:
        return '',404
    return jsonify(unit=item.unit, price = item.sale_price if item.sale_price else 0),200


@sales_bp.post('/price')
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
    company = UserForCompany.query.filter_by(role="vendeurf").filter_by(fk_user_id=current_user.id).first().fk_company_id
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


@sales_bp.get('/command_items')
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


@sales_bp.get('/exit_voucher/add')
@sales_bp.post('/exit_voucher/add')
@login_required
def add_exit_voucher():#Créer un bon de livraison
    session['endpoint']="stocks"
    form = ExitVoucherForm()
    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if form.validate_on_submit():
        entities = list()
        last_q = ExitVoucher.query.filter_by(fk_company_id=company).order_by(ExitVoucher.id.desc()).first()
        _q = ExitVoucher()
        # sum_amounts = 0
        if enumerate(form.entities):
            for _index, entry in enumerate(form.entities):
                # if entry.quantity.data:
                #     entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    # sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    return render_template("sales/add_exit_voucher.html",
                                           form=form, nested=ExitVoucherEntryField(),
                                           # somme=sum_amounts
                                           )
                _ = Entry()
                _.fk_item_id = entry.item.data.id
                _.in_stock = entry.item.data.stock_quantitys
                _.quantity = entry.quantity.data
                entities.append(_)
        if form.add.data:
            form.entities.append_entry({
                'item': Item.query.filter_by(is_disabled=False) \
                    .filter_by(fk_company_id=UserForCompany.query.filter_by(role="vendeur") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                'quantity': 1,
            })
            return render_template('sales/add_exit_voucher.html', form=form, nested=ExitVoucherEntryField(),
                                   )
        _q.created_by = current_user.id
        _q.intern_reference = "BS-1/" + str(datetime.datetime.now().date().year)
        if last_q:
            last_intern_ref = int(last_q.intern_reference.split('-')[1].split('/')[0])
            year = int(last_q.intern_reference.split('-')[1].split('/')[1])
            if year == datetime.datetime.now().date().year:
                _q.intern_reference = "BS-" + str(last_intern_ref + 1) + "/" + str(datetime.datetime.now().date().year)
        for e in entities:
            e.fk_exit_voucher_id = _q.id
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
        db.session.add(_q)
        db.session.commit()
        flash('Bon de sortie crée avec succès', 'success')
        return render_template("sales/add_exit_voucher.html", form=form,
                               nested=ExitVoucherEntryField(),
                               to_approve=True,
                               to_print=True)
    return render_template("sales/add_exit_voucher.html", form=form, nested=ExitVoucherEntryField())


@sales_bp.get('/exit_voucher/all')
@login_required
def exit_vouchers():#Bon de livraison
    session['endpoint']='stocks'
    company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id=current_user.id).first()
    if not company:
        return render_template('errors/401.html')
    exit_vouchers_1 = ExitVoucher.query.join(DeliveryNote, DeliveryNote.id == ExitVoucher.fk_delivery_note_id) \
                                        .join(Order, Order.id == DeliveryNote.fk_order_id) \
                                        .filter(Order.fk_company_id == company.fk_company_id).all()
    exit_vouchers_2 = ExitVoucher.query.join(Order, Order.id == ExitVoucher.fk_order_id) \
                                        .filter(Order.fk_company_id == company.fk_company_id).all()
    _f_liste = exit_vouchers_1 + exit_vouchers_2
    liste =  list()
    indexe = 1
    if _f_liste:
        for obj in _f_liste:
            _dict = obj.repr()
            _dict.update({
                'indexe':indexe
            })
            liste.append(_dict)
            indexe += 1
    return render_template('sales/exit_voucher.html', liste = liste)


@sales_bp.get('/deliveries')
@login_required
def deliveries():
    session['endpoint'] = 'sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role == "vendeur").first()
    # _deliveries = DeliveryNote.query.filter_by(fk_company_id=user_for_company.fk_company_id) \
    #     .order_by(Order.created_at.desc()).all()
    _deliveries = DeliveryNote.query.join(Order, Order.id == DeliveryNote.fk_order_id) \
        .filter(Order.fk_company_id == user_for_company.fk_company_id).order_by(Order.created_at.desc()) \
        .filter(DeliveryNote.created_by == current_user.id) \
        .all()
    liste = list()
    if _deliveries:
        indexe = 1
        for delivery in _deliveries:
            _dict = delivery.repr()
            _dict.update({'index': indexe})
            liste.append(_dict)
            indexe += 1
    return render_template("sales/deliveries.html", liste=liste)


@sales_bp.get('/order/<int:o_id>/print')
@login_required
def print_order(o_id):
    order = Order.query.filter_by(is_deleted = False).filter_by(category='vente').filter_by(id=o_id).first()
    if not order:
        return render_template('errors/404.html', blueprint='sales_bp')
    company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id=current_user.id).first()
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
                    titre="Bon de commande",
                    object=order.repr(),
                    total_letters=str.upper(total_letters))
    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'BC_{order.intern_reference}.pdf',
                      automatic_download=False)



@sales_bp.post('/info')
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
    total=Pay.query.filter_by(fk_invoice_id = invoice.id).all()
    total = sum([t.amount for t in total])
    return jsonify(
                code=invoice.intern_reference,
                montant='{:,.2f}'.format(invoice.total),
                reste='{:,.2f}'.format(invoice.total - total)),200


@sales_bp.get('/clients')
@login_required
def clients():
    user_for_company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id=current_user.id).first()
    _clients = Client.query.filter_by(is_deleted = False).filter_by(fk_company_id=user_for_company.fk_company_id).all()
    liste = list()
    if _clients:
        _index = 1
        for client in _clients:
            _dict = client.repr()
            _dict.update({
                'indexe':_index
            })
            liste.append(_dict)
            _index+=1
    return render_template('sales/clients.html', liste=liste)


@sales_bp.get('/clients/add')
@sales_bp.post('/clients/add')
@login_required
def add_client():
    session['endpoint']='sales'
    user_for_company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id=current_user.id).first()
    if not user_for_company:
        return render_template('errors/404.html', blueprint="sales_bp")
    form  = ClientForm()
    if form.validate_on_submit():
        client = Client()
        client.fk_company_id = user_for_company.fk_company_id
        client.full_name = form.full_name.data
        client.category = form.category.data
        db.session.add(client)
        db.session.commit()
        contact = Contact()
        contact.key="telephone"
        contact.value=form.contacts.data
        contact.fk_client_id = client.id
        db.session.add(contact)
        db.session.commit()
        flash('Client Ajouté','success')
        return redirect(url_for('sales_bp.add_client'))
    return render_template('sales/add_client.html', form = form)

# from flask import abort
# @sales_bp.post('/employees/get')
# @login_required
# def get_user():
#     session['endpoint'] = 'clients'
#
#     data = request.json
#     user = User.query.get(int(data['user_id']))
#     if not user:
#         abort(404)
#     company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id = current_user.id).first()
#     user_company = UserForCompany.query.filter_by(fk_user_id=user.id)
#     if company.fk_company_id != user_company.first().fk_company_id:
#         abort(404)
#     user_company = user_company.filter_by(fk_company_id=company.id).first()
#
#     _dict = User.query.get(user.id).repr(['location','locations'])
#     if user.fk_store_id:
#         return jsonify(message=f"<h4 class='h4 fw-bold'>{user.full_name}</h4> \
#                                 <span class='fw-bold mb-3'>Pseudonyme: </span>{user.username} <br> \
#                                 <span class='fw-bold mb-3'>Rôle: </span>{user_company.role if user_company is not None else '/'} <br> \
#                                 <span class='fw-bold mb-3'>Lieu(x) de travail: </span><br>" + _dict['location']), 200
#     return jsonify(message = f"<h4 class='h4 fw-bold'>{user.full_name}</h4> \
#                         <span class='fw-bold mb-3'>Pseudonyme: </span>{user.username} <br> \
#                         <span class='fw-bold mb-3'>Rôle: </span>{user_company.role if user_company is not None else '/'} <br> \
#                         <span class='fw-bold mb-3'>Lieu(x) de travail: </span><br>"+'<br>'.join(_dict['locations'])), 200


@sales_bp.get('/clients/<int:client_id>/edit')
@sales_bp.post('/clients/<int:client_id>/edit')
@login_required
def edit_client(client_id):
    session['endpoint'] = 'sales'
    form = ClientForm()
    _client = Client.query.get(client_id)
    if not _client:
        return render_template('errors/404.html', blueprint="sales_bp")
    if request.method=="GET":
        form = ClientForm(
            full_name=_client.full_name,
            category=_client.category,
            contacts=Contact.query.filter_by(fk_client_id = _client.id).first().value if Contact.query.filter_by(fk_client_id = _client.id).first() else ''
        )

    if form.validate_on_submit():
        _client.full_name = form.full_name.data
        _client.category = form.category.data
        contact = Contact.query.filter_by(fk_client_id=_client.id).filter_by(value=form.contacts.data).first()
        if not contact:
            contact = Contact()
        contact.key = "téléphone"
        contact.value = form.contacts.data
        contact.fk_client_id = _client.id
        db.session.add(contact)
        db.session.commit()
        flash('Objet modifié avec succès','success')
        return redirect(url_for('sales_bp.clients'))
    return render_template('sales/add_client.html', form = form)


@sales_bp.get('/client/<int:client_id>/delete')
@login_required
def delete_client(client_id):
    session['endpoint'] = 'sales'
    _client = Client.query.get(client_id)
    if not _client:
        return render_template('errors/404.html', blueprint='sales_bp')
    if not _client.orders and not _client.quotations and not _client.invoices:
        db.session.delete(_client)
        db.session.commit()
        return redirect(url_for('sales_bp.clients'))

    _client.is_deleted = True
    db.session.add(_client)
    db.session.commit()
    flash('Objet supprimé avec succès','success')
    return redirect(url_for("sales_bp.clients"))


@sales_bp.get('/order/<int:o_id>/approve')
@login_required
def approve_order(o_id):
    session['endpoint']='sales'
    order = Order.query.get(o_id)
    if not order:
        return render_template('errors/404.html', blueprint="sales_bp")

    company = UserForCompany.query.filter_by(role="vendeur") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if order.is_deleted or order.fk_company_id != company:
        return render_template('errors/404.html', blueprint="sales_bp")

    if order.is_canceled:
        flash('Commande déjà approuvée','warning')
        return redirect(url_for('sales_bp.orders'))
    for entry in order.entries:
        item = Item.query.get(entry.fk_item_id)
        if item.stock_quantity < entry.quantity:
            flash(f'Le stock du produit {item.label} est insuffisant pour cette commande','danger')
            return redirect(url_for('sales_bp.orders'))
    order.is_canceled=False
    db.session.add(order)
    db.session.commit()
    flash(f'Commande {order.intern_reference} est approuvée','success')
    return redirect(url_for('sales_bp.orders'))


@sales_bp.get('/sales/<int:o_id>/delivery')
@login_required
def order_delivery(o_id):
    cmd=Order.query.get(o_id)
    if not cmd:
        return render_template('errors/404.html', blueprint="sales_bp")

    if cmd.is_deleted:
        return render_template('errors/404.html', blueprint="sales_bp")

    company = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id = current_user.id).first().fk_company_id
    if company != cmd.fk_company_id:
        return render_template('errors/404.html', blueprint="sales_bp")

    if cmd.is_canceled != None and cmd.is_canceled == True:
        flash('commande annulé impossible de générer le bon de livraison','warning')
        return redirect(url_for('sales_bp.orders'))
    if cmd.is_delivered and cmd.is_delivered==True:
        flash('Bon de commande déjà généré','warning')
        return redirect(url_for('sales_bp.orders'))

    dl = DeliveryNote()
    last_d = DeliveryNote.query.join(Order, Order.id == DeliveryNote.fk_order_id) \
                                    .filter(Order.fk_company_id == company) \
                                        .order_by(DeliveryNote.id.desc()).first()

    dl.intern_reference = "BL-1/"+str(datetime.datetime.now().year)
    if last_d:
        last_reference = int(last_d.intern_reference.split('-')[1].split('/')[0])
        year = int(last_d.intern_reference.split('-')[1].split('/')[1])
        if year == datetime.datetime.now().year:
            dl.intern_reference = "BL-"+str(last_reference+1)+"/"+ str(datetime.datetime.now().year)
    dl.created_by = current_user.id
    dl.fk_order_id = cmd.id
    db.session.add(dl)
    db.session.commit()
    for entry in cmd.entries:
        entry.fk_delivery_note_id = dl.id
        db.session.add(entry)
        db.session.commit()
    # cmd.is_delivered = True
    cmd.is_canceled = False
    db.session.add(cmd)
    db.session.commit()
    flash(f'Document {dl.intern_reference} sauvegardé','success')
    return redirect(url_for('sales_bp.print_delivery_note', bl_id=dl.id))