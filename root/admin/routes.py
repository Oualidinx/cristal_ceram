from flask import abort, render_template, session, flash, redirect, url_for, request, jsonify
import calendar

from fontTools.varLib.mutator import curr

from root.admin import admin_bp
from root import database as db
from flask_login import login_required
from root.admin.forms import *
from root.auth.forms import ResetPasswordForm
from root.models import Supplier, Tax, PurchaseReceipt, InvoiceTax, OrderTax, Warehouse, Store
from root.models import Format, Aspect, Stock, Client, Contact, Quotation, Expense, Pay
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from datetime import timedelta as td, datetime as dt


@admin_bp.before_request
def admin_before_request():
    session['role'] = "Manager"
    if current_user.is_authenticated:
        user = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
        if not user:
            return render_template('errors/401.html')


@admin_bp.get('/')
@login_required
def index():
    calendar.setfirstweekday(6)
    if 'endpoint' in session:
        del session['endpoint']

    _dict = dict()
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    _dict['suppliers'] = len(
        Supplier.query.filter_by(fk_company_id=company.fk_company_id).filter_by(is_deleted=False).all())
    _dict['clients'] = len(
        Client.query.filter_by(fk_company_id=company.fk_company_id).filter_by(is_deleted=False).all())
    _dict['items'] = len(Item.query.filter_by(fk_company_id=company.fk_company_id).filter_by(is_disabled=False).all())
    _products = Item.query.join(Entry, Entry.fk_item_id == Item.id) \
        .join(Order, Order.id == Entry.fk_order_id) \
        .filter(sa.and_(Order.fk_company_id == company.fk_company_id, Item.fk_company_id == company.fk_company_id)) \
        .filter(sa.and_(Order.category == "vente", Order.is_delivered == True)).group_by(Item.id)

    revenue, _expenses = dict(), dict()
    query_pay = Pay.query.filter(Pay.fk_company_id == company.fk_company_id)
    query_expense = Expense.query.filter(Expense.fk_company_id == company.fk_company_id)
    revenue['today'] = sum(
        [pay.amount for pay in query_pay.filter(func.date(Pay.payment_date) == func.date(dt.now().date())).all()])

    _expenses['today'] = sum(
        [exp.amount for exp in query_expense.filter(func.date(Expense.created_at) == func.date(dt.now().date())).all()])
    day = dt.now().date()
    weekday = calendar.weekday(day.year, day.month, day.day)
    l = list()
    revenue['week'], revenue['month'], revenue['year'] = 0, 0, 0

    # ================================
    # % CALCUL DE TOUS LES REVENUS %
    # ================================

    if query_pay.all():
        stop = False
        while not stop:
            pay = query_pay.filter(func.date(Pay.payment_date) == func.date(day))
            if pay.all():
                revenue['week'] += sum([_pay.amount for _pay in pay])
            day -= td(days=1)
            if weekday == 5:
                stop = True
                # pay = query_expense.filter(func.date(Expense.created_at) == func.date(day))
                # if pay.all():
                #     _expenses['week'] += sum([_pay.amount for _pay in pay])
            weekday = dt.weekday(day)
        # /while weekday!=4:
        #     pay = query_pay.filter(func.date(Pay.payment_date) == func.date(day))
        #     if pay.all():
        #         revenue['week'] += sum([_pay.amount for _pay in pay])
        #     day -= td(days=1)
        #     weekday = dt.weekday(day)

        # if weekday == 4:
        #     pay = query_pay.filter(func.date(Pay.payment_date) == func.date(day)).all()
        #     if pay:
        #         expenses['week'] += sum([_pay.amount for _pay in pay])

        day = dt.now().date()
        day_in_month = day.day

        while day_in_month != 1:
            pay = query_pay.filter(func.date(Pay.payment_date) == func.date(day))
            if pay.all():
                revenue['month'] += sum([_pay.amount for _pay in pay])
            day -= td(days=1)
            day_in_month = day.day

        if day_in_month == 1:
            pay = query_pay.filter(func.date(Pay.payment_date) == func.date(day))
            if pay.all():
                revenue['month'] += sum([_pay.amount for _pay in pay])

        day = dt.now().date()
        day_in_month = day.day
        month_in_year = day.month
        while (month_in_year != 1) or (day_in_month != 1):
            pay = query_pay.filter(func.date(Pay.payment_date) == func.date(day))
            if pay.all():
                revenue['year'] += sum([_pay.amount for _pay in pay])
            day -= td(days=1)

            day_in_month = day.day
            month_in_year = day.month
        if (month_in_year == 1) and (day_in_month == 1):
            pay = query_pay.filter(func.date(Pay.payment_date) == func.date(day))
            if pay.all():
                revenue['year'] += sum([_pay.amount for _pay in pay])

        # =================================
        # % CALCUL DE TOUTES LES DÉPENSES % 
        # =================================

    day = dt.now().date()
    _expenses['week'], _expenses['month'], _expenses['year'] = 0, 0, 0
    query_expense = query_expense.filter(func.date(Expense.created_at) <= func.date(day))
    weekday = dt.weekday(day)
    if query_expense.all():
        stop = False
        while not stop:
            pay = query_expense.filter(func.date(Expense.created_at) == func.date(day))
            if pay.all():
                _expenses['week'] += sum([_pay.amount for _pay in pay])
            day -= td(days=1)
            if weekday == 5:
                stop = True
                # pay = query_expense.filter(func.date(Expense.created_at) == func.date(day))
                # if pay.all():
                #     _expenses['week'] += sum([_pay.amount for _pay in pay])
            weekday = dt.weekday(day)

        day = dt.now().date()
        day_in_month = day.day

        while day_in_month != 1:
            pay = query_expense.filter(func.date(Expense.created_at) == func.date(day))
            if pay.all():
                _expenses['month'] += sum([_pay.amount for _pay in pay])
            day -= td(days=1)
            day_in_month = day.day

        if day_in_month == 1:
            pay = query_expense.filter(func.date(Expense.created_at) == func.date(day))
            if pay.all():
                _expenses['month'] += sum([_pay.amount for _pay in pay])

        day = dt.now().date()
        day_in_month = day.day
        month_in_year = day.month
        while (month_in_year != 1) or (day_in_month != 1):
            pay = query_expense.filter(func.date(Expense.created_at) == func.date(day))
            if pay.all():
                _expenses['year'] += sum([_pay.amount for _pay in pay])
            day -= td(days=1)

            day_in_month = day.day
            month_in_year = day.month
            if (month_in_year == 1) and (day_in_month == 1):
                pay = query_expense.filter(func.date(Expense.created_at) == func.date(day))
                if pay.all():
                    _expenses['year'] += sum([_pay.amount for _pay in pay])
    return render_template("admin/index.html",
                           info=_dict,
                           date=dt.now().date(),
                           products=[item.repr(['id', 'intern_reference', 'label', 'stock_qte', 'delivered_quantity',
                                                'stock_value']) for item in _products.all()[:10]],
                           revenue=revenue,
                           expense=_expenses
                           )


@admin_bp.get("/taxes/new")
@admin_bp.post("/taxes/new")
@login_required
def new_taxes():
    form = TaxesForm()
    if form.validate_on_submit():
        tax = Tax()
        tax.name = form.name.data
        tax.label = form.label.data
        tax.value = float(form.value.data)
        tax.sign = form.sign.data
        # if form.sell_or_bye.data:
        #     tax.for_sell = True
        # else:
        #     tax.for_buy = True

        if form.applied_before_TVA.data:
            tax.applied_before_TVA = True
        else:
            tax.applied_after_TVA = True
        if form.on_applied_products.data:
            tax.on_applied_products = True

        # if form.on_applied_TVA.data:
        #     tax.on_applied_TVA = True
        db.session.add(tax)
        db.session.commit()
        flash('Ajout avec succès', 'success')
        return redirect(url_for('admin_bp.new_taxes'))
    return render_template('admin/new_taxes.html', form=form)


@admin_bp.get('/taxes/<int:tax_id>/delete')
@login_required
def delete_tax(tax_id):
    tax = Tax.query.get(tax_id)
    if not tax:
        return render_template("errors/404.html", blueprint='admin_bp')

    invoices_taxes = InvoiceTax.query.filter_by(fk_tax_id=tax.id).all()
    orders_taxes = OrderTax.query.filter_by(fk_tax_id=tax.id).all()
    if invoices_taxes is not None or orders_taxes is not None:
        flash('Opération impossible: tax déjà utilisé', 'danger')
        return redirect(url_for("admin_bp.taxes"))

    db.session.delete(tax)
    db.session.commit()
    flash('Suppression avec succès', 'success')
    return redirect(url_for('admin_bp.taxes'))


@admin_bp.get('/taxes/<int:tax_id>/edit')
@login_required
def edit_tax(tax_id):
    form = TaxesForm()
    tax = Tax.query.get(tax_id)
    if not tax:
        return render_template('errors/404.html', blueprint='admin_bp')

    if request.method == "GET":
        form.name.data = tax.name
        form.label.data = tax.label
        form.value.data = tax.value
        form.sign.data = tax.sign
        form.on_applied_products.data = True if tax.on_applied_products else False
        form.applied_before_TVA.data = True if tax.applied_before_TVA == True else False

    if form.validate_on_submit():
        tax_1 = Tax.query.filter_by(created_by=current_user.id).filter(
            func.lower(Tax.label) == str.lower(form.label.data)).first()
        if tax_1 and tax_1.id == tax.id:
            flash('Nom de Tax déjà existe', 'warning')
            return redirect(url_for('admin_bp.edit_tax', tax_id=tax_id))
        tax.label = form.label.data
        tax.name = form.name.data
        tax.value = float(form.value.data)
        tax.sign = form.sign.data

        if form.applied_before_TVA.data:
            if form.applied_before_TVA.data is True:
                tax.applied_before_TVA = True
                tax.applied_after_TVA = False
            else:
                tax.applied_before_TVA = False
                tax.applied_after_TVA = True

        if form.on_applied_products.data:
            tax.on_applied_products = form.on_applied_products.data

        db.session.add(tax)
        db.session.commit()
        flash('Ajout avec succès', 'success')
        return redirect(url_for('admin_bp.new_taxes'))
    return render_template('admin/new_taxes.html', form=form)


@admin_bp.post('/taxes/get')
@login_required
def get_tax():
    data = request.json()
    tax = Tax.query.get(data['tax_id'])
    fixed = "Fixée" if tax.is_fixed else "%"
    applied_before = "Avant TVA" if tax.applied_before_TVA == True else "Après TVA"
    if tax:
        return jsonify(message=f"<h5 class='h5'>{tax.name}</h5> \
                            Abréviation: {tax.label} <br> \
                            Valeur: {tax.sign}{tax.value} {fixed}  <br> \
                            Appliqué {applied_before}"), 200
    return render_template('errors/404.html', blueprint="admin_bp")


@admin_bp.get('/taxes')
@login_required
def taxes():
    _taxes = User.query.get(current_user.id).taxes
    liste = None
    if _taxes:
        liste = [
            obj.repr(['id', 'name', 'label', 'value', 'sign']) for obj in [
                company.taxes for company in _taxes
            ]
        ]
    return render_template('admin/taxes.html', liste=liste)


