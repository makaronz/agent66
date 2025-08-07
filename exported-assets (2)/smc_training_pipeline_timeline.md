
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    🏋️‍♀️ PIPELINE SZKOLENIA I WALIDACJI SMC AGENT                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

📅 TIMELINE: 2019-2025 DATA SPLIT
┌────────────────┬────────────────┬────────────────┬────────────────┐
│   TRAIN SET    │  VALIDATION    │   TEST SET     │  PAPER TRADE   │
│  2019-2022     │   2022-2023    │  2023-2024     │   2024-2025    │
│   (3 years)    │   (1 year)     │   (1 year)     │   (6 weeks)    │
└────────────────┴────────────────┴────────────────┴────────────────┘

🔄 KROKI SZCZEGÓŁOWE:

1️⃣ DATASET SPLIT & PREPROCESSING:
```python
# Temporal split - no data leakage
train_data = ohlcv_data['2019-01-01':'2022-12-31']  # 70%
val_data = ohlcv_data['2023-01-01':'2023-12-31']    # 15% 
test_data = ohlcv_data['2024-01-01':'2024-12-31']   # 15%

# Multi-timeframe alignment
def preprocess_data(raw_data):
    # Resample to multiple timeframes
    tf_1m = raw_data.resample('1T').ohlc()
    tf_5m = raw_data.resample('5T').ohlc() 
    tf_15m = raw_data.resample('15T').ohlc()

    # Forward-fill missing values
    for df in [tf_1m, tf_5m, tf_15m]:
        df.fillna(method='ffill', inplace=True)

    return tf_1m, tf_5m, tf_15m
```

2️⃣ LABELING SMC EVENTS:
```python
class SMCLabeler:
    def label_order_blocks(self, ohlcv_data, volume_data):
        labels = pd.DataFrame(index=ohlcv_data.index)

        # Order Block formation labels (1/-1/0)
        labels['ob_bullish'] = self.detect_bullish_ob(ohlcv_data, volume_data)
        labels['ob_bearish'] = self.detect_bearish_ob(ohlcv_data, volume_data)

        # CHOCH/BOS labels
        labels['choch'] = self.detect_choch(ohlcv_data)
        labels['bos'] = self.detect_bos(ohlcv_data) 

        # Liquidity sweep labels
        labels['liq_sweep'] = self.detect_liquidity_sweeps(ohlcv_data)

        return labels

    def create_trading_labels(self, price_data, smc_features, lookahead_periods=20):
        # Future return-based labeling
        future_returns = price_data.close.pct_change(lookahead_periods).shift(-lookahead_periods)

        # Triple barrier method
        labels = pd.Series(index=price_data.index, dtype=int)

        for i in range(len(price_data) - lookahead_periods):
            entry_price = price_data.close.iloc[i]

            # Dynamic barriers based on SMC context
            if smc_features['trend'].iloc[i] == 'bullish':
                profit_target = 0.015  # 1.5% for trending markets
                stop_loss = -0.008     # 0.8% stop
            else:
                profit_target = 0.010  # 1.0% for ranging markets 
                stop_loss = -0.005     # 0.5% stop

            if future_returns.iloc[i] > profit_target:
                labels.iloc[i] = 1    # Long signal
            elif future_returns.iloc[i] < stop_loss:
                labels.iloc[i] = -1   # Short signal  
            else:
                labels.iloc[i] = 0    # Hold signal

        return labels
```

