"""
Database models and connection setup
Using SQLAlchemy for ORM
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

db = SQLAlchemy()


def init_db(app):
    """Initialize database with Flask app"""
    # Use SQLite for MVP, can switch to PostgreSQL later
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///stock_forecast.db')
    
    # Handle postgres:// vs postgresql:// for compatibility
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()


class Product(db.Model):
    """Product/SKU master data"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(500))
    length = db.Column(db.Float, default=0)
    width = db.Column(db.Float, default=0)
    height = db.Column(db.Float, default=0)
    cbm = db.Column(db.Float, default=0)
    weight = db.Column(db.Float, default=0)
    barcode = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('OrderLine', back_populates='product', lazy='dynamic')
    stock_levels = db.relationship('StockLevel', back_populates='product', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'description': self.description,
            'length': self.length,
            'width': self.width,
            'height': self.height,
            'cbm': self.cbm,
            'weight': self.weight,
            'barcode': self.barcode
        }


class Order(db.Model):
    """Sales orders from Cin7"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    cin7_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    order_number = db.Column(db.String(100), index=True)
    order_date = db.Column(db.Date, index=True)
    warehouse_code = db.Column(db.String(50), index=True)
    status = db.Column(db.String(50))
    reference = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lines = db.relationship('OrderLine', back_populates='order', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'cin7_id': self.cin7_id,
            'order_number': self.order_number,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'warehouse_code': self.warehouse_code,
            'status': self.status,
            'reference': self.reference,
            'lines': [line.to_dict() for line in self.lines]
        }


class OrderLine(db.Model):
    """Individual line items in orders"""
    __tablename__ = 'order_lines'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    sku = db.Column(db.String(100), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)
    warehouse_code = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', back_populates='lines')
    product = db.relationship('Product', back_populates='orders')
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'quantity': self.quantity,
            'warehouse_code': self.warehouse_code
        }


class StockLevel(db.Model):
    """Current stock levels by warehouse"""
    __tablename__ = 'stock_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    sku = db.Column(db.String(100), nullable=False, index=True)
    warehouse_code = db.Column(db.String(50), nullable=False, index=True)
    on_hand = db.Column(db.Float, default=0)
    available = db.Column(db.Float, default=0)
    allocated = db.Column(db.Float, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', back_populates='stock_levels')
    
    # Unique constraint on sku + warehouse
    __table_args__ = (
        db.UniqueConstraint('sku', 'warehouse_code', name='_sku_warehouse_uc'),
    )
    
    def to_dict(self):
        return {
            'sku': self.sku,
            'warehouse_code': self.warehouse_code,
            'on_hand': self.on_hand,
            'available': self.available,
            'allocated': self.allocated,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class ForecastConfig(db.Model):
    """Configuration for forecasting parameters"""
    __tablename__ = 'forecast_config'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False, index=True)
    lead_time_days = db.Column(db.Integer, default=30)
    buffer_stock_days = db.Column(db.Integer, default=30)
    min_order_qty = db.Column(db.Float, default=1)
    order_multiple = db.Column(db.Float, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'sku': self.sku,
            'lead_time_days': self.lead_time_days,
            'buffer_stock_days': self.buffer_stock_days,
            'min_order_qty': self.min_order_qty,
            'order_multiple': self.order_multiple,
            'is_active': self.is_active
        }
