from flask_wtf import FlaskForm
from wtforms.fields import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, ValidationError, EqualTo
from wtforms.fields.html5 import EmailField
from root.models import User


class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur: ', validators=[DataRequired()])
    password = PasswordField('Mot de passe: ', validators=[DataRequired()])
    submit = SubmitField('Se connecter')
    def validate_username(self, username):
        # if email_regex.search(username.data) is None:
        #     raise ValidationError('username Invalide')
        user = User.query.filter_by(username=username.data).first()
        if not user:
            raise ValidationError('Veuillez vérifier vos informations')


class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('Nouveau mot de passe:', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmer le mot de passe:', validators=[DataRequired(), EqualTo('new_password', "Vérifier le mot de passe")])
    submit = SubmitField('MAJ')


class RequestToken(FlaskForm):
    email = EmailField('Saisissez votre email: ', validators=[DataRequired()])
    submit = SubmitField('Envoyer')

    def validate_email(self, email):
        user = User.query.filter_by(email = email.data).filter_by(role="student").filter_by(is_deleted = 0).first()
        if not user:
            raise ValidationError('Email invalide')