@admin_bp.get('/warehouses')
@admin_bp.post('/warehouses')
@login_required
def warehouses():
    session['endpoint'] = 'warehouses'
    _warehouses = Warehouse.query \
        .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
                   .filter_by(fk_user_id=current_user.id).first().fk_company_id)
    liste = list()
    if _warehouses:
        indexe = 1
        for warehouse in _warehouses:
            _dict = warehouse.repr()
            _dict.update({'index': indexe})
            indexe += 1
            liste.append(_dict)
    # _warehouses = [obj.repr() for obj in _warehouses] if _warehouses else None
    form = WarehouseForm()
    if form.validate_on_submit():
        warehouse = Warehouse(
            name=form.name.data,
            address=form.address.data,
            contact=form.contact.data,
            fk_company_id=UserForCompany.query.filter_by(fk_user_id=current_user.id) \
                .filter_by(role="manager").first().fk_company_id
        )
        db.session.add(warehouse)
        db.session.commit()
        flash('Ajout avec succès', 'success')
        return redirect(url_for("admin_bp.warehouses"))

    return render_template('admin/warehouses.html', form=form, liste=liste)


@admin_bp.get('/warehouses/<int:warehouse_id>/edit')
@admin_bp.post('/warehouses/<int:warehouse_id>/edit')
@login_required
def edit_warehouse(warehouse_id):
    form = EditWarehouseForm()
    warehouse = Warehouse.query.get(warehouse_id)
    if not warehouse:
        return render_template('errors/404.html', blueprint="admin_bp")
    if request.method == "GET":
        form.name.data = warehouse.name
        form.contact.data = warehouse.contact
        form.address.data = warehouse.address

    if form.validate_on_submit():
        warehouse.name = form.name.data
        warehouse.address = form.address.data
        warehouse.contact = form.contact.data
        db.session.add(warehouse)
        db.session.commit()
        flash('Modification avec succès', 'success')
        return redirect(url_for('admin_bp.warehouses'))
    return render_template("admin/new_warehouse.html", form=form)


@admin_bp.get('/warehouses/<int:warehouse_id>/delete')
@login_required
def delete_warehouse(warehouse_id):
    warehouse = Warehouse.query.get(warehouse_id)
    user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id).filter_by(role="manager").first()
    if not warehouse:
        return render_template('errors/404.html', blueprint="admin_bp")
    if warehouse.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="admin_bp")
    if warehouse.stocks:
        flash('Impossible de supprimer le dépôt', "danger")
        return redirect(url_for("admin_bp.warehouses"))
    _user_for_company = UserForCompany.query.filter_by(fk_company_id=user_for_company.fk_company_id) \
        .filter_by(fk_warehouse_id=warehouse_id)
    if _user_for_company.all():
        for ufc in _user_for_company:
            db.session.delete(ufc)
            db.session.commit()
    db.session.delete(warehouse)
    db.session.commit()
    flash('Objet supprimé', 'success')
    return redirect(url_for("admin_bp.warehouses"))


'''
Manage users
'''


