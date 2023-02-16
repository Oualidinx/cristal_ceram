import datetime
from http import client

from flask import abort, render_template, session, flash, redirect, url_for, request, jsonify

from root.admin import admin_bp
from root import database
from flask_login import login_required
from root.admin.forms import *
from root.auth.forms import ResetPasswordForm
from root.models import Supplier, Tax, User, InvoiceTax, OrderTax, Warehouse,  Store, Format, Aspect, Stock, Client, Contact
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
@admin_bp.post('/warehouses/add')
@login_required
def add_warehouse():
    form = WarehouseForm()
    if form.validate_on_submit():
        warehouse = Warehouse(
            name = form.name.data,
            address = form.address.data,
            contact = form.contact.data,
            fk_company_id = UserForCompany.query.filter_by(fk_user_id = current_user.id) \
                .filter_by(role="manager").first().fk_company_id
        )
        database.session.add(warehouse)
        database.session.commit()
        flash('Ajout avec succès', 'success')
        return redirect(url_for("admin_bp.add_warehouse"))
    return render_template("admin/new_warehouse.html", form = form)


@admin_bp.get('/warehouses')
@login_required
def warehouses():
    _warehouses = Warehouse.query \
                    .filter_by(fk_company_id = UserForCompany.query.filter_by(role="manager") \
                               .filter_by(fk_user_id=current_user.id).first().fk_company_id)

    _warehouses = [obj.repr() for obj in _warehouses] if warehouses else None
    return render_template('admin/warehouses.html', liste = _warehouses)


@admin_bp.get('/warehouses/<int:warehouse_id>/edit')
@admin_bp.post('/warehouses/<int:warehouse_id>/edit')
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
        return redirect(url_for('admin_bp.warehouses'))
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
        flash('Impossible de supprimer le dépôt',"danger")
        return redirect(url_for("admin_bp.warehouses"))
    database.session.delete(warehouse)
    database.session.commit()
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
    form = EmployeeForm()
    if request.method == "POST" and request.json['role'] in ['1','2']:
        data = request.json['role']
        if data == '1':
            return jsonify(messages = [{'ID':st.id,'name':str(st)} for st in Store.query.filter_by(fk_company_id = company.id).all()])
        return jsonify(messages = [{'ID':wh.id,'name':str(wh)} for wh in Warehouse.query.filter_by(fk_company_id = company.id).all()])
    return jsonify(status=400)


@admin_bp.get('/employees/new')
@admin_bp.post('/employees/new')
@login_required
def create_user():
    form = EmployeeForm()
    company = Company.query.get(UserForCompany.query.filter_by(role="manager").filter_by(
        fk_user_id=current_user.id).first().fk_company_id)
    if not company:
        return render_template('errors/404.html', blueprint="admin_bp")
    company_warehouses = Warehouse.query.filter_by(fk_company_id = company.id).all()
    company_store = Store.query.filter_by(fk_company_id=company.id).all()

    if not company_warehouses or not company_store:
        flash('Vous devez d\'abord ajouter vos dépôts', 'info')
        flash('Vous devez d\'abord ajouter vos magasin', "info")
        return render_template('admin/new_user.html', form = form)

    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.created_by = current_user.id
        user.password_hash = generate_password_hash(form.password.data, "sha256")
        user.full_name = form.full_name.data
        if not form.role.data or form.role.data not in ['1','2']:
            flash('Veuillez choisir le rôle',"warnings")
            return render_template("admin/new_user.html", form=form)
        else:
            user.fk_store_id = int(request.form.get('location')) if form.role.data == '1' else None
            database.session.add(user)
            database.session.commit()
            user_for_company = UserForCompany()
            user_for_company.fk_company_id = company.id
            user_for_company.fk_warehouse_id = int(request.form.get('location')) if form.role.data == '2' else None
            user_for_company.fk_user_id = user.id
            if form.role.data == '1':
                user_for_company.role = "vendeur"
            else:
                user_for_company.role = "magasiner"
            database.session.add(user_for_company)
            database.session.commit()
            flash('Employé ajouté avec succès','success')
            return redirect(url_for("admin_bp.create_user"))
    return render_template("admin/new_user.html", form = form)


@admin_bp.get('/employees')
@login_required
def users():
    companies = Company.query.join(UserForCompany, UserForCompany.fk_company_id == Company.id)\
                                .filter(and_(UserForCompany.role == "manager",UserForCompany.fk_user_id == current_user.id))
    liste = list()
    if companies.all():
        for company in companies:
            t_users = company.users
            liste = liste + [
                user.repr(columns=['id', 'full_name', 'username','_session','role', 'status','location'])
                    for user in  t_users
            ]
            # print(liste)

        # liste = None
    return  render_template('admin/users.html', liste =  liste)


