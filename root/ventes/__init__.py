from flask import Blueprint

sales_bp = Blueprint('sales_bp', __name__, url_prefix="/sales")

from root.ventes import routes