3️⃣ PRE-TRAINING SUPERVISED:
```python
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

# Feature engineering for supervised learning
def create_features(ohlcv_data, smc_indicators):
    features = pd.DataFrame(index=ohlcv_data.index)

    # Price-based features
    features['rsi_14'] = talib.RSI(ohlcv_data.close, 14)
    features['macd'] = talib.MACD(ohlcv_data.close)[0]
    features['bollinger_pos'] = (ohlcv_data.close - talib.BBANDS(ohlcv_data.close)[1]) /                                 (talib.BBANDS(ohlcv_data.close)[0] - talib.BBANDS(ohlcv_data.close)[1])

    # SMC-specific features  
    features['ob_distance'] = smc_indicators['nearest_ob_distance']
    features['fvg_count'] = smc_indicators['unfilled_fvg_count'] 
    features['liquidity_strength'] = smc_indicators['liquidity_concentration']
    features['structure_age'] = smc_indicators['structure_age']

    # Volume features
    features['volume_ma_ratio'] = ohlcv_data.volume / ohlcv_data.volume.rolling(20).mean()
    features['price_volume_trend'] = talib.ADOSC(ohlcv_data.high, ohlcv_data.low, 
                                                 ohlcv_data.close, ohlcv_data.volume)

    return features.dropna()

# Supervised model training
def train_supervised_model(features, labels):
    # Ensemble approach
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    xgb_model = XGBClassifier(n_estimators=200, max_depth=8, learning_rate=0.1)

    # Cross-validation with time series split
    from sklearn.model_selection import TimeSeriesSplit
    tscv = TimeSeriesSplit(n_splits=5)

    rf_scores = cross_val_score(rf_model, features, labels, cv=tscv, scoring='f1_macro')
    xgb_scores = cross_val_score(xgb_model, features, labels, cv=tscv, scoring='f1_macro')

    print(f"RF F1-Score: {rf_scores.mean():.3f} (+/- {rf_scores.std() * 2:.3f})")
    print(f"XGB F1-Score: {xgb_scores.mean():.3f} (+/- {xgb_scores.std() * 2:.3f})")

    # Train final models
    rf_model.fit(features, labels)
    xgb_model.fit(features, labels)

    return rf_model, xgb_model
```

4️⃣ FINE-TUNING RL-HF (Reinforcement Learning - High Frequency):
```python
import gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env

class SMCTradingEnv(gym.Env):
    def __init__(self, ohlcv_data, smc_features, transaction_cost=0.001):
        super(SMCTradingEnv, self).__init__()

        self.data = ohlcv_data
        self.smc_features = smc_features
        self.transaction_cost = transaction_cost
        self.current_step = 0
        self.position = 0  # -1, 0, 1 for short, neutral, long
        self.cash = 10000  # Starting capital
        self.portfolio_value = 10000

        # Action space: 0=Hold, 1=Buy, 2=Sell  
        self.action_space = gym.spaces.Discrete(3)

        # Observation space: OHLCV + SMC features
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(50,), dtype=np.float32  # 50 features
        )

    def step(self, action):
        # Execute trading action
        reward = self._execute_trade(action)

        # Move to next timestep
        self.current_step += 1

        # Get new observation
        obs = self._get_observation()

        # Check if episode is done
        done = self.current_step >= len(self.data) - 1

        return obs, reward, done, {}

    def _execute_trade(self, action):
        current_price = self.data.close.iloc[self.current_step]
        prev_portfolio_value = self.portfolio_value

        # SMC-aware reward shaping
        smc_context = self.smc_features.iloc[self.current_step]

        if action == 1 and self.position <= 0:  # Buy signal
            if smc_context['ob_bullish'] > 0.5:  # Strong bullish order block
                base_reward = 0.1  # Bonus for SMC confluence
            else:
                base_reward = 0.0

            # Execute buy
            self.position = 1
            self.cash *= (1 - self.transaction_cost)

        elif action == 2 and self.position >= 0:  # Sell signal  
            if smc_context['ob_bearish'] > 0.5:  # Strong bearish order block
                base_reward = 0.1
            else:
                base_reward = 0.0

            # Execute sell
            self.position = -1 
            self.cash *= (1 - self.transaction_cost)

        else:
            base_reward = 0.0  # Hold action

        # Calculate portfolio value
        if self.position == 1:
            self.portfolio_value = self.cash * (current_price / self.data.close.iloc[self.current_step-1])
        elif self.position == -1:
            self.portfolio_value = self.cash * (self.data.close.iloc[self.current_step-1] / current_price)
        else:
            self.portfolio_value = self.cash

        # Reward based on portfolio change + SMC bonus
        portfolio_return = (self.portfolio_value - prev_portfolio_value) / prev_portfolio_value
        reward = portfolio_return + base_reward

        # Penalty for excessive trading
        if action != 0:
            reward -= 0.001  # Small penalty for non-hold actions

        return reward

# RL Agent Training
def train_rl_agent(env, total_timesteps=100000):
    # PPO with custom policy for SMC
    model = PPO(
        "MlpPolicy", 
        env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64, 
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        verbose=1,
        tensorboard_log="./ppo_smc_tensorboard/"
    )

    # Training with callbacks
    from stable_baselines3.common.callbacks import EvalCallback

    eval_callback = EvalCallback(
        env, 
        best_model_save_path='./best_smc_model/',
        log_path='./eval_logs/',
        eval_freq=10000
    )

    model.learn(total_timesteps=total_timesteps, callback=eval_callback)
    return model
```

5️⃣ WALK-FORWARD BACKTEST (2019-2025):
```python
def walk_forward_backtest(model, data_2019_2025, window_size=252, step_size=63):
    results = []

    for start in range(0, len(data_2019_2025) - window_size, step_size):
        end = start + window_size

        # Training window
        train_data = data_2019_2025.iloc[start:end]

        # Test window (next period)
        test_data = data_2019_2025.iloc[end:end+step_size]

        # Retrain model on new data
        model_retrained = retrain_model(model, train_data)

        # Test performance
        test_results = evaluate_model(model_retrained, test_data)

        results.append({
            'start_date': train_data.index[0],
            'end_date': test_data.index[-1], 
            'sharpe_ratio': test_results['sharpe'],
            'max_drawdown': test_results['max_dd'],
            'win_rate': test_results['win_rate'],
            'profit_factor': test_results['profit_factor']
        })

    return pd.DataFrame(results)
```

6️⃣ PAPER TRADING (6 tygodni):
```bash
# Docker setup for paper trading
docker-compose up -d paper-trading-env

# Monitor real-time performance  
docker logs -f smc-agent-paper-trading

# Daily performance reports
python generate_daily_report.py --mode=paper-trading
```

🧪 HIPOTEZY TESTOWE:

H1: SMC-enhanced features improve prediction accuracy vs baseline technical indicators
    - Baseline: RSI, MACD, Bollinger Bands
    - SMC: Order Blocks, CHOCH, FVG, Liquidity sweeps
    - Metric: F1-score, Precision, Recall

H2: RL agent outperforms supervised learning in volatile markets  
    - Test during high volatility periods (VIX > 25)
    - Compare: PPO vs XGBoost vs Random Forest
    - Metric: Risk-adjusted returns (Sharpe, Sortino)

H3: Multi-timeframe SMC features reduce false signals
    - Single TF: 5m only
    - Multi TF: 1m + 5m + 15m alignment
    - Metric: Signal precision, drawdown periods

📊 STATISTICAL TESTS:

```python
from scipy import stats
import numpy as np

def statistical_validation(baseline_returns, smc_returns):
    # Mann-Whitney U test (non-parametric)
    statistic, p_value_mw = stats.mannwhitneyu(
        smc_returns, baseline_returns, 
        alternative='greater'
    )

    # Superior Predictive Ability (SPA) test
    def spa_test(forecast_errors_base, forecast_errors_smc, num_bootstrap=1000):
        diff = forecast_errors_base - forecast_errors_smc

        bootstrap_stats = []
        for _ in range(num_bootstrap):
            # Bootstrap resampling
            boot_sample = np.random.choice(diff, size=len(diff), replace=True)
            boot_stat = np.mean(boot_sample) / np.std(boot_sample) * np.sqrt(len(diff))
            bootstrap_stats.append(boot_stat)

        # P-value calculation
        p_value_spa = np.mean(np.array(bootstrap_stats) >= 0)
        return p_value_spa

    # Diebold-Mariano test for forecast accuracy
    def dm_test(errors1, errors2):
        d = errors1**2 - errors2**2
        mean_d = np.mean(d)
        var_d = np.var(d, ddof=1)
        dm_stat = mean_d / np.sqrt(var_d / len(d))
        p_value_dm = 2 * (1 - stats.norm.cdf(abs(dm_stat)))
        return dm_stat, p_value_dm

    results = {
        'mann_whitney_p': p_value_mw,
        'spa_p_value': spa_test(baseline_returns, smc_returns),
        'dm_statistic': dm_test(baseline_returns, smc_returns)[0],
        'dm_p_value': dm_test(baseline_returns, smc_returns)[1]
    }

    return results

# Acceptance criteria
def evaluate_statistical_significance(test_results):
    alpha = 0.05  # 5% significance level

    tests_passed = {
        'mann_whitney': test_results['mann_whitney_p'] < alpha,
        'spa_test': test_results['spa_p_value'] < alpha, 
        'dm_test': test_results['dm_p_value'] < alpha
    }

    if sum(tests_passed.values()) >= 2:
        return "SMC approach statistically superior"
    else:
        return "No significant improvement detected"
```



┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        ⏱️ HARMONOGRAM PROJEKTU - 4 FAZY                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

📊 TABELA CZASOWO-ZASOBOWA:

┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────────────────┐
│     FAZA     │     CZAS     │   ZASOBY     │   PERSONEL   │       DELIVERABLES       │
├──────────────┼──────────────┼──────────────┼──────────────┼──────────────────────────┤
│  RESEARCH    │   6 tygodni  │ 10k USD      │ 2 deweloperów│ • SMC Library            │
│              │              │              │ 1 researcher │ • Data Pipeline          │
│              │              │              │              │ • Feature Engineering   │
│              │              │              │              │ • Market Analysis        │
├──────────────┼──────────────┼──────────────┼──────────────┼──────────────────────────┤
│  PROTOTYP    │   8 tygodni  │ 25k USD      │ 3 deweloperów│ • MVP Trading Agent      │
│              │              │              │ 1 ML engineer│ • Backtesting Framework  │
│              │              │              │ 1 DevOps     │ • Basic ML Models        │
│              │              │              │              │ • Docker Infrastructure  │
├──────────────┼──────────────┼──────────────┼──────────────┼──────────────────────────┤
│    TESTY     │  10 tygodni  │ 40k USD      │ 4 deweloperów│ • Production System      │
│              │              │              │ 1 QA tester  │ • Advanced RL Models     │
│              │              │              │ 1 risk mgr   │ • Risk Management        │
│              │              │              │              │ • Paper Trading Results │
├──────────────┼──────────────┼──────────────┼──────────────┼──────────────────────────┤
│ PRODUCTION   │  12 tygodni  │ 60k USD      │ 5 deweloperów│ • Live Trading System    │
│              │              │              │ 2 DevOps     │ • Monitoring Dashboard   │
│              │              │              │ 1 compliance │ • Regulatory Compliance  │
│              │              │              │              │ • Performance Reports   │
├──────────────┼──────────────┼──────────────┼──────────────┼──────────────────────────┤
│   ŁĄCZNIE    │  36 tygodni  │ 135k USD     │   Peak: 9    │       Full System        │
│              │  (9 miesięcy)│              │              │                          │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────────────────┘

🔍 SZCZEGÓŁOWY BREAKDOWN FAZA PO FAZIE:

FAZA 1: RESEARCH (Tygodnie 1-6) 🔬
┌─ Tydzień 1-2: Market Research & SMC Analysis
│  ├─ Audyt existing SMC libraries (joshyattridge, smtlab)
│  ├─ Competition analysis (retail vs institutional approaches)  
│  └─ Data source evaluation (Binance, ByBit, OANDA APIs)
│
├─ Tydzień 3-4: Data Pipeline Development
│  ├─ WebSocket connectors implementation
│  ├─ Historical data ingestion (2019-2025)
│  ├─ TimescaleDB setup and optimization
│  └─ Multi-timeframe data alignment
│
└─ Tydzień 5-6: SMC Feature Engineering
   ├─ Order Block detection algorithms
   ├─ CHOCH/BOS identification logic
   ├─ Liquidity sweep detection
   └─ Fair Value Gap calculation

