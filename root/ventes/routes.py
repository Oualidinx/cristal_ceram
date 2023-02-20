from flask import url_for, redirect, render_template, session, jsonify
from root import database as db
from flask_login import login_required, current_user
from root.ventes import sales_bp

@sales_bp.before_request
def sales_before_request():
    session['role']="Vendeur"


@sales_bp.get('/')
# @login_required
def index():
    return render_template('sales/index.html')



