from root.achats import purchases_bp
from root import database as db
from flask_login import login_required, current_user
from flask import url_for, session, render_template, redirect, jsonify


@purchases_bp.before_request
def purchases_before_request():
    session['role'] = "Magasiner"


@purchases_bp.get('/')
# @login_required
def index():
    return render_template('purchases/index.html')