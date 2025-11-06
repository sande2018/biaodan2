from datetime import datetime
from app import db
from sqlalchemy.dialects.sqlite import JSON
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    cdk_enabled = db.Column(db.Boolean, default=False)
    cdk_stock = db.Column(db.Integer, default=0)
    cdk_description = db.Column(db.Text, nullable=True)
    cdk_popup = db.Column(db.Boolean, default=False)
    ip_limit = db.Column(db.Integer, default=0)  # 0表示无限制
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    fields = db.relationship('FormField', backref='form', lazy='dynamic')
    submissions = db.relationship('FormSubmission', backref='form', lazy='dynamic')
    cdks = db.relationship('CDK', backref='form', lazy='dynamic')

class FormField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # text, email, phone, select, radio, checkbox, textarea
    required = db.Column(db.Boolean, default=False)
    options = db.Column(JSON, nullable=True)  # 用于select, radio, checkbox
    placeholder = db.Column(db.String(200), nullable=True)
    order = db.Column(db.Integer, default=0)
    validation_rules = db.Column(JSON, nullable=True)
    style = db.Column(JSON, nullable=True)

class FormSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    data = db.Column(JSON, nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(500), nullable=False)
    cdk_id = db.Column(db.Integer, db.ForeignKey('cdk.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CDK(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