@admin_bp.get('/items')
@admin_bp.post('/items')
@login_required
def items():
    company = Company.query.get(UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not request.json or not company:
        # return '',404
        return render_template('errors/404.html', blueprint="admin_bp")
    if request.method == "POST" and request.json['role'] in ['1', '2']:
        data = request.json['role']
        if data == '1':
            return jsonify(messages=[{'ID': st.id, 'name': str(st)} for st in
                                     Store.query.filter_by(fk_company_id=company.id).all()])
        return jsonify(messages=[{'ID': wh.id, 'name': str(wh)} for wh in
                                 Warehouse.query.filter_by(fk_company_id=company.id).all()])
    return jsonify(status=400)


@admin_bp.get('/employees/new')
@admin_bp.post('/employees/new')
@login_required
def create_user():
    session['endpoint'] = 'users'
    form = EmployeeForm()
    company = Company.query.get(UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not company:
        return render_template('errors/404.html', blueprint="admin_bp")
    company_warehouses = Warehouse.query.filter_by(fk_company_id=company.id).all()
    company_store = Store.query.filter_by(fk_company_id=company.id).all()

    if not company_warehouses or not company_store:
        flash('Vous devez d\'abord ajouter vos dépôts', 'info')
        flash('Vous devez d\'abord ajouter vos magasin', "info")
        return render_template('admin/new_user.html', form=form)

    if form.validate_on_submit():
        user = User()

        user.username = form.username.data
        user.created_by = current_user.id
        user.password_hash = generate_password_hash(form.password.data, "sha256")
        user.full_name = form.full_name.data
        if not form.role.data or form.role.data not in [1, 2]:
            flash('Veuillez choisir le rôle', "warning")
            return render_template("admin/new_user.html", form=form)
        else:
            user.fk_store_id = request.form.get('location') if form.role.data == 1 else None
            db.session.add(user)
            db.session.commit()
            user_for_company = UserForCompany()
            user_for_company.fk_company_id = company.id
            user_for_company.fk_warehouse_id = request.form.get('location') if form.role.data == 2 else None
            user_for_company.fk_user_id = user.id
            if form.role.data == 1:
                user_for_company.role = "vendeur"
            else:
                user_for_company.role = "magasiner"
            db.session.add(user_for_company)
            db.session.commit()
            flash('Employé ajouté avec succès', 'success')
            return redirect(url_for("admin_bp.create_user"))
    return render_template("admin/new_user.html", form=form)


import sqlalchemy as sa


@admin_bp.get('/employees')
@login_required
def users():
    session['endpoint'] = 'users'
    current_cmp = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    _users = User.query.join(UserForCompany, UserForCompany.fk_user_id == User.id) \
        .filter(sa.or_(UserForCompany.role == "vendeur", UserForCompany.role == "magasiner")) \
        .filter(UserForCompany.fk_company_id == current_cmp.fk_company_id).all()
    liste = list()
    if _users:
        for user in _users:
            liste.append(user.repr(columns=['id', 'full_name', 'username', '_session', 'role', 'status', 'location']))
            # t_users = company.users
            # liste = liste + [
            #     user.repr(columns=['id', 'full_name', 'username','_session','role', 'status','location'])
            #         for user in  t_users
            # ]

    return render_template('admin/users.html', liste=liste)


@admin_bp.get('/users/<int:user_id>/edit')
@admin_bp.post('/users/<int:user_id>/edit')
@login_required
def edit_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return render_template('errors/404.html', blueprint="admin_bp")
    user_for_company = UserForCompany.query.filter_by(fk_user_id=user.id)
    if not user_for_company.first():
        return render_template('errors/404.html', blueprint="admin_bp")
    this_user_role = user_for_company.first().role
    company = Company.query.get(user_for_company.first().fk_company_id)
    manager_company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    if company.id != manager_company.fk_company_id:
        return render_template('errors/401.html')

    form = UpdateUserForm()
    if request.method == "GET":
        query = Warehouse.query.join(UserForCompany, UserForCompany.fk_warehouse_id == Warehouse.id) \
            .filter(Warehouse.fk_company_id == manager_company.fk_company_id)
        print(query.filter(UserForCompany.role == "magasiner").filter(UserForCompany.fk_user_id == user.id).all())
        form = UpdateUserForm(
            role=1 if this_user_role == "vendeur" else 2 if this_user_role == "magasiner" else 0,
            warehouses=query.filter(UserForCompany.role == "magasiner").filter(
                UserForCompany.fk_user_id == user.id).all(),
            username=user.username,
            full_name=user.full_name,
            stores=Store.query.get(user.fk_store_id) if user.fk_store_id else []
        )
    if form.validate_on_submit():
        company_users = company.users
        for u in company_users:
            if u.id != user.id and func.lower(u.full_name) == func.lower(form.full_name.data):
                flash('Nom de l\'utilisateur déjà existe', 'warning')
                return redirect(url_for("admin_bp.edit_user", user_id=user.id))
        user.full_name = form.full_name.data
        for u in company_users:
            if u.id != user.id and func.lower(u.username) == func.lower(form.username.data):
                flash('Pseudonyme déjà existe', 'warning')
                return redirect(url_for("admin_bp.edit_user", user_id=user.id))
        user.username = form.username.data

        user_for_company = UserForCompany.query.filter_by(fk_company_id=manager_company.fk_company_id) \
            .filter_by(fk_user_id=user.id)

        if form.role.data == 2:
            if this_user_role == "magasiner":
                _w = len(user_for_company.all())
                f_w = len(form.warehouses.data)
                if f_w == 0:
                    flash('Il faut sélectionner au moins un dépôt', 'danger')
                    return redirect(url_for('admin_bp.edit_user', user_id=user.id))
                if _w > f_w:
                    for ID in [wh.fk_warehouse_id for wh in user_for_company.all()]:
                        if ID not in [wh.id for wh in form.warehouses.data]:
                            u_f_c = user_for_company.filter_by(fk_warehouse_id=int(ID)).first()
                            db.session.delete(u_f_c)
                            db.session.commit()
                elif _w < f_w:
                    for ID in [wh.id for wh in form.warehouses.data]:
                        if ID not in [wh.fk_warehouse_id for wh in user_for_company.all()]:
                            u_f_c = UserForCompany(fk_user_id=user.id, fk_company_id=company.id,
                                                   fk_warehouse_id=ID, role="magasiner")
                            db.session.add(u_f_c)
                            db.session.commit()
                else:
                    # temps = [wh for wh in user_for_company.all()]
                    ids = [wh.id for wh in form.warehouses.data]
                    counter = 0
                    for temp in [wh for wh in user_for_company.all()]:
                        # for ID in [wh.id for wh in form.warehouses.data]:
                        temp.start_from = dt.utcnow()
                        temp.fk_warehouse_id = ids[counter]
                        db.session.add(temp)
                        db.session.commit()

            else:
                user.fk_store_id = None
                db.session.add(user)
                db.session.delete(user_for_company.first())
                db.session.commit()
                for warehouse in form.warehouses.data:
                    u_f_c = UserForCompany()
                    u_f_c.fk_user_id, u_f_c.fk_company_id = user.id, company.id
                    u_f_c.fk_warehouse_id = warehouse.id
                    u_f_c.role = "magasiner"
                    db.session.add(u_f_c)
                    db.session.commit()

        else:
            if not form.stores.data:
                flash('Il faut séléctionner le magasin pour cet employé', 'danger')
                return redirect(url_for('admin_bp.edit_user', user_id=user.id))
            user.fk_store_id = form.stores.data.id

            if this_user_role == 'vendeur':
                u_f_c = user_for_company.first()
                u_f_c.start_from = dt.utcnow()
                db.session.add(u_f_c)
                db.session.commit()
            else:
                user_warehouses = [wh for wh in user_for_company.all()]
                for wh in user_warehouses:
                    db.session.delete(wh)
                    db.session.commit()
                u_f_c = UserForCompany()
                u_f_c.fk_user_id, u_f_c.fk_company_id = user.id, company.id
                u_f_c.fk_warehouse_id = None
                u_f_c.role = "vendeur"
                db.session.add(u_f_c)
                db.session.commit()
            db.session.add(user)
            db.session.commit()
        flash('Mise à jour avec succès', 'success')
        return redirect(url_for('admin_bp.users'))
    return render_template('admin/edit_user.html',
                           user=user,
                           role=UserForCompany.query.filter_by(fk_user_id=user.id).first().role,
                           form=form)


@admin_bp.get('/users/<int:user_id>/disable')
@login_required
def disable_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return render_template("errors/404.html", blueprint="admin_bp")

    if user.is_disabled:
        flash('Erreur', 'danger')
        return redirect(url_for("admin_bp.users"))

    current_cmp = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    # current_companies = Company.query.join(UserForCompany, Company.id == UserForCompany.fk_company_id) \
    #     .filter(Company.id == current_cmp.fk_company_id).all()
    # if current_companies:
    #     for company in current_companies:
    #         if user in company.users:
    #
    #             if user_for_company:
    if user.fk_store_id:
        user.fk_store_id = None

    user_for_company = UserForCompany.query.filter_by(fk_user_id=user.id).filter_by(
        fk_company_id=current_cmp.fk_company_id)
    if user_for_company.all():
        for ufc in user_for_company:
            db.session.delete(ufc)
            db.session.commit()
    user.is_disabled = True
    db.session.add(user)
    db.session.commit()
    flash('Opération se termine avec succès', "success")
    return redirect(url_for("admin_bp.users"))
    # return render_template('errors/404.html', blueprint="admin_bp")


# @admin_bp.get('/employees/get')
@admin_bp.post('/employees/get')
@login_required
def get_user():
    session['endpoint'] = 'users'

    data = request.json
    user = User.query.get(int(data['user_id']))
    if not user:
        abort(404)
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    user_company = UserForCompany.query.filter_by(fk_user_id=user.id)
    if company.fk_company_id != user_company.first().fk_company_id:
        abort(404)
    user_company = user_company.filter_by(fk_company_id=company.id).first()

    _dict = User.query.get(user.id).repr(['location', 'locations'])
    if user.fk_store_id:
        return jsonify(message=f"<h4 class='h4 fw-bold'>{user.full_name}</h4> \
                                <span class='fw-bold mb-3'>Pseudonyme: </span>{user.username} <br> \
                                <span class='fw-bold mb-3'>Rôle: </span>{user_company.role if user_company is not None else '/'} <br> \
                                <span class='fw-bold mb-3'>Lieu(x) de travail: </span><br>" + _dict['location']), 200
    return jsonify(message=f"<h4 class='h4 fw-bold'>{user.full_name}</h4> \
                        <span class='fw-bold mb-3'>Pseudonyme: </span>{user.username} <br> \
                        <span class='fw-bold mb-3'>Rôle: </span>{user_company.role if user_company is not None else '/'} <br> \
                        <span class='fw-bold mb-3'>Lieu(x) de travail: </span><br>" + '<br>'.join(
        _dict['locations'])), 200


@admin_bp.get('/stocks')
@login_required
def stocks():
    """
                            à revoir
    """

    return render_template('admin/stocks.html', liste=None)


@admin_bp.get('/stock/<int:stock_id>/detach')
@login_required
def detach_stock(stock_id):
    stock = Stock.query.get(stock_id)
    if not stock:
        return render_template("errors/404.html", blueprint="admin_bp")

    company = Company.query.get(Warehouse.query.get(stock.fk_warehouse_id))
    if not company:
        return render_template('errors/404.html', blueprint="admin_bp")

    if User.query.filter_by(role="manager") \
            .filter_by(fk_user_id=current_user.id).filter_by(fk_company_id=company.id).first() is None:
        return render_template('errors/404.html', blueprint="admin_bp")

    stock.fk_warehouse_id = None
    db.session.add(stock)
    db.session.commit()
    flash('Opération terminé avec succès', "success")
    return redirect(url_for("admin_bp.stocks"))


@admin_bp.get('/stock/<int:stock_id>/attach')
@admin_bp.post('/stock/<int:stock_id>/attach')
@login_required
def attach_stock(stock_id):
    form = AttachWareHouseForm()
    stock = Stock.query.get(stock_id)
    if request.method == 'GET':
        if not stock:
            return render_template("errors/404.html", blueprint="admin_bp")

        company = Company.query.get(Warehouse.query.get(stock.fk))
        # if not company:
        #     return render_template('errors/404.html', blueprint="admin_bp")

        if User.query.filter_by(role="manager") \
                .filter_by(fk_user_id=current_user.id).filter_by(fk_company_id=company.id).first() is None:
            return render_template('errors/404.html', blueprint="admin_bp")
        if stock.fk_warehouse_id is not None:
            flash('Stock déjà attaché à un dépôt. Veuillez d\'abord détacher le puis réesseyer.', "warning")
            return redirect(url_for("admin_bp.stocks"))
        form.warehouse.query_factory = lambda: Warehouse.query.join(Company, Company.id == Warehouse.fk_company_id) \
            .join(UserForCompany, UserForCompany.fk_company_id == Company.id) \
            .filter(sa.and_(UserForCompany.role == "manager", UserForCompany.fk_user_id == current_user.id)) \
            .all()
        if stock.stock_qte:
            form.stock_qte.data = stock.stock_qte
        form.stock_sec.data = stock.stock_sec

    if form.validate_on_submit():
        if Warehouse.query.get(form.warehouse.data):
            return render_template('errors/404.html', blueprint="admin_bp")
        stock.fk_warehouse_id = int(form.warehouse.data)
        db.session.add(stock)
        db.session.commit()
        flash('Opération terminée avec succès', 'success')
    return redirect(url_for('admin_bp.stocks'))


@admin_bp.get('/products/formats')
@admin_bp.post('/products/formats')
@login_required
def formats():
    session['endpoint'] = 'product'
    c_id = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    _formats = Format.query.filter_by(fk_company_id=c_id).all()
    liste = None
    if _formats:
        liste = [
            {
                'id': obj.id,
                'label': obj.label
            } for obj in _formats
        ]

    form = FormatForm()
    if form.validate_on_submit():
        _format = Format()
        f = Format.query.filter_by(fk_company_id=c_id).filter(
            func.lower(Format.label) == str.lower(form.label.data)).first()
        if f:
            _format = f
        _format.label = form.label.data
        _format.created_by = current_user.id
        _format.fk_company_id = c_id
        db.session.add(_format)
        db.session.commit()
        flash('Objet ajouté avec succès', 'success')
        return redirect(url_for('admin_bp.formats'))

    return render_template('admin/formats.html', form=form, liste=liste)


@admin_bp.get('/products/formats/<int:format_id>/edit')
@admin_bp.post('/products/formats/<int:format_id>/edit')
@login_required
def edit_format(format_id):
    session['endpoint'] = 'product'
    form = EditFormatForm()
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    format_ = Format.query.filter_by(fk_company_id=company).filter_by(id=format_id).first()
    if not format_:
        return render_template("errors/404.html", blueprint="admin_bp")
    if request.method == "GET":
        form.label.data = format_.label
    if form.validate_on_submit():
        format_.label = form.label.data
        db.session.add(format_)
        db.session.commit()
        flash('Objet modifie avec succès', "success")
        return redirect(url_for("admin_bp.formats"))
    return render_template("admin/add_format.html", form=form)


@admin_bp.get('/products/format/<int:format_id>/delete')
@login_required
def delete_format(format_id):
    session['endpoint'] = 'product'
    _format = Format.query.get(format_id)
    if not _format:
        return render_template("errors/404.html", blueprint="admin_bp")

    item_brand_category = Item.query.filter_by(fk_format_id=_format.id).first()
    if item_brand_category:
        flash('impossible de supprimé cet objet', "danger")
        return redirect(url_for('admin_bp.formats'))
    db.session.delete(_format)
    db.session.commit()
    flash('Objet supprimé', 'success')
    return redirect(url_for("admin_bp.formats"))


@admin_bp.get('/products/aspects/<int:aspect_id>/edit')
@admin_bp.post('/products/aspects/<int:aspect_id>/edit')
@login_required
def edit_aspect(aspect_id):
    session['endpoint'] = 'product'
    form = EditAspectForm()
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    aspect_ = Aspect.query.filter_by(fk_company_id=company).filter_by(id=aspect_id).first()

    if not aspect_:
        return render_template("errors/404.html", blueprint="admin_bp")
    if request.method == "GET":
        form.label.data = aspect_.label
    if form.validate_on_submit():
        aspect_.label = form.label.data
        db.session.add(aspect_)
        db.session.commit()
        flash('Objet modifié avec succès', "success")
        return redirect(url_for("admin_bp.aspects"))
    return render_template("admin/add_aspect.html", form=form)


@admin_bp.get('/products/aspect/<int:aspect_id>/delete')
@login_required
def delete_aspect(aspect_id):
    session['endpoint'] = 'product'
    _aspect = Aspect.query.get(aspect_id)
    if not _aspect:
        return render_template("errors/404.html", blueprint="admin_bp")

    item_brand_category = Item.query.filter_by(fk_aspect_id=_aspect.id).first()
    if item_brand_category:
        flash('impossible de supprimé cet objet', "danger")
        return redirect(url_for('admin_bp.aspects'))
    db.session.delete(_aspect)
    db.session.commit()
    flash('Objet supprimé', 'success')
    return redirect(url_for("admin_bp.aspects"))


@admin_bp.get('/products/aspects')
@admin_bp.post('/products/aspects')
@login_required
def aspects():
    session['endpoint'] = 'product'
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    _aspects = Aspect.query.filter_by(fk_company_id=company).all()
    liste = None
    if _aspects:
        liste = [
            {'id': aspect.id, 'label': aspect.label} for aspect in _aspects
        ]

    form = AspectForm()

    c_id = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id

    if form.validate_on_submit():
        aspect = Aspect()
        _aspect = Aspect.query.filter_by(fk_company_id=c_id).filter(
            func.lower(Aspect.label) == str.lower(form.label.data)).first()
        if _aspect:
            aspect = _aspect
        aspect.label = form.label.data
        aspect.created_by = current_user.id
        aspect.fk_company_id = c_id
        db.session.add(aspect)
        db.session.commit()
        flash('Objet ajouté avec succès', 'success')
        return redirect(url_for('admin_bp.aspects'))

    return render_template('admin/aspects.html',
                           form=form,
                           liste=liste)


@admin_bp.get('/products')
@login_required
def products():
    session['endpoint'] = 'product'
    company = Company.query.get(UserForCompany.query.filter_by(role="manager") \
                                .filter_by(fk_user_id=current_user.id).first().fk_company_id)
    _products = Item.query.filter_by(is_disabled=False).filter_by(fk_company_id=company.id).all()
    liste = None
    if _products:
        liste = [product.repr(
            ['id', 'label', 'format', 'aspect', 'serie', 'intern_reference', 'expired_at', 'stock_sec', 'stock_qte'])
                 for product in _products]
    return render_template('admin/items.html', liste=liste)


@admin_bp.get('/products/add')
@admin_bp.post('/products/add')
@login_required
def add_product():
    session['endpoint'] = 'product'
    __formats = Format.query.filter_by(
        fk_company_id=UserForCompany.query.filter_by(role='manager').filter_by(fk_user_id=current_user.id) \
            .first().fk_company_id).all()
    __aspect = Aspect.query.filter_by(
        fk_company_id=UserForCompany.query.filter_by(role='manager').filter_by(fk_user_id=current_user.id) \
            .first().fk_company_id).all()
    if not __formats:
        flash('Il faut ajouter les formats', 'warning')
    if not __aspect:
        flash('Il faut ajouter les aspects', 'warning')
    form = NewItemForm()
    if form.validate_on_submit():
        item = Item()
        item.label = form.label.data
        item.serie = form.serie.data
        item.manufacturer = form.manufacturer.data if form.manufacturer.data else None
        item.unit = form.unit.data if form.unit.data else None
        if form.piece_per_unit.data and not item.unit:
            flash('Veuillez sélectionner l\'unité puis réesseyer', 'warning')
            return redirect(url_for('admin_bp.add_product'))
        else:
            item.piece_per_unit = float(form.piece_per_unit.data)
        # if form.sale_price.data:
        #     item.sale_price = float(form.sale_price.data)
        item.stock_sec = form.stock_sec.data
        item.use_for = form.utilisation.data if form.utilisation.data else None
        item.intern_reference = form.intern_reference.data if form.intern_reference.data else None
        item.fk_aspect_id = form.aspect.data.id if form.aspect.data else None
        item.fk_format_id = form.format.data.id if form.format.data else None
        item.used_for = form.utilisation.data
        item.created_by = current_user.id
        item.fk_company_id = UserForCompany.query.filter_by(role="manager").filter_by(
            fk_user_id=current_user.id).first().id
        item.expired_at = form.expired_at.data if form.expired_at.data else None
        db.session.add(item)
        db.session.commit()
        flash('Objet ajouté avec succès', "success")
        return redirect(url_for('admin_bp.add_product'))
    return render_template("admin/new_item.html", form=form)


@admin_bp.get('/products/<int:p_id>/delete')
@login_required
def delete_product(p_id):
    _product = Item.query.get(p_id)
    if not _product:
        return render_template('errors/404.html', blueprint="admin_bp")

    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    if not company:
        return render_template('errors/401.html')

    if company.fk_company_id != _product.fk_company_id:
        return render_template('errors/401.html')
    entries = Entry.query.filter_by(fk_item_id=_product.id)
    _stocks = Stock.query.filter_by(fk_item_id=_product.id)
    if entries.all() or _stocks.all():
        _product.is_disabled = True
        db.session.add(_product)
        db.session.commit()
    else:
        db.session.delete(_product)
        db.session.commit()
    flash('Objet supprimé', 'success')
    return redirect(url_for('admin_bp.products'))


@admin_bp.get('/products/<int:item_id>/edit')
@admin_bp.post('/products/<int:item_id>/edit')
@login_required
def edit_product(item_id):
    session['endpoint'] = 'product'
    item = Item.query.get(item_id)
    if not item:
        return render_template('errors/404.html', blueprint="admin_bp")

    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().id
    form = EditItemForm()
    if request.method == "GET":
        form = EditItemForm(
            format=Format.query.get(item.fk_format_id) if item.fk_format_id else None,
            aspect=Aspect.query.get(item.fk_aspect_id) if item.fk_aspect_id else None,
            used_for=item.use_for if item.use_for else None,
            label=item.label,
            manufaturer=item.manufacturer if item.manufacturer else None,
            unit=item.unit if item.unit else None,
            piece_per_unit=item.piece_per_unit if item.piece_per_unit else None,
            stock_sec=item.stock_sec,
            serie=item.serie if item.serie else None,
            intern_reference=item.intern_reference if item.intern_reference else None,
            expired_at=item.expired_at if item.expired_at else None,
        )
    if form.validate_on_submit():

        _item = Item.query.filter_by(fk_company_id=company) \
            .filter(func.lower(Item.label) == str.lower(form.label.data)).first()
        if _item and item.id != _item.id:
            flash('Nom déjà utilisé', 'warning')
            return redirect(url_for('admin_bp.edit_product', item_id=item.id))
        item.label = form.label.data

        if form.intern_reference.data:
            _item = Item.query.filter_by(fk_company_id=company) \
                .filter(func.lower(Item.intern_reference) == str.lower(form.intern_reference.data)).first()
            if _item and item.id != _item.id:
                flash('Référence déjà utilisé', 'warning')
                return redirect(url_for('admin_bp.edit_product', item_id=item.id))
            item.intern_reference = form.intern_reference.data
        else:
            item.intern_reference = None

        item.manufacturer = form.manufacturer.data if form.manufacturer.data else None
        item.unit = form.unit.data if form.unit.data else None
        if form.piece_per_unit.data and not item.unit:
            flash('Veuillez sélectionner \'unité puis réesseyer', 'warning')
            return redirect(url_for('admin_bp.edit_product', item_id=item.id))
        else:
            item.piece_per_unit = float(form.piece_per_unit.data)
        item.company_id = company
        item.expired_at = form.expired_at.data if form.expired_at.data else None
        item.fk_aspect_id = form.aspect.data
        item.fk_format_id = form.format.data

        item.stock_sec = form.stock_sec.data
        item.utilisation = form.utilisation.data
        item.fk_item_id = item.id
        db.session.add(item)
        db.session.commit()
        flash('Objet ajouté avec succès', "success")
    return render_template("admin/new_item.html", form=form)


from sqlalchemy.sql import or_


@admin_bp.get('/products/<int:item_id>/get')
@login_required
def get_item(item_id):
    session['endpoint'] = 'product'
    item = Item.query.get(item_id)
    if not item:
        return render_template('errors/404.html', blueprint="admin_bp")
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id) \
        .first().fk_company_id
    if item.fk_company_id != company:
        return render_template('errors/404.html', blueprint="admin_bp")
    entries = [entry.repr(['date_reference', 'reference', 'type', 'date', 'in_stock', 'beneficiary',
                           'status', 'delivered_quantity', 'qc'])
               for entry in Entry.query.filter_by(fk_item_id=item_id).all()
               ]
    entries = [
        entry for entry in entries if entry['status'] != None or entry['beneficiary'] == None
    ]

    return render_template('admin/item_info.html', item=item.repr(), entries=entries)


@admin_bp.get('/stores')
@admin_bp.post('/stores')
@login_required
def stores():
    session['endpoint'] = 'stores'
    _stores = Store.query \
        .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
                   .filter_by(fk_user_id=current_user.id).first().fk_company_id)

    _stores = [obj.repr() for obj in _stores] if _stores else None
    form = StoreForm()
    if form.validate_on_submit():
        store = Store()
        store.name = form.name.data
        store.address = form.address.data
        store.contact = form.contact.data
        store.fk_company_id = UserForCompany.query.filter_by(role="manager").filter_by(
            fk_user_id=current_user.id).first().fk_company_id
        db.session.add(store)
        db.session.commit()
        flash('Objet ajouté avec success', 'success')
        return redirect(url_for('admin_bp.stores'))
    return render_template('admin/stores.html', form=form, liste=_stores)