FAZA 2: PROTOTYP (Tygodnie 7-14) 🛠️
┌─ Tydzień 7-8: Core Trading Logic
│  ├─ SMC indicator library completion
│  ├─ Signal generation framework  
│  ├─ Basic position sizing logic
│  └─ Risk management foundations
│
├─ Tydzień 9-11: ML Model Development
│  ├─ Supervised learning baseline (XGBoost, RF)
│  ├─ Feature selection and engineering
│  ├─ Cross-validation framework
│  └─ Performance evaluation metrics
│
└─ Tydzień 12-14: Infrastructure Setup
   ├─ Docker containerization
   ├─ Basic monitoring (Prometheus)
   ├─ Backtesting engine implementation
   └─ Paper trading simulation

FAZA 3: TESTY (Tygodnie 15-24) 🧪
┌─ Tydzień 15-17: Advanced ML Development
│  ├─ Reinforcement Learning environment setup
│  ├─ PPO agent implementation and training
│  ├─ Hyperparameter optimization (Optuna)
│  └─ Model ensemble techniques
│
├─ Tydzień 18-20: Risk & Performance Optimization  
│  ├─ Advanced risk management (VaR, drawdown limits)
│  ├─ Position sizing optimization (Kelly Criterion)
│  ├─ Portfolio correlation analysis
│  └─ Slippage and transaction cost modeling
│
├─ Tydzień 21-22: Paper Trading Phase
│  ├─ 6-week paper trading execution
│  ├─ Real-time performance monitoring
│  ├─ Model behavior analysis
│  └─ Edge case handling
│
└─ Tydzień 23-24: Testing & Validation
   ├─ Statistical significance testing
   ├─ Stress testing (market crash scenarios)
   ├─ Latency optimization (<100ms target)
   └─ Security audit and penetration testing

FAZA 4: PRODUCTION (Tygodnie 25-36) 🚀
┌─ Tydzień 25-28: Production Infrastructure
│  ├─ Kubernetes cluster setup (AWS/GCP)
│  ├─ Load balancing and auto-scaling
│  ├─ Database replication and backup
│  └─ CI/CD pipeline implementation
│
├─ Tydzień 29-32: Compliance & Monitoring
│  ├─ Regulatory compliance (MiFID II, ESMA)
│  ├─ Audit trail implementation  
│  ├─ Advanced monitoring (Grafana dashboards)
│  └─ Alerting system setup
│
├─ Tydzień 33-35: Live Trading Launch
│  ├─ Gradual capital deployment ($10k → $100k → $1M)
│  ├─ Real-time performance validation
│  ├─ Model retraining pipeline
│  └─ Customer support infrastructure
│
└─ Tydzień 36: Documentation & Handover
   ├─ Technical documentation completion
   ├─ User manual and API documentation  
   ├─ Training materials for operations team
   └─ Project retrospective and lessons learned

💰 KOSZTY SZCZEGÓŁOWE:

Hardware & Infrastructure:
• Cloud Computing (AWS/GCP): $15k
• Development Workstations: $8k  
• Trading APIs & Data Feeds: $12k

Software & Licenses:
• Development Tools & IDEs: $3k
• Monitoring & Analytics: $5k
• Third-party Libraries: $2k  

Personnel (9 months):
• Senior Developers (4x): $80k
• ML Engineer: $25k
• DevOps Engineers (2x): $30k
• QA Tester: $15k
• Risk Manager: $20k
• Compliance Specialist: $10k

🎯 KLUCZOWE KAMIENIE MILOWE:

Week 6: ✅ SMC Feature Library Complete
Week 14: ✅ MVP Trading Agent Ready  
Week 24: ✅ Paper Trading Results Validated
Week 30: ✅ Production Infrastructure Live
Week 36: ✅ Full System Operational

⚠️ RYZYKA I MITYGACJA:

• Data Quality Issues → Multiple data source validation
• Model Overfitting → Robust cross-validation + walk-forward testing  
• Regulatory Changes → Early compliance consultation
• Market Regime Shifts → Adaptive model retraining
• Technical Failures → Redundant infrastructure + circuit breakers
