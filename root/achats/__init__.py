from flask import Blueprint

purchases_bp = Blueprint('purchases_bp', __name__, url_prefix="/purchases")

from root.achats import routes