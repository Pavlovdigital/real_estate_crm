from flask import Blueprint, render_template, abort, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
# Updated import for parser_service to include run_parsing_task
from app.services.parser_service import run_parsing_task 
# Scrapers are now called from within run_parsing_task, so direct import here might not be needed
# from app.scrapers.olx_scraper import scrape_olx 
# from app.scrapers.krisha_scraper import scrape_krisha
from flask import current_app, session # Added session for status
import threading # For background tasks
import logging # Already imported but good to note

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
# Logger for admin blueprint
admin_logger = logging.getLogger(__name__ + '.admin_bp')
if not admin_logger.handlers:
    admin_handler = logging.StreamHandler()
    admin_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    admin_handler.setFormatter(admin_formatter)
    admin_logger.addHandler(admin_handler)
    admin_logger.setLevel(logging.INFO)

@admin_bp.before_request
@login_required
def require_admin_access():
    """Ensures only users with the 'Admin' role can access admin routes."""
    if not current_user.is_authenticated or not current_user.role or current_user.role.name != 'Admin':
        flash("У вас нет доступа к этой странице.", "danger")
        abort(403) # Forbidden

@admin_bp.route('/parser')
def parser_dashboard():
    """Displays the main parser management dashboard."""
    # Placeholder for last run status (could be fetched from a log, db, or session)
    last_run_summary = session.get('last_parser_run_summary', None) # Example using session
    last_run_summary = session.get('last_parser_run_summary', None) 
    return render_template('admin/parser_dashboard.html', title="Управление Парсером", last_run_summary=last_run_summary)

@admin_bp.route('/parser/run/olx', methods=['POST']) # Corrected to POST
def run_olx_parser_route():
    # Using current_app._get_current_object() to pass the actual app instance to the thread
    app_context = current_app._get_current_object()
    
    olx_url = app_context.config.get('OLX_BASE_URL', "https://www.olx.kz/nedvizhimost/prodazha-kvartiry/petropavlovsk/?search%5Bfilter_enum_tipsobstvennosti%5D%5B0%5D=ot_hozyaina")
    
    # Initialize parser status in session
    session['parser_status'] = {
        "progress_percent": 0, "current_task": "Инициализация парсера OLX.kz...",
        "log": [f"{datetime.now().strftime('%H:%M:%S')}: Запрос на запуск OLX.kz парсера."],
        "complete": False, "summary": None, "error": None
    }
    session.modified = True # Ensure session is saved

    thread = threading.Thread(target=run_parsing_task, args=(app_context, "OLX.kz", 1, olx_url)) # num_pages = 1 for test
    thread.start()
    
    admin_logger.info("Парсер OLX.kz запущен в фоновом потоке.")
    return jsonify({"status": "started", "message": "Парсинг OLX.kz запущен в фоновом режиме..."})

@admin_bp.route('/parser/run/krisha', methods=['POST']) # Changed to POST
def run_krisha_parser_route():
    app_context = current_app._get_current_object()
    krisha_url = app_context.config.get('KRISHA_BASE_URL', "https://krisha.kz/prodazha/kvartiry/petropavlovsk/?das[who]=1")

    session['parser_status'] = {
        "progress_percent": 0, "current_task": "Инициализация парсера Krisha.kz...",
        "log": [f"{datetime.now().strftime('%H:%M:%S')}: Запрос на запуск Krisha.kz парсера."],
        "complete": False, "summary": None, "error": None
    }
    session.modified = True

    thread = threading.Thread(target=run_parsing_task, args=(app_context, "Krisha.kz", 1, krisha_url)) # num_pages = 1 for test
    thread.start()

    admin_logger.info("Парсер Krisha.kz запущен в фоновом потоке.")
    return jsonify({"status": "started", "message": "Парсинг Krisha.kz запущен в фоновом режиме..."})

@admin_bp.route('/parser/status')
def parser_status_route():
    status = session.get('parser_status', {
        "progress_percent": 0, "current_task": "Нет активных задач.",
        "log": [], "complete": True, "summary": None, "error": None
    })
    # admin_logger.debug(f"Polling status: {status}") # Can be verbose
    return jsonify(status)


# Session is already imported

# --- User Management Routes ---
from app.models import User, Role # Ensure User, Role are imported
from app.forms import AdminUserEditForm # Will be created in next step

@admin_bp.route('/users')
def list_users():
    """Lists all users for admin management."""
    # Consider adding pagination for many users: users = User.query.paginate(page=request.args.get('page', 1, type=int), per_page=15)
    users = User.query.order_by(User.id).all()
    return render_template('admin/user_list.html', users=users, title="Управление пользователями")

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id)
    form = AdminUserEditForm(obj=user_to_edit) # Pass obj to pre-populate and for validation context

    # Populate role choices
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]

    if form.validate_on_submit():
        # Store original username/email before attempting to change, for validation check
        original_username = user_to_edit.username
        original_email = user_to_edit.email

        # Check for username uniqueness if changed
        if form.username.data != original_username:
            if User.query.filter_by(username=form.username.data).first():
                form.username.errors.append("Это имя пользователя уже занято.")
            else:
                user_to_edit.username = form.username.data
        
        # Check for email uniqueness if changed
        if form.email.data != original_email:
            if User.query.filter_by(email=form.email.data).first():
                form.email.errors.append("Этот email уже используется.")
            else:
                user_to_edit.email = form.email.data
        
        user_to_edit.role_id = form.role_id.data

        if not form.errors: # If no new validation errors were added
            try:
                db.session.commit()
                flash(f"Данные пользователя '{user_to_edit.username}' успешно обновлены.", "success")
                return redirect(url_for('admin.list_users'))
            except Exception as e:
                db.session.rollback()
                admin_logger.error(f"Ошибка обновления пользователя {user_to_edit.username}: {e}", exc_info=True)
                flash(f"Ошибка при обновлении пользователя: {str(e)}", "danger")
    
    # For GET request, pre-populate form fields (already done by passing obj=user_to_edit to form constructor)
    # form.username.data = user_to_edit.username
    # form.email.data = user_to_edit.email
    # form.role_id.data = user_to_edit.role_id
            
    return render_template('admin/user_edit_form.html', 
                           form=form, 
                           user=user_to_edit, 
                           title=f"Редактировать: {user_to_edit.username}")
                           
# Import datetime for session initialization log
from datetime import datetime
