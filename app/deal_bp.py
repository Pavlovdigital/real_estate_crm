from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Deal, Client, Property, User, DealStatusEnum, Role
from app.forms import DealForm
import json # For parsing interests JSON if needed, and for JSON responses
import logging

deal_bp = Blueprint('deal', __name__, url_prefix='/deals')
logger = logging.getLogger(__name__ + '.deal_bp')

@deal_bp.before_request
@login_required # All deal routes require login
def before_request():
    # Future: Role-based access can be refined here.
    # For now, any logged-in user can view, admins/agents can modify.
    pass

def _populate_deal_form_choices(form):
    """Helper to populate choices for SelectFields in DealForm."""
    form.client_id.choices = [(c.id, c.name) for c in Client.query.order_by(Client.name).all()]
    form.property_id.choices = [(p.id, f"{p.name} ({p.address})") for p in Property.query.order_by(Property.name).all()]
    # For agents, consider filtering by an 'Agent' role if such a role is consistently used.
    form.agent_id.choices = [(u.id, u.username) for u in User.query.order_by(User.username).all()]
    form.stage.choices = DealStatusEnum.choices()


@deal_bp.route('/')
def list_deals():
    """Lists all deals."""
    # Eager load related objects to prevent N+1 queries in template
    deals = Deal.query.options(
        db.joinedload(Deal.client),
        db.joinedload(Deal.property),
        db.joinedload(Deal.agent)
    ).order_by(Deal.created_at.desc()).all()
    return render_template('deals/deals.html', deals=deals, title="Все сделки")

@deal_bp.route('/add', methods=['GET', 'POST'])
def add_deal():
    """Adds a new deal."""
    form = DealForm()
    _populate_deal_form_choices(form)

    if form.validate_on_submit():
        new_deal = Deal(
            title=form.title.data,
            client_id=form.client_id.data,
            property_id=form.property_id.data,
            agent_id=form.agent_id.data, # Could default to current_user.id if user is an agent
            stage=form.stage.data
        )
        # If current_user is an agent and no specific agent_id is selected,
        # one might default form.agent_id.data to current_user.id in the form or here.
        # For now, it's a required selection.
        try:
            db.session.add(new_deal)
            db.session.commit()
            flash(f"Сделка '{new_deal.title}' успешно создана.", 'success')
            return redirect(url_for('deal.list_deals'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка создания сделки {form.title.data}: {e}", exc_info=True)
            flash(f"Ошибка при создании сделки: {str(e)}", 'danger')
            
    return render_template('deals/deal_form.html', title="Создать сделку", form=form, legend="Новая сделка")

@deal_bp.route('/<int:deal_id>/edit', methods=['GET', 'POST'])
def edit_deal(deal_id):
    """Edits an existing deal."""
    deal = Deal.query.get_or_404(deal_id)
    # Authorization: e.g., only agent assigned or admin can edit.
    # if deal.agent_id != current_user.id and not current_user.role.name == 'Admin':
    #     flash("У вас нет прав для редактирования этой сделки.", "danger")
    #     abort(403)

    form = DealForm(obj=deal)
    _populate_deal_form_choices(form)
        
    if form.validate_on_submit():
        deal.title = form.title.data
        deal.client_id = form.client_id.data
        deal.property_id = form.property_id.data
        deal.agent_id = form.agent_id.data
        deal.stage = form.stage.data
        # updated_at is handled by SQLAlchemy
        try:
            db.session.commit()
            flash(f"Сделка '{deal.title}' успешно обновлена.", 'success')
            return redirect(url_for('deal.list_deals'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка обновления сделки {deal.title}: {e}", exc_info=True)
            flash(f"Ошибка при обновлении сделки: {str(e)}", 'danger')

    return render_template('deals/deal_form.html', title="Редактировать сделку", form=form, legend=f"Редактирование: {deal.title}", deal_id=deal.id)

@deal_bp.route('/<int:deal_id>/delete', methods=['POST'])
def delete_deal(deal_id):
    """Deletes a deal."""
    deal = Deal.query.get_or_404(deal_id)
    # Add authorization if needed
    try:
        db.session.delete(deal)
        db.session.commit()
        flash(f"Сделка '{deal.title}' успешно удалена.", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка удаления сделки {deal.title}: {e}", exc_info=True)
        flash(f"Ошибка при удалении сделки: {str(e)}", 'danger')
        
    return redirect(url_for('deal.list_deals'))

@deal_bp.route('/kanban')
def kanban_board():
    """Displays deals on a Kanban board."""
    deals_by_stage = {}
    for stage_enum_member in DealStatusEnum:
        deals_by_stage[stage_enum_member.value] = Deal.query.filter_by(stage=stage_enum_member.value)\
            .options(db.joinedload(Deal.client), db.joinedload(Deal.property), db.joinedload(Deal.agent))\
            .order_by(Deal.updated_at.desc()).all()
            
    # Pass DealStatusEnum itself to the template to iterate over its members for columns
    return render_template('deals/kanban.html', title="Доска сделок (Канбан)", deals_by_stage=deals_by_stage, stages=DealStatusEnum)

@deal_bp.route('/<int:deal_id>/update_stage', methods=['POST'])
@login_required # Ensure only logged-in users can do this
def update_deal_stage(deal_id):
    """API endpoint to update a deal's stage (for Kanban drag-drop)."""
    deal = Deal.query.get_or_404(deal_id)
    data = request.get_json()
    new_stage_value = data.get('stage')

    if not new_stage_value:
        return jsonify({"status": "error", "message": "Новая стадия не указана."}), 400

    # Validate if the new_stage_value is a valid DealStatusEnum value
    valid_stages = [s.value for s in DealStatusEnum]
    if new_stage_value not in valid_stages:
        return jsonify({"status": "error", "message": f"Некорректная стадия: {new_stage_value}."}), 400
    
    # Authorization (optional, e.g., only assigned agent or admin)
    # if deal.agent_id != current_user.id and not current_user.role.name == 'Admin':
    #     return jsonify({"status": "error", "message": "Нет прав для изменения стадии этой сделки."}), 403

    try:
        deal.stage = new_stage_value
        deal.updated_at = datetime.utcnow() # Manually update if not relying on onupdate for this specific change type.
        db.session.commit()
        logger.info(f"Стадия сделки ID {deal.id} ('{deal.title}') обновлена на '{new_stage_value}' пользователем {current_user.username}.")
        return jsonify({"status": "success", "message": "Стадия сделки успешно обновлена."})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка обновления стадии для сделки ID {deal.id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Ошибка сервера при обновлении стадии: {str(e)}"}), 500