@admin_bp.get('/users/<int:user_id>/edit')
@admin_bp.post('/users/<int:user_id>/edit')
@login_required
def edit_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return render_template('errors/404.html', blueprint="admin_bp")
    user_for_company = UserForCompany.query.filter_by(fk_user_id=user.id).first()
    if not user_for_company:
        return render_template('errors/404.html', blueprint="admin_bp")
    form = UpdateUserForm()
    if request.method=="GET":
        query = Warehouse.query.join(UserForCompany, UserForCompany.fk_warehouse_id == Warehouse.id)
        form = UpdateUserForm(
            role=1 if user_for_company.role == "vendeur" else 2 if user_for_company.role == "magasiner" else 0,
            warehouses=query.filter_by(role="magasiner").filter_by(fk_user_id=user.id).all(),
            username = user.username,
            full_name = user.full_name,
            stores=user.fk_store_id if user.fk_store_id else []
        )
    if form.validate_on_submit():
        company_users=Company.query.get(user_for_company.fk_company_id).users
        for u in company_users:
            if u.id != user.id and func.lower(u.full_name) == func.lower(form.full_name.data):
                flash('Nom de l\'utilisateur déjà existe', 'warning')
                return redirect(url_for("admin_bp.edit_user", user_id=user.id))
        user.full_name = form.full_name.data
        for u in company_users:
            if u.id != user.id and func.lower(u.username) == func.lower(form.username.data):
                flash('Pseudonyme déjà existe','warning')
                return redirect(url_for("admin_bp.edit_user", user_id = user.id))
        user.username = form.username.data
        company= UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first()
        user_for_company = UserForCompany.query \
            .filter_by(fk_user_id=user.id) \
            .filter_by(fk_company_id=company.fk_company_id)
        print(f'role {type(form.role.data)} ')
        if form.role.data == 2:
            if user_for_company.first().role=="magasiner":
                _w = len(user_for_company.all())
                f_w = len(form.warehouses.data)
                if f_w == 0:
                    flash('Il faut sélectionner au moins un dépôt', 'danger')
                    return redirect(url_for('admin_bp.edit_user', user_id=user.id))
                if _w > f_w:
                    for ID in [wh.fk_warehouse_id for wh in user_for_company.all()]:
                        if ID not in [wh.id for wh in form.warehouses.data]:
                            u_f_c = user_for_company.filter_by(fk_warehouse_id = int(ID)).first()
                            database.session.delete(u_f_c)
                            database.session.commit()
                elif _w<f_w:
                    for ID in [wh.id for wh in form.warehouses.data]:
                        if ID not in [wh.fk_warehouse_id for wh in user_for_company.all()]:
                            u_f_c = UserForCompany(fk_user_id = user.id, fk_company_id = company.id,
                                                   fk_warehouse_id=ID, role="magasiner")
                            database.session.add(u_f_c)
                            database.session.commit()
                else:
                    temp = [wh for wh in user_for_company.all()]
                    IDs = [wh.id for wh in form.warehouses.data]
                    counter = 0
                    for temp in [wh for wh in user_for_company.all()]:
                    # for ID in [wh.id for wh in form.warehouses.data]:
                        temp.start_from = datetime.datetime.utcnow()
                        temp.fk_warehouse_id = IDs[counter]
                        database.session.add(temp)
                        database.session.commit()

            else:
                user.fk_store_id = None
                database.session.add(user)
                database.session.delete(user_for_company.first())
                database.session.commit()
        else:
            if not form.stores.data:
                flash('Il faut séléctionner le magasin pour cet employé','danger')
                return redirect(url_for('admin_bp.edit_user',user_id = user.id))
            user.fk_store_id = form.stores.data.id
            database.session.add(user)
            database.session.commit()
            if user_for_company.first().role=='vendeur':
                u_f_c = user_for_company.first()
                u_f_c.start_from = datetime.datetime.utcnow()
                database.session.add(u_f_c)
                database.session.commit()
            else:
                user_warehouses = [wh for wh in user_for_company.all()]
                for wh in user_warehouses:
                    database.session.delete(wh)
                    database.session.commit()
                u_f_c = UserForCompany(fk_user_id=user.id, fk_company_id=company.id,
                                       fk_warehouse_id=None, role="vendeur")
                database.session.add(u_f_c)
                database.session.commit()
        # database.session.add(user)
        # database.session.commit()
        flash('Mise à jour avec succès','success')
        return redirect(url_for('admin_bp.users'))
    return render_template('admin/edit_user.html',
                           user = user,
                           role=UserForCompany.query.filter_by(fk_user_id = user.id).first().role,
                           form = form)


@admin_bp.get('/users/<int:user_id>/disable')
@login_required
def disable_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return render_template("errors/404.html", blueprint="admin_bp")

    if user.is_disabled:
        flash('Erreur', 'danger')
        return redirect(url_for("admin_bp.users"))
    user.is_disabled = True
    current_companies = Company.query.join(UserForCompany, Company.id == UserForCompany.fk_company_id) \
        .filter(and_(UserForCompany.role == "manager", UserForCompany.fk_user_id == current_user.id)) \
        .all()
    if current_companies:
        for company in current_companies:
            if user in company.users:
                user_for_company = UserForCompany.query.filter_by(fk_user_id=user.id).filter_by(fk_company_id = company.id).first()
                if user_for_company:
                    user.fk_store_id = None
                    user.fk_warehouse_id = None
                    database.session.add(user)
                    database.session.delete(user_for_company)
                    database.session.commit()
                    flash('Opération se termine avec succès',"success")
                    return redirect(url_for("admin_bp.users"))
    return render_template('errors/404.html', blueprint="admin_bp")


