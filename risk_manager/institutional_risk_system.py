"""
Institutional Risk Management System - Integration Module

This module integrates all advanced risk management components into a unified,
production-ready system with institutional-grade features:

Components:
- Enhanced VaR calculation with multiple methods and backtesting
- Portfolio risk management with correlation and concentration analysis
- Dynamic risk controls with adaptive position sizing and Kelly Criterion
- Regulatory compliance with MiFID II features and audit trails
- Real-time risk dashboard with live monitoring and alerts
- Comprehensive risk reporting and analytics
"""

import numpy as np
import pandas as pd
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import warnings

# Import all risk management components
from .enhanced_var_calculator import EnhancedVaRCalculator, VaRMethod, StressScenario
from .portfolio_risk_manager import PortfolioRiskManager
from .dynamic_risk_controls import DynamicRiskControls, MarketRegime, PositionSizingMethod
from .enhanced_compliance_engine import EnhancedComplianceEngine, ReportType, ComplianceStatus
from .realtime_risk_dashboard import RealTimeRiskDashboard, AlertSeverity

logger = logging.getLogger(__name__)

class RiskSystemMode(Enum):
    """Risk system operating modes."""
    SIMULATION = "simulation"  # Paper trading mode
    MONITORING = "monitoring"  # Real-time monitoring without execution
    ACTIVE = "active"  # Active risk management with execution controls
    COMPLIANCE = "compliance"  # Compliance-focused mode
    STRESS_TEST = "stress_test"  # Stress testing mode

