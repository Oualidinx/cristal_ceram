from flask import Blueprint

auth_bp = Blueprint('auth_bp',__name__, url_prefix="/auth", template_folder="templates/auth")

from root.auth import routes