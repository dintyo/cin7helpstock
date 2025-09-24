"""
Sales velocity calculation module
Calculates sales velocity (units per day) for SKUs
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func, and_
from database import db, OrderLine, Order
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class SalesVelocityCalculator:
    """Calculates sales velocity and related metrics"""
    
    def __init__(self, database):
        self.db = database
    
    def calculate_velocity(self, sku: str, days: int = 30, 
                          warehouse: Optional[str] = None) -> Dict:
        """
        Calculate sales velocity for a SKU
        
        Args:
            sku: SKU code
            days: Number of days to look back
            warehouse: Optional warehouse filter (VIC/QLD/NSW)
        
        Returns:
            Dictionary with velocity metrics
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            # Build query
            query = self.db.session.query(
                func.sum(OrderLine.quantity).label('total_quantity'),
                func.count(OrderLine.id).label('order_count'),
                func.min(Order.order_date).label('first_order'),
                func.max(Order.order_date).label('last_order')
            ).join(
                Order, OrderLine.order_id == Order.id
            ).filter(
                and_(
                    OrderLine.sku == sku,
                    Order.order_date >= start_date,
                    Order.order_date <= end_date,
                    Order.status != 'VOIDED'  # Exclude cancelled orders
                )
            )
            
            # Add warehouse filter if specified
            if warehouse:
                query = query.filter(Order.warehouse_code == warehouse)
            
            result = query.first()
            
            total_quantity = result.total_quantity or 0
            order_count = result.order_count or 0
            
            # Calculate actual days with sales
            actual_days = days
            if result.first_order and result.last_order:
                actual_days = (result.last_order - result.first_order).days + 1
                actual_days = min(actual_days, days)  # Cap at requested days
            
            # Calculate velocity
            daily_average = total_quantity / actual_days if actual_days > 0 else 0
            
            # Get daily breakdown for trend analysis
            daily_sales = self._get_daily_sales(sku, start_date, end_date, warehouse)
            
            # Calculate trend (simple linear regression)
            trend = self._calculate_trend(daily_sales)
            
            # Calculate variability (coefficient of variation)
            variability = self._calculate_variability(daily_sales)
            
            return {
                'sku': sku,
                'period_days': days,
                'actual_days': actual_days,
                'total_quantity': total_quantity,
                'order_count': order_count,
                'daily_average': daily_average,
                'weekly_average': daily_average * 7,
                'monthly_average': daily_average * 30,
                'trend': trend,  # Positive = increasing, negative = decreasing
                'variability': variability,  # Higher = more variable
                'warehouse': warehouse or 'ALL',
                'first_sale': result.first_order.isoformat() if result.first_order else None,
                'last_sale': result.last_order.isoformat() if result.last_order else None
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate velocity for {sku}: {e}")
            return {
                'sku': sku,
                'error': str(e),
                'daily_average': 0,
                'weekly_average': 0,
                'monthly_average': 0
            }
    
    def _get_daily_sales(self, sku: str, start_date, end_date, 
                        warehouse: Optional[str] = None) -> List[Dict]:
        """Get daily sales breakdown"""
        query = self.db.session.query(
            Order.order_date,
            func.sum(OrderLine.quantity).label('quantity')
        ).join(
            Order, OrderLine.order_id == Order.id
        ).filter(
            and_(
                OrderLine.sku == sku,
                Order.order_date >= start_date,
                Order.order_date <= end_date,
                Order.status != 'VOIDED'
            )
        ).group_by(Order.order_date)
        
        if warehouse:
            query = query.filter(Order.warehouse_code == warehouse)
        
        results = query.all()
        
        # Convert to list of dicts
        daily_data = []
        for date, quantity in results:
            daily_data.append({
                'date': date,
                'quantity': quantity or 0
            })
        
        return daily_data
    
    def _calculate_trend(self, daily_sales: List[Dict]) -> float:
        """Calculate sales trend using linear regression"""
        if len(daily_sales) < 2:
            return 0.0
        
        try:
            # Create DataFrame
            df = pd.DataFrame(daily_sales)
            if df.empty:
                return 0.0
            
            # Add numeric day column
            df['day_num'] = range(len(df))
            
            # Simple linear regression
            x = df['day_num'].values
            y = df['quantity'].values
            
            # Calculate slope
            if len(x) > 1:
                slope = np.polyfit(x, y, 1)[0]
                return float(slope)
            
        except Exception as e:
            logger.error(f"Failed to calculate trend: {e}")
        
        return 0.0
    
    def _calculate_variability(self, daily_sales: List[Dict]) -> float:
        """Calculate coefficient of variation for sales"""
        if not daily_sales:
            return 0.0
        
        try:
            quantities = [d['quantity'] for d in daily_sales]
            
            if not quantities:
                return 0.0
            
            mean_qty = np.mean(quantities)
            if mean_qty == 0:
                return 0.0
            
            std_qty = np.std(quantities)
            cv = (std_qty / mean_qty) * 100  # As percentage
            
            return float(cv)
            
        except Exception as e:
            logger.error(f"Failed to calculate variability: {e}")
            return 0.0
    
    def calculate_velocity_bulk(self, skus: List[str], days: int = 30) -> List[Dict]:
        """Calculate velocity for multiple SKUs"""
        results = []
        for sku in skus:
            velocity = self.calculate_velocity(sku, days)
            results.append(velocity)
        
        # Sort by daily average (highest first)
        results.sort(key=lambda x: x.get('daily_average', 0), reverse=True)
        
        return results
    
    def get_top_movers(self, days: int = 30, limit: int = 20) -> List[Dict]:
        """Get top selling SKUs by velocity"""
        # Get all SKUs with sales in the period
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        query = self.db.session.query(
            OrderLine.sku,
            func.sum(OrderLine.quantity).label('total_quantity')
        ).join(
            Order, OrderLine.order_id == Order.id
        ).filter(
            and_(
                Order.order_date >= start_date,
                Order.order_date <= end_date,
                Order.status != 'VOIDED'
            )
        ).group_by(
            OrderLine.sku
        ).order_by(
            func.sum(OrderLine.quantity).desc()
        ).limit(limit)
        
        results = []
        for sku, total_quantity in query.all():
            velocity = self.calculate_velocity(sku, days)
            results.append(velocity)
        
        return results
    
    def get_slow_movers(self, days: int = 90, threshold: float = 0.1) -> List[Dict]:
        """Get slow-moving SKUs (low velocity)"""
        # Get all SKUs
        from database import Product
        all_skus = self.db.session.query(Product.sku).all()
        
        slow_movers = []
        for (sku,) in all_skus:
            velocity = self.calculate_velocity(sku, days)
            
            # Check if it's a slow mover
            if velocity.get('daily_average', 0) < threshold:
                slow_movers.append(velocity)
        
        # Sort by velocity (lowest first)
        slow_movers.sort(key=lambda x: x.get('daily_average', 0))
        
        return slow_movers
    
    def calculate_seasonality(self, sku: str, months: int = 12) -> Dict:
        """Calculate seasonality patterns for a SKU"""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=months * 30)
            
            # Get monthly aggregates
            query = self.db.session.query(
                func.extract('month', Order.order_date).label('month'),
                func.extract('year', Order.order_date).label('year'),
                func.sum(OrderLine.quantity).label('quantity')
            ).join(
                Order, OrderLine.order_id == Order.id
            ).filter(
                and_(
                    OrderLine.sku == sku,
                    Order.order_date >= start_date,
                    Order.order_date <= end_date,
                    Order.status != 'VOIDED'
                )
            ).group_by(
                func.extract('year', Order.order_date),
                func.extract('month', Order.order_date)
            )
            
            monthly_data = {}
            for month, year, quantity in query.all():
                month_key = f"{int(year)}-{int(month):02d}"
                monthly_data[month_key] = quantity or 0
            
            # Calculate average by month
            month_averages = {}
            for month_num in range(1, 13):
                month_quantities = [
                    qty for key, qty in monthly_data.items() 
                    if key.endswith(f"-{month_num:02d}")
                ]
                if month_quantities:
                    month_averages[month_num] = np.mean(month_quantities)
                else:
                    month_averages[month_num] = 0
            
            # Calculate seasonality index (ratio to average)
            overall_average = np.mean(list(month_averages.values()))
            seasonality_index = {}
            
            if overall_average > 0:
                for month, avg in month_averages.items():
                    seasonality_index[month] = avg / overall_average
            else:
                seasonality_index = {m: 1.0 for m in range(1, 13)}
            
            return {
                'sku': sku,
                'monthly_averages': month_averages,
                'seasonality_index': seasonality_index,
                'peak_month': max(month_averages, key=month_averages.get) if month_averages else None,
                'low_month': min(month_averages, key=month_averages.get) if month_averages else None
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate seasonality for {sku}: {e}")
            return {
                'sku': sku,
                'error': str(e)
            }
