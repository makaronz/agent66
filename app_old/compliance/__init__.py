"""
Compliance Module - Regulatory Compliance and Reporting

Handles comprehensive regulatory compliance and reporting requirements for the SMC Trading Agent.
Includes MiFID reporting, regulatory monitoring, and compliance validation features.

Key Features:
- MiFID II reporting and compliance monitoring
- Regulatory requirement validation and enforcement
- Automated compliance reporting and documentation
- Risk assessment and regulatory risk monitoring
- Audit trail maintenance and record keeping
- Compliance alerts and violation detection
- Regulatory change management and updates

Usage:
    from smc_trading_agent.compliance import ComplianceEngine
    
    engine = ComplianceEngine()
    report = engine.generate_regulatory_report(period_start, period_end)
"""

__version__ = "1.0.0"
__description__ = "Regulatory compliance and reporting features"
__keywords__ = ["compliance", "mifid", "regulatory", "reporting", "audit"]

# Import compliance components
from .mifid_reporting import ComplianceEngine

# Package-level exports
__all__ = [
    'ComplianceEngine',
    '__version__',
    '__description__'
]

# Convenience functions
def get_compliance_engine(config: dict = None) -> ComplianceEngine:
    """
    Factory function to create a ComplianceEngine instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        ComplianceEngine instance
    """
    return ComplianceEngine(config or {})