# @admin_bp.get('/users/<int:user_id>/enable')
# @login_required
# def enable_user(user_id):
#     user = User.query.get(user_id)
#     if not user:
#         return render_template("errors/404.html", blueprint="admin_bp")
#
#     if not user.is_disabled:
#         flash('Erreur', 'danger')
#         return redirect(url_for("admin_bp.users"))
#     user.is_disabled = False
#     database.session.add(user)
#     user_for_company = UserForCompany()
#     user_for_company.fk_company_id = Warehouse.query.get(user.fk_warehouse_id).fk_company_id
#     user_for_company.fk_user_id = user.id
#     database.session.add(user_for_company)
#     database.session.commit()
#     flash('Opération se termine avec succès', "success")
#     return redirect(url_for("admin_bp.users"))

#
# @admin_bp.get('/users/<int:user_id>/attach/warehouses/<int:warehouse_id>')
# @login_required
# def attach_user_warehouse(user_id, warehouse_id):
#     user=User.query.get(user_id)
#     if not user:
#         return render_template('errors/404.html', blueprint="admin_bp")
#
#     user_for_company = UserForCompany.query.filter(UserForCompany.role =='magasiner').filter_by(fk_user_id = user.id)
#     if len(user_for_company.all()) > 0 or user.fk_store_id:
#         flash('Employé déjà attaché à un dépôt. Veuillez d\'abord détacher-le de l\'ancien dépôt puis réessayer','danger')
#         return redirect(url_for('admin_bp.users'))
#
#     warehouse = Warehouse.query.get(warehouse_id)
#     if not warehouse:
#         return render_template('errors/404.html', blueprint="admin_bp")
#
#     current_companies = Company.query.join(UserForCompany, Company.id == UserForCompany.fk_company_id) \
#         .filter(and_(UserForCompany.role == "manager", UserForCompany.fk_user_id == current_user.id)) \
#         .all()
#     if not current_companies:
#         return render_template('errors/404.html',blueprint="admin_bp")
#     founded = False
#     fk_company_id = None
#     while not founded:
#         for company in current_companies:
#             if user in company.users and warehouse in company.warehouses:
#                 fk_company_id = company.id
#                 founded = True
#     if not founded:
#         return render_template("errors/404.html", blueprint="admin_bp")
#     temp = user_for_company.filter_by(fk_warehouse_id = warehouse.id).first()
#     # if not temp:
#     #     return render_template('errors/404.html', blueprint="admin_bp")
#     temp = UserForCompany(
#         role="magasiner",
#         fk_user_id=user.id,
#         fk_company_id= fk_company_id,
#         fk_warehouse_id = warehouse.id
#     )
#     database.session.add(temp)
#     database.session.commit()
#     flash('Opération se termine avec succès','success')
#     return redirect(url_for('admin_bp.users'))\


# @admin_bp.get('/users/<int:user_id>/detach')
# @admin_bp.post('/users/<int:user_id>/detach')
# @login_required
# def detach_user_warehouse(user_id):
#     user = User.query.get(user_id)
#     if not user:
#         return render_template('errors/404.html', blueprint="admin_bp")
#     user_warehouses = Warehouse.query.filter_by(role="magasiner").filter_by(fk_user_id=user.id).all()
#     if not user_warehouses:
#         flash('Cet employé n\'est pas un magasiner','warning')
#         return redirect(url_for('admin_bp.edit_user', user_id = user.id))
#
#     form = WarehousesForm()
#     query =  Warehouse.query.join(UserForCompany, UserForCompany.fk_warehouse_id == Warehouse.id ) \
#                                                             .filter(UserForCompany.fk_user_id == user.id)
#     if not query.all():
#         flash('Erreur','danger')
#         return redirect(url_for('admin_bp.edit_user', user_id = user.id))
#     form.warehouses.query_factory = lambda : Warehouse.query.join(UserForCompany, UserForCompany.fk_warehouse_id == Warehouse.id ) \
#                                                             .filter(UserForCompany.fk_user_id == user.id).all()
#     if form.validate_on_submit():
#         if len(form.warehouses.data) == len(query.all()):
#             flash(f"Opération impossible: vous ne pouvez pas détacher l'employée {user.full_name} de tout les lieux. Veuillez d'abord changer son role puis réessayer",'danger')
#             return redirect(url_for("admin_bp.edit_user", user_id=user.id))
#         founded = False
#         for ID in form.warehouses.data:
#             user_for_company = query.filter_by(fk_warehouse_id = int(ID)).first()
#             if user_for_company:
#                 founded = True
#                 database.session.delete(user_for_company)
#         if founded:
#             database.session.commit()
#         flash('Opération terminée avec succès','success')
#     return redirect(url_for("admin_bp.edit_user", user_id = user.id))

