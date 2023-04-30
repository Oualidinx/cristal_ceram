from flask import Blueprint

socket_notification_bp = Blueprint('socket_notification_bp', __name__, url_prefix="/notifications")

from . import routes