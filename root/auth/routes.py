from root.auth import auth_bp
from flask import render_template, redirect, url_for, session, flash, request, current_app
from werkzeug.security import check_password_hash
from root import mail, database
from flask_mail import Message
from root.models import User, UserForCompany, Contact, Address, Company
from root.auth.forms import LoginForm, RequestToken, ResetPasswordForm, UpdateUserForm
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

def send_reset_email(user):
    # token = user.get_token()
    user_name = current_app.config['MAIL_USERNAME']
    msg = Message('Password Reset Request',
                  sender=user_name,  # from domain
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link: 
                         {url_for("auth_bp.reset_password", token=user.get_token(), _external=True)}
                        If you did not make this request then simply ignore this email and no changes will be made.'''
    mail.send(msg)


@auth_bp.get('/login')
@auth_bp.post('/login')
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).filter_by(is_disabled=False).first() #filter_by(is_deleted=0).
        if user and not user.is_disabled:
            if check_password_hash(user.password_hash, form.password.data):
                login_user(user, remember=False)
                nex_page = request.args.get('next')
                if nex_page:
                    return redirect(nex_page)
                user_for_company = UserForCompany.query.filter_by(fk_user_id = user.id).first()
                if not user_for_company:
                    return render_template('errors/401.html')
                if user_for_company.role == "manager":
                    return redirect(url_for('admin_bp.index'))
                if user_for_company.role == "vendeur":
                    return redirect(url_for('sales_bp.index'))
                return redirect(url_for("purchases_bp.index"))
            else:
                flash('Veuillez vérifier les informations', 'danger')
        else:
            flash('veuillez verifier les informations', 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/recover_password')
def request_token():
    form = RequestToken()
    # if form.validate_on_submit():
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('Un message a été transmis à votre email. Si Vous n\'avez aucun compte, vous ne recevez rien', 'info')
        return redirect(url_for('auth_bp.login'))
    return render_template('auth/request_token.html', form=form)

    
@auth_bp.get("/reset_password/<string:token>")
@auth_bp.post("/reset_password/<string:token>")
def reset_password(token):
    user = User.verify_reset_token(token)
    if user is None:
        flash('Il y a une erreur', 'warning')
        return redirect(url_for('auth_bp.request_token'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.new_password.data, "SHA256")
        database.session.add(user)
        database.session.commit()
        flash('Votre mot de passe a été changé avec succès', 'success')
        return redirect(url_for('auth_bp.login'))
    return render_template("auth/reset_password.html", form=form)


@auth_bp.get('/settings')
@auth_bp.post("/settings")
@login_required
def settings():

    edit_account = UpdateUserForm()
    company = UserForCompany.query.filter_by(role='manager').filter_by(fk_user_id=current_user.id).first()
    address = Address.query.filter_by(fk_company_id=company.fk_company_id).first()
    contact = Contact.query.filter_by(fk_company_id=company.fk_company_id).first()
    # if request.method=='GET':
    user = User.query.get(current_user.id)
    edit_account.username.data = user.username
    edit_account.company_name.data = Company.query.get(company.fk_company_id).name

    if contact:
        edit_account.contact.data = contact.value

    if address:
        edit_account.address.data = address.label

    if edit_account.validate_on_submit():
        print('edit account form')
        _company = Company.query.join(Contact, Contact.fk_company_id == Company.id).filter(Contact.value == edit_account.contact.data).first()
        if _company and _company.id != company.id:
            flash('Contact déjà existe','danger')
            return render_template('auth/settings.html', edit = edit_account)
        if not contact:
            contact = Contact()
            contact.fk_company_id = company.id
            contact.key = "téléphone"
        contact.value = edit_account.contact.data
        database.session.add(contact)
        database.session.commit()
        _company = Company.query.join(Address, Address.fk_company_id == Company.id).filter(
            Address.label == edit_account.address.data).first()

        if _company and _company.id != company.id:
            flash('Address déjà existe','danger')
            return render_template('auth/settings.html', edit=edit_account)

        if not address:
            address = Address()
            address.fk_company_id = company.id

        address.label = edit_account.address.data
        database.session.add(address)
        database.session.commit()

        _company = Company.query.filter_by(name = edit_account.company_name.data).first()
        if _company and _company.id != company.id:
            flash('Entreprise déjà existe','danger')
            return render_template('auth/settings.html', edit = edit_account)

        company.name = edit_account.company_name.data
        database.session.add(company)
        database.session.commit()
        flash('Mise à jour des informations avec succès','success')
        return redirect(url_for('auth_bp.settings'))

    return render_template('auth/settings.html', edit = edit_account)


@auth_bp.get('/settings/update_password')
@auth_bp.post('/settings/update_password')
@login_required
def update_manager_password():
    reset_form = ResetPasswordForm()
    if reset_form.validate_on_submit():
        user = User.query.get(current_user.id)
        user.password_hash = generate_password_hash(reset_form.new_password.data, "SHA256")
        database.session.add(user)
        database.session.commit()
        flash('Mot de passe modifié', 'success')
        return redirect(url_for('auth_bp.settings'))
    return render_template('auth/reset_password.html', form=reset_form)