#
# @admin_bp.get('/users/<int:user_id>/attach/stores/<int:store_id>')
# @login_required
# def attach_user_store(user_id, store_id):
#     user = User.query.get(user_id)
#     if not user:
#         return render_template('errors/404.html', blueprint="admin_bp")
#     user_for_company = UserForCompany.query.filter(UserForCompany.role == 'magasiner').filter_by(fk_user_id=user.id)
#     if len(user_for_company.all()) > 0 or user.fk_store_id:
#         flash('Employé déjà attaché à un dépôt. Veuillez d\'abord détacher-le de l\'ancien dépôt puis réessayer','danger')
#         return redirect(url_for('admin_bp.users'))
#     store = Store.query.get(store_id)
#     if not store:
#         return render_template('errors/404.html', blueprint="admin_bp")
#     current_companies = Company.query.join(UserForCompany, Company.id == UserForCompany.fk_company_id) \
#         .filter(and_(UserForCompany.role == "manager", UserForCompany.fk_user_id == current_user.id)) \
#         .all()
#     if not current_companies:
#         return render_template('errors/404.html',blueprint="admin_bp")
#     founded = False
#     fk_company_id = 0
#     while not founded:
#         for company in current_companies:
#             if user in company.users and store in company.stores:
#                 fk_company_id = company.id
#                 founded = True
#
#     if not founded:
#         return render_template("errors/404.html", blueprint="admin_bp")
#     user.fk_store_id = store.id
#     database.session.add(user)
#     temp = UserForCompany(
#         role="vendeur",
#         fk_user_id = user.id,
#         fk_company_id = fk_company_id,
#         fk_warehouse_id=None
#     )
#     database.session.add(temp)
#     database.session.commit()
#     flash('Opération se termine avec succès','success')
#     return redirect(url_for('admin_bp.users'))

#
# @admin_bp.get('/users/<int:user_id>/detach/stores/<int:store_id>')
# @login_required
# def detach_user_store(user_id, store_id):
#     user = User.query.get(user_id)
#     if not user:
#         return render_template('errors/404.html', blueprint="admin_bp")
#     user_for_company = UserForCompany.query.filter(UserForCompany.role == 'magasiner').filter_by(fk_user_id=user.id)
#     if not len(user_for_company) == 0 and not user.fk_store_id:
#         flash('Employé déjà détaché','danger')
#         return redirect(url_for('admin_bp.users'))
#
#     store = Store.query.get(store_id)
#     if not store:
#         return render_template('errors/404.html', blueprint="admin_bp")
#
#     current_companies = Company.query.join(UserForCompany, Company.id == UserForCompany.fk_company_id) \
#         .filter(and_(UserForCompany.role == "manager", UserForCompany.fk_user_id == current_user.id)) \
#         .all()
#     if not current_companies:
#         return render_template('errors/404.html',blueprint="admin_bp")
#     founded = False
#     while not founded:
#         for company in current_companies:
#             if user in company.users and store in company.stores:
#                 founded = True
#
#     if not founded:
#         return render_template("errors/404.html", blueprint="admin_bp")
#     user.fk_store_id = None
#     database.session.add(user)
#     temp = UserForCompany.query.filter_by(role="vendeur").filter_by(fk_user_id = user.id).first()
#     if not temp:
#         return render_template('errors/404.html', blueprint="admin_bp")
#     database.session.delete(temp)
#     database.session.commit()
#     flash('Opération se termine avec succès','success')
#     return redirect(url_for('admin_bp.users'))


# @admin_bp.get('/employees/get')
@admin_bp.post('/employees/get')
@login_required
def get_user():
    data = request.json
    user = User.query.get(int(data['user_id']))
    if not user:
        abort(404)
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id = current_user.id).first()
    user_company = UserForCompany.query.filter_by(fk_user_id=user.id)
    if company.fk_company_id != user_company.first().fk_company_id:
        abort(404)
    user_company = user_company.filter_by(fk_company_id=company.id).first()
    _dict = User.query.get(user.id).repr(['locations'])
    return jsonify(message = f"<h4 class='h4 fw-bold'>{user.full_name}</h4> \
                        <span class='fw-bold mb-3'>Pseudonyme: </span>{user.username} <br> \
                        <span class='fw-bold mb-3'>Rôle: </span>{user_company.role if user_company is not None else '/'} <br> \
                        <span class='fw-bold mb-3'>Lieu(x) de travail: </span><br>"+'<br>'.join(_dict['locations'])), 200


@admin_bp.get('/stocks')
@login_required
def stocks():
    user_companies = UserForCompany.query.filter_by(fk_user_id = current_user.id).all()
    if not user_companies or len(user_companies) == 0:
        return render_template('errors/404.html', blueprint="admin_bp")
    liste = None
    for company in user_companies:
        if company.warehouses:
            for warehouse in company.warehouses:
                liste = liste + warehouse.stocks
    _liste = [obj.repr() for obj in liste]
    return render_template('admin/stocks.html', liste = _liste)


@admin_bp.get('/stocks/add')
@admin_bp.post('/stocks/add')
@login_required
def add_stock():
    form = StockForm()
    if request.method=="GET":
        form.item.query_factory = lambda : Item.query.filter_by(created_by = current_user.id).all()
        form.warehouse.query_factory = lambda :  Warehouse.query.join(Company, Company.id == Warehouse.fk_company_id) \
                                                                .join(UserForCompany, UserForCompany.fk_company_id == Company.id) \
                                                                .filter(and_(UserForCompany.role=="manager", UserForCompany.fk_user_id == current_user.id))\
                                                                .all()
    if form.validate_on_submit():
        stock = Stock()
        stock.stock_qte = float(form.stock_qte.data) if form.stock_qte.data else None
        stock.stock_sec = float(form.stock_sec.data)
        if Warehouse.query.get(form.warehouse.data) is None or Item.query.get(form.item.data) is None:
            return render_template('errors/404.html', blueprint="admin_bp")
        stock.fk_warehouse_id = int(form.warehouse.data)
        stock.fk_item_id = int(form.item.data)
        database.session.add(stock)
        database.session.commit()
        flash("Objet ajouté avec succès","success")
    return render_template("admin/new_stock.html", form = form)


