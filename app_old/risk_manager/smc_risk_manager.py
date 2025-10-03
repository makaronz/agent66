import yaml

class SMCRiskManager:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.risk_config = config['risk_manager']
        self.max_position_size = self.risk_config['max_position_size']
        self.max_daily_loss = self.risk_config['max_daily_loss']
        self.max_drawdown = self.risk_config['max_drawdown']
        self.circuit_breaker_threshold = self.risk_config['circuit_breaker_threshold']
        self.position_limits = self.risk_config['position_limits']

    def check_position_size(self, symbol, size):
        """Checks if the position size is within the defined limits."""
        limit = self.position_limits.get(symbol, self.position_limits['default'])
        if size > limit:
            return False, f"Position size {size} for {symbol} exceeds limit of {limit}"
        return True, ""

    def check_daily_loss(self, current_loss):
        """Checks if the daily loss exceeds the maximum allowed."""
        if current_loss > self.max_daily_loss:
            return False, f"Daily loss {current_loss} exceeds limit of {self.max_daily_loss}"
        return True, ""

    def check_drawdown(self, current_drawdown):
        """Checks if the drawdown exceeds the maximum allowed."""
        if current_drawdown > self.max_drawdown:
            return False, f"Drawdown {current_drawdown} exceeds limit of {self.max_drawdown}"
        return True, ""

    def check_circuit_breaker(self, market_change):
        """Checks if the market change triggers the circuit breaker."""
        if abs(market_change) > self.circuit_breaker_threshold:
            return False, f"Market change {market_change} triggers circuit breaker at {self.circuit_breaker_threshold}"
        return True, ""

    def assess_trade_risk(self, symbol, size, current_loss, current_drawdown, market_change):
        """Assesses the risk of a potential trade."""
        checks = [
            self.check_position_size(symbol, size),
            self.check_daily_loss(current_loss),
            self.check_drawdown(current_drawdown),
            self.check_circuit_breaker(market_change)
        ]

        for is_ok, message in checks:
            if not is_ok:
                return False, message
        
        return True, "Trade is within risk parameters"