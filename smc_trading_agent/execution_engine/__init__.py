"""
Execution Engine Module - High-Performance Trade Execution

Handles high-performance trade execution and order management for the SMC Trading Agent.
Implemented in Rust for optimal performance, low latency, and reliable exchange communication.

Key Features:
- High-performance order execution with minimal latency
- Multi-exchange order routing and management
- Real-time order status tracking and updates
- Advanced order types and execution strategies
- Exchange connectivity and API management
- Performance monitoring and optimization

Implementation:
- Core execution logic implemented in Rust (executor.rs)
- Python bindings for integration with the main system
- Optimized for low-latency trading requirements
- Supports multiple exchange APIs and protocols

Usage:
    # Rust implementation provides high-performance execution
    # Python integration available through FFI bindings
    from smc_trading_agent.execution_engine import executor
    
    # Order execution through Rust backend
    result = executor.execute_order(order_params)
"""

__version__ = "1.0.0"
__description__ = "High-performance trade execution engine (Rust implementation)"
__keywords__ = ["execution-engine", "rust", "high-performance", "order-management", "trading"]

# Package-level exports
__all__ = [
    '__version__',
    '__description__'
]

# Note: Rust implementation provides the core functionality
# Python bindings available for integration