@admin_bp.get('/stock/<int:stock_id>/detach')
@login_required
def detach_stock(stock_id):
    stock = Stock.query.get(stock_id)
    if not stock:
        return render_template("errors/404.html", blueprint="admin_bp")

    company = Company.query.get(Warehouse.query.get(stock.fk_warehouse_id))
    if not company :
        return render_template('errors/404.html', blueprint="admin_bp")

    if User.query.filter_by(role="manager") \
            .filter_by(fk_user_id=current_user.id).filter_by(fk_company_id=company.id).first() is None:
        return render_template('errors/404.html', blueprint="admin_bp")

    stock.fk_warehouse_id = None
    database.session.add(stock)
    database.session.commit()
    flash('Opération terminé avec succès', "success")
    return redirect(url_for("admin_bp.stocks"))


@admin_bp.get('/stock/<int:stock_id>/attach')
@admin_bp.post('/stock/<int:stock_id>/attach')
@login_required
def attach_stock(stock_id):
    form = AttachWareHouseForm()
    if request.method == 'GET':
        stock = Stock.query.get(stock_id)
        if not stock:
            return render_template("errors/404.html", blueprint="admin_bp")

        company = Company.query.get(Warehouse.query.get(stock.fk_warehouse_id))
        if not company:
            return render_template('errors/404.html', blueprint="admin_bp")

        if User.query.filter_by(role="manager") \
                .filter_by(fk_user_id=current_user.id).filter_by(fk_company_id=company.id).first() is None:
            return render_template('errors/404.html', blueprint="admin_bp")
        if stock.fk_warehouse_id is not None:
            flash('Stock déjà attaché à un dépôt. Veuillez d\'abord détacher le puis réessayer.', "warning")
            return redirect(url_for("admin_bp.stocks"))
        form.warehouse.query_factory = lambda: Warehouse.query.join(Company, Company.id == Warehouse.fk_company_id) \
            .join(UserForCompany, UserForCompany.fk_company_id == Company.id) \
            .filter(and_(UserForCompany.role == "manager", UserForCompany.fk_user_id == current_user.id)) \
            .all()
        if stock.stock_qte:
            form.stock_qte.data = stock.stock_qte
        form.stock_sec.data = stock.stock_sec

    if form.validate_on_submit():
        if Warehouse.query.get(form.warehouse.data):
            return render_template('errors/404.html', blueprint="admin_bp")
        stock.fk_warehouse_id=int(form.warehouse.data)
        database.session.add(stock)
        database.session.commit()
        flash('Opération terminée avec succès','success')
    return redirect(url_for('admin_bp.stocks'))


@admin_bp.get('/products/formats')
@login_required
def formats():
    c_id = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    _formats = Format.query.filter_by(fk_company_id=c_id).all()
    liste = None
    if _formats:
        liste = [
            {
                'id':obj.id,
                'label': obj.label
            } for obj in _formats
        ]
    return render_template('admin/formats.html', liste = liste)

@admin_bp.get('/products/format/add')
@admin_bp.post('/products/format/add')
@login_required
def add_format():
    form = FormatForm()
    c_id = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if form.validate_on_submit():
        _format = Format()
        f = Format.query.filter_by(fk_company_id=c_id).filter(
            func.lower(Format.label) == str.lower(form.label.data)).first()
        if f:
            _format = f
        _format.label = form.label.data
        _format.created_by = current_user.id
        _format.fk_company_id = c_id
        database.session.add(_format)
        database.session.commit()
        flash('Objet ajouté avec succès','success')
        return redirect(url_for('admin_bp.add_format'))
    return render_template('admin/add_format.html', form = form)


@admin_bp.get('/products/formats/<int:format_id>/edit')
@admin_bp.post('/products/formats/<int:format_id>/edit')
@login_required
def edit_format(format_id):
    form = EditFormatForm()
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id = current_user.id).first().fk_company_id
    format_ = Format.query.filter_by(fk_company_id=company).filter_by(id = format_id).first()
    if not format_:
        return render_template("errors/404.html", blueprint="admin_bp")
    if request.method=="GET":
        form.label.data = format_.label
    if form.validate_on_submit():
        format_.label = form.label.data
        database.session.add(format_)
        database.session.commit()
        flash('Objet modifie avec succès',"success")
        return redirect(url_for("admin_bp.formats"))
    return render_template("admin/add_format.html", form = form)


@admin_bp.get('/products/format/<int:format_id>/delete')
@login_required
def delete_format(format_id):
    _format = Format.query.get(format_id)
    if not _format:
        return render_template("errors/404.html", blueprint="admin_bp")

    item_brand_category = Item.query.filter_by(fk_format_id = _format.id).first()
    if item_brand_category:
        flash('impossible de supprimé cet objet', "danger")
        return redirect(url_for('admin_bp.formats'))
    database.session.delete(_format)
    database.session.commit()
    flash('Objet supprimé','success')
    return redirect(url_for("admin_bp.formats"))