@admin_bp.get('/stores/<int:store_id>/block')
@login_required
def block_store(store_id):
    store = Store.query.get(store_id)
    if not store:
        return render_template('errors/404.html', blueprint="admin_bp")

    if store.is_disabled:
        flash('Erreur', 'danger')
        return redirect(url_for('admin_bp.stores'))

    if UserForCompany.query.filter_by(role="manager") \
            .filter(sa.and_(UserForCompany.fk_user_id == current_user.id,
                            UserForCompany.fk_company_id == store.fk_company_id)).first() is None:
        return render_template('errors/404.html', bluepint="admin_bp")
    store.is_disabled = True
    db.session.add(store)
    db.session.commit()
    flash('Opération terminée avec succès', 'success')
    return redirect(url_for("admin_bp.stores"))


@admin_bp.get('/stores/<int:store_id>/unblock')
@login_required
def unblock_store(store_id):
    store = Store.query.get(store_id)
    if not store:
        return render_template('errors/404.html', blueprint="admin_bp")

    if not store.is_disabled:
        flash('Erreur', 'danger')
        return redirect(url_for('admin_bp.stores'))

    if UserForCompany.query.filter_by(role="manager") \
            .filter(sa.sand_(UserForCompany.fk_user_id == current_user.id,
                             UserForCompany.fk_company_id == store.fk_company_id)).first() is None:
        return render_template('errors/404.html', bluepint="admin_bp")
    store.is_disabled = False
    db.session.add(store)
    db.session.commit()
    flash('Opération terminée avec succès', 'success')
    return redirect(url_for("admin_bp.stores"))


@admin_bp.get('/stores/<int:store_id>/edit')
@admin_bp.post('/stores/<int:store_id>/edit')
@login_required
def edit_store(store_id):
    form = EditStoreForm()
    store = Store.query.get(store_id)
    if not store:
        return render_template('errors/404.html', blueprint="admin_bp")

    if store.is_disabled:
        flash('Opération impossible', 'danger')
        return redirect(url_for('admin_bp.stores'))

    if UserForCompany.query.filter_by(role="manager") \
            .filter(sa.and_(UserForCompany.fk_user_id == current_user.id,
                            UserForCompany.fk_company_id == store.fk_company_id)).first() is None:
        return render_template('errors/404.html', bluepint="admin_bp")
    if request.method == "GET":
        form.name.data = store.name
        form.address.data = store.address
        form.contact.data = store.contact
        # form.seller.query_factory=lambda : Company.query.get(UserForCompany.query. \
        #                                                      filter_by(role="manager")\
        #                                                      .filter_by(fk_user_id=current_user.id)\
        #                                                      .first().fk_company_id).users

    if form.validate_on_submit():
        store.name = form.name.data
        store.address = form.address.data
        store.contact = form.contact.data
        db.session.add(store)
        db.session.commit()
        flash('Objet ajouté avec success', 'success')
        return redirect(url_for('admin_bp.stores'))
    return render_template("admin/new_store.html", form=form)


@admin_bp.get('/stores/<int:store_id>/delete')
@login_required
def delete_store(store_id):
    store = Store.query.get(store_id)
    user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id).filter_by(role="manager").first()
    if not store:
        return render_template('errors/404.html', blueprint="admin_bp")
    if store.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="admin_bp")
    if store.sellers:
        for seller in store.sellers:
            seller.fk_store_id = None
            db.session.add(seller)
        db.session.commit()
    db.session.delete(store)
    db.session.commit()
    flash('Objet supprimé', 'success')
    return redirect(url_for("admin_bp.stores"))


@admin_bp.get('/employees/<int:user_id>/change_password')
@admin_bp.post('/employees/<int:user_id>/change_password')
@login_required
def change_password(user_id):
    session['endpoint'] = 'users'

    user = User.query.get(user_id)
    if not user:
        flash('Employés introuvable', 'danger')
        return redirect(url_for('admin_bp.edit_user', user_id=user.id))

    _users = Company.query.get(UserForCompany.query.filter_by(role="manager") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id).users
    if not _users or user not in _users:
        flash('Employés introuvable', 'danger')
        return redirect(url_for('admin_bp.edit_user', user_id=user.id))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.new_password.data, "SHA256")
        db.session.add(user)
        db.session.commit()
        flash('Opération terminée avec succès', 'success')
        return redirect(url_for('admin_bp.edit_user', user_id=user.id))
    return render_template('auth/reset_password.html', form=form)


@admin_bp.get('/clients')
@login_required
def clients():
    session['endpoint'] = 'sales'
    _clients = Client.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
                                      .filter_by(fk_user_id=current_user.id).first().fk_company_id).all()
    liste = None
    if _clients:
        liste = [
            client.repr() for client in _clients
        ]
    return render_template('admin/clients.html', liste=liste)


@admin_bp.get('/clients/<int:client_id>/get')
@login_required
def get_client(client_id):
    session['endpoint'] = 'sales'
    item = Client.query.get(client_id)
    if not item:
        return render_template('errors/404.html', blueprint="admin_bp")
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if item.fk_company_id != company:
        return render_template('errors/404.html')
    indexe = 1
    liste = list()
    for order in item.repr(['orders'])['orders']:
        _dict = order
        _dict.update({
            'index': indexe
        })
        liste.append(_dict)
        indexe += 1
    return render_template('admin/client_info.html',
                           item=item.repr(
                               ['id', 'nb_cmd', 'contact', 'category', 'full_name', 'total', 'adjusted', 'to_adjust']),
                           liste=liste)


@admin_bp.get('/clients/<int:client_id>/edit')
@admin_bp.post('/clients/<int:client_id>/edit')
@login_required
def edit_client(client_id):
    session['endpoint'] = 'sales'
    form = EditClientForm()
    _client = Client.query.get(client_id)
    if not _client:
        return render_template('errors/404.html', blueprint="admin_bp")
    if request.method == "GET":
        form = EditClientForm(
            full_name=_client.full_name,
            category=_client.category,
            contacts=Contact.query.filter_by(fk_client_id=_client.id).first().value if Contact.query.filter_by(
                fk_client_id=_client.id).first() else ''
        )

    if form.validate_on_submit():
        c = Client.query.filter(sa.func.lower(Client.full_name) == sa.func.lower(form.full_name.data)).first()
        if c and c.id != _client.id:
            flash('Le nouveau nom existe déjà', 'danger')
            return redirect(url_for('admin_bp.edit_client', client_id=client_id))
        _client.full_name = form.full_name.data

        _client.category = form.category.data
        _contact = Contact.query.filter_by(value=form.contacts.data).first()
        if _contact and _contact.fk_client_id != _client.id:
            flash('Le contact saisie existe déjà', 'danger')
            return redirect(url_for('admin_bp.edit_client', client_id=client_id))
        contact = Contact.query.filter_by(fk_client_id=_client.id).first()
        if not contact:
            contact = Contact()
        contact.key = "téléphone"
        contact.value = form.contacts.data
        contact.fk_client_id = _client.id
        db.session.add(contact)
        db.session.commit()
        flash('Objet modifié avec succès', 'success')
        return redirect(url_for('admin_bp.clients'))
    return render_template('admin/add_client.html', form=form)


@admin_bp.get('/client/add')
@admin_bp.post('/client/add')
@login_required
def add_client():
    form = ClientForm()
    session['endpoint'] = 'sales'
    if form.validate_on_submit():
        _client = Client()
        _client.full_name = form.full_name.data
        _client.category = form.category.data
        _client.fk_company_id = UserForCompany.query.filter_by(role="manager").filter_by(
            fk_user_id=current_user.id).first().fk_company_id
        db.session.add(_client)
        db.session.commit()
        contact = Contact()
        contact.key = 'téléphone'
        contact.value = form.contacts.data
        contact.fk_client_id = _client.id
        db.session.add(contact)
        db.session.commit()
        flash('Objet ajouté avec succès', 'success')
        return redirect(url_for('admin_bp.add_client'))
    return render_template('admin/add_client.html', form=form)


@admin_bp.get('/client/<int:client_id>/delete')
@login_required
def delete_client(client_id):
    session['endpoint'] = 'sales'
    _client = Client.query.get(client_id)
    if not _client:
        return render_template('errors/404.html', blueprint="admin_bp")
    if not _client.orders and not _client.quotations and not _client.invoices:
        contact = Contact.query.filter_by(fk_client_id=_client.id).first()
        if contact:
            db.session.delete(contact)
            db.session.commit()
        db.session.delete(_client)
        db.session.commit()
        return redirect(url_for('admin_bp.clients'))

    _client.is_deleted = True
    db.session.add(_client)
    db.session.commit()
    flash('Objet supprimé avec succès', 'success')
    return redirect(url_for("admin_bp.clients"))


@admin_bp.get('/suppliers')
@login_required
def suppliers():
    session['endpoint'] = 'purchase'
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role='manager').filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers.all():
        flash('Veuillez ajouter tous les fournisseurs', 'warning')
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
                                          .filter_by(fk_user_id=current_user.id).first().fk_company_id).all()
    liste = None
    if _suppliers:
        liste = [
            supplier.repr() for supplier in _suppliers
        ]
    return render_template('admin/suppliers.html', liste=liste)


@admin_bp.get('/suppliers/<int:supplier_id>/edit')
@admin_bp.post('/suppliers/<int:supplier_id>/edit')
@login_required
def edit_supplier(supplier_id):
    session['endpoint'] = 'purchase'
    form = EditSupplierForm()
    supplier = Supplier.query.get(supplier_id)
    if not supplier:
        return render_template('errors/404.html')
    if request.method == "GET":
        form = EditSupplierForm(
            full_name=supplier.full_name,
            category=supplier.category,
            contacts=Contact.query.filter_by(fk_supplier_id=supplier.id).first().value if Contact.query.filter_by(
                fk_supplier_id=supplier.id).first() else ''
        )

    if form.validate_on_submit():
        c = Supplier.query.filter(sa.func.lower(Supplier.full_name) == sa.func.lower(form.full_name.data)).first()
        if c and c.id != supplier.id:
            flash('Le nouveau nom existe déjà', 'danger')
            return redirect(url_for('admin_bp.edit_supplier', supplier_id=supplier_id))
        supplier.full_name = form.full_name.data

        supplier.category = form.category.data
        _contact = Contact.query.filter_by(value=form.contacts.data).first()
        if _contact and _contact.fk_supplier_id != supplier.id:
            flash('Le contact saisie existe déjà', 'danger')
            return redirect(url_for('admin_bp.edit_supplier', supplier_id=supplier_id))

        supplier.full_name = form.full_name.data
        supplier.category = form.category.data
        contact = Contact.query.filter_by(fk_supplier_id=supplier.id).first()
        if not contact:
            contact = Contact()
        contact.key = "téléphone"
        contact.value = form.contacts.data
        contact.fk_supplier_id = supplier.id
        db.session.add(contact)
        db.session.commit()
        flash('Objet modifié avec succès', 'success')
        return redirect(url_for('admin_bp.suppliers'))
    return render_template('admin/add_supplier.html', form=form)


@admin_bp.get('/supplier/add')
@admin_bp.post('/supplier/add')
@login_required
def add_supplier():
    session['endpoint'] = 'purchase'

    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier()
        supplier.full_name = form.full_name.data
        supplier.category = form.category.data
        supplier.fk_company_id = UserForCompany.query.filter_by(role="manager").filter_by(
            fk_user_id=current_user.id).first().fk_company_id
        db.session.add(supplier)
        db.session.commit()
        _contact = Contact()
        _contact.key = 'téléphone'
        _contact.value = form.contacts.data
        _contact.fk_supplier_id = supplier.id
        db.session.add(_contact)
        db.session.commit()
        flash('Objet ajouté avec succès', 'success')
        return redirect(url_for('admin_bp.add_supplier'))
    return render_template('admin/add_supplier.html', form=form)


@admin_bp.get('/suppliers/<int:supplier_id>/delete')
@login_required
def delete_supplier(supplier_id):
    session['endpoint'] = 'purchase'
    _supplier = Supplier.query.get(supplier_id)
    if not _supplier:
        return render_template('errors/404.html')
    if _supplier.orders:
        flash('Impossible de supprimer ce fournisseur', "danger")
        return redirect(url_for('admin_bp.suppliers'))
    contact = Contact.query.filter_by(fk_supplier_id=_supplier.id).first()
    if contact:
        db.session.delete(contact)
        db.session.commit()
    db.session.delete(_supplier)
    db.session.commit()
    flash('Objet supprimé avec succès', 'success')
    return redirect(url_for("admin_bp.suppliers"))


@admin_bp.get('/purchase/orders')
@login_required
def purchases_orders():
    session['endpoint'] = "purchase"
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers.all():
        flash('Veuillez ajouter tous les fournisseurs', 'warning')
    _orders = Order.query.filter_by(category="achat").filter_by(
        fk_company_id=UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id) \
        .first().fk_company_id
        ).filter(Order.is_deleted == False).all()
    liste = list()
    if _orders:
        indexe = 1
        for order in _orders:
            _dict = order.repr()
            _dict.update({'index': indexe})
            indexe += 1
            liste.append(_dict)
    return render_template('admin/purchases_orders.html', liste=liste)


@admin_bp.get("/purchase/orders/add")
@admin_bp.post('/purchase/orders/add')
@login_required
def new_order():
    session['endpoint'] = 'purchase'
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role='manager').filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers:
        flash('Veuillez ajouter tous les fournisseurs', 'warning')
    form = PurchaseOrderForm()
    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    _suppliers = Supplier.query.filter_by(fk_company_id=company)
    if not _suppliers:
        flash("Veuillez d'abord ajouter des fournisseurs", 'warning')

    if form.validate_on_submit():
        entities = list()
        _q = Order()
        _q.created_by = current_user.id
        _q.category = "achat"
        sum_amounts = 0
        if enumerate(form.entities):
            sum_amounts = 0
            for _index, entry in enumerate(form.entities):
                sum_amounts += entry.amount.data
                if entry.quantity.data:
                    entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    # sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    sum_amounts = sum([e.amount.data for i, e in enumerate(form.entities)])
                    return render_template("admin/new_order.html",
                                           form=form, nested=EntryField(),
                                           somme=sum_amounts)
                _ = Entry()
                _.fk_item_id = entry.item.data.id
                _.in_stock = entry.item.data.stock_quantity
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
                    .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                'unit_price': 0,
                'quantity': 1,
                'amount': 0
            })
            return render_template('admin/new_order.html',
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
            return render_template('admin/new_order.html',
                                   form=form,
                                   nested=EntryField(),
                                   somme=sum_amounts)
        if form.order_date.data:
            _q.created_at = form.order_date.data
        _q.created_by = current_user.id
        _q.fk_company_id = company
        _q.fk_supplier_id = form.fournisseur.data.id
        _q.fk_client_id = None
        _q.total = sum_amounts
        last_q = Order.query.filter_by(category="achat").filter_by(fk_company_id=company).order_by(Order.id.desc())
        _q.intern_reference = "BC-1/" + str(datetime.now().date().year)
        if last_q.first():
            last_intern_ref = int(last_q.first().intern_reference.split('-')[1].split('/')[0])
            year = int(last_q.first().intern_reference.split('-')[1].split('/')[1])
            if year == datetime.now().date().year:
                _q.intern_reference = "BC-" + str(last_intern_ref + 1) + "/" + str(datetime.now().date().year)

        db.session.add(_q)
        db.session.commit()
        sum_amounts = 0
        for e in entities:
            sum_amounts += e.total_price
            e.fk_order_id = _q.id
            e.fk_quotation_id, e.fk_exit_voucher_id = None, None
            e.fk_invoice_id, e.fk_delivery_note_id = None, None
            db.session.add(e)
            db.session.commit()
        _q.total = sum_amounts
        db.session.add(_q)
        db.session.commit()
        flash(f'Commande {_q.intern_reference} crée avec succès', 'success')
        # return redirect(url_for('purchases_bp.new_order'))
        return render_template("admin/new_order.html", form=form,
                               somme=_q.total,
                               new_command=True,
                               order_id=_q.id,
                               disable_save=True,
                               nested=EntryField(),
                               to_print=True)
    return render_template("admin/new_order.html", form=form, nested=EntryField(), somme=0)


@admin_bp.get('/quotations')
@login_required
def quotations():
    session['endpoint'] = 'sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role == "manager").first()
    _quotations = Quotation.query.filter_by(fk_company_id=user_for_company.fk_company_id) \
        .filter_by(created_by=current_user.id).filter_by(is_deleted=False) \
        .order_by(Quotation.created_at.desc()).all()
    liste = list()
    if _quotations:
        indexe = 1
        for quotation in _quotations:
            _dict = quotation.repr()
            _dict.update({'index': indexe})
            liste.append(_dict)
            indexe += 1
    return render_template("admin/quotations.html", liste=liste)


@admin_bp.get('/quotations/<int:q_id>/delete')
@login_required
def delete_quotation(q_id):
    session['endpoint'] = 'sales'
    quotation = Quotation.query.get(q_id)
    if not quotation:
        return render_template('errors/404.html', blueprint="sales_bp")

    user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id).filter_by(role="manager").first()
    if quotation.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="admin_bp")
    for e in quotation.entries:
        if not e.fk_order_id and not e.fk_invoice_id and not e.fk_delivery_note_id:
            db.session.delete(e)
            db.session.commit()
    quotation.is_deleted = True
    db.session.add(quotation)
    db.session.commit()
    flash('Objet Supprimé avec succès', 'success')
    return redirect(url_for('admin_bp.quotations'))


