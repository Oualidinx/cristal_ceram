from root.auth import auth_bp
from flask import render_template, redirect, url_for, session, flash, request, current_app
from werkzeug.security import check_password_hash
from root import mail, database
from flask_mail import Message
from root.models import User
from root.auth.forms import LoginForm, RequestToken, ResetPasswordForm
from flask_login import login_user, logout_user, login_required
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
        user = User.query.filter_by(username=form.username.data).first() #filter_by(is_deleted=0).
        if user:
            if check_password_hash(user.password_hash, form.password.data):
                login_user(user, remember=False)
                nex_page = request.args.get('next')
                if nex_page:
                    return redirect(nex_page)

                if user.role == "master":
                    return redirect(url_for('admin_bp.index'))
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