@admin_bp.get('/products/aspect/add')
@admin_bp.post('/products/aspect/add')
@login_required
def add_aspect():
    form = AspectForm()
    c_id= UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if form.validate_on_submit():
        aspect = Aspect()
        _aspect = Aspect.query.filter_by(fk_company_id = c_id).filter(func.lower(Aspect.label) == str.lower(form.label.data)).first()
        if _aspect:
            aspect = _aspect
        aspect.label = form.label.data
        aspect.created_by = current_user.id
        aspect.fk_company_id = c_id
        database.session.add(aspect)
        database.session.commit()
        flash('Objet ajouté avec succès','success')
        return redirect(url_for('admin_bp.add_aspect'))
    return render_template('admin/add_aspect.html', form = form)

@admin_bp.get('/products/aspects/<int:aspect_id>/edit')
@admin_bp.post('/products/aspects/<int:aspect_id>/edit')
@login_required
def edit_aspect(aspect_id):
    print(aspect_id)
    form = EditAspectForm()
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    aspect_ = Aspect.query.filter_by(fk_company_id=company).filter_by(id=aspect_id).first()

    if not aspect_:
        return render_template("errors/404.html", blueprint="admin_bp")
    if request.method=="GET":
        form.label.data = aspect_.label
    if form.validate_on_submit():
        aspect_.label = form.label.data
        database.session.add(aspect_)
        database.session.commit()
        flash('Objet modifié avec succès',"success")
        return redirect(url_for("admin_bp.aspects"))
    return render_template("admin/add_aspect.html", form = form)


@admin_bp.get('/products/aspect/<int:aspect_id>/delete')
@login_required
def delete_aspect(aspect_id):
    _aspect = Aspect.query.get(aspect_id)
    if not _aspect:
        return render_template("errors/404.html", blueprint="admin_bp")

    item_brand_category = Item.query.filter_by(fk_aspect_id = _aspect.id).first()
    if item_brand_category:
        flash('impossible de supprimé cet objet', "danger")
        return redirect(url_for('admin_bp.aspects'))
    database.session.delete(_aspect)
    database.session.commit()
    flash('Objet supprimé','success')
    return redirect(url_for("admin_bp.aspects"))


@admin_bp.get('/products/aspects')
@login_required
def aspects():
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id = current_user.id).first().fk_company_id
    _aspects = Aspect.query.filter_by(fk_company_id=company).all()
    liste = None
    if _aspects:
        liste = [
            {'id':aspect.id, 'label':aspect.label} for aspect in _aspects
        ]
    return render_template('admin/aspects.html', liste = liste)

@admin_bp.get('/products')
@login_required
def products():
    company = Company.query.get(UserForCompany.query.filter_by(role="manager") \
                                .filter_by(fk_user_id = current_user.id).first().fk_company_id)
    _products = Item.query.filter_by(fk_company_id=company.id).all()
    liste = None
    if _products:
        liste = [product.repr(['id','label','format','aspect','serie','intern_reference','expired_at','stock_sec']) for product in _products]
    return render_template('admin/items.html', liste = liste)


@admin_bp.get('/products/add')
@admin_bp.post('/products/add')
@login_required
def add_product():
    __formats = Format.query.filter_by(
                                fk_company_id=UserForCompany.query.filter_by(role='manager').filter_by(fk_user_id=current_user.id)\
                                                                                            .first().fk_company_id).all()
    __aspect = Aspect.query.filter_by(
                                fk_company_id=UserForCompany.query.filter_by(role='manager').filter_by(fk_user_id=current_user.id)\
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
            flash('Veuillez sélectionner \'unité puis réesseyer','warning')
            return redirect(url_for('admin_bp.add_product'))
        else:
            item.piece_per_unit = float(form.piece_per_unit.data)
        item.stock_sec = form.stock_sec.data
        item.use_for = form.utilisation.data if form.utilisation.data else None
        item.intern_reference = form.intern_reference.data if form.intern_reference.data else None
        item.fk_aspect_id = form.aspect.data.id if form.aspect.data else None
        item.fk_format_id = form.format.data.id if form.format.data else None
        item.used_for = form.utilisation.data
        item.created_by = current_user.id
        item.fk_company_id = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id = current_user.id).first().id
        item.expired_at = form.expired_at.data if form.expired_at.data else None
        database.session.add(item)
        database.session.commit()
        flash('Objet ajouté avec succès',"success")
        return redirect(url_for('admin_bp.add_product'))
    return render_template("admin/new_item.html", form=form)


@admin_bp.get('/products/<int:item_id>/edit')
@admin_bp.post('/products/<int:item_id>/edit')
@login_required
def edit_product(item_id):
    item = Item.query.get(item_id)
    if not item:
        return render_template('errors/404.html', blueprint="admin_bp")

    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id = current_user.id).first().id
    form = EditItemForm()
    if request.method=="GET":
        form = EditItemForm(
            format=Format.query.get(item.fk_format_id) if item.fk_aspect_id else None,
            aspect=Aspect.query.get(item.fk_aspect_id) if item.fk_aspect_id else None,
            used_for = item.use_for if item.use_for else None,
            label = item.label,
            manufaturer = item.manufacturer if item.manufacturer else None,
            unit = item.unit if item.unit else None,
            piece_per_unit = item.piece_per_unit if item.piece_per_unit else None,
            stock_sec = item.stock_sec,
            serie = item.serie if item.serie else None,
            intern_reference = item.intern_reference if item.intern_reference else None,
            expired_at = item.expired_at if item.expired_at else None,
        )
    if form.validate_on_submit():

        _item = Item.query.filter_by(fk_company_id=company) \
            .filter(func.lower(Item.label) == str.lower(form.label.data)).first()
        if _item and item.id != _item.id:
            flash('Nom déjà utilisé','warning')
            return redirect(url_for('admin_bp.edit_product', item_id = item.id))
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
            return redirect(url_for('admin_bp.edit_product', item_id = item.id))
        else:
            item.piece_per_unit = float(form.piece_per_unit.data)
        item.company_id = company
        item.expired_at = form.expired_at.data if form.expired_at.data else None
        item.fk_aspect_id = form.aspect.data
        item.fk_format_id = form.format.data

        item.stock_sec = form.stock_sec.data
        item.utilisation = form.utilisation.data
        item.fk_item_id = item.id
        database.session.add(item)
        database.session.commit()
        flash('Objet ajouté avec succès',"success")
    return render_template("admin/new_item.html", form=form)


@admin_bp.get('/products/<int:item_id>/get')
@login_required
def get_item(item_id):
    item = Item.query.get(item_id)
    if not item:
        return render_template('errors/404.html', blueprint="admin_bp")
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if item.fk_company_id != company:
        return render_template('errors/404.html')
    return render_template('admin/item_info.html', item = item.repr())


@admin_bp.get('/stores')
@login_required
def stores():
    _stores = Store.query \
        .filter_by(fk_company_id=UserForCompany.query.filter_by(role="manager") \
                   .filter_by(fk_user_id=current_user.id).first().fk_company_id)

    _stores = [obj.repr() for obj in _stores] if _stores else None
    return render_template('admin/stores.html', liste=_stores)


@admin_bp.get('/stores/add')
@admin_bp.post('/stores/add')
@login_required
def add_store():
    form = StoreForm()
    # if request.method == "GET":
    #     form.seller.query_factory = lambda: Company.query.get(UserForCompany.query. \
    #                                                       filter_by(role="manager") \
    #                                                       .filter_by(fk_user_id=current_user.id) \
    #                                                       .first().fk_company_id).users
    if form.validate_on_submit():
        store= Store()
        store.name = form.name.data
        store.address = form.address.data
        store.contact = form.contact.data
        store.fk_company_id = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
        database.session.add(store)
        database.session.commit()
        flash('Objet ajouté avec success','success')
        return redirect(url_for('admin_bp.add_store'))
    else:
        print(form.errors)
    return render_template("admin/new_store.html", form = form)


@admin_bp.get('/stores/<int:store_id>/block')
@login_required
def block_store(store_id):
    store = Store.query.get(store_id)
    if not store:
        return render_template('errors/404.html', blueprint="admin_bp")

    if store.is_disabled:
        flash('Erreur','danger')
        return redirect(url_for('admin_bp.stores'))

    if  UserForCompany.query.filter_by(role="manager") \
                                .filter(and_(UserForCompany.fk_user_id==current_user.id,
                                             UserForCompany.fk_company_id==store.fk_company_id)).first() is None:
        return render_template('errors/404.html', bluepint="admin_bp")
    store.is_disabled = True
    database.session.add(store)
    database.session.commit()
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
            .filter(and_(UserForCompany.fk_user_id == current_user.id,
                         UserForCompany.fk_company_id == store.fk_company_id)).first() is None:
        return render_template('errors/404.html', bluepint="admin_bp")
    store.is_disabled = False
    database.session.add(store)
    database.session.commit()
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
            .filter(and_(UserForCompany.fk_user_id == current_user.id,
                         UserForCompany.fk_company_id == store.fk_company_id)).first() is None:
        return render_template('errors/404.html', bluepint="admin_bp")
    if request.method=="GET":
        form.name.data = store.name
        form.address.data = store.address
        form.contact.data = store.contact
        form.seller.query_factory=lambda : Company.query.get(UserForCompany.query. \
                                                             filter_by(role="manager")\
                                                             .filter_by(fk_user_id=current_user.id)\
                                                             .first().fk_company_id).users

    if form.validate_on_submit():
        store.name = form.name.data
        store.address = form.address.data
        store.contact = form.contact.data
        database.session.add(store)
        database.session.commit()
        flash('Objet ajouté avec success','success')
        return redirect(url_for('admin_bp.stores'))
    return render_template("admin/new_store.html", form = form)


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
            database.session.add(seller)
        database.session.commit()
    database.session.delete(store)
    database.session.commit()
    flash('Objet supprimé','success')
    return redirect(url_for("admin_bp.stores"))


@admin_bp.get('/employees/<int:user_id>/change_password')
@admin_bp.post('/employees/<int:user_id>/change_password')
@login_required
def change_password(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('Employés introuvable','danger')
        return redirect(url_for('admin_bp.edit_user', user_id = user.id))

    _users = Company.query.get(UserForCompany.query.filter_by(role="manager") \
                               .filter_by(fk_user_id = current_user.id).first().fk_company_id).users
    if not _users or user not in _users:
        flash('Employés introuvable','danger')
        return redirect(url_for('admin_bp.edit_user', user_id=user.id))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.new_password.data, "SHA256")
        database.session.add(user)
        database.session.commit()
        flash('Opération terminée avec succès','success')
        return redirect(url_for('admin_bp.edit_user', user_id=user.id))
    return render_template('auth/reset_password.html', form = form)


