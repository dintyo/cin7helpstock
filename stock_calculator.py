"""
Stock calculation and management module
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func
from database import db, Product, Order, OrderLine, StockLevel, ForecastConfig
import logging

logger = logging.getLogger(__name__)


class StockCalculator:
    """Handles stock calculations and database operations"""
    
    def __init__(self, database):
        self.db = database
    
    def store_order(self, order_data: Dict) -> bool:
        """Store order from Cin7 in database"""
        try:
            # Check if order already exists
            existing = Order.query.filter_by(cin7_id=order_data.get('SaleID')).first()
            if existing:
                return False
            
            # Parse order date
            order_date = None
            if order_data.get('OrderDate'):
                try:
                    order_date = datetime.strptime(order_data['OrderDate'], '%Y-%m-%dT%H:%M:%S').date()
                except:
                    order_date = datetime.strptime(order_data['OrderDate'][:10], '%Y-%m-%d').date()
            
            # Create order
            order = Order(
                cin7_id=order_data.get('SaleID'),
                order_number=order_data.get('OrderNumber'),
                order_date=order_date,
                warehouse_code=order_data.get('warehouse_code', 'UNKNOWN'),
                status=order_data.get('Status'),
                reference=order_data.get('Reference')
            )
            
            self.db.session.add(order)
            self.db.session.commit()
            
            # Store order lines if we have detail
            if 'Lines' in order_data:
                for line in order_data.get('Lines', []):
                    self._store_order_line(order.id, line, order.warehouse_code)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store order: {e}")
            self.db.session.rollback()
            return False
    
    def _store_order_line(self, order_id: int, line_data: Dict, warehouse_code: str) -> bool:
        """Store individual order line"""
        try:
            sku = line_data.get('SKU', '')
            if not sku:
                return False
            
            # Find or create product
            product = Product.query.filter_by(sku=sku).first()
            
            line = OrderLine(
                order_id=order_id,
                product_id=product.id if product else None,
                sku=sku,
                quantity=line_data.get('Quantity', 0),
                warehouse_code=warehouse_code
            )
            
            self.db.session.add(line)
            self.db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store order line: {e}")
            self.db.session.rollback()
            return False
    
    def store_product(self, product_data: Dict) -> bool:
        """Store product/SKU in database"""
        try:
            sku = product_data.get('sku', '')
            if not sku:
                return False
            
            # Check if product exists
            product = Product.query.filter_by(sku=sku).first()
            
            if product:
                # Update existing
                product.description = product_data.get('description', product.description)
                product.length = product_data.get('length', product.length)
                product.width = product_data.get('width', product.width)
                product.height = product_data.get('height', product.height)
                product.cbm = product_data.get('cbm', product.cbm)
                product.weight = product_data.get('weight', product.weight)
                product.barcode = product_data.get('barcode', product.barcode)
                product.updated_at = datetime.utcnow()
            else:
                # Create new
                product = Product(
                    sku=sku,
                    description=product_data.get('description'),
                    length=product_data.get('length', 0),
                    width=product_data.get('width', 0),
                    height=product_data.get('height', 0),
                    cbm=product_data.get('cbm', 0),
                    weight=product_data.get('weight', 0),
                    barcode=product_data.get('barcode')
                )
                self.db.session.add(product)
            
            self.db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store product: {e}")
            self.db.session.rollback()
            return False
    
    def update_stock_levels(self, stock_data: List[Dict]) -> int:
        """Update stock levels from Cin7 data"""
        updated_count = 0
        
        for item in stock_data:
            try:
                sku = item.get('sku', '')
                warehouse = item.get('warehouse', 'UNKNOWN')
                
                if not sku:
                    continue
                
                # Find or create stock level record
                stock = StockLevel.query.filter_by(
                    sku=sku,
                    warehouse_code=warehouse
                ).first()
                
                if stock:
                    stock.on_hand = item.get('on_hand', 0)
                    stock.available = item.get('available', 0)
                    stock.allocated = item.get('allocated', 0)
                    stock.last_updated = datetime.utcnow()
                else:
                    stock = StockLevel(
                        sku=sku,
                        warehouse_code=warehouse,
                        on_hand=item.get('on_hand', 0),
                        available=item.get('available', 0),
                        allocated=item.get('allocated', 0)
                    )
                    self.db.session.add(stock)
                
                self.db.session.commit()
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update stock level for {sku}: {e}")
                self.db.session.rollback()
        
        return updated_count
    
    def calculate_stock_by_warehouse(self, stock_data: List[Dict]) -> Dict:
        """Group stock data by warehouse"""
        warehouse_stock = {
            'VIC': {},
            'QLD': {},
            'NSW': {},
            'TOTAL': {}
        }
        
        # First, update the database
        self.update_stock_levels(stock_data)
        
        # Then aggregate by warehouse
        for item in stock_data:
            sku = item.get('sku', '')
            warehouse = item.get('warehouse', 'UNKNOWN')
            on_hand = item.get('on_hand', 0)
            
            if not sku:
                continue
            
            # Add to specific warehouse
            if warehouse in warehouse_stock:
                if sku not in warehouse_stock[warehouse]:
                    warehouse_stock[warehouse][sku] = 0
                warehouse_stock[warehouse][sku] += on_hand
            
            # Add to total
            if sku not in warehouse_stock['TOTAL']:
                warehouse_stock['TOTAL'][sku] = 0
            warehouse_stock['TOTAL'][sku] += on_hand
        
        return warehouse_stock
    
    def get_stock_on_hand(self, sku: str) -> Dict:
        """Get current stock levels for a SKU across all warehouses"""
        stock_levels = StockLevel.query.filter_by(sku=sku).all()
        
        result = {
            'sku': sku,
            'total': 0,
            'by_warehouse': {}
        }
        
        for stock in stock_levels:
            result['by_warehouse'][stock.warehouse_code] = {
                'on_hand': stock.on_hand,
                'available': stock.available,
                'allocated': stock.allocated
            }
            result['total'] += stock.on_hand
        
        return result
    
    def get_all_skus(self) -> List[Dict]:
        """Get all SKUs with basic info"""
        products = Product.query.all()
        return [p.to_dict() for p in products]
    
    def get_forecast_config(self, sku: str) -> Optional[Dict]:
        """Get forecast configuration for a SKU"""
        config = ForecastConfig.query.filter_by(sku=sku).first()
        if config:
            return config.to_dict()
        
        # Return default config if none exists
        return {
            'sku': sku,
            'lead_time_days': 30,
            'buffer_stock_days': 30,
            'min_order_qty': 1,
            'order_multiple': 1,
            'is_active': True
        }
    
    def update_forecast_config(self, sku: str, config_data: Dict) -> bool:
        """Update forecast configuration for a SKU"""
        try:
            config = ForecastConfig.query.filter_by(sku=sku).first()
            
            if config:
                config.lead_time_days = config_data.get('lead_time_days', config.lead_time_days)
                config.buffer_stock_days = config_data.get('buffer_stock_days', config.buffer_stock_days)
                config.min_order_qty = config_data.get('min_order_qty', config.min_order_qty)
                config.order_multiple = config_data.get('order_multiple', config.order_multiple)
                config.is_active = config_data.get('is_active', config.is_active)
                config.updated_at = datetime.utcnow()
            else:
                config = ForecastConfig(
                    sku=sku,
                    lead_time_days=config_data.get('lead_time_days', 30),
                    buffer_stock_days=config_data.get('buffer_stock_days', 30),
                    min_order_qty=config_data.get('min_order_qty', 1),
                    order_multiple=config_data.get('order_multiple', 1),
                    is_active=config_data.get('is_active', True)
                )
                self.db.session.add(config)
            
            self.db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update forecast config: {e}")
            self.db.session.rollback()
            return False