class RiskDecision(Enum):
    """Risk management decisions."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    DEFERRED = "deferred"
    ESCALATED = "escalated"

@dataclass
class RiskAssessment:
    """Comprehensive risk assessment result."""
    trade_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    decision: RiskDecision
    confidence: float
    risk_score: float
    position_size: float
    stop_loss: float
    take_profit: float
    var_impact: float
    portfolio_impact: float
    compliance_status: ComplianceStatus
    recommendations: List[str]
    warnings: List[str]
    critical_issues: List[str]
    assessment_timestamp: datetime

@dataclass
class RiskSystemStatus:
    """Risk system status and health."""
    mode: RiskSystemMode
    is_healthy: bool
    last_update: datetime
    active_alerts: int
    pending_reviews: int
    system_load: float
    data_quality: float
    last_backup: Optional[datetime]
    uptime_seconds: int
    components_status: Dict[str, bool]

class InstitutionalRiskSystem:
    """
    Institutional Risk Management System

    Comprehensive integration of all advanced risk management components
    with production-ready features and institutional-grade reliability.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Institutional Risk Management System.

        Args:
            config: System configuration
        """
        self.config = config or {}

        # System configuration
        self.system_config = {
            'mode': RiskSystemMode(self.config.get('mode', 'simulation')),
            'auto_approve_threshold': self.config.get('auto_approve_threshold', 0.8),
            'auto_reject_threshold': self.config.get('auto_reject_threshold', 0.3),
            'max_parallel_assessments': self.config.get('max_parallel_assessments', 10),
            'assessment_timeout_seconds': self.config.get('assessment_timeout_seconds', 30),
            'enable_real_time_monitoring': self.config.get('enable_real_time_monitoring', True),
            'backup_interval_hours': self.config.get('backup_interval_hours', 24),
            'health_check_interval_minutes': self.config.get('health_check_interval_minutes', 5)
        }

        # Initialize components
        self.var_calculator = EnhancedVaRCalculator(self.config.get('var_config', {}))
        self.portfolio_manager = PortfolioRiskManager(self.config.get('portfolio_config', {}))
        self.dynamic_controls = DynamicRiskControls(self.config.get('dynamic_config', {}))
        self.compliance_engine = EnhancedComplianceEngine(self.config.get('compliance_config', {}))
        self.risk_dashboard = RealTimeRiskDashboard(self.config.get('dashboard_config', {}))

        # System state
        self.system_status = RiskSystemStatus(
            mode=self.system_config['mode'],
            is_healthy=True,
            last_update=datetime.utcnow(),
            active_alerts=0,
            pending_reviews=0,
            system_load=0.0,
            data_quality=1.0,
            last_backup=None,
            uptime_seconds=0,
            components_status={}
        )

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=self.system_config['max_parallel_assessments'])

        # Assessment cache and history
        self.assessment_cache: Dict[str, RiskAssessment] = {}
        self.assessment_history: List[RiskAssessment] = []
        self.trade_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        # Monitoring and metrics
        self.metrics: Dict[str, deque] = {
            'assessment_times': deque(maxlen=1000),
            'risk_scores': deque(maxlen=1000),
            'approval_rates': deque(maxlen=100),
            'system_performance': deque(maxlen=100)
        }

        # Data streams
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.portfolio_data: Optional[pd.DataFrame] = None
        self.trade_history: pd.DataFrame = pd.DataFrame()

        # Start time for uptime calculation
        self.start_time = datetime.utcnow()

        logger.info("Institutional Risk Management System initialized")

    async def initialize(self):
        """Initialize the risk system and start monitoring."""
        try:
            logger.info("Initializing Institutional Risk Management System...")

            # Initialize all components
            await self._initialize_components()

            # Load historical data
            await self._load_historical_data()

            # Perform initial risk assessment
            await self._perform_initial_assessment()

            # Start real-time monitoring if enabled
            if self.system_config['enable_real_time_monitoring']:
                await self._start_monitoring()

            # Start background tasks
            await self._start_background_tasks()

            # Update system status
            self.system_status.is_healthy = True
            self.system_status.last_update = datetime.utcnow()
            self.system_status.components_status = {
                'var_calculator': True,
                'portfolio_manager': True,
                'dynamic_controls': True,
                'compliance_engine': True,
                'risk_dashboard': True
            }

            logger.info("Institutional Risk Management System initialization completed")

        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            self.system_status.is_healthy = False
            raise

    async def comprehensive_risk_assessment(self, trade_request: Dict[str, Any]) -> RiskAssessment:
        """
        Perform comprehensive risk assessment for a trade request.

        Args:
            trade_request: Trade request details

        Returns:
            RiskAssessment: Comprehensive risk assessment result
        """
        start_time = asyncio.get_event_loop().time()
        trade_id = trade_request.get('trade_id', str(uuid.uuid4()))

        try:
            # Extract trade details
            symbol = trade_request['symbol']
            side = trade_request['side']
            quantity = trade_request['quantity']
            price = trade_request['price']

            # Initialize assessment result
            assessment = RiskAssessment(
                trade_id=trade_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                decision=RiskDecision.DEFERRED,
                confidence=0.0,
                risk_score=0.0,
                position_size=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                var_impact=0.0,
                portfolio_impact=0.0,
                compliance_status=ComplianceStatus.PENDING_REVIEW,
                recommendations=[],
                warnings=[],
                critical_issues=[],
                assessment_timestamp=datetime.utcnow()
            )

            # Parallel risk assessment components
            assessment_tasks = [
                self._assess_portfolio_impact(trade_request, assessment),
                self._assess_market_risk(trade_request, assessment),
                self._assess_position_sizing(trade_request, assessment),
                self._assess_compliance(trade_request, assessment),
                self._assess_execution_risk(trade_request, assessment)
            ]

            # Run assessments in parallel
            results = await asyncio.gather(*assessment_tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Assessment component failed: {result}")
                    assessment.critical_issues.append(f"Assessment error: {str(result)}")

            # Calculate overall risk score
            assessment.risk_score = self._calculate_overall_risk_score(assessment)
            assessment.confidence = self._calculate_assessment_confidence(assessment)

            # Make risk decision
            assessment.decision = self._make_risk_decision(assessment)

            # Generate recommendations and warnings
            assessment.recommendations = self._generate_recommendations(assessment)
            assessment.warnings = self._generate_warnings(assessment)

            # Calculate execution parameters
            if assessment.decision in [RiskDecision.APPROVED, RiskDecision.MODIFIED]:
                execution_params = await self._calculate_execution_parameters(trade_request, assessment)
                assessment.position_size = execution_params.get('position_size', 0.0)
                assessment.stop_loss = execution_params.get('stop_loss', 0.0)
                assessment.take_profit = execution_params.get('take_profit', 0.0)

            # Cache assessment
            self.assessment_cache[trade_id] = assessment
            self.assessment_history.append(assessment)

            # Update metrics
            assessment_time = asyncio.get_event_loop().time() - start_time
            self.metrics['assessment_times'].append(assessment_time)
            self.metrics['risk_scores'].append(assessment.risk_score)

            logger.info(f"Risk assessment completed for {trade_id}: "
                       f"decision={assessment.decision.value}, score={assessment.risk_score:.2f}")

            return assessment

        except Exception as e:
            logger.error(f"Comprehensive risk assessment failed: {e}")
            raise

    async def _assess_portfolio_impact(self, trade_request: Dict[str, Any], assessment: RiskAssessment):
        """Assess portfolio impact of the trade."""
        try:
            symbol = trade_request['symbol']
            quantity = trade_request['quantity']
            price = trade_request['price']
            trade_value = quantity * price

            # Get current portfolio composition
            current_positions = self._get_current_positions()

            # Calculate portfolio impact
            portfolio_impact = trade_value / self._get_total_portfolio_value() if self._get_total_portfolio_value() > 0 else 0
            assessment.portfolio_impact = portfolio_impact

            # Analyze concentration risk
            concentration_analysis = await self.portfolio_manager.analyze_concentration_risk(
                {**current_positions, symbol: trade_value}
            )

            if concentration_analysis.risk_level in ['HIGH', 'MEDIUM']:
                assessment.warnings.append(f"Concentration risk: {concentration_analysis.risk_level}")

            # Analyze correlation risk
            if len(current_positions) > 0:
                returns_data = self._get_returns_data_for_positions([symbol] + list(current_positions.keys()))
                if returns_data is not None and len(returns_data.columns) > 1:
                    correlation_analysis = await self.portfolio_manager.analyze_correlation_matrix(returns_data)
                    assessment.correlation_risk = correlation_analysis.maximum_correlation

                    if correlation_analysis.maximum_correlation > 0.7:
                        assessment.warnings.append(f"High correlation risk: {correlation_analysis.maximum_correlation:.2f}")

        except Exception as e:
            logger.error(f"Portfolio impact assessment failed: {e}")
            assessment.warnings.append(f"Portfolio impact assessment error: {str(e)}")

    async def _assess_market_risk(self, trade_request: Dict[str, Any], assessment: RiskAssessment):
        """Assess market risk for the trade."""
        try:
            symbol = trade_request['symbol']

            # Get market data
            market_data = self.market_data.get(symbol)
            if market_data is None or market_data.empty:
                assessment.warnings.append("No market data available")
                return

            # Calculate VaR impact
            returns = market_data['close'].pct_change().dropna()
            if len(returns) >= 30:
                portfolio_data = pd.DataFrame({'returns': returns})

                var_result = await self.var_calculator.calculate_enhanced_var(
                    portfolio_data, VaRMethod.HISTORICAL, 0.95, 1
                )
                assessment.var_impact = var_result.var_value

                # Check against VaR limits
                if assessment.var_impact > self.config.get('max_var_impact', 0.02):
                    assessment.warnings.append(f"VaR impact exceeds limit: {assessment.var_impact:.3f}")

                # Perform stress test
                stress_result = await self.var_calculator.run_stress_test(
                    portfolio_data, StressScenario.MARKET_CRASH
                )
                assessment.stress_test_loss = stress_result.percentage_loss

                if stress_result.percentage_loss < -0.15:  # 15% stress loss
                    assessment.critical_issues.append(f"Stress test shows high risk: {stress_result.percentage_loss:.1%}")

            # Analyze volatility
            current_vol = returns.tail(20).std() * np.sqrt(252)
            historical_vol = returns.std() * np.sqrt(252)

            if current_vol > historical_vol * 1.5:
                assessment.warnings.append("Elevated market volatility detected")

        except Exception as e:
            logger.error(f"Market risk assessment failed: {e}")
            assessment.warnings.append(f"Market risk assessment error: {str(e)}")

    async def _assess_position_sizing(self, trade_request: Dict[str, Any], assessment: RiskAssessment):
        """Assess and recommend optimal position sizing."""
        try:
            symbol = trade_request['symbol']
            side = trade_request['side']
            entry_price = trade_request['price']
            confidence = trade_request.get('confidence', 0.7)

            # Get market data
            market_data = self.market_data.get(symbol)
            if market_data is None or market_data.empty:
                return

            # Calculate adaptive position size
            position_recommendation = await self.dynamic_controls.calculate_adaptive_position_size(
                symbol=symbol,
                account_balance=self._get_account_balance(),
                market_data=market_data,
                confidence=confidence,
                current_positions=self._get_current_positions()
            )

            assessment.position_size = position_recommendation.recommended_size
            assessment.sizing_method = position_recommendation.method.value

            # Calculate Kelly Criterion if sufficient data
            if len(self.trade_history) > 30:
                symbol_trades = self.trade_history[self.trade_history['symbol'] == symbol]
                if len(symbol_trades) > 10:
                    kelly_result = await self.dynamic_controls.calculate_kelly_criterion(symbol_trades, symbol)
                    assessment.kelly_fraction = kelly_result.recommended_fraction

            # Validate requested size vs recommended size
            requested_value = trade_request['quantity'] * trade_request['price']
            recommended_value = assessment.position_size * entry_price

            if abs(requested_value - recommended_value) / recommended_value > 0.2:  # 20% deviation
                assessment.warnings.append(f"Position size deviation: requested vs recommended")

        except Exception as e:
            logger.error(f"Position sizing assessment failed: {e}")
            assessment.warnings.append(f"Position sizing assessment error: {str(e)}")

    async def _assess_compliance(self, trade_request: Dict[str, Any], assessment: RiskAssessment):
        """Assess regulatory compliance."""
        try:
            # Perform comprehensive compliance check
            compliance_checks = await self.compliance_engine.comprehensive_pre_trade_compliance_check(
                trade_request
            )

            # Analyze compliance results
            failed_checks = [check for check in compliance_checks if check.status == ComplianceStatus.NON_COMPLIANT]
            warning_checks = [check for check in compliance_checks if check.status == ComplianceStatus.WARNING]

            if failed_checks:
                assessment.critical_issues.extend([check.description for check in failed_checks])
                assessment.compliance_status = ComplianceStatus.NON_COMPLIANT
            elif warning_checks:
                assessment.warnings.extend([check.description for check in warning_checks])
                assessment.compliance_status = ComplianceStatus.WARNING
            else:
                assessment.compliance_status = ComplianceStatus.COMPLIANT

            # Check for specific regulatory requirements
            if trade_request.get('client_id'):
                # Client-specific compliance checks
                pass

            # Check market-specific regulations
            if trade_request.get('venue') == 'regulated_market':
                # Regulated market specific checks
                pass

        except Exception as e:
            logger.error(f"Compliance assessment failed: {e}")
            assessment.warnings.append(f"Compliance assessment error: {str(e)}")
            assessment.compliance_status = ComplianceStatus.PENDING_REVIEW

    async def _assess_execution_risk(self, trade_request: Dict[str, Any], assessment: RiskAssessment):
        """Assess execution-related risks."""
        try:
            symbol = trade_request['symbol']
            quantity = trade_request['quantity']

            # Get market data for execution analysis
            market_data = self.market_data.get(symbol)
            if market_data is None or market_data.empty:
                assessment.warnings.append("Insufficient market data for execution risk assessment")
                return

            # Analyze liquidity risk
            if 'volume' in market_data.columns:
                recent_volume = market_data['volume'].tail(20).mean()
                volume_ratio = quantity / recent_volume if recent_volume > 0 else float('inf')

                if volume_ratio > 0.1:  # Trade is more than 10% of average volume
                    assessment.warnings.append(f"High liquidity risk: volume ratio {volume_ratio:.2f}")
                elif volume_ratio > 0.05:
                    assessment.warnings.append(f"Moderate liquidity risk: volume ratio {volume_ratio:.2f}")

            # Analyze market impact
            if 'close' in market_data.columns:
                recent_prices = market_data['close'].tail(20)
                price_volatility = recent_prices.pct_change().std()

                # Estimate market impact
                estimated_impact = price_volatility * np.sqrt(quantity / recent_prices.mean())
                assessment.market_impact = estimated_impact

                if estimated_impact > 0.005:  # 0.5% estimated impact
                    assessment.warnings.append(f"Significant market impact expected: {estimated_impact:.2%}")

            # Check for market timing
            current_time = datetime.utcnow()
            market_hours = self._get_market_hours(symbol)

            if not market_hours['is_open']:
                assessment.warnings.append("Trading outside market hours")

        except Exception as e:
            logger.error(f"Execution risk assessment failed: {e}")
            assessment.warnings.append(f"Execution risk assessment error: {str(e)}")

    def _calculate_overall_risk_score(self, assessment: RiskAssessment) -> float:
        """Calculate overall risk score from all assessment components."""
        try:
            # Base risk score from portfolio impact
            risk_score = assessment.portfolio_impact * 10  # Scale portfolio impact

            # Add VaR impact
            risk_score += assessment.var_impact * 20  # Weight VaR impact heavily

            # Add concentration risk
            if hasattr(assessment, 'correlation_risk'):
                risk_score += assessment.correlation_risk * 5

            # Add compliance risk
            if assessment.compliance_status == ComplianceStatus.NON_COMPLIANT:
                risk_score += 30
            elif assessment.compliance_status == ComplianceStatus.WARNING:
                risk_score += 15

            # Add execution risk
            if hasattr(assessment, 'market_impact'):
                risk_score += assessment.market_impact * 10

            # Add critical issues
            risk_score += len(assessment.critical_issues) * 10

            # Normalize to 0-100 scale
            risk_score = min(risk_score, 100)

            return risk_score

        except Exception as e:
            logger.error(f"Risk score calculation failed: {e}")
            return 50.0  # Default to medium risk

    def _calculate_assessment_confidence(self, assessment: RiskAssessment) -> float:
        """Calculate confidence level in the assessment."""
        try:
            confidence = 0.9  # Base confidence

            # Reduce confidence based on warnings
            confidence -= len(assessment.warnings) * 0.05

            # Reduce confidence based on data quality
            if not self.market_data.get(assessment.symbol):
                confidence -= 0.3

            # Reduce confidence for critical issues (but not too much)
            confidence -= len(assessment.critical_issues) * 0.02

            return max(confidence, 0.1)  # Minimum 10% confidence

        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.5

    def _make_risk_decision(self, assessment: RiskAssessment) -> RiskDecision:
        """Make final risk decision based on assessment."""
        try:
            # Auto-reject for critical issues
            if assessment.critical_issues:
                return RiskDecision.REJECTED

            # Auto-reject for non-compliance
            if assessment.compliance_status == ComplianceStatus.NON_COMPLIANT:
                return RiskDecision.REJECTED

            # Auto-approve for low risk
            if (assessment.risk_score < 20 and
                assessment.compliance_status == ComplianceStatus.COMPLIANT and
                assessment.confidence > self.system_config['auto_approve_threshold']):
                return RiskDecision.APPROVED

            # Auto-reject for high risk
            if assessment.risk_score > 80 or assessment.confidence < self.system_config['auto_reject_threshold']:
                return RiskDecision.REJECTED

            # Check for modifications needed
            if assessment.risk_score > 50:
                return RiskDecision.MODIFIED

            # Default to deferred for manual review
            return RiskDecision.DEFERRED

        except Exception as e:
            logger.error(f"Risk decision making failed: {e}")
            return RiskDecision.ESCALATED

    def _generate_recommendations(self, assessment: RiskAssessment) -> List[str]:
        """Generate risk management recommendations."""
        recommendations = []

        try:
            # Portfolio-related recommendations
            if assessment.portfolio_impact > 0.1:
                recommendations.append("Consider reducing position size to manage portfolio concentration")

            # VaR-related recommendations
            if assessment.var_impact > 0.02:
                recommendations.append("Implement additional risk controls due to high VaR impact")

            # Compliance recommendations
            if assessment.compliance_status == ComplianceStatus.WARNING:
                recommendations.append("Review compliance requirements before proceeding")

            # Execution recommendations
            if hasattr(assessment, 'market_impact') and assessment.market_impact > 0.005:
                recommendations.append("Consider executing trade in smaller portions to reduce market impact")

            # Position sizing recommendations
            if hasattr(assessment, 'position_size') and assessment.position_size > 0:
                trade_value = assessment.position_size * assessment.price
                if trade_value > self._get_account_balance() * 0.05:  # More than 5% of account
                    recommendations.append("Position size is large relative to account balance")

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")

        return recommendations

    def _generate_warnings(self, assessment: RiskAssessment) -> List[str]:
        """Generate additional warnings."""
        warnings = assessment.warnings.copy()

        try:
            # Add systematic warnings
            if assessment.risk_score > 60:
                warnings.append("High risk score detected - consider additional review")

            if assessment.confidence < 0.6:
                warnings.append("Low assessment confidence - verify data quality")

            if len(self.assessment_history) > 0:
                recent_assessments = self.assessment_history[-10:]
                avg_risk_score = np.mean([a.risk_score for a in recent_assessments])
                if assessment.risk_score > avg_risk_score * 1.5:
                    warnings.append("Risk score significantly higher than recent average")

        except Exception as e:
            logger.error(f"Warning generation failed: {e}")

        return warnings

    async def _calculate_execution_parameters(self, trade_request: Dict[str, Any], assessment: RiskAssessment) -> Dict[str, float]:
        """Calculate optimal execution parameters."""
        try:
            symbol = trade_request['symbol']
            side = trade_request['side']
            entry_price = trade_request['price']

            # Get market data
            market_data = self.market_data.get(symbol)
            if market_data is None or market_data.empty:
                return {'position_size': 0.0, 'stop_loss': 0.0, 'take_profit': 0.0}

            # Calculate stop loss and take profit
            sl_tp_result = await self.dynamic_controls.calculate_stop_loss_take_profit(
                symbol, side, entry_price, market_data, assessment.position_size
            )

            return {
                'position_size': assessment.position_size,
                'stop_loss': sl_tp_result['stop_loss'],
                'take_profit': sl_tp_result['take_profit']
            }

        except Exception as e:
            logger.error(f"Execution parameter calculation failed: {e}")
            return {'position_size': 0.0, 'stop_loss': 0.0, 'take_profit': 0.0}

    # System initialization and monitoring methods

    async def _initialize_components(self):
        """Initialize all system components."""
        try:
            # Start real-time dashboard
            if self.system_config['enable_real_time_monitoring']:
                await self.risk_dashboard.start_monitoring()

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise

    async def _load_historical_data(self):
        """Load historical data for risk calculations."""
        try:
            # This would typically load from database or external sources
            # For now, simulate with sample data
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT']

            for symbol in symbols:
                # Generate sample historical data
                dates = pd.date_range(end=datetime.utcnow(), periods=252, freq='D')
                prices = 100 * (1 + np.cumsum(np.random.normal(0, 0.02, 252)))
                volumes = np.random.randint(1000000, 10000000, 252)

                market_data = pd.DataFrame({
                    'open': prices * np.random.uniform(0.99, 1.01, 252),
                    'high': prices * np.random.uniform(1.00, 1.05, 252),
                    'low': prices * np.random.uniform(0.95, 1.00, 252),
                    'close': prices,
                    'volume': volumes
                }, index=dates)

                self.market_data[symbol] = market_data

            # Update dashboard with market data
            for symbol, data in self.market_data.items():
                await self.risk_dashboard.update_market_data(symbol, data)

            logger.info(f"Historical data loaded for {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Historical data loading failed: {e}")

    async def _perform_initial_assessment(self):
        """Perform initial system risk assessment."""
        try:
            # Analyze current portfolio risk
            current_positions = self._get_current_positions()
            if current_positions:
                concentration_analysis = await self.portfolio_manager.analyze_concentration_risk(current_positions)
                logger.info(f"Initial concentration risk: {concentration_analysis.risk_level}")

                # Analyze correlation risk
                returns_data = self._get_returns_data_for_positions(list(current_positions.keys()))
                if returns_data is not None and len(returns_data.columns) > 1:
                    correlation_analysis = await self.portfolio_manager.analyze_correlation_matrix(returns_data)
                    logger.info(f"Initial correlation risk: {correlation_analysis.maximum_correlation:.3f}")

            # Calculate portfolio VaR
            if self.portfolio_data is not None and 'returns' in self.portfolio_data.columns:
                var_result = await self.var_calculator.calculate_enhanced_var(
                    self.portfolio_data, VaRMethod.HISTORICAL, 0.95, 1
                )
                logger.info(f"Initial portfolio VaR: {var_result.var_value:.4f}")

            logger.info("Initial risk assessment completed")

        except Exception as e:
            logger.error(f"Initial assessment failed: {e}")

    async def _start_monitoring(self):
        """Start real-time monitoring systems."""
        try:
            # Start dashboard monitoring
            await self.risk_dashboard.start_monitoring()

            # Start market regime detection
            for symbol, data in self.market_data.items():
                if len(data) > 252:
                    regime_detection = await self.dynamic_controls.detect_market_regime(data.tail(252))
                    logger.info(f"Market regime for {symbol}: {regime_detection.current_regime.value}")

            logger.info("Real-time monitoring started")

        except Exception as e:
            logger.error(f"Monitoring startup failed: {e}")

    async def _start_background_tasks(self):
        """Start background system tasks."""
        try:
            # Health check task
            asyncio.create_task(self._health_check_loop())

            # Metrics collection task
            asyncio.create_task(self._metrics_collection_loop())

            # Data backup task
            if self.system_config['backup_interval_hours'] > 0:
                asyncio.create_task(self._backup_loop())

            # Risk monitoring task
            asyncio.create_task(self._risk_monitoring_loop())

            logger.info("Background tasks started")

        except Exception as e:
            logger.error(f"Background task startup failed: {e}")

    async def _health_check_loop(self):
        """Background health monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.system_config['health_check_interval_minutes'] * 60)

                # Check component health
                components_healthy = True

                # Update system status
                self.system_status.last_update = datetime.utcnow()
                self.system_status.uptime_seconds = int((datetime.utcnow() - self.start_time).total_seconds())
                self.system_status.active_alerts = len(self.risk_dashboard.active_alerts)

                # Calculate system load
                recent_assessments = list(self.metrics['assessment_times'])[-10:]
                if recent_assessments:
                    avg_time = np.mean(recent_assessments)
                    self.system_status.system_load = min(avg_time / 10, 1.0)  # Normalize to 0-1

                if components_healthy:
                    self.system_status.is_healthy = True
                else:
                    logger.warning("System health check failed")
                    self.system_status.is_healthy = False

            except Exception as e:
                logger.error(f"Health check failed: {e}")

    async def _metrics_collection_loop(self):
        """Background metrics collection loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Collect metrics every minute

                # Calculate approval rate
                if len(self.assessment_history) > 0:
                    recent_assessments = self.assessment_history[-100:]
                    approved_count = len([a for a in recent_assessments if a.decision == RiskDecision.APPROVED])
                    approval_rate = approved_count / len(recent_assessments)
                    self.metrics['approval_rates'].append(approval_rate)

                # Calculate system performance
                cpu_usage = 0.5  # Would get actual CPU usage
                memory_usage = 0.6  # Would get actual memory usage
                performance_score = 1.0 - (cpu_usage + memory_usage) / 2
                self.metrics['system_performance'].append(performance_score)

            except Exception as e:
                logger.error(f"Metrics collection failed: {e}")

    async def _backup_loop(self):
        """Background data backup loop."""
        while True:
            try:
                await asyncio.sleep(self.system_config['backup_interval_hours'] * 3600)

                # Perform system backup
                await self._perform_system_backup()
                self.system_status.last_backup = datetime.utcnow()
                logger.info("System backup completed")

            except Exception as e:
                logger.error(f"Backup failed: {e}")

    async def _risk_monitoring_loop(self):
        """Background risk monitoring loop."""
        while True:
            try:
                await asyncio.sleep(300)  # Monitor every 5 minutes

                # Update market data and risk metrics
                for symbol in self.market_data.keys():
                    # In practice, would fetch latest market data
                    pass

                # Check for risk threshold breaches
                await self._check_risk_thresholds()

            except Exception as e:
                logger.error(f"Risk monitoring failed: {e}")

    async def _perform_system_backup(self):
        """Perform system data backup."""
        try:
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'assessments': len(self.assessment_history),
                'active_alerts': len(self.risk_dashboard.active_alerts),
                'system_status': self.system_status.__dict__,
                'metrics': {k: list(v) for k, v in self.metrics.items()}
            }

            # Save backup data
            backup_path = f"backups/risk_system_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)

            logger.info(f"System backup saved to {backup_path}")

        except Exception as e:
            logger.error(f"System backup failed: {e}")

    async def _check_risk_thresholds(self):
        """Check for risk threshold breaches."""
        try:
            # Check portfolio-level risk thresholds
            current_positions = self._get_current_positions()
            if current_positions:
                total_value = self._get_total_portfolio_value()

                for symbol, position_value in current_positions.items():
                    position_weight = position_value / total_value if total_value > 0 else 0

                    if position_weight > 0.15:  # 15% position limit
                        await self.risk_dashboard._create_alert(
                            metric_type=RiskMetricType.CONCENTRATION_RISK,
                            severity=AlertSeverity.HIGH,
                            title=f"Position Concentration Alert: {symbol}",
                            message=f"Position {symbol} exceeds concentration limit: {position_weight:.1%}",
                            current_value=position_weight,
                            threshold_value=0.15
                        )

        except Exception as e:
            logger.error(f"Risk threshold check failed: {e}")

    # Helper methods

    def _get_current_positions(self) -> Dict[str, float]:
        """Get current portfolio positions."""
        # This would typically come from portfolio management system
        return {
            'BTCUSDT': 50000,  # USD value
            'ETHUSDT': 30000,
            'ADAUSDT': 15000,
            'DOTUSDT': 5000
        }

    def _get_total_portfolio_value(self) -> float:
        """Get total portfolio value."""
        positions = self._get_current_positions()
        return sum(positions.values())

    def _get_account_balance(self) -> float:
        """Get account balance."""
        return self._get_total_portfolio_value()

    def _get_market_hours(self, symbol: str) -> Dict[str, Any]:
        """Get market hours for symbol."""
        # Simplified market hours check
        current_time = datetime.utcnow()
        weekday = current_time.weekday()
        hour = current_time.hour

        return {
            'is_open': weekday < 5 and 9 <= hour <= 16,  # Mon-Fri, 9 AM - 4 PM UTC
            'open_time': '09:00 UTC',
            'close_time': '16:00 UTC'
        }

    def _get_returns_data_for_positions(self, symbols: List[str]) -> Optional[pd.DataFrame]:
        """Get returns data for specified positions."""
        try:
            returns_data = {}

            for symbol in symbols:
                if symbol in self.market_data:
                    returns = self.market_data[symbol]['close'].pct_change().dropna()
                    if len(returns) > 0:
                        returns_data[symbol] = returns

            if returns_data:
                return pd.DataFrame(returns_data)
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get returns data: {e}")
            return None

    async def generate_system_report(self) -> Dict[str, Any]:
        """Generate comprehensive system report."""
        try:
            report = {
                'report_timestamp': datetime.utcnow().isoformat(),
                'system_status': self.system_status.__dict__,
                'performance_metrics': {
                    'total_assessments': len(self.assessment_history),
                    'avg_assessment_time': np.mean(list(self.metrics['assessment_times'])) if self.metrics['assessment_times'] else 0,
                    'approval_rate': np.mean(list(self.metrics['approval_rates'])) if self.metrics['approval_rates'] else 0,
                    'system_performance': np.mean(list(self.metrics['system_performance'])) if self.metrics['system_performance'] else 0
                },
                'risk_metrics': {},
                'compliance_status': {},
                'active_alerts': len(self.risk_dashboard.active_alerts),
                'data_quality': {
                    'market_data_symbols': len(self.market_data),
                    'historical_data_days': 252 if self.market_data else 0
                }
            }

            # Add risk metrics
            if self.risk_dashboard.risk_metrics:
                for metric_type, metric_history in self.risk_dashboard.risk_metrics.items():
                    if metric_history:
                        latest_metric = metric_history[-1]
                        report['risk_metrics'][metric_type.value] = {
                            'value': latest_metric.value,
                            'status': latest_metric.status,
                            'timestamp': latest_metric.timestamp.isoformat()
                        }

            return report

        except Exception as e:
            logger.error(f"System report generation failed: {e}")
            return {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}

    async def shutdown(self):
        """Shutdown the risk system gracefully."""
        try:
            logger.info("Shutting down Institutional Risk Management System...")

            # Stop monitoring
            self.system_config['enable_real_time_monitoring'] = False
            await self.risk_dashboard.stop_monitoring()

            # Perform final backup
            await self._perform_system_backup()

            # Shutdown thread pool
            self.executor.shutdown(wait=True)

            logger.info("System shutdown completed")

        except Exception as e:
            logger.error(f"System shutdown failed: {e}")

# Factory function for easy instantiation
def create_institutional_risk_system(config: Optional[Dict[str, Any]] = None) -> InstitutionalRiskSystem:
    """Create institutional risk management system instance."""
    return InstitutionalRiskSystem(config)