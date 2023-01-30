from flask import render_template, session, flash, redirect, url_for, request, jsonify
from root.admin import admin_bp
from root import database
from flask_login import login_required
from root.admin.forms import *
from root.models import Tax, User, InvoiceTax, OrderTax, Warehouse, Stock, Store
from werkzeug.security import generate_password_hash

@admin_bp.before_request
def admin_before_request():
    session['actual_role'] = "admin"


@admin_bp.get('/')
@login_required
def index():
    return render_template("admin/master_dashboard.html")


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
        if form.sell_or_bye.data:
            tax.for_sell = True
        else:
            tax.for_buy = True

        if form.applied_before_TVA.data:
            tax.applied_before_TVA = True
        else:
            tax.applied_after_TVA = True
        if form.on_applied_products.data:
            tax.on_applied_products = True

        if form.on_applied_TVA.data:
            tax.on_applied_TVA = True
        database.session.add(tax)
        database.session.commit()
        flash('Ajout avec succès','success')
        return redirect(url_for('admin_bp.new_taxes'))
    return render_template('admin/new_taxes.html', form = form)


@admin_bp.get('/taxes/<int:tax_id>/delete')
@login_required
def delete_tax(tax_id):
    tax = Tax.query.get(tax_id)
    if not tax:
        return render_template("errors/404.html", blueprint='admin_bp')

    invoices_taxes = InvoiceTax.query.filter_by(fk_tax_id = tax.id).all()
    orders_taxes = OrderTax.query.filter_by(fk_tax_id = tax.id).all()
    if invoices_taxes is not None or orders_taxes is not None:
        flash('Opération impossible: tax déjà utilisé', 'danger')
        return redirect(url_for("admin_bp.taxes"))

    database.session.delete(tax)
    database.session.commit()
    flash('Suppression avec succès','success')
    return redirect(url_for('admin_bp.taxes'))


@admin_bp.get('/taxes/<int:tax_id>/edit')
@login_required
def edit_tax(tax_id):
    form = TaxesForm()
    tax = Tax.query.get(tax_id)
    if not tax:
        return render_template('errors/404.html', blueprint='admin_bp')

    if request.method=="GET":
        form.name.data = tax.name
        form.label.data = tax.label
        form.value.data = tax.value
        form.sign.data = tax.sign
        form.on_applied_products.data = True if tax.on_applied_products else False
        form.applied_before_TVA.data = True if tax.applied_before_TVA==True else False

    if form.validate_on_submit():
        tax_1 = Tax.query.filter_by(created_by = current_user.id).filter(func.lower(Tax.label) == str.lower(form.label.data)).first()
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

        database.session.add(tax)
        database.session.commit()
        flash('Ajout avec succès', 'success')
        return redirect(url_for('admin_bp.new_taxes'))
    return render_template('admin/new_taxes.html', form=form)


@admin_bp.post('/taxes/get')
@login_required
def get_tax():
    data = request.json()
    tax = Tax.query.get(data['tax_id'])
    fixed="Fixée" if tax.is_fixed else "%"
    applied_before = "Avant TVA" if tax.applied_before_TVA == True else "Après TVA"
    if tax:
        return jsonify(message = f"<h5 class='h5'>{tax.name}</h5> \
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
    return render_template('admin/taxes.html', liste = liste)


@admin_bp.get('/warehouses/add')
@login_required
def add_warehouse():
    form = WarehouseForm()
    if form.validate_on_submit():
        warehouse = Warehouse(
            name = form.name.data,
            address = form.address.data,
            contact = form.contact.data,
            company_id = UserForCompany.query.filter_by(fk_user_id = current_user.id) \
                .filter_by(role="manager").first().fk_company_id
        )
        database.session.add(warehouse)
        database.session.commit()
        flash('Ajout avec succès', 'success')
    return render_template("admin/new_warehouse.html", form = form)


@admin_bp.get('/warehouses')
@login_required
def warehouses():
    _warehouses = Warehouse.query \
                    .filter_by(fk_company_id = UserForCompany.query.filter_by(role="manager") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id).all()

    _warehouses = [obj.repr() for obj in _warehouses] if warehouses else None
    return render_template('admin/warehouses.html', liste = _warehouses)


@admin_bp.get('/warehouses/<int:warehouse_id>/edit')
@login_required
def edit_warehouse(warehouse_id):
    form = EditWarehouseForm()
    warehouse = Warehouse.query.get(warehouse_id)
    if not warehouse:
        return render_template('errors/404.html', blueprint="admin_bp")
    if request.method=="GET":
        form.name.data = warehouse.name
        form.contact.data = warehouse.contact
        form.address.data = warehouse.address

    if form.validate_on_submit():
        warehouse.name = form.name.data
        warehouse.address = form.address.data
        warehouse.contact = form.contact.data
        database.session.add(warehouse)
        database.session.commit()
        flash('Modification avec succès', 'success')
    return render_template("admin/new_warehouse.html", form = form)


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
        flash('Impossible de supprimer l\'entrepôt',"danger")
        return redirect(url_for("admin_bp.warehouses"))
    database.session.delete(warehouse)
    database.session.commit()
    return redirect(url_for("admin_bp.warehouses"))


'''
Manage users
'''

@admin_bp.get('/items')
@admin_bp.post('/items')
@login_required
def items():
    company = Company.query.get(UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id).first()
    if not request.json or not company:
        return '',404
    if request.json['role'] in ['1','2']:
        data = request.json['role']
        if data == '1':
            return jsonify(messages = [{'ID':st.id,'name':st} for st in Store.query.filter_by(fk_company_id = company.id).all()])
        return jsonify(messages = [{'ID':wh.id,'name':wh} for wh in Warehouse.query.filter_by(fk_company_id = company.id).all()])
    return jsonify(status=400)


@admin_bp.get('/employees/new')
@admin_bp.post('/employees/new')
@login_required
def create_user():
    form = EmployeeForm()
    company = Company.query.get(UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id).first()
    if not company:
        return render_template('errors/404.html', blueprint="admin_bp")
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.password_hash = generate_password_hash(form.password.data, "sha265")
        user.full_name = form.full_name.data
        if not form.role.data or form.role.data not in ['1','2']:
            flash('Veuillez choisir le rôle',"warnings")
            return render_template("admin/new_user.html", form=form)
        else:
            user.fk_warehouse_id = int(form.location.data) if form.role.data == '2' else None
            user.fk_store_id = int(form.location.data) if form.role.data == '1' else None
            database.session.add(user)
            database.session.commit()
            user_for_company = UserForCompany()
            user_for_company.fk_company_id = company.id
            user_for_company.fk_user_id = user.id
            if form.role.data == '1':
                user_for_company.role = "vendeur"
            else:
                user.role = "magasiner"
            database.session.add(user_for_company)
            database.session.commit()
            flash('Employé ajouté avec succès','success')
            return redirect(url_for("admin_bp.create_user"))
    return render_template("admin/new_user.html", form = form)


@admin_bp.get('/users')
@login_required
def users():
    pass

