from flask import Blueprint

sales_bp = Blueprint('Sales', __name__, url_prefix="/sales")

from root.ventes import routes