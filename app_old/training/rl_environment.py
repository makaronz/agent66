import gymnasium as gym
import numpy as np

class SMCTradingEnv(gym.Env):
    def __init__(self, ohlcv_data, smc_features, transaction_cost=0.001):
        super(SMCTradingEnv, self).__init__()
        # Action space: 0=Hold, 1=Buy, 2=Sell  
        self.action_space = gym.spaces.Discrete(3)
        # Observation space: OHLCV + SMC features
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(50,), dtype=np.float32
        )
        self.smc_features = smc_features
        self.current_step = 0
        
    def _execute_trade(self, action):
        # SMC-aware reward shaping
        smc_context = self.smc_features.iloc[self.current_step]
        base_reward = 0
        if action == 1 and smc_context.get('ob_bullish', 0) > 0.5:
            base_reward = 0.1  # Bonus for SMC confluence
        return base_reward
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        # Return initial observation
        return np.zeros(self.observation_space.shape), {}

    def step(self, action):
        self.current_step += 1
        reward = self._execute_trade(action)
        done = self.current_step >= len(self.smc_features) - 1
        truncated = False # Not used
        info = {}
        # Return next observation, reward, done, truncated, info
        return np.zeros(self.observation_space.shape), reward, done, truncated, info