@admin_bp.get('/clients')
@login_required
def clients():
    _clients = Client.query.filter_by(fk_company_id = UserForCompany.query.filter_by(role="manager") \
                                      .filter_by(fk_user_id = current_user.id).first().fk_company_id).all()
    liste = None
    if _clients:
        liste = [
            client.repr() for client in _clients
        ]
        print(liste)
    return render_template('admin/clients.html', liste = liste)


@admin_bp.get('/clients/<int:client_id>/get')
@login_required
def get_client(client_id):
    item = Client.query.get(client_id)
    if not item:
        return render_template('errors/404.html', blueprint="admin_bp")
    company = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
    if item.fk_company_id != company:
        return render_template('errors/404.html')
    return render_template('admin/client_info.html', item = item.repr())

@admin_bp.get('/clients/<int:client_id>/edit')
@admin_bp.post('/clients/<int:client_id>/edit')
@login_required
def edit_client(client_id):
    form = ClientForm()
    _client = Client.query.get(client_id)
    if not _client:
        return render_template('errors/404.html')
    if request.method=="GET":
        form = ClientForm(
            full_name=_client.full_name,
            category=_client.category,
            contacts=Contact.query.get(_client.id).value
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
        database.session.add(contact)
        database.session.commit()
        flash('Objet modifié avec succès','success')
        return redirect(url_for('admin_bp.clients'))
    return render_template('admin/add_client.html', form = form)



@admin_bp.get('/client/add')
@admin_bp.post('/client/add')
@login_required
def add_client():
    form = ClientForm()
    if form.validate_on_submit():
        _client = Client()
        _client.full_name = form.full_name.data
        _client.category = form.category.data
        _client.fk_company_id = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
        database.session.add(_client)
        database.session.commit()
        contact = Contact()
        contact.key='téléphone'
        contact.value = form.contacts.data
        contact.fk_client_id = _client.id

        database.session.add(contact)
        database.session.commit()
        flash('Objet ajouté avec succès','success')
        return redirect(url_for('admin_bp.add_supplier'))
    return render_template('admin/add_supplier.html', form = form)


@admin_bp.get('/client/<int:client_id>/delete')
@login_required
def delete_client(client_id):
    _client = Client.query.get(client_id)
    if not _client:
        return render_template('errors/404.html')
    if _client.orders :
        flash('Impossible de supprimer ce client',"danger")
        return redirect(url_for('admin_bp.clients'))

    database.session.delete(_client)
    database.session.commit()
    flash('Objet supprimé avec succès','success')
    return redirect(url_for("admin_bp.clients"))


@admin_bp.get('/suppliers')
@login_required
def suppliers():
    _suppliers = Supplier.query.filter_by(fk_company_id = UserForCompany.query.filter_by(role="manager") \
                                      .filter_by(fk_user_id = current_user.id).first().fk_company_id).all()
    liste = None
    if _suppliers:
        liste = [
            supplier.repr() for supplier in _suppliers
        ]
    return render_template('admin/suppliers.html', liste = liste)


@admin_bp.get('/suppliers/<int:supplier_id>/edit')
@admin_bp.post('/suppliers/<int:supplier_id>/edit')
@login_required
def edit_supplier(supplier_id):
    form = SupplierForm()
    supplier = Supplier.query.get(supplier_id)
    if not supplier:
        return render_template('errors/404.html')
    if request.method=="GET":
        form = SupplierForm(
            full_name=supplier.full_name,
            category=supplier.category,
            contacts=Contact.query.get(supplier.id).value
        )

    if form.validate_on_submit():
        supplier.full_name = form.full_name.data
        supplier.category = form.category.data
        contact = Contact.query.filter_by(fk_client_id=supplier.id).filter_by(value=form.contacts.data).first()
        if not contact:
            contact = Contact()
        contact.key = "téléphone"
        contact.value = form.contacts.data
        contact.fk_supplier_id = supplier.id
        database.session.add(contact)
        database.session.commit()
        flash('Objet modifié avec succès','success')
        return redirect(url_for('admin_bp.suppliers'))
    return render_template('admin/add_supplier.html', form = form)



@admin_bp.get('/supplier/add')
@admin_bp.post('/supplier/add')
@login_required
def add_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier()
        supplier.full_name = form.full_name.data
        supplier.category = form.category.data
        supplier.fk_company_id = UserForCompany.query.filter_by(role="manager").filter_by(fk_user_id=current_user.id).first().fk_company_id
        database.session.add(supplier)
        database.session.commit()
        _contact = Contact()
        _contact.key='téléphone'
        _contact.value = form.contacts.data
        _contact.fk_client_id = _contact.id

        database.session.add(_contact)
        database.session.commit()
        flash('Objet ajouté avec succès','success')
        return redirect(url_for('admin_bp.add_supplier'))
    return render_template('admin/add_supplier.html', form = form)



@admin_bp.get('/suppliers/<int:supplier_id>/delete')
@login_required
def delete_supplier(supplier_id):
    _supplier = Supplier.query.get(supplier_id)
    if not _supplier:
        return render_template('errors/404.html')
    if _supplier.orders :
        flash('Impossible de supprimer ce fournisseur',"danger")
        return redirect(url_for('admin_bp.suppliers'))

    database.session.delete(_supplier)
    database.session.commit()
    flash('Objet supprimé avec succès','success')
    return redirect(url_for("admin_bp.suppliers"))

