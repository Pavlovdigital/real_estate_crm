from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Client, User
from app.forms import ClientForm
import json
import logging

client_bp = Blueprint('client', __name__, url_prefix='/clients')
logger = logging.getLogger(__name__ + '.client_bp')

@client_bp.before_request
@login_required # All client routes require login
def before_request():
    # Could add role-specific checks here if needed in the future,
    # e.g., only 'Admin' or 'Agent' can modify clients.
    # For now, any logged-in user can manage clients.
    pass

@client_bp.route('/')
def list_clients():
    """Lists all clients."""
    clients = Client.query.order_by(Client.name).all()
    return render_template('clients/clients.html', clients=clients, title="Клиенты")

@client_bp.route('/add', methods=['GET', 'POST'])
def add_client():
    """Adds a new client."""
    form = ClientForm()
    if form.validate_on_submit():
        interests_data = None
        if form.interests_json.data:
            try:
                interests_data = json.loads(form.interests_json.data)
            except json.JSONDecodeError:
                flash('Ошибка в формате JSON для поля "Интересы". Изменения не сохранены.', 'danger')
                return render_template('clients/client_form.html', title="Добавить клиента", form=form, legend="Новый клиент")
        
        new_client = Client(
            name=form.name.data,
            phone=form.phone.data if form.phone.data else None,
            email=form.email.data if form.email.data else None,
            notes=form.notes.data,
            interests=interests_data,
            added_by_user_id=current_user.id
        )
        try:
            db.session.add(new_client)
            db.session.commit()
            flash(f"Клиент '{new_client.name}' успешно добавлен.", 'success')
            return redirect(url_for('client.list_clients'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка добавления клиента {form.name.data}: {e}", exc_info=True)
            flash(f"Ошибка при добавлении клиента: {str(e)}", 'danger')
            
    return render_template('clients/client_form.html', title="Добавить клиента", form=form, legend="Новый клиент")

@client_bp.route('/<int:client_id>/edit', methods=['GET', 'POST'])
def edit_client(client_id):
    """Edits an existing client."""
    client = Client.query.get_or_404(client_id)
    # Optional: Add authorization check if only admin or original adder can edit.
    # if client.added_by_user_id != current_user.id and not current_user.role.name == 'Admin':
    #     flash("У вас нет прав для редактирования этого клиента.", "danger")
    #     return redirect(url_for('client.list_clients'))

    form = ClientForm(obj=client) # Pre-populate form
    if request.method == 'GET':
        # Format interests back to JSON string for TextArea
        form.interests_json.data = json.dumps(client.interests, ensure_ascii=False, indent=2) if client.interests else ''
        
    if form.validate_on_submit():
        client.name = form.name.data
        client.phone = form.phone.data if form.phone.data else None
        client.email = form.email.data if form.email.data else None
        client.notes = form.notes.data
        
        if form.interests_json.data:
            try:
                client.interests = json.loads(form.interests_json.data)
            except json.JSONDecodeError:
                flash('Ошибка в формате JSON для поля "Интересы". Изменения не сохранены.', 'danger')
                return render_template('clients/client_form.html', title="Редактировать клиента", form=form, legend=f"Редактирование: {client.name}", client_id=client.id)
        else:
            client.interests = None
            
        try:
            db.session.commit()
            flash(f"Данные клиента '{client.name}' успешно обновлены.", 'success')
            return redirect(url_for('client.list_clients'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка обновления клиента {client.name}: {e}", exc_info=True)
            flash(f"Ошибка при обновлении клиента: {str(e)}", 'danger')

    return render_template('clients/client_form.html', title="Редактировать клиента", form=form, legend=f"Редактирование: {client.name}", client_id=client.id)

@client_bp.route('/<int:client_id>/delete', methods=['POST'])
def delete_client(client_id):
    """Deletes a client."""
    client = Client.query.get_or_404(client_id)
    # Optional: Add authorization check here as well
    # if client.added_by_user_id != current_user.id and not current_user.role.name == 'Admin':
    #     flash("У вас нет прав для удаления этого клиента.", "danger")
    #     return redirect(url_for('client.list_clients'))
    try:
        db.session.delete(client)
        db.session.commit()
        flash(f"Клиент '{client.name}' успешно удален.", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка удаления клиента {client.name}: {e}", exc_info=True)
        flash(f"Ошибка при удалении клиента: {str(e)}", 'danger')
        
    return redirect(url_for('client.list_clients'))
