import logging

class SMCRiskManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Risk Manager (SMCRiskManager) initialized.")

    def calculate_stop_loss(self, entry_price: float, direction: str, order_blocks: list, structure: dict) -> float:
        """
        Calculates the stop-loss price based on the nearest relevant structure.
        """
        if direction == "BUY":
            # For a long, SL is below the low of the bullish order block
            relevant_ob = self.find_nearest_bullish_ob(entry_price, order_blocks)
            if relevant_ob:
                sl_price = relevant_ob['price_level'][1] * 0.998  # 0.2% buffer below the low
                self.logger.info("Calculated SL based on bullish order block.", extra={'sl_price': sl_price})
                return sl_price
            else:
                # Fallback to a generic percentage
                sl_price = entry_price * 0.98 # 2% stop loss
                self.logger.warning("No relevant OB for SL calculation, using fallback.", extra={'sl_price': sl_price})
                return sl_price
        else: # SELL
            # For a short, SL is above the high of the bearish order block
            relevant_ob = self.find_nearest_bearish_ob(entry_price, order_blocks)
            if relevant_ob:
                sl_price = relevant_ob['price_level'][0] * 1.002 # 0.2% buffer above the high
                self.logger.info("Calculated SL based on bearish order block.", extra={'sl_price': sl_price})
                return sl_price
            else:
                sl_price = entry_price * 1.02 # 2% stop loss
                self.logger.warning("No relevant OB for SL calculation, using fallback.", extra={'sl_price': sl_price})
                return sl_price

    def calculate_take_profit(self, entry_price: float, stop_loss_price: float, direction: str, risk_reward_ratio: float = 3.0) -> float:
        """
        Calculates the take-profit price based on a fixed risk/reward ratio.
        """
        risk_per_share = abs(entry_price - stop_loss_price)
        if direction == "BUY":
            tp_price = entry_price + (risk_per_share * risk_reward_ratio)
        else: # SELL
            tp_price = entry_price - (risk_per_share * risk_reward_ratio)
        
        self.logger.info(f"Calculated TP for {risk_reward_ratio}:1 R/R.", extra={'tp_price': tp_price})
        return tp_price

    def find_nearest_bullish_ob(self, entry_price, order_blocks):
        # Finds the closest bullish order block below the entry price
        # For a bullish order block, we want the low to be below entry price for stop loss placement
        bullish_obs = [ob for ob in order_blocks if ob['type'] == 'bullish' and ob['price_level'][1] < entry_price]
        if not bullish_obs:
            return None
        return min(bullish_obs, key=lambda ob: entry_price - ob['price_level'][1])

    def find_nearest_bearish_ob(self, entry_price, order_blocks):
        # Finds the closest bearish order block above the entry price
        # For a bearish order block, we want the high to be above entry price for stop loss placement
        bearish_obs = [ob for ob in order_blocks if ob['type'] == 'bearish' and ob['price_level'][0] > entry_price]
        if not bearish_obs:
            return None
        return min(bearish_obs, key=lambda ob: ob['price_level'][0] - entry_price)