# @admin_bp.get('/quotations/<int:q_id>/get')
# @login_required
# def get_quotation(q_id):
#     session['endpoint'] = 'sales'
#     quotation = Quotation.query.get(q_id)
#
#     if not quotation:
#         return render_template('errors/404.html', blueprint="admin_bp")
#
#     user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id).filter_by(role="manager").first()
#     if quotation.fk_company_id != user_for_company.fk_company_id:
#         return render_template('errors/404.html', blueprint="admin_bp")
#
#     return render_template("admin/quotation_info.html", quotation=quotation.repr())


from root.ventes.forms import QuotationForm, EntryField
from root.models import Entry


@admin_bp.get('/quotations/add')
@admin_bp.post('/quotations/add')
@login_required
def add_quotation():
    session['endpoint'] = 'sales'
    form = QuotationForm()
    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    _clients = Client.query.filter_by(fk_company_id=company)
    if not _clients:
        flash("Veuillez d'abord ajouter des clients", 'warning')

    if form.validate_on_submit():
        entities = list()
        _q = Quotation()
        sum_amounts = 0
        if enumerate(form.entities):
            for _index, entry in enumerate(form.entities):
                if entry.quantity.data:
                    entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    return render_template("sales/new_quotation.html",
                                           form=form, nested=EntryField(),
                                           somme=sum_amounts)
                _ = Entry()
                _.fk_item_id = entry.item.data.id
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
        _q.fk_client_id = form.client.data.id
        _q.total = sum_amounts
        # db.session.add(_q)
        # db.session.commit()
        last_q = Quotation.query.filter_by(fk_company_id=company).order_by(Quotation.created_at.desc()).first()
        if last_q:
            last_intern_ref = last_q.intern_reference.split('-')[1].split('/')[0]
            year = last_q.intern_reference.split('-')[1].split('/')[2]
            if year == dt.now().date().year:
                _q.intern_reference = "DEV-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
                    dt.now().date().year)
            else:
                _q.intern_reference = "DEV-1/" + str(company) + "/" + str(dt.now().date().year)
        else:
            _q.intern_reference = "DEV-1/" + str(company) + "/" + str(dt.now().date().year)
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
        flash('Devis crée avec succès', 'success')
        # return redirect(url_for('sales_bp.add_quotation'))
        return render_template("sales/new_quotation.html", form=form,
                               somme=_q.total,
                               nested=EntryField(),
                               to_approve=True,
                               to_print=True)
    return render_template("sales/new_quotation.html", form=form, nested=EntryField(), somme=0)


@admin_bp.get('/quotation/<int:q_id>/approve')
@login_required
def approve_quotation(q_id):
    session['endpoint'] = 'sales'
    quotation = Quotation.query.get(q_id)
    if not quotation:
        return render_template('errors/404.html', blueprint="admin_bp")

    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if quotation.is_deleted or quotation.fk_company_id != company:
        return render_template('errors/404.html', blueprint="admin_bp")

    if quotation.is_approved:
        flash('Devis déjà approuvé', 'warning')
        return redirect(url_for('admin_bp.quotations'))

    quotation.is_approved = True
    db.session.add(quotation)
    db.session.commit()
    flash(f'Devis {quotation.intern_reference} est approuvé', 'success')
    return redirect(url_for('admin_bp.quotations'))


from root.models import Order


@admin_bp.get('/quotations/<int:q_id>/get/order')
@login_required
def quotation_order(q_id):
    session['endpoint'] = "sales"
    quotation = Quotation.query.get(q_id)
    if not quotation:
        return render_template('errors/404.html', blueprint="admin_bp")

    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if quotation.is_deleted or quotation.fk_company_id != company:
        return render_template('errors/404.html', blueprint="admin_bp")

    entities = quotation.entries
    order = Order()
    last_o = Order.query.filter_by(fk_company_id=company).order_by(Order.created_at.desc()).first()
    if last_o and last_o.intern_reference.split('/')[1] == str(dt.now().date().year):
        last_intern_ref = last_o.intern_reference.split('-').split('/')[0]
        order.intern_reference = "BC-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
            dt.now().date().year)
    else:
        order.intern_reference = "BC-1/" + str(company) + "/" + str(dt.now().date().year)
    order.fk_client_id = quotation.fk_client_id
    order.category = "vente"
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
    return redirect(url_for('admin_bp.quotations'))


from root.models import Invoice


@admin_bp.get('/quotations/<int:q_id>/get/invoice')
@login_required
def quotation_invoice(q_id):
    session['endpoint'] = "sales"
    quotation = Quotation.query.get(q_id)
    if not quotation:
        return render_template('errors/404.html', blueprint="admin_bp")

    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    if quotation.is_deleted or quotation.fk_company_id != company:
        return render_template('errors/404.html', blueprint="admin_bp")

    entities = quotation.entries
    invoice = Invoice()
    last_o = Order.query.filter_by(fk_company_id=company).order_by(Order.created_at.desc()).first()
    if last_o and last_o.intern_reference.split('/')[1] == str(dt.now().date().year):
        last_intern_ref = last_o.intern_reference.split('-').split('/')[0]
        invoice.intern_reference = "BL-" + (last_intern_ref + 1) + "/" + str(company) + "/" + str(
            dt.now().date().year)
    else:
        invoice.intern_reference = "BL-1/" + str(company) + "/" + str(dt.now().date().year)
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
    return redirect(url_for('admin_bp.quotations'))


@admin_bp.get('/orders')
@login_required
def orders():
    session['endpoint'] = 'sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role == "manager").first()
    _orders = Order.query.filter_by(fk_company_id=user_for_company.fk_company_id) \
        .order_by(Order.created_at.desc()).all()
    liste = list()
    if _orders:
        indexe = 1
        for quotation in _orders:
            _dict = quotation.repr()
            _dict.update({'index': indexe})
            liste.append(_dict)
            indexe += 1
    return render_template("admin/orders.html", liste=liste)


from root.models import User
from root.admin.forms import PaiementForm


@admin_bp.get('/invoices')
@admin_bp.post('/invoices')
@login_required
def invoices():
    session['endpoint'] = 'sales'
    user_for_company = UserForCompany.query.filter(UserForCompany.fk_user_id == current_user.id) \
        .filter(UserForCompany.role == "manager").first()
    """\.filter_by(is_deleted=False)"""
    _orders = Invoice.query.filter_by(inv_type="vente").filter_by(fk_company_id=user_for_company.fk_company_id) \
        .order_by(Invoice.id.desc()).all()
    liste = list()
    form = PaiementForm()
    if _orders:
        indexe = 1
        for quotation in _orders:
            _dict = quotation.repr()
            _dict.update({'index': indexe})
            liste.append(_dict)
            indexe += 1
    if form.validate_on_submit():
        code = request.form.get('code')
        invoice = Invoice.query.filter_by(intern_reference=code).first()
        if not invoice:
            flash('Facture introuvable', 'danger')
            return redirect(url_for('admin_bp.invoices'))
        pay = Pay()
        pay.fk_company_id = user_for_company.fk_company_id
        pay.fk_invoice_id = invoice.id
        pay.created_by = current_user.id
        pay.amount = float(form.amount.data)
        pay.is_in_cash = True
        pay.label = f"paiement de la facture  {invoice.intern_reference}"
        pay.pay_information = f"Paiement d'une facture d'où de code = {invoice.intern_reference} générée par {User.query.get(invoice.created_by).full_name} avec total de {invoice.total}, le {invoice.created_at.date()}"
        db.session.add(pay)
        db.session.commit()

        flash(f'{form.data.get("code")} a été payée', 'success')
        return redirect(url_for('admin_bp.invoices'))
    print(form.errors)
    return render_template("admin/invoices.html", form=form, liste=liste)


from num2words import num2words
from flask_weasyprint import HTML, render_pdf


@admin_bp.get('/invoices/<int:i_id>/print')
@login_required
def print_invoice(i_id):
    invoice = Invoice.query.filter_by(inv_type='vente').filter_by(id=i_id).first()
    if not invoice:
        return render_template('errors/404.html', blueprint='admin_bp')
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
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
                           titre="Facture de vente",
                           total_letters=str.upper(total_letters))

    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'facture_{invoice.intern_reference}.pdf',
                      automatic_download=False)


@admin_bp.get('/sales/delivery')
@login_required
def delivery_notes():
    return render_template('sales/deliveries.html')


@admin_bp.get('/inventory')
@admin_bp.post('/inventory')
@login_required
def create_inventory():
    session['endpoint'] = "stocks"
    form = InventoryForm()
    if form.validate_on_submit():
        stock = Stock.query.filter_by(fk_item_id=form.item.data.id) \
            .filter_by(fk_warehouse_id=form.warehouse.data.id) \
            .first()
        if not stock:
            stock = Stock()
            stock.fk_warehouse_id = form.warehouse.data.id
            stock.fk_item_id = form.item.data.id
            db.session.add(stock)
            db.session.commit()
        stock.stock_qte += float(form.quantity.data)
        stock.created_by = current_user.id
        stock.last_purchase = form.purchase_date.data
        stock.last_purchase_price = form.purchase_price.data
        db.session.add(stock)
        db.session.commit()
        item = Item.query.get(form.item.data.id)
        entry = Entry()
        entry.fk_item_id = item.id
        item.stock_quantity += float(form.quantity.data)
        db.session.add(item)
        db.session.commit()
        entry.in_stock = item.stock_quantity
        entry.quantity = stock.stock_qte
        entry.unit_price = stock.last_purchase_price
        entry.total_price = stock.stock_qte * stock.last_purchase_price
        db.session.add(entry)
        db.session.commit()
        item = Item.query.get(form.item.data.id)
        item.purchase_price = float(form.purchase_price.data)
        item.sale_price = float(form.sale_price.data)
        db.session.add(item)
        db.session.commit()
        flash('Objet crée avec succès', 'success')
        # return redirect(url_for('admin_bp.create_inventory'))
        return render_template('admin/new_inventory.html', form=form)
    return render_template('admin/new_inventory.html', form=form)


@admin_bp.post('/item_unit')
@login_required
def get_unit():
    data = request.json
    item = Item.query.get(int(data['item_id']))
    if not item:
        return '', 404
    return jsonify(unit=item.unit, price=item.purchase_price), 200


@admin_bp.get('/expenses')
@admin_bp.post('/expenses')
@login_required
def expenses():
    session['endpoint'] = "purchase"
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers.all():
        flash('Veuillez ajouter tous les fournisseurs', 'warning')

    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()

    if not ExpenseCategory.query.filter_by(fk_company_id=company.fk_company_id).all():
        flash('Veuillez ajouter toutes les catégories de dépense que vous avez besoins', 'warning')

    _expenses = Expense.query.filter_by(fk_company_id=company.fk_company_id).all()
    liste = list()
    if _expenses:
        indexe = 1
        for expense in _expenses:
            _dict = expense.repr()
            _dict.update(
                {
                    'indexe': indexe
                }
            )
            liste.append(_dict)
            indexe += 1
    form = ExpenseForm()
    if form.validate_on_submit():
        expense = Expense()
        expense.label = form.label.data
        if form.description.data:
            expense.description = form.description.data
        expense.fk_category_id = form.expense_category.data.id
        expense.amount = float(form.amount.data)
        expense.fk_company_id = company.fk_company_id
        expense.created_by = current_user.id
        db.session.add(expense)
        db.session.commit()
        flash('Dépense ajoutée', 'success')
        return redirect(url_for('admin_bp.expenses'))

    _company = Company.query.get(company.fk_company_id)

    return render_template('admin/expenses.html',
                           item=_company.repr(['adjusted_invoices', 'total', 'rest_to_adjust']),
                           liste=liste, form=form)


