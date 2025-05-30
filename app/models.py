from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
# db is now initialized in app/__init__.py, so we import it from there
from app import db 
from datetime import datetime

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy='dynamic')
    # Add a relationship to properties for admin/system use if needed
    # properties = db.relationship('Property', backref='role_info', lazy='dynamic')


    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False) 
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    # Renaming backref to avoid conflict with Property.added_by_user relationship
    properties = db.relationship('Property', backref='creator_of_property', lazy='dynamic') 
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # Optional for User

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Property(db.Model):
    __tablename__ = 'properties'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False) 
    address = db.Column(db.String(255), nullable=True) # User schema implies address might not always be required initially
    
    cat = db.Column(db.String(32), nullable=True)  # Категория недвижимости (e.g. "Квартира", "Дом")
    status = db.Column(db.String(32), nullable=True) # Статус объекта (e.g. "Активно", "Продано", "В архиве")
    
    district = db.Column(db.String(64), nullable=True) 
    price = db.Column(db.Float, nullable=True) 
    
    # plan = db.Column(db.String(32), nullable=True) # User schema name for layout, was 'layout' previously
    # Sticking to 'layout' as it was in the model for multiple steps, to reduce migration complexity unless 'plan' is critical
    layout = db.Column(db.String(100), nullable=True) # Retaining 'layout' from prior model. User schema has 'plan'

    floor = db.Column(db.Integer, nullable=True)
    total_floors = db.Column(db.Integer, nullable=True) 
    area = db.Column(db.Float, nullable=True) # общая площадь, nullable based on typical initial data
    
    m = db.Column(db.String(32), nullable=True)      # Материал стен
    s = db.Column(db.String(16), nullable=True)      # Площадь (возможно жилая - "s")
    s_kh = db.Column(db.String(16), nullable=True)   # Площадь кухни
    blkn = db.Column(db.String(16), nullable=True)   # Балкон
    p = db.Column(db.String(16), nullable=True)      # Расположение (угловая/неугловая)
    
    condition = db.Column(db.String(64), nullable=True) # Состояние (was String(100))
    seller_phone = db.Column(db.String(32), nullable=True) # Increased length (was String(20))
    
    street = db.Column(db.String(128), nullable=True) # Улица
    d_kv = db.Column(db.String(32), nullable=True)   # Дом/квартира номер

    year = db.Column(db.String(16), nullable=True) # Год постройки (was year_built, Integer)
    description = db.Column(db.Text, nullable=True)
    
    source = db.Column(db.String(32), nullable=True) # Источник объявления (e.g., "OLX", "Krisha", "Manual")
    photos = db.Column(db.Text, nullable=True) # Renamed from image_urls, stores comma-separated or JSON list
    link = db.Column(db.String(512), nullable=True, index=True) # Renamed from source_url (original ad URL)
    external_id = db.Column(db.String(128), nullable=True, index=True) # Updated length from 100
    
    added_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Was nullable=False
    last_scraped_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # This is the direct relationship from Property to User who created it.
    added_by_user = db.relationship('User', foreign_keys=[added_by_user_id], backref=db.backref('created_properties', lazy='dynamic'))
    history_entries = db.relationship('PropertyHistory', backref='property_item', lazy='dynamic', cascade="all, delete-orphan")
    # The 'deals_collection' backref will be created from the Deal.property relationship.
    # deals = db.relationship('Deal', backref='property_item', lazy='dynamic') # This line is removed
    images = db.relationship('PropertyImage', backref='property', lazy='dynamic', cascade="all, delete-orphan")

    # Unique constraint for source and external_id
    __table_args__ = (db.UniqueConstraint('source', 'external_id', name='_source_external_id_uc'),)

    def __repr__(self):
        return f'<Property {self.id} - {self.name}>'

class PropertyImage(db.Model):
    __tablename__ = 'property_images'
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False, index=True)
    # image_data = db.Column(db.LargeBinary, nullable=False) # Storing large blobs might not be ideal for all DBs/performance
    # Storing path to image is generally preferred. Let's assume path is stored, not blob.
    # If blob is truly needed, uncomment above and ensure DB support.
    # CRITICAL: Use LargeBinary for image_data. DO NOT use String or Text for a path.
    image_data = db.Column(db.LargeBinary, nullable=False)
    filename = db.Column(db.String(255), nullable=True) # Original filename for context
    mimetype = db.Column(db.String(50), nullable=True) # e.g., 'image/jpeg', 'image/png'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PropertyImage {self.id} for Property {self.property_id}>'

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True, unique=True)
    email = db.Column(db.String(120), nullable=True, unique=True)
    notes = db.Column(db.Text, nullable=True)
    interests = db.Column(db.JSON, nullable=True) # Store client interests as JSON
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    added_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # Relationship to User (Agent/Admin who added the client)
    # added_by = db.relationship('User', backref=db.backref('added_clients', lazy='dynamic')) 
    # Decided not to add backref immediately to User to keep it simple, can be added later.
    # For consistency, let's ensure added_by relationship is available for querying
    added_by = db.relationship('User', backref=db.backref('created_clients', lazy='dynamic')) # Changed backref


    def __repr__(self):
        return f'<Client {self.name}>'

import enum

class DealStatusEnum(enum.Enum):
    NEW = "Новая"
    IN_PROGRESS = "В работе"
    NEGOTIATION = "Переговоры" 
    CLOSED_WON = "Успешно закрыта"
    CLOSED_LOST = "Не закрыта"

    @classmethod
    def choices(cls):
        # Returns list of tuples like [('Новая', 'Новая'), ('В Работе', 'В Работе')] for SelectField
        return [(choice.value, choice.value) for choice in cls]

    @classmethod
    def values(cls):
        # Returns list of string values like ['Новая', 'В работе', ...]
        return [choice.value for choice in cls]

class Deal(db.Model):
    __tablename__ = 'deals'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False, default="Сделка")
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Responsible agent
    
    stage = db.Column(db.String(50), nullable=False, default=DealStatusEnum.NEW.value)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = db.relationship('Client', backref=db.backref('deals', lazy='dynamic'))
    # The backref 'deals_collection' will create Property.deals_collection
    property = db.relationship('Property', backref=db.backref('deals_collection', lazy='dynamic')) 
    agent = db.relationship('User', backref=db.backref('assigned_deals', lazy='dynamic'))

    def __repr__(self):
        return f'<Deal {self.title} - Client: {self.client.name if self.client else "N/A"}>'

class PropertyHistory(db.Model):
    __tablename__ = 'property_history'
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # User who made the change
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)

    # Relationships
    # property relationship defined in Property model via backref='history_entries'
    user = db.relationship('User', backref=db.backref('property_history_entries', lazy='dynamic')) 

    def __repr__(self):
        return f'<PropertyHistory {self.id} for Property {self.property_id} - Field: {self.field_name}>'
