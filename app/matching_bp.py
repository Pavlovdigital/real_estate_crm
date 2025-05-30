from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Client, Property, DealStatusEnum # Assuming Property model has necessary fields
from app.forms import ClientSelectionForm
import json # For parsing interests JSON
import logging
from sqlalchemy import or_ # For OR conditions in query

matching_bp = Blueprint('matching', __name__, url_prefix='/matching')
logger = logging.getLogger(__name__ + '.matching_bp')

def _populate_client_selection_form_choices(form):
    """Helper to populate choices for client selection."""
    clients = Client.query.order_by(Client.name).all()
    form.client_id.choices = [('', '--- Выберите клиента ---')] + [(c.id, c.name) for c in clients]

@matching_bp.route('/properties', methods=['GET', 'POST'])
@login_required
def match_properties_to_client():
    form = ClientSelectionForm()
    _populate_client_selection_form_choices(form)
    
    matching_properties = []
    selected_client = None
    client_interests_display = {} # For displaying interests in template

    if form.validate_on_submit():
        client_id = form.client_id.data
        selected_client = Client.query.get(client_id)

        if selected_client:
            logger.info(f"Поиск совпадений для клиента: {selected_client.name} (ID: {client_id})")
            if selected_client.interests and isinstance(selected_client.interests, dict): # Ensure interests is a dict
                interests = selected_client.interests
                client_interests_display = interests # Pass raw interests for display
                
                query = Property.query
                
                # Price range
                if interests.get('min_price') is not None:
                    query = query.filter(Property.price >= interests['min_price'])
                if interests.get('max_price') is not None:
                    query = query.filter(Property.price <= interests['max_price'])
                
                # Area range
                if interests.get('min_area') is not None:
                    query = query.filter(Property.area >= interests['min_area'])
                if interests.get('max_area') is not None:
                    query = query.filter(Property.area <= interests['max_area'])

                # Districts (can be a list or single string in JSON)
                districts_interest = interests.get('districts')
                if districts_interest:
                    if isinstance(districts_interest, list):
                        query = query.filter(Property.district.in_(districts_interest))
                    elif isinstance(districts_interest, str):
                        query = query.filter(Property.district == districts_interest)
                
                # Condition (single string)
                if interests.get('condition'):
                    query = query.filter(Property.condition == interests['condition'])
                
                # Layout (single string)
                if interests.get('layout'):
                    query = query.filter(Property.layout == interests['layout'])

                # Floor (min/max)
                if interests.get('min_floor') is not None:
                     query = query.filter(Property.floor >= interests['min_floor'])
                if interests.get('max_floor') is not None:
                     query = query.filter(Property.floor <= interests['max_floor'])

                # Year built (from/to)
                if interests.get('year_built_from') is not None:
                     query = query.filter(Property.year_built >= interests['year_built_from'])
                if interests.get('year_built_to') is not None:
                     query = query.filter(Property.year_built <= interests['year_built_to'])

                # Exclude properties already in "Успешно закрыта" or "В работе" deals for this client to avoid suggesting them again.
                # This is a more advanced filter.
                # existing_deals_subquery = db.session.query(Deal.property_id).filter(
                #     Deal.client_id == client_id,
                #     or_(Deal.stage == DealStatusEnum.CLOSED_WON.value, Deal.stage == DealStatusEnum.IN_PROGRESS.value)
                # ).subquery()
                # query = query.filter(Property.id.notin_(existing_deals_subquery))


                matching_properties = query.order_by(Property.price).all()
                
                if matching_properties:
                    flash(f"Найдено {len(matching_properties)} подходящих объектов для клиента '{selected_client.name}'.", "success")
                else:
                    flash(f"Подходящие объекты для клиента '{selected_client.name}' по указанным интересам не найдены.", "info")
            else:
                flash(f"У клиента '{selected_client.name}' не указаны или некорректно заданы интересы (требуется JSON).", "warning")
                client_interests_display = {"ошибка": "Интересы не заданы или указаны некорректно."} if not selected_client.interests else selected_client.interests
        else:
            flash("Клиент не найден.", "danger")
            
    # If GET request, client_id might be in args
    elif request.method == 'GET' and request.args.get('client_id'):
        try:
            client_id = int(request.args.get('client_id'))
            form.client_id.data = client_id # Pre-select client in form
            # Optionally, trigger form validation and processing if you want GET to also show results
            # For now, GET just pre-selects the client. User needs to click submit.
            selected_client = Client.query.get(client_id)
            if selected_client and selected_client.interests and isinstance(selected_client.interests, dict):
                 client_interests_display = selected_client.interests
            elif selected_client:
                 client_interests_display = {"info": "У этого клиента не заданы интересы в формате JSON."}


        except ValueError:
            flash("Некорректный ID клиента в URL.", "danger")


    return render_template('matching/matching_properties.html', 
                           title="Подбор объектов для клиента", 
                           form=form, 
                           matching_properties=matching_properties,
                           selected_client=selected_client,
                           client_interests_display=client_interests_display)