@admin_bp.get('/expense_categories')
@admin_bp.post('/expense_categories')
@login_required
def expense_categories():
    session['endpoint'] = "purchase"
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers.all():
        flash('Veuillez ajouter tous les fournisseurs', 'warning')
    form = ExpenseCategoryForm()
    liste = list()
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    categories = ExpenseCategory.query.filter_by(is_deleted=False) \
        .filter_by(fk_company_id=company.fk_company_id).all()
    if categories:
        indexe = 1
        for category in categories:
            _dict = category.repr()
            _dict.update({
                'index': indexe
            })
            liste.append(_dict)
            indexe += 1

    if form.validate_on_submit():
        category = ExpenseCategory()
        category.label = form.label.data
        category.fk_company_id = company.fk_company_id
        db.session.add(category)
        db.session.commit()
        flash('Objet Ajouté', 'success')
        return redirect(url_for('admin_bp.expense_categories'))

    return render_template('admin/expense_categories.html', form=form, liste=liste)


@admin_bp.get('/expense_categories/<int:e_id>/delete')
@login_required
def delete_category(e_id):
    category = ExpenseCategory.query.get(e_id)
    if not category:
        return render_template('errors/404.html', blueprint="admin_bp")
    if category.is_deleted:
        return render_template('errors/404.html', blueprint="admin_bp")
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    if not company:
        return render_template('errors/404.html', blueprint="admin_bp")
    if category.fk_company_id != company.fk_company_id:
        return render_template('errors/404.html', blueprint="admin_bp")
    category.is_deleted = True
    db.session.add(category)
    db.session.commit()
    flash(f'la catégorie "{category.label}" est supprimée', 'success')
    return redirect(url_for('admin_bp.expense_categories'))


@admin_bp.get('/receipts')
@login_required
def purchase_receipts():
    session['endpoint'] = "purchase"
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers.all():
        flash('Veuillez ajouter tous les fournisseurs', 'warning')
    _receipts = PurchaseReceipt.query.filter_by(is_deleted=False) \
        .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
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
    return render_template("admin/purchases_receipts.html", liste=liste)


@admin_bp.get('/receipts/add')
@admin_bp.post('/receipts/add')
@login_required
def new_purchase_receipt():
    session['endpoint'] = 'orders'
    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    _suppliers = Supplier.query.filter_by(fk_company_id=company)
    if not _suppliers:
        flash("Veuillez d'abord ajouter des fournisseurs", 'warning')
    form = PurchaseReceiptForm()
    if form.validate_on_submit():
        entities = list()
        _q = PurchaseReceipt()
        _q.created_by = current_user.id
        sum_amounts = 0
        document = Order.query.get(form.command_reference.data.id)
        if enumerate(form.entities):
            sum_amounts = 0
            for _index, entry in enumerate(form.entities):

                sum_amounts += entry.amount.data
                if entry.quantity.data:
                    entry.amount.data = entry.unit_price.data * entry.quantity.data
                if entry.delete_entry.data:
                    sum_amounts -= entry.amount.data
                    del form.entities.entries[_index]
                    return render_template("admin/new_receipt.html",
                                           form=form, nested=PurchaseField())

                item = Item.query.get(entry.item.data.id)
                item.sale_price = float(entry.sale_price.data)
                db.session.add(item)
                db.session.commit()
                _ = Entry()

                _.delivered_quantity = float(entry.quantity.data)
                c_entry = Entry.query.filter_by(fk_order_id=form.command_reference.data.id) \
                    .filter_by(fk_item_id=entry.item.data.id).filter(Entry.fk_purchase_receipt_id == None) \
                    .first()
                if c_entry:
                    _.quantity = c_entry.quantity
                _.fk_item_id = entry.item.data.id
                _.fk_order_id = form.command_reference.data.id
                _.in_stock = entry.item.data.stock_quantity
                _.unit_price = entry.unit_price.data
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
                    'item': Item.query.join(Entry, Entry.fk_item_id == Item.id) \
                        .filter(Item.fk_company_id == company) \
                        .filter(Item.is_disabled == False) \
                        .filter(Entry.fk_order_id == form.command_reference.data.id).all(),
                    'unit_price': 0,
                    'quantity': 1,
                    'amount': 0
                })
                return render_template('admin/new_receipt.html',
                                       form=form,
                                       somme=sum_amounts,
                                       nested=PurchaseField())
            else:
                form.entities.append_entry({
                    'item': Item.query.filter_by(is_disabled=False) \
                        .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
                                   .filter_by(fk_user_id=current_user.id).first().fk_company_id).all(),
                    'unit_price': 0,
                    'quantity': 1,
                    'amount': 0
                })
                return render_template('admin/new_receipt.html',
                                       form=form,
                                       somme=sum_amounts,
                                       nested=PurchaseField())
        if form.fin.data:
            if enumerate(form.entities):
                sum_amounts = 0
                for _index, entry in enumerate(form.entities):
                    if entry.quantity.data:
                        entry.amount.data = entry.unit_price.data * entry.quantity.data
                    sum_amounts += entry.amount.data
            return render_template('admin/new_receipt.html',
                                   form=form,
                                   somme=sum_amounts,
                                   nested=PurchaseField())

        if enumerate(form.entities):
            for _index, entry in enumerate(form.entities):
                stock = Stock.query.filter_by(fk_item_id=entry.item.data.id).first()
                if not stock:
                    flash(f"Article {Item.query.get(entry.item.data.id).label} n'a pas de stock", 'warning')
                    return render_template("admin/new_receipt.html",
                                           form=form, nested=PurchaseField(),
                                           somme=sum_amounts)
            for _index, entry in enumerate(form.entities):

                c_entry = Entry.query.filter_by(fk_order_id=form.command_reference.data.id) \
                    .filter_by(fk_item_id=entry.item.data.id).filter(Entry.fk_purchase_receipt_id == None) \
                    .first()
                if c_entry:
                    if (c_entry.quantity - c_entry.delivered_quantity) < float(entry.quantity.data):
                        flash(
                            f"La quantity du {Item.query.get(entry.item.data.id).label} est suppérieur à la quantity commandée",
                            "warning")
                        return render_template("admin/new_receipt.html",
                                               form=form, nested=PurchaseField(),
                                               somme=sum_amounts)
                    # else:
                    c_entry.delivered_quantity += float(entry.quantity.data)
                    db.session.add(c_entry)

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
        last_q = PurchaseReceipt.query.filter_by(fk_company_id=company).order_by(PurchaseReceipt.id.desc()).first()
        _q.intern_reference = "BR-1/" + str(datetime.now().date().year)
        if last_q:
            last_intern_ref = int(last_q.intern_reference.split('-')[1].split('/')[0])
            year = int(last_q.intern_reference.split('-')[1].split('/')[1])
            if year == datetime.now().date().year:
                _q.intern_reference = "BR-" + str(last_intern_ref + 1) + "/" + str(datetime.now().date().year)
        db.session.add(_q)
        db.session.commit()
        sum_amounts = 0
        for e in entities:
            sum_amounts += e.total_price
            e.fk_purchase_receipt_id = _q.id
            e.fk_quotation_id, e.fk_exit_voucher_id = None, None
            e.fk_invoice_id, e.fk_delivery_note_id = None, None
            item = Item.query.get(e.fk_item_id)
            # item.sale_price = e.sale_price.data
            _price = e.unit_price
            db.session.add(item)
            db.session.commit()
            db.session.add(e)
            db.session.commit()
            stock = Stock.query.filter_by(fk_item_id=e.fk_item_id).first()
            stock.stock_qte += e.delivered_quantity
            stock.last_purchase_price = e.unit_price
            db.session.add(stock)
            db.session.commit()
        to_valid = True
        db.session.add(_q)
        db.session.commit()
        for _e in document.entries:
            if _e.quantity != _e.delivered_quantity:
                to_valid = False
        if to_valid:
            document.is_delivered = True
            db.session.add(document)
            db.session.commit()
        _q.total = sum_amounts
        _q.fk_order_id = form.command_reference.data.id
        db.session.add(_q)
        db.session.commit()
        flash(f'Bon {_q.intern_reference} crée avec succès', 'success')
        return render_template("admin/new_receipt.html", form=form,
                               somme=_q.total,
                               new_command=True,
                               disable_save=True,
                               nested=PurchaseField(),
                               to_print=True)
    return render_template("admin/new_receipt.html", form=form, nested=PurchaseField(), somme=0)


@admin_bp.post('/price')
@login_required
def get_purchase_price():
    data = request.json
    if not data:
        return jsonify(
            message='Demande annulé'
        ), 400
    if 'cmd_id' not in data or 'product' not in data:
        return jsonify(
            text="Demande annulé"
        ), 400
    if data['cmd_id'] == '__None':
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
        ), 404
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if order.fk_company_id != company:
        return jsonify(
            text="Erreur inattendue"
        ), 404
    for entry in order.entries:
        if entry.fk_item_id == int(data['product']):
            return jsonify(
                unit=Item.query.get(entry.fk_item_id).unit,
                price=entry.unit_price,
                quantity=entry.quantity,
                delivered_quantity=entry.delivered_quantity,
                amount=entry.unit_price * entry.quantity,
                sum=float(data['sum']) + float(entry.quantity * entry.unit_price)
            ), 200
    return jsonify(
        text=f"Article ne se trouve pas dans la commande {Order.query.get(data['cmd_id']).intern_reference}"), 404


@admin_bp.get('/commands')
@login_required
def get_commands():
    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id).first().fk_company_id
    commands = Order.query.filter(Order.is_deleted == False).filter_by(fk_company_id=company)
    if 'type' in request.args:
        commands = commands.filter_by(category=request.args.get('type'))
    if "search" in request.args:
        commands = commands.filter(Order.is_canceled == None) \
            .filter(Order.intern_reference.like(func.lower(f'%{request.args["search"]}%')))
    data = list()
    if commands.all():
        for command in commands.all():
            b = Client.query.get(command.fk_client_id) if command.fk_client_id else None
            if b:
                data.append({
                    'id': command.id,
                    'text': str.upper(Client.query.get(command.fk_client_id).full_name) + "," + command.intern_reference
                            + ' ,Le ' + str(command.created_at.date())
                })
            else:
                data.append({
                    'id': command.id,
                    'text': str.upper(Supplier.query.get(
                        command.fk_supplier_id).full_name) + ", " + command.intern_reference + ' ,Le ' + str(
                        command.created_at.date())
                })
        return jsonify(total_count=len(data),
                       items=data), 200
    return jsonify(total_count=0,
                   items=[]), 404


@admin_bp.route('/purchases/purchase_invoices', methods=['GET', 'POST'])
@login_required
def purchase_invoices():
    session['endpoint'] = "purchase"
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers.all():
        flash('Veuillez ajouter tous les fournisseurs', 'warning')
    form = ExpenseForm()
    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id) \
        .first().fk_company_id
    _invoices = Invoice.query.filter_by(fk_company_id=company).all()
    liste = list()
    if _invoices:
        indexe = 1
        for receipt in _invoices:
            _dict = receipt.repr()
            _dict.update({'index': indexe})
            indexe += 1
            liste.append(_dict)
    form.label.data = "rien a ecrire"
    form.description.data = "rien à ecrire"
    if form.validate_on_submit():
        print(form.expense_category.data)
        code = request.form.get('code')
        invoice = Invoice.query.filter_by(intern_reference=code).first()
        if not invoice:
            flash('Facture introuvable', 'danger')
            return redirect(url_for('admin_bp.purchase_invoices'))
        expense = Expense()
        expense.fk_company_id = company
        expense.fk_category_id = form.expense_category.data.id
        expense.created_by = current_user.id
        expense.amount = float(form.amount.data)
        expense.label = f"paiement de la facture  {invoice.intern_reference}"
        expense.fk_invoice_id = invoice.id
        expense.description = f"Paiement d'une facture d'où de code = {invoice.intern_reference} générée par {User.query.get(invoice.created_by).full_name} avec total de {invoice.total}, le {invoice.created_at.date()}"
        db.session.add(expense)
        db.session.commit()
        flash(f'Le paiement à été terminé avec succès', 'success')
        return redirect(url_for('admin_bp.purchase_invoices'))

    return render_template("admin/purchase_invoices.html", liste=liste, form=form)


@admin_bp.post('/info')
@login_required
def get_info():
    data = request.json
    if 'invoice_id' not in data:
        return '', 400

    if len(data) != 1:
        return '', 400

    invoice = Invoice.query.filter_by(intern_reference=data['invoice_id']).first()
    if not invoice:
        return '', 404
    total = Expense.query.filter_by(fk_invoice_id=invoice.id).all()
    total = sum([t.amount for t in total])
    return jsonify(
        code=invoice.intern_reference,
        montant='{:,.2f}'.format(invoice.total),
        reste='{:,.2f}'.format(invoice.total - total)), 200


@admin_bp.get('/purchase/invoices/<int:i_id>/print')
@login_required
def print_purchase_invoice(i_id):
    invoice = Invoice.query.filter_by(inv_type='achat').filter_by(id=i_id).first()
    if not invoice:
        return render_template('errors/404.html', blueprint='admin_bp')
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
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
                      download_filename=f'facture d\'achat_{invoice.intern_reference}.pdf',
                      automatic_download=False)


@admin_bp.get('/purchase/order/<int:o_id>/print')
@login_required
def print_purchase_order(o_id):
    session['endpoint'] = "purchase"
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers.all():
        flash('Veuillez ajouter tous les fournisseurs', 'warning')
    order = Order.query.filter_by(category='achat').filter_by(id=o_id).first()
    if not order:
        return render_template('errors/404.html', blueprint='admin_bp')
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
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
                           company=company.repr(),
                           titre="Bon d'achat",
                           object=order.repr(),
                           total_letters=str.upper(total_letters))
    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'bon de achat_{order.intern_reference}.pdf',
                      automatic_download=False)


@admin_bp.get('/purchase/orders/<int:o_id>/delete')
@login_required
def delete_purchase_order(o_id):
    session['endpoint'] = 'purchase'

    order = Order.query.filter_by(category="achat").filter_by(id=o_id).first()

    if not order:
        return render_template('errors/404.html', blueprint="admin_bp")

    user_for_company = UserForCompany.query.filter_by(fk_user_id=current_user.id) \
        .filter_by(role="manager").first()

    if order.fk_company_id != user_for_company.fk_company_id:
        return render_template('errors/404.html', blueprint="admin_bp")

    for e in order.entries:
        db.session.delete(e)
        db.session.commit()
    order.is_deleted = True
    db.session.add(order)
    db.session.commit()
    flash('Objet Supprimé avec succès', 'success')
    return redirect(url_for('admin_bp.purchases_orders'))


@admin_bp.get('/purchases/orders/<int:o_id>/receipt')
@login_required
def order_receipt(o_id):
    session['endpoint'] = "purchase"
    _suppliers = Supplier.query.filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not _suppliers.all():
        flash('Veuillez ajouter tous les fournisseurs', 'warning')
    order = Order.query.get(o_id)
    if not order:
        return render_template("errors/404.html", blueprint="admin_bp")

    if order.category != "achat":
        return render_template('errors/404.html', blueprint="admin_bp")

    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if order.fk_company_id != company:
        return render_template('errors/404.html',
                               blueprint="admin_bp")

    if order.is_canceled:
        flash('Impossible de créer un bon réception pour une commande annulé', 'danger')
        return redirect(url_for('admin_bp.purchases_orders'))
    order.is_delivered = True
    db.session.add(order)
    db.session.commit()
    p_receipt = PurchaseReceipt()
    last_q = PurchaseReceipt.query.filter_by(fk_company_id=company).order_by(
        PurchaseReceipt.created_at.desc()).first()
    p_receipt.intern_reference = "BR-1/" + str(datetime.now().date().year)
    if last_q:
        last_intern_ref = int(last_q.intern_reference.split('-')[1].split('/')[0])
        year = int(last_q.intern_reference.split('-')[1].split('/')[1])
        if year == datetime.now().date().year:
            p_receipt.intern_reference = "BR-" + str(last_intern_ref + 1) + "/" + str(datetime.now().date().year)
    p_receipt.fk_supplier_id = order.fk_supplier_id
    p_receipt.created_by = current_user.id
    p_receipt.total = order.total
    p_receipt.fk_company_id = order.fk_company_id
    p_receipt.fk_order_id = order.id
    db.session.add(p_receipt)
    db.session.commit()
    for e in order.entries:
        _ = Entry()
        _.delivered_quantity = float(e.quantity)
        _.fk_item_id = e.fk_item_id
        _.fk_order_id = e.fk_order_id
        item = Item.query.get(e.fk_item_id)
        _.in_stock = item.stock_quantity
        _.unit_price = e.unit_price
        item.purchase_price = e.total_price
        # item.sale_price = e.sale_price
        _.total_price = e.amount
        # e.fk_purchase_receipt_id = p_receipt.id
        e.delivered_quantity = e.quantity
        e.in_stock = item.stock_quantity
        stock = Stock.query.filter_by(fk_item_id=e.fk_item_id).first()
        if stock:
            stock.stock_qte += e.quantity
            stock.last_purchase_price = e.unit_price
            db.session.add(stock)
            db.session.commit()
        # else:
        # flash(f'Veuillez rajouter des stock pour le produit {Item.query.get(e.fk_item_id)}','warning')
        # return redirect(url_for('purchases_bp.purchases_receipts'))
        # item = Item.query.get(e.fk_item_id)
        # item.stock_quantity += e.quantity
        db.session.add(e)
        db.session.commit()
        db.session.add(_)
        db.session.commit()
    flash(f'Entrée {p_receipt.intern_reference} sauvegardée', 'success')
    print('''
    générer un PDF à télécharger par le manager et le magasiner
    ''')
    return redirect(url_for('admin_bp.purchases_orders'))


@admin_bp.get('/purchase/receipt/<int:r_id>/print')
@login_required
def print_receipt(r_id):
    receipt = PurchaseReceipt.query.filter_by(id=r_id).first()
    if not receipt:
        return render_template('errors/404.html', blueprint='admin_bp')
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
    if not company:
        return render_template('errors/401.html')
    if receipt.fk_company_id != company.fk_company_id:
        return render_template('errors/401.html')
    company = Company.query.get(company.fk_company_id)
    total_letters = num2words(receipt.total, lang='fr') + " dinars algérien"
    virgule = receipt.total - float(int(receipt.total))
    if virgule > 0:
        total_letters += f' et {int(round(virgule, 2))} centimes'
    html = render_template('printouts/printable_template.html',
                           company=company.repr(),
                           object=receipt.repr_(),
                           titre="Bon de réception",
                           total_letters=str.upper(total_letters))

    response = HTML(string=html)
    return render_pdf(response,
                      download_filename=f'bon de réception_{receipt.intern_reference}.pdf',
                      automatic_download=False)


@admin_bp.get('/purchase/receipt/<int:r_id>/invoice')
@admin_bp.post('/purchase/receipt/<int:r_id>/invoice')
@login_required
def receipt_invoice(r_id):
    receipt = PurchaseReceipt.query.get(r_id)
    if not receipt:
        return render_template('errors/404.html', blueprint="admin_bp")
    company = UserForCompany.query.filter_by(role="manager") \
        .filter_by(fk_user_id=current_user.id) \
        .first().fk_company_id
    if receipt.fk_company_id != company:
        return render_template('errors/404.html', blueprint="admin_bp")

    invoice = Invoice.query.filter_by(fk_receipt_id=receipt.id).first()
    if invoice:
        flash('Bon déjà facturé', 'warning')
        return redirect(url_for('admin_bp.purchase_receipts'))
    form = InvoiceForm()
    sum_amounts = 0
    if request.method == "GET":
        form.recipient.data = Supplier.query.get(receipt.fk_supplier_id)
        form.order_date.data = receipt.created_at.date()
        for entry in receipt.entries:
            sum_amounts += entry.quantity * entry.unit_price
            form.entities.append_entry({
                'item': Item.query.get(entry.fk_item_id),
                'unit_price': entry.unit_price,
                'quantity': entry.quantity,
                'amount': entry.quantity * entry.unit_price
            })

    if form.validate_on_submit():
        invoice = Invoice()
        invoice.fk_company_id = company
        invoice.fk_supplier_id = form.recipient.data.id
        invoice.total = receipt.total
        invoice.created_by = current_user.id
        invoice.fk_receipt_id = receipt.id
        invoice.is_valid = True
        invoice.inv_type = "achat"
        invoice.reference_supplier_invoice = None
        if form.reference_supplier_invoice.data:
            invoice.reference_supplier_invoice = form.reference_supplier_invoice.data
        last_q = Invoice.query.filter_by(inv_type="achat").filter_by(fk_company_id=company).order_by(
            Invoice.created_at.desc()).first()
        invoice.intern_reference = "FAC-1/" + str(datetime.now().date().year)
        if last_q:
            last_intern_ref = int(last_q.intern_reference.split('-')[1].split('/')[0])
            year = int(last_q.intern_reference.split('-')[1].split('/')[1])
            if year == datetime.now().date().year:
                invoice.intern_reference = "FAC-" + str(last_intern_ref + 1) + "/" + str(datetime.now().date().year)

        invoice.fk_order_id = PurchaseReceipt.query.get(invoice.fk_receipt_id).fk_order_id
        db.session.add(invoice)
        db.session.commit()
        for entry in receipt.entries:
            entry.fk_invoice_id = invoice.id
            db.session.add(entry)
            db.session.commit()
        flash('Document sauvegardée', 'success')
        return redirect(url_for("admin_bp.purchase_receipts"))
    return render_template('purchases/new_invoice.html', somme=sum_amounts,
                           nested=InvoiceEntryField(), form=form)


@admin_bp.post('/purchase/expense_info')
@login_required
def expense_info():
    data = request.json
    expense = Expense.query.get(int(data['exp_id']))
    days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    if not expense:
        return '', 404
    return jsonify(
        title=expense.label,
        description=expense.description,
        day=days[datetime.weekday(expense.created_at.date())],
        date=datetime.strftime(expense.created_at, "%d-%m-%Y"),
        hours=datetime.strftime(expense.created_at, "%H:%M")
    )

# @admin_bp.get('/sales/<int:o_id>/delivery')
# @login_required
# def order_delivery(o_id):
#     return redirect(url_for('admin_bp.orders'))
