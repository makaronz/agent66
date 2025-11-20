#!/usr/bin/env python3
"""
WebSocket API Server for Real-Time Dashboard Streaming

Provides WebSocket endpoints for:
- Real-time metrics streaming
- Live alerts and notifications
- Trading signal broadcasts
- System health updates
- Market data streaming
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import random

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.warning("Websockets library not available. Install with: pip install websockets")

# Project imports
from monitoring.enhanced_monitoring import get_monitoring_system
from monitoring.real_time_dashboard import get_dashboard_manager

logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    """WebSocket client connection information"""
    websocket: WebSocketServerProtocol
    client_id: str
    connected_at: datetime
    last_ping: datetime
    subscriptions: Set[str]
    user_id: Optional[str] = None
    permissions: List[str] = None


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    type: str
    data: Any
    timestamp: datetime
    client_id: Optional[str] = None
    message_id: Optional[str] = None


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, ClientConnection] = {}
        self.message_queue = asyncio.Queue()
        self.running = False
        self.monitoring_system = None
        self.dashboard_manager = None

        # Subscription topics
        self.available_subscriptions = {
            'metrics': 'Real-time trading and system metrics',
            'alerts': 'Alert notifications and system warnings',
            'signals': 'Trading signals and market opportunities',
            'health': 'System health status updates',
            'market_data': 'Live market data and price updates'
        }

    async def start(self):
        """Start the WebSocket server"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("Websockets library not available. Cannot start WebSocket server.")
            return

        self.running = True
        self.monitoring_system = get_monitoring_system()
        self.dashboard_manager = get_dashboard_manager()

        # Start background tasks
        asyncio.create_task(self.message_processor())
        asyncio.create_task(self.metrics_broadcaster())
        asyncio.create_task(self.health_checker())
        asyncio.create_task(self.heartbeat_sender())

        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

        # Start the WebSocket server
        async with websockets.serve(
            self.handle_client_connection,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        ):
            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

    async def stop(self):
        """Stop the WebSocket server"""
        self.running = False

        # Close all client connections
        for client_id, client in list(self.clients.items()):
            try:
                await client.websocket.close()
            except Exception as e:
                logger.error(f"Error closing client {client_id}: {e}")

        self.clients.clear()
        logger.info("WebSocket server stopped")

    async def handle_client_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket client connections"""
        client_id = str(uuid.uuid4())

        # Create client connection
        client = ClientConnection(
            websocket=websocket,
            client_id=client_id,
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            subscriptions=set(),
            permissions=['read']  # Default permissions
        )

        self.clients[client_id] = client
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")

        try:
            # Send welcome message
            await self.send_to_client(client_id, WebSocketMessage(
                type='welcome',
                data={
                    'client_id': client_id,
                    'server_time': datetime.now().isoformat(),
                    'available_subscriptions': self.available_subscriptions
                },
                timestamp=datetime.now()
            ))

            # Handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(client_id, data)
                except json.JSONDecodeError:
                    await self.send_error(client_id, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await self.send_error(client_id, f"Error processing message: {str(e)}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error in client handler for {client_id}: {e}")
        finally:
            # Clean up client
            if client_id in self.clients:
                del self.clients[client_id]

    async def handle_client_message(self, client_id: str, data: Dict[str, Any]):
        """Handle incoming messages from clients"""
        client = self.clients.get(client_id)
        if not client:
            return

        message_type = data.get('type')
        message_data = data.get('data', {})

        # Update last ping
        client.last_ping = datetime.now()

        if message_type == 'subscribe':
            await self.handle_subscription(client_id, message_data)
        elif message_type == 'unsubscribe':
            await self.handle_unsubscription(client_id, message_data)
        elif message_type == 'acknowledge_alert':
            await self.handle_alert_acknowledgment(client_id, message_data)
        elif message_type == 'resolve_alert':
            await self.handle_alert_resolution(client_id, message_data)
        elif message_type == 'get_initial_data':
            await self.send_initial_data(client_id)
        elif message_type == 'ping':
            await self.send_pong(client_id)
        else:
            await self.send_error(client_id, f"Unknown message type: {message_type}")

    async def handle_subscription(self, client_id: str, data: Dict[str, Any]):
        """Handle client subscription requests"""
        client = self.clients.get(client_id)
        if not client:
            return

        topics = data.get('topics', [])
        if isinstance(topics, str):
            topics = [topics]

        for topic in topics:
            if topic in self.available_subscriptions:
                client.subscriptions.add(topic)
                logger.info(f"Client {client_id} subscribed to {topic}")
            else:
                await self.send_error(client_id, f"Unknown subscription topic: {topic}")

        await self.send_to_client(client_id, WebSocketMessage(
            type='subscription_confirmed',
            data={'subscriptions': list(client.subscriptions)},
            timestamp=datetime.now()
        ))

    async def handle_unsubscription(self, client_id: str, data: Dict[str, Any]):
        """Handle client unsubscription requests"""
        client = self.clients.get(client_id)
        if not client:
            return

        topics = data.get('topics', [])
        if isinstance(topics, str):
            topics = [topics]

        for topic in topics:
            client.subscriptions.discard(topic)
            logger.info(f"Client {client_id} unsubscribed from {topic}")

        await self.send_to_client(client_id, WebSocketMessage(
            type='unsubscription_confirmed',
            data={'subscriptions': list(client.subscriptions)},
            timestamp=datetime.now()
        ))

    async def handle_alert_acknowledgment(self, client_id: str, data: Dict[str, Any]):
        """Handle alert acknowledgment"""
        alert_id = data.get('alert_id')
        if not alert_id:
            await self.send_error(client_id, "Missing alert_id")
            return

        # In a real implementation, this would update the alert in the database
        logger.info(f"Client {client_id} acknowledged alert {alert_id}")

        # Broadcast alert update to all subscribed clients
        await self.broadcast_to_subscribers('alerts', WebSocketMessage(
            type='alert_updated',
            data={
                'alert_id': alert_id,
                'acknowledged': True,
                'acknowledged_by': client_id,
                'acknowledged_at': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        ))

    async def handle_alert_resolution(self, client_id: str, data: Dict[str, Any]):
        """Handle alert resolution"""
        alert_id = data.get('alert_id')
        if not alert_id:
            await self.send_error(client_id, "Missing alert_id")
            return

        # In a real implementation, this would update the alert in the database
        logger.info(f"Client {client_id} resolved alert {alert_id}")

        # Broadcast alert update to all subscribed clients
        await self.broadcast_to_subscribers('alerts', WebSocketMessage(
            type='alert_updated',
            data={
                'alert_id': alert_id,
                'resolved': True,
                'resolved_by': client_id,
                'resolved_at': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        ))

    async def send_initial_data(self, client_id: str):
        """Send initial data to a newly connected client"""
        try:
            # Get current metrics
            metrics_data = await self.get_current_metrics()

            # Get active alerts
            alerts_data = await self.get_active_alerts()

            # Get system health
            health_data = await self.get_system_health()

            # Send initial data package
            await self.send_to_client(client_id, WebSocketMessage(
                type='initial_data',
                data={
                    'metrics': metrics_data,
                    'alerts': alerts_data,
                    'health': health_data,
                    'timestamp': datetime.now().isoformat()
                },
                timestamp=datetime.now()
            ))

        except Exception as e:
            logger.error(f"Error sending initial data to {client_id}: {e}")
            await self.send_error(client_id, f"Error loading initial data: {str(e)}")

    async def send_pong(self, client_id: str):
        """Send pong response to ping"""
        await self.send_to_client(client_id, WebSocketMessage(
            type='pong',
            data={'timestamp': datetime.now().isoformat()},
            timestamp=datetime.now()
        ))

    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """Send a message to a specific client"""
        client = self.clients.get(client_id)
        if not client:
            return

        try:
            message_data = {
                'type': message.type,
                'data': message.data,
                'timestamp': message.timestamp.isoformat()
            }

            if message.client_id:
                message_data['client_id'] = message.client_id

            if message.message_id:
                message_data['message_id'] = message.message_id

            await client.websocket.send(json.dumps(message_data, default=str))
        except Exception as e:
            logger.error(f"Error sending message to {client_id}: {e}")
            # Remove disconnected client
            if client_id in self.clients:
                del self.clients[client_id]

    async def send_error(self, client_id: str, error_message: str):
        """Send error message to client"""
        await self.send_to_client(client_id, WebSocketMessage(
            type='error',
            data={'error': error_message},
            timestamp=datetime.now()
        ))

    async def broadcast_to_subscribers(self, topic: str, message: WebSocketMessage):
        """Broadcast message to all clients subscribed to a topic"""
        disconnected_clients = []

        for client_id, client in self.clients.items():
            if topic in client.subscriptions:
                try:
                    await client.websocket.send(json.dumps({
                        'type': message.type,
                        'data': message.data,
                        'timestamp': message.timestamp.isoformat(),
                        'topic': topic
                    }, default=str))
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Remove disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.clients:
                del self.clients[client_id]

    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all connected clients"""
        disconnected_clients = []

        for client_id, client in self.clients.items():
            try:
                await client.websocket.send(json.dumps({
                    'type': message.type,
                    'data': message.data,
                    'timestamp': message.timestamp.isoformat()
                }, default=str))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Remove disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.clients:
                del self.clients[client_id]

    async def message_processor(self):
        """Process queued messages"""
        while self.running:
            try:
                message = await self.message_queue.get()
                await self.broadcast_to_all(message)
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def metrics_broadcaster(self):
        """Broadcast metrics updates to subscribers"""
        while self.running:
            try:
                if any('metrics' in client.subscriptions for client in self.clients.values()):
                    metrics_data = await self.get_current_metrics()

                    await self.broadcast_to_subscribers('metrics', WebSocketMessage(
                        type='metrics_update',
                        data=metrics_data,
                        timestamp=datetime.now()
                    ))

                await asyncio.sleep(2)  # Update every 2 seconds

            except Exception as e:
                logger.error(f"Error in metrics broadcaster: {e}")
                await asyncio.sleep(5)

    async def health_checker(self):
        """Periodically check system health and broadcast updates"""
        while self.running:
            try:
                if any('health' in client.subscriptions for client in self.clients.values()):
                    health_data = await self.get_system_health()

                    await self.broadcast_to_subscribers('health', WebSocketMessage(
                        type='health_update',
                        data=health_data,
                        timestamp=datetime.now()
                    ))

                await asyncio.sleep(30)  # Update every 30 seconds

            except Exception as e:
                logger.error(f"Error in health checker: {e}")
                await asyncio.sleep(60)

    async def heartbeat_sender(self):
        """Send periodic heartbeat messages to all clients"""
        while self.running:
            try:
                # Check for inactive clients
                inactive_clients = []
                current_time = datetime.now()

                for client_id, client in self.clients.items():
                    if (current_time - client.last_ping).total_seconds() > 60:  # 1 minute timeout
                        inactive_clients.append(client_id)

                # Remove inactive clients
                for client_id in inactive_clients:
                    logger.info(f"Removing inactive client {client_id}")
                    if client_id in self.clients:
                        del self.clients[client_id]

                # Send heartbeat to remaining clients
                await self.broadcast_to_all(WebSocketMessage(
                    type='heartbeat',
                    data={
                        'server_time': current_time.isoformat(),
                        'connected_clients': len(self.clients)
                    },
                    timestamp=current_time
                ))

                await asyncio.sleep(30)  # Send heartbeat every 30 seconds

            except Exception as e:
                logger.error(f"Error in heartbeat sender: {e}")
                await asyncio.sleep(30)

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current trading and system metrics"""
        try:
            # Simulate metrics data - in production, this would come from the monitoring system
            metrics = {
                'trading': {
                    'total_trades': random.randint(100, 200),
                    'win_rate': random.uniform(0.6, 0.8),
                    'total_pnl': random.uniform(1000, 5000),
                    'open_positions': random.randint(1, 10),
                    'daily_return': random.uniform(-2, 5),
                    'sharpe_ratio': random.uniform(1.0, 2.5),
                    'max_drawdown': random.uniform(-15, -5)
                },
                'system': {
                    'cpu_usage': random.uniform(20, 80),
                    'memory_usage': random.uniform(40, 90),
                    'disk_usage': random.uniform(60, 95),
                    'network_io': random.uniform(0, 100),
                    'active_connections': random.randint(50, 200)
                },
                'market': {
                    'btc_price': random.uniform(40000, 50000),
                    'eth_price': random.uniform(2000, 3000),
                    'market_volume': random.uniform(1000000, 5000000),
                    'volatility_index': random.uniform(15, 35)
                }
            }

            return metrics

        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return {}

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        try:
            # Simulate alerts - in production, this would come from the alert system
            alerts = [
                {
                    'id': str(uuid.uuid4()),
                    'severity': random.choice(['low', 'medium', 'high', 'critical']),
                    'category': random.choice(['system', 'trading', 'risk', 'performance']),
                    'title': 'High CPU Usage Detected',
                    'message': f'System CPU usage is at {random.uniform(70, 95):.1f}%',
                    'timestamp': datetime.now().isoformat(),
                    'acknowledged': False,
                    'resolved': False,
                    'component': 'System Monitor'
                }
                for _ in range(random.randint(0, 5))
            ]

            return alerts

        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            # Simulate health data - in production, this would come from health checks
            health = {
                'overall_status': random.choice(['healthy', 'warning', 'critical']),
                'components': [
                    {
                        'name': 'Data Pipeline',
                        'status': random.choice(['healthy', 'warning']),
                        'latency': random.uniform(5, 50),
                        'last_check': datetime.now().isoformat()
                    },
                    {
                        'name': 'SMC Detector',
                        'status': 'healthy',
                        'latency': random.uniform(5, 30),
                        'last_check': datetime.now().isoformat()
                    },
                    {
                        'name': 'Risk Manager',
                        'status': random.choice(['healthy', 'warning']),
                        'latency': random.uniform(5, 25),
                        'last_check': datetime.now().isoformat()
                    },
                    {
                        'name': 'Execution Engine',
                        'status': 'healthy',
                        'latency': random.uniform(1, 15),
                        'last_check': datetime.now().isoformat()
                    }
                ],
                'uptime': random.uniform(99, 100),
                'last_check': datetime.now().isoformat()
            }

            return health

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {}

    async def send_alert(self, alert_data: Dict[str, Any]):
        """Send alert to all subscribed clients"""
        await self.broadcast_to_subscribers('alerts', WebSocketMessage(
            type='new_alert',
            data=alert_data,
            timestamp=datetime.now()
        ))

    async def send_trading_signal(self, signal_data: Dict[str, Any]):
        """Send trading signal to all subscribed clients"""
        await self.broadcast_to_subscribers('signals', WebSocketMessage(
            type='new_signal',
            data=signal_data,
            timestamp=datetime.now()
        ))

    async def send_market_data_update(self, market_data: Dict[str, Any]):
        """Send market data update to all subscribed clients"""
        await self.broadcast_to_subscribers('market_data', WebSocketMessage(
            type='market_update',
            data=market_data,
            timestamp=datetime.now()
        ))


# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> Optional[WebSocketManager]:
    """Get global WebSocket manager instance"""
    return _websocket_manager


def initialize_websocket_manager(host: str = "localhost", port: int = 8765) -> WebSocketManager:
    """Initialize global WebSocket manager"""
    global _websocket_manager
    _websocket_manager = WebSocketManager(host, port)
    return _websocket_manager


# Utility functions for sending alerts and signals
async def send_system_alert(severity: str, title: str, message: str, component: str = ""):
    """Send system alert to all dashboard clients"""
    manager = get_websocket_manager()
    if manager:
        alert_data = {
            'id': str(uuid.uuid4()),
            'severity': severity,
            'category': 'system',
            'title': title,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'acknowledged': False,
            'resolved': False,
            'component': component
        }
        await manager.send_alert(alert_data)


async def send_trading_alert(severity: str, title: str, message: str, component: str = ""):
    """Send trading alert to all dashboard clients"""
    manager = get_websocket_manager()
    if manager:
        alert_data = {
            'id': str(uuid.uuid4()),
            'severity': severity,
            'category': 'trading',
            'title': title,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'acknowledged': False,
            'resolved': False,
            'component': component
        }
        await manager.send_alert(alert_data)


async def send_trading_signal(symbol: str, signal_type: str, confidence: float,
                            strategy: str = "", entry_price: float = None,
                            stop_loss: float = None, take_profit: float = None):
    """Send trading signal to all dashboard clients"""
    manager = get_websocket_manager()
    if manager:
        signal_data = {
            'id': str(uuid.uuid4()),
            'symbol': symbol,
            'signal_type': signal_type,
            'confidence': confidence,
            'strategy': strategy,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now().isoformat()
        }
        await manager.send_trading_signal(signal_data)


async def main():
    """Main function to start the WebSocket server"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    manager = initialize_websocket_manager()

    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Shutting down WebSocket server...")
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())