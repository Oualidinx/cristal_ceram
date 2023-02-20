from flask import Blueprint

purchases_bp = Blueprint('Purchases', __name__, url_prefix="/purchases")

from root.achats import routes