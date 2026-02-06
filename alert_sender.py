#!/usr/bin/env python3
"""
Mega MU Alert Sender
Checks alerts and sends email notifications
"""

import os
import sys
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional

try:
    import mysql.connector
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('alert_sender.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class EmailSender:
    """Handles email sending"""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('ALERT_EMAIL_FROM', self.smtp_user)
    
    def send_email(self, to_email: str, subject: str, body_html: str) -> bool:
        """Send email notification"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            html_part = MIMEText(body_html, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME', 'mega_mu_trader')
            )
            self.cursor = self.conn.cursor(dictionary=True)
            logger.info("Database connection established")
            return True
        except mysql.connector.Error as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts with user info"""
        query = """
            SELECT 
                a.id as alert_id,
                a.user_id,
                a.item_name,
                a.alert_type,
                a.threshold,
                a.last_triggered,
                u.email,
                u.name
            FROM alerts a
            JOIN users u ON a.user_id = u.id
            WHERE a.is_active = 1
                AND u.email IS NOT NULL
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def get_latest_price(self, item_name: str) -> Optional[Dict]:
        """Get latest price for an item"""
        query = """
            SELECT price_numeric, seller_name, collected_at
            FROM price_history
            WHERE item_name = %s
                AND price_numeric IS NOT NULL
            ORDER BY collected_at DESC
            LIMIT 1
        """
        self.cursor.execute(query, (item_name,))
        result = self.cursor.fetchone()
        return result
    
    def get_price_statistics(self, item_name: str, days: int = 7) -> Optional[Dict]:
        """Get price statistics for an item"""
        query = """
            SELECT 
                AVG(price_numeric) as avg_price,
                MIN(price_numeric) as min_price,
                MAX(price_numeric) as max_price,
                STDDEV(price_numeric) as std_dev
            FROM price_history
            WHERE item_name = %s
                AND price_numeric IS NOT NULL
                AND collected_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        self.cursor.execute(query, (item_name, days))
        result = self.cursor.fetchone()
        return result
    
    def update_alert_triggered(self, alert_id: int):
        """Update alert last triggered timestamp"""
        query = """
            UPDATE alerts
            SET last_triggered = NOW()
            WHERE id = %s
        """
        self.cursor.execute(query, (alert_id,))
        self.conn.commit()


class AlertChecker:
    """Checks alerts and triggers notifications"""
    
    def __init__(self, db: DatabaseManager, email_sender: EmailSender):
        self.db = db
        self.email_sender = email_sender
    
    def check_price_below(self, alert: Dict, current_price: int) -> bool:
        """Check if price is below threshold"""
        if alert['threshold'] is None:
            return False
        return current_price < alert['threshold']
    
    def check_price_above(self, alert: Dict, current_price: int) -> bool:
        """Check if price is above threshold"""
        if alert['threshold'] is None:
            return False
        return current_price > alert['threshold']
    
    def check_percentage_change(self, alert: Dict, current_price: int, avg_price: float) -> bool:
        """Check if price changed by percentage threshold"""
        if alert['threshold'] is None or avg_price == 0:
            return False
        
        change_percent = abs((current_price - avg_price) / avg_price) * 100
        return change_percent >= alert['threshold']
    
    def check_flash_deal(self, current_price: int, avg_price: float) -> bool:
        """Check if item is a flash deal (30%+ below average)"""
        if avg_price == 0:
            return False
        
        discount_percent = ((avg_price - current_price) / avg_price) * 100
        return discount_percent >= 30
    
    def check_price_peak(self, current_price: int, avg_price: float) -> bool:
        """Check if price is at peak (30%+ above average)"""
        if avg_price == 0:
            return False
        
        increase_percent = ((current_price - avg_price) / avg_price) * 100
        return increase_percent >= 30
    
    def create_email_body(self, alert: Dict, price_data: Dict, stats: Optional[Dict]) -> str:
        """Create HTML email body"""
        item_name = alert['item_name']
        alert_type = alert['alert_type']
        current_price = price_data['price_numeric']
        seller = price_data['seller_name']
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; margin: 20px 0; }}
                .price {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
                .stats {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #4CAF50; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 Alerta Mega MU Trader</h1>
                </div>
                <div class="content">
                    <h2>{item_name}</h2>
                    <p><strong>Tipo de Alerta:</strong> {alert_type.replace('_', ' ').title()}</p>
                    <p><strong>Preço Atual:</strong> <span class="price">{current_price:,}</span></p>
                    <p><strong>Vendedor:</strong> {seller}</p>
                    <p><strong>Data:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        """
        
        if stats:
            avg_price = stats.get('avg_price', 0)
            min_price = stats.get('min_price', 0)
            max_price = stats.get('max_price', 0)
            
            if avg_price:
                html += f"""
                    <div class="stats">
                        <h3>Estatísticas (7 dias)</h3>
                        <p><strong>Preço Médio:</strong> {avg_price:,.0f}</p>
                        <p><strong>Preço Mínimo:</strong> {min_price:,}</p>
                        <p><strong>Preço Máximo:</strong> {max_price:,}</p>
                """
                
                if avg_price > 0:
                    diff_percent = ((current_price - avg_price) / avg_price) * 100
                    diff_color = "green" if diff_percent < 0 else "red"
                    html += f"""
                        <p><strong>Variação da Média:</strong> 
                        <span style="color: {diff_color};">{diff_percent:+.1f}%</span></p>
                    """
                
                html += "</div>"
        
        html += """
                </div>
                <div class="footer">
                    <p>Mega MU Trader - Sistema de Monitoramento de Preços</p>
                    <p>Este é um alerta automático. Não responda a este email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def check_alert(self, alert: Dict) -> bool:
        """Check if alert should be triggered"""
        item_name = alert['item_name']
        alert_type = alert['alert_type']
        
        # Get latest price
        price_data = self.db.get_latest_price(item_name)
        if not price_data:
            return False
        
        current_price = price_data['price_numeric']
        
        # Get statistics
        stats = self.db.get_price_statistics(item_name)
        avg_price = stats.get('avg_price', 0) if stats else 0
        
        # Check alert condition
        should_trigger = False
        
        if alert_type == 'price_below':
            should_trigger = self.check_price_below(alert, current_price)
        elif alert_type == 'price_above':
            should_trigger = self.check_price_above(alert, current_price)
        elif alert_type == 'percentage_change':
            should_trigger = self.check_percentage_change(alert, current_price, avg_price)
        elif alert_type == 'flash_deal':
            should_trigger = self.check_flash_deal(current_price, avg_price)
        elif alert_type == 'price_peak':
            should_trigger = self.check_price_peak(current_price, avg_price)
        
        if should_trigger:
            # Send email
            subject = f"Alerta: {item_name} - {alert_type.replace('_', ' ').title()}"
            body = self.create_email_body(alert, price_data, stats)
            
            if self.email_sender.send_email(alert['email'], subject, body):
                self.db.update_alert_triggered(alert['alert_id'])
                return True
        
        return False
    
    def run_checks(self):
        """Run all alert checks"""
        logger.info("Starting alert checks...")
        
        alerts = self.db.get_active_alerts()
        logger.info(f"Found {len(alerts)} active alerts")
        
        triggered_count = 0
        
        for alert in alerts:
            try:
                if self.check_alert(alert):
                    triggered_count += 1
            except Exception as e:
                logger.error(f"Error checking alert {alert['alert_id']}: {e}")
        
        logger.info(f"Alert checks complete. Triggered {triggered_count} alerts")
        return triggered_count


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Mega MU Alert Sender Starting")
    logger.info("=" * 60)
    
    db = DatabaseManager()
    
    if not db.connect():
        logger.error("Failed to connect to database")
        sys.exit(1)
    
    try:
        email_sender = EmailSender()
        checker = AlertChecker(db, email_sender)
        triggered = checker.run_checks()
        
        logger.info(f"Alert check completed. {triggered} alerts triggered")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Alert check failed: {e}")
        sys.exit(1)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
