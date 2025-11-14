# User Onboarding Guide

## Welcome to SMC Trading Agent

This comprehensive guide will help you get started with the SMC Trading Agent platform. Follow these steps to set up your account, configure your trading strategies, and begin automated trading using Smart Money Concepts.

## 📋 Prerequisites

Before you begin, ensure you have:

- [ ] Valid email address for account registration
- [ ] Exchange account(s) with API access enabled:
  - **Binance**: Spot and/or Futures trading account
  - **Bybit**: Unified Trading Account (UTA) recommended
  - **Oanda**: Live or Demo trading account
- [ ] Minimum account balance: $1,000 USD equivalent
- [ ] Basic understanding of cryptocurrency/forex trading
- [ ] Two-factor authentication app (Google Authenticator, Authy, etc.)

## 🚀 Step 1: Account Registration

### 1.1 Create Your Account

1. Navigate to [https://app.smc-trading.com/register](https://app.smc-trading.com/register)
2. Fill in the registration form:
   ```
   Full Name: [Your full legal name]
   Email Address: [your.email@domain.com]
   Password: [Strong password with 8+ characters]
   Confirm Password: [Repeat your password]
   Country: [Select your country of residence]
   ```
3. Accept the Terms of Service and Privacy Policy
4. Click "Create Account"

![Registration Form](../images/registration-form.png)

### 1.2 Email Verification

1. Check your email inbox for a verification message from `noreply@smc-trading.com`
2. Click the verification link in the email
3. You'll be redirected to the login page with a confirmation message

### 1.3 Initial Login

1. Go to [https://app.smc-trading.com/login](https://app.smc-trading.com/login)
2. Enter your email and password
3. Click "Sign In"

## 🔐 Step 2: Security Setup

### 2.1 Enable Two-Factor Authentication (2FA)

**Important**: 2FA is mandatory for all trading accounts.

1. After first login, you'll be prompted to set up 2FA
2. Download a 2FA app if you don't have one:

   - **Google Authenticator** (iOS/Android)
   - **Authy** (iOS/Android/Desktop)
   - **Microsoft Authenticator** (iOS/Android)

3. Follow the setup process:
   ```
   1. Open your 2FA app
   2. Scan the QR code displayed on screen
   3. Enter the 6-digit code from your app
   4. Save your backup codes in a secure location
   5. Click "Enable 2FA"
   ```

![2FA Setup](../images/2fa-setup.png)

### 2.2 Set Up Backup Codes

1. After enabling 2FA, download your backup codes
2. Store them securely (password manager, encrypted file, or printed copy)
3. These codes can be used if you lose access to your 2FA device

### 2.3 Configure Security Preferences

Navigate to **Settings > Security** and configure:

- **Login Notifications**: Enable email notifications for new logins
- **API Access Logs**: Enable logging of all API key usage
- **Session Timeout**: Set automatic logout after inactivity (recommended: 30 minutes)
- **IP Whitelist**: Optionally restrict access to specific IP addresses

## 🔑 Step 3: Exchange API Configuration

### 3.1 Binance API Setup

#### Create Binance API Keys:

1. Log in to your Binance account
2. Go to **Account > API Management**
3. Click **Create API**
4. Complete identity verification if required
5. Name your API key: "SMC Trading Agent"
6. Configure permissions:
   ```
   ✅ Enable Reading
   ✅ Enable Spot & Margin Trading
   ✅ Enable Futures Trading (if using futures)
   ❌ Enable Withdrawals (NOT recommended)
   ```
7. Set IP restrictions (recommended):
   - Add the SMC Trading Agent server IPs
   - Contact support for current IP addresses

#### Add API Keys to SMC Trading Agent:

1. In SMC Trading Agent, go to **Settings > Exchange APIs**
2. Click **Add Exchange > Binance**
3. Fill in the form:
   ```
   Exchange: Binance
   Environment: Live Trading (or Testnet for testing)
   API Key: [Your Binance API Key]
   Secret Key: [Your Binance Secret Key]
   Passphrase: [Leave empty for Binance]
   ```
4. Click **Test Connection** to verify
5. Click **Save** when test passes

![Binance API Setup](../images/binance-api-setup.png)

### 3.2 Bybit API Setup

#### Create Bybit API Keys:

1. Log in to your Bybit account
2. Go to **Account & Security > API**
3. Click **Create New Key**
4. Configure settings:

   ```
   Key Name: SMC Trading Agent
   Key Type: System-generated API Keys

   Permissions:
   ✅ Read-Write
   ✅ Contract Trading
   ✅ Spot Trading
   ✅ Wallet
   ❌ Asset Exchange (NOT recommended)

   IP Restrictions: [Add SMC Trading Agent IPs]
   ```

#### Add to SMC Trading Agent:

1. Go to **Settings > Exchange APIs**
2. Click **Add Exchange > Bybit**
3. Enter your API credentials
4. Test and save the connection

### 3.3 Oanda API Setup

#### Get Oanda API Access:

1. Log in to your Oanda account
2. Go to **Manage Funds > fxTrade API**
3. Generate your API token
4. Note your Account ID

#### Add to SMC Trading Agent:

1. Go to **Settings > Exchange APIs**
2. Click **Add Exchange > Oanda**
3. Enter:
   ```
   API Token: [Your Oanda API Token]
   Account ID: [Your Oanda Account ID]
   Environment: Live (or Practice for demo)
   ```

## ⚙️ Step 4: Trading Configuration

### 4.1 Risk Management Settings

Navigate to **Settings > Risk Management** and configure:

#### Global Risk Limits:

```
Maximum Position Size: $1,000 (adjust based on your capital)
Maximum Daily Loss: 2% of account balance
Maximum Drawdown: 5% of account balance
Risk per Trade: 1% of account balance
```

#### Position Sizing:

```
Position Sizing Method: Fixed Percentage
Risk Percentage: 1%
Maximum Positions: 5 concurrent positions
```

#### Stop Loss Settings:

```
Default Stop Loss: 2% from entry
Maximum Stop Loss: 5% from entry
Trailing Stop: Enabled
Trailing Distance: 1%
```

![Risk Management](../images/risk-management.png)

### 4.2 SMC Strategy Configuration

#### Basic SMC Settings:

1. Go to **Trading > Strategy Configuration**
2. Select **SMC (Smart Money Concepts)**
3. Configure parameters:

```
Order Block Detection:
- Minimum Block Size: 50 pips
- Block Validation Period: 4 hours
- Maximum Block Age: 24 hours

Liquidity Zones:
- Zone Strength Threshold: 3 touches
- Zone Validity Period: 12 hours
- Minimum Zone Size: 20 pips

Fair Value Gaps:
- Minimum Gap Size: 10 pips
- Gap Fill Threshold: 50%
- Maximum Gap Age: 8 hours

Market Structure:
- Trend Confirmation: 3 higher highs/lower lows
- Structure Break Confirmation: Close beyond level
- Retest Requirement: Enabled
```

#### Timeframe Settings:

```
Primary Analysis: 4H
Secondary Analysis: 1H
Entry Timeframe: 15M
Confirmation Timeframe: 5M
```

### 4.3 Notification Settings

Configure alerts in **Settings > Notifications**:

#### Signal Notifications:

```
✅ New SMC Signals
✅ Trade Entries
✅ Trade Exits
✅ Stop Loss Hits
✅ Take Profit Hits
```

#### System Notifications:

```
✅ System Errors
✅ API Connection Issues
✅ Risk Limit Breaches
✅ Daily Performance Summary
```

#### Delivery Methods:

```
✅ Email Notifications
✅ In-App Notifications
✅ Telegram Bot (optional)
✅ SMS Alerts (premium feature)
```

## 📊 Step 5: Dashboard Overview

### 5.1 Main Dashboard

After configuration, your dashboard will display:

#### Portfolio Overview:

- **Total Balance**: Combined balance across all exchanges
- **Available Balance**: Funds available for trading
- **Unrealized P&L**: Current open position profits/losses
- **Daily P&L**: Today's realized profits/losses

#### Active Positions:

- **Open Trades**: Currently active positions
- **Pending Orders**: Orders waiting for execution
- **Recent Signals**: Latest SMC signals generated

#### Performance Metrics:

- **Win Rate**: Percentage of profitable trades
- **Average Win/Loss**: Average profit vs average loss
- **Sharpe Ratio**: Risk-adjusted return metric
- **Maximum Drawdown**: Largest peak-to-trough decline

![Dashboard Overview](../images/dashboard-overview.png)

### 5.2 Trading Interface

#### Signal Analysis Panel:

- **Market Structure**: Current trend analysis
- **Order Blocks**: Identified institutional levels
- **Liquidity Zones**: Areas of accumulated orders
- **Fair Value Gaps**: Price imbalances to be filled

#### Trade Management:

- **Manual Override**: Ability to close positions manually
- **Risk Adjustment**: Modify stop loss and take profit levels
- **Position Sizing**: Adjust trade size before entry

## 🎯 Step 6: Your First Trade

### 6.1 Paper Trading (Recommended)

Before live trading, practice with paper trading:

1. Go to **Settings > Trading Mode**
2. Select **Paper Trading**
3. Set virtual balance: $10,000
4. Enable all SMC strategies
5. Monitor performance for 1-2 weeks

### 6.2 Live Trading Setup

When ready for live trading:

1. Switch to **Live Trading** mode
2. Start with minimum position sizes
3. Monitor closely for the first few trades
4. Gradually increase position sizes as confidence grows

### 6.3 Monitoring Your First Trade

#### Pre-Trade Checklist:

- [ ] Risk management settings configured
- [ ] Stop loss and take profit levels set
- [ ] Position size appropriate for account balance
- [ ] Market conditions suitable for SMC strategy

#### During Trade:

- Monitor the trade through the **Active Positions** panel
- Watch for SMC signal confirmations
- Be prepared to manually intervene if needed

#### Post-Trade Analysis:

- Review trade performance in **Analytics > Trade History**
- Analyze what worked and what didn't
- Adjust strategy parameters if necessary

## 📈 Step 7: Performance Monitoring

### 7.1 Analytics Dashboard

Access detailed analytics in **Analytics > Performance**:

#### Key Metrics to Monitor:

```
Profitability Metrics:
- Total Return: Overall account growth
- Monthly Returns: Month-by-month performance
- Risk-Adjusted Returns: Sharpe and Sortino ratios

Risk Metrics:
- Value at Risk (VaR): Potential loss estimation
- Maximum Drawdown: Worst losing streak
- Win/Loss Ratio: Success rate analysis

Trading Metrics:
- Average Trade Duration: How long positions are held
- Trade Frequency: Number of trades per day/week
- Market Exposure: Percentage of time in market
```

### 7.2 Strategy Performance

Monitor individual strategy performance:

#### SMC Strategy Metrics:

- **Order Block Success Rate**: Percentage of successful OB trades
- **Liquidity Zone Accuracy**: How often LZ levels hold
- **Fair Value Gap Fill Rate**: Percentage of gaps that get filled
- **Market Structure Accuracy**: Trend identification success

### 7.3 Regular Review Process

#### Weekly Review:

- [ ] Check overall performance vs benchmarks
- [ ] Review risk metrics and drawdown
- [ ] Analyze strategy effectiveness
- [ ] Adjust parameters if needed

#### Monthly Review:

- [ ] Comprehensive performance analysis
- [ ] Strategy optimization
- [ ] Risk management review
- [ ] Goal setting for next month

## 🛠️ Step 8: Advanced Features

### 8.1 Custom Indicators

Create custom SMC indicators:

1. Go to **Tools > Custom Indicators**
2. Use the visual indicator builder
3. Combine multiple SMC concepts
4. Backtest your custom indicators

### 8.2 Strategy Optimization

Use the built-in optimizer:

1. Navigate to **Tools > Strategy Optimizer**
2. Select parameters to optimize
3. Set optimization period (recommended: 6 months)
4. Run optimization and review results

### 8.3 API Access

For advanced users, access the REST API:

1. Go to **Settings > API Access**
2. Generate API credentials
3. Review API documentation at [https://api.smc-trading.com/docs](https://api.smc-trading.com/docs)
4. Build custom integrations

## 🆘 Step 9: Support and Resources

### 9.1 Getting Help

#### Support Channels:

- **Help Center**: [https://help.smc-trading.com](https://help.smc-trading.com)
- **Live Chat**: Available 24/7 in the application
- **Email Support**: support@smc-trading.com
- **Community Forum**: [https://community.smc-trading.com](https://community.smc-trading.com)

#### Response Times:

- **Critical Issues**: Within 1 hour
- **General Support**: Within 4 hours
- **Feature Requests**: Within 24 hours

### 9.2 Educational Resources

#### Learning Materials:

- **SMC Trading Course**: Comprehensive video series
- **Webinars**: Weekly live trading sessions
- **Blog**: Market analysis and strategy insights
- **YouTube Channel**: Educational content and tutorials

#### Documentation:

- **User Manual**: Complete feature documentation
- **API Documentation**: Technical integration guide
- **Strategy Guides**: Detailed SMC implementation guides
- **FAQ**: Frequently asked questions

### 9.3 Community

Join our trading community:

#### Discord Server:

- Real-time chat with other traders
- Strategy discussions
- Market analysis sharing
- Support from experienced users

#### Telegram Groups:

- **Signals Channel**: Real-time trade signals
- **Discussion Group**: Strategy and market talk
- **Announcements**: Platform updates and news

## ✅ Onboarding Checklist

Complete this checklist to ensure proper setup:

### Account Setup:

- [ ] Account registered and email verified
- [ ] Two-factor authentication enabled
- [ ] Backup codes saved securely
- [ ] Security preferences configured

### Exchange Integration:

- [ ] At least one exchange API configured
- [ ] API permissions properly set
- [ ] Connection tested successfully
- [ ] IP restrictions configured (if applicable)

### Trading Configuration:

- [ ] Risk management settings configured
- [ ] SMC strategy parameters set
- [ ] Notification preferences configured
- [ ] Trading mode selected (paper/live)

### Testing and Verification:

- [ ] Paper trading tested
- [ ] Dashboard familiarization complete
- [ ] First live trade executed (if ready)
- [ ] Performance monitoring set up

### Support and Learning:

- [ ] Help resources bookmarked
- [ ] Community channels joined
- [ ] Educational materials accessed
- [ ] Support contact information saved

## 🎉 Congratulations!

You've successfully completed the SMC Trading Agent onboarding process. You're now ready to:

- Execute automated SMC trading strategies
- Monitor and optimize your performance
- Leverage institutional trading concepts
- Scale your trading operations

### Next Steps:

1. **Start Small**: Begin with minimal position sizes
2. **Learn Continuously**: Engage with educational content
3. **Monitor Closely**: Watch your first few weeks of trading
4. **Optimize Gradually**: Make incremental improvements
5. **Stay Connected**: Engage with the community

### Important Reminders:

- **Risk Management**: Never risk more than you can afford to lose
- **Continuous Learning**: Markets evolve, keep learning
- **Regular Reviews**: Monitor and adjust your strategies
- **Stay Informed**: Keep up with platform updates and market news

Welcome to the future of algorithmic trading with Smart Money Concepts!

---

**Need Help?**  
Contact our support team at support@smc-trading.com or use the live chat feature in the application.

**Last Updated**: $(date)  
**Document Version**: 1.0.0  
**Next Review Date**: $(date -d "+1 month")
