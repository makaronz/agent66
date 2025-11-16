#!/usr/bin/env python3
"""
Simple Entry Point for SMC Trading Agent - Paper Trading Mode

This is a simplified launcher that avoids complex service orchestration.
Perfect for quick testing and personal use.
"""

import sys
import asyncio
import logging
import signal
import pandas as pd
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Global flag for shutdown
shutdown_flag = False

# Global paper trading engine (will be set in main)
paper_engine = None

# FastAPI app
app = FastAPI(title="SMC Trading Agent API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.get("/api/python/paper-trades")
async def get_paper_trades(limit: int = 50):
    """Get paper trading history."""
    if paper_engine is None:
        return {"success": False, "error": "Paper trading engine not initialized"}
    try:
        trades = paper_engine.get_trade_history(limit=limit)
        return {"success": True, "data": trades}
    except Exception as e:
        logger.error(f"Failed to get paper trades: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/api/python/positions")
async def get_positions():
    """Get open positions."""
    if paper_engine is None:
        return {"success": False, "error": "Paper trading engine not initialized"}
    try:
        positions = paper_engine.get_open_positions()
        return {"success": True, "data": positions}
    except Exception as e:
        logger.error(f"Failed to get positions: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/api/python/account")
async def get_account():
    """Get account summary."""
    if paper_engine is None:
        return {"success": False, "error": "Paper trading engine not initialized"}
    try:
        summary = paper_engine.get_account_summary()
        return {"success": True, "data": summary}
    except Exception as e:
        logger.error(f"Failed to get account summary: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "success": True,
        "status": "healthy",
        "paper_engine_initialized": paper_engine is not None
    }


def handle_shutdown(signum, frame):
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_flag = True


async def main():
    """Main trading loop - simplified version."""
    global paper_engine
    
    logger.info("=" * 60)
    logger.info("SMC TRADING AGENT - PAPER TRADING MODE")
    logger.info("=" * 60)
    
    try:
        # Import components
        from data_pipeline.live_data_client import LiveDataClient
        from smc_detector.indicators import SMCIndicators
        from decision_engine.simple_heuristic import SimpleSMCHeuristic
        from risk_manager.smc_risk_manager import SMCRiskManager
        from execution_engine.paper_trading import PaperTradingEngine
        
        logger.info("✓ All components imported successfully")
        
        # Initialize components
        data_client = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()
        decision_engine = SimpleSMCHeuristic(min_confidence=0.70)
        risk_manager = SMCRiskManager(config={
            'max_position_size': 1000,
            'max_daily_loss': 500,
            'stop_loss_percent': 2.0,
            'take_profit_ratio': 3.0
        })
        paper_engine = PaperTradingEngine(initial_balance=10000.0, max_positions=3)
        
        logger.info("✓ All components initialized")
        logger.info(f"✓ Paper Trading Engine: ${paper_engine.balance:.2f} balance")
        logger.info("")
        
        # Start FastAPI server in background
        logger.info("🌐 Starting FastAPI server on port 8000...")
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server_task = asyncio.create_task(server.serve())
        logger.info("✅ FastAPI server started - API available at http://localhost:8000")
        logger.info("")
        
        # Main trading loop
        cycle_count = 0
        
        while not shutdown_flag:
            cycle_count += 1
            logger.info(f"{'='*60}")
            logger.info(f"CYCLE #{cycle_count} - {asyncio.get_event_loop().time():.0f}s")
            logger.info(f"{'='*60}")
            
            try:
                # 1. Fetch live OHLCV data
                logger.info("Step 1: Fetching live market data...")
                market_data = await data_client.get_latest_ohlcv_data("BTC/USDT", "1h", limit=100)
                
                if market_data is None or market_data.empty:
                    logger.warning("⚠️ No market data received, skipping cycle")
                    await asyncio.sleep(60)
                    continue
                
                # Fix DataFrame format - SMC detector expects 'timestamp' column
                if 'timestamp' not in market_data.columns:
                    # Reset index if timestamp is in index
                    if isinstance(market_data.index, pd.DatetimeIndex):
                        market_data = market_data.reset_index()
                        if 'index' in market_data.columns:
                            market_data = market_data.rename(columns={'index': 'timestamp'})
                    else:
                        # Create timestamp column from index
                        market_data = market_data.reset_index()
                        if 'timestamp' not in market_data.columns:
                            market_data['timestamp'] = pd.Timestamp.now()
                
                logger.info(f"✓ Received {len(market_data)} OHLCV candles")
                logger.info(f"  Latest price: ${market_data['close'].iloc[-1]:.2f}")
                
                # 2. Detect SMC patterns
                logger.info("Step 2: Detecting SMC patterns...")
                order_blocks = smc_detector.detect_order_blocks(market_data)
                
                if not order_blocks:
                    logger.info("→ No significant SMC patterns detected")
                else:
                    logger.info(f"✓ Detected {len(order_blocks)} order block(s)")
                    for ob in order_blocks[:2]:  # Log first 2
                        logger.info(f"  - {ob.get('direction', 'unknown')}: {ob.get('price_level')}")
                
                # 3. Generate trading signal
                if order_blocks:
                    logger.info("Step 3: Generating trading signal...")
                    signal = decision_engine.make_decision(order_blocks, market_data)
                    
                    if signal and signal.get('confidence', 0) > 0.70:
                        logger.info(f"✓ Signal: {signal['action']} @ ${signal['entry_price']:.2f} (confidence: {signal['confidence']:.1%})")
                        
                        # 4. Calculate risk parameters
                        logger.info("Step 4: Calculating risk parameters...")
                        stop_loss = risk_manager.calculate_stop_loss(
                            signal['entry_price'],
                            signal['action'],
                            order_blocks,
                            {}
                        )
                        take_profit = risk_manager.calculate_take_profit(
                            signal['entry_price'],
                            stop_loss,
                            signal['action']
                        )
                        
                        logger.info(f"✓ Stop Loss: ${stop_loss:.2f}")
                        logger.info(f"✓ Take Profit: ${take_profit:.2f}")
                        
                        # 5. Execute paper trade
                        logger.info("Step 5: Executing paper trade...")
                        
                        # Calculate position size (1% of balance)
                        account = paper_engine.get_account_summary()
                        position_size = (account['balance'] * 0.01) / signal['entry_price']
                        
                        # Execute
                        trade = paper_engine.execute_order(
                            symbol="BTC/USDT",
                            side=signal['action'],
                            size=position_size,
                            price=signal['entry_price'],
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            reason=f"SMC {signal.get('pattern_type', 'pattern')} detected"
                        )
                        
                        if trade:
                            logger.info(f"✅ PAPER TRADE EXECUTED!")
                            logger.info(f"   Trade ID: {trade.id}")
                            logger.info(f"   Symbol: {trade.symbol}")
                            logger.info(f"   Side: {trade.side}")
                            logger.info(f"   Size: {trade.size:.4f}")
                            logger.info(f"   Entry: ${trade.entry_price:.2f}")
                            logger.info(f"   Stop Loss: ${trade.stop_loss:.2f if trade.stop_loss else 'None'}")
                            logger.info(f"   Take Profit: ${trade.take_profit:.2f if trade.take_profit else 'None'}")
                        else:
                            logger.warning("⚠️ Paper trade rejected by engine")
                    else:
                        if signal:
                            logger.info(f"→ Signal confidence too low ({signal.get('confidence', 0):.1%} < 70%)")
                        else:
                            logger.info("→ No trading signal generated")
                
                # 6. Update open positions
                if paper_engine.positions:
                    logger.info(f"Step 6: Updating {len(paper_engine.positions)} open position(s)...")
                    
                    # Get live prices
                    live_prices = {}
                    for symbol in paper_engine.positions.keys():
                        price_data = await data_client.get_latest_ohlcv_data(symbol, "1h", limit=1)
                        if price_data is not None and not price_data.empty:
                            live_prices[symbol] = price_data['close'].iloc[-1]
                    
                    # Update positions (checks SL/TP)
                    paper_engine.update_positions(live_prices)
                    
                    # Log position status
                    for symbol, position in paper_engine.positions.items():
                        pnl = position.unrealized_pnl
                        pnl_pct = position.unrealized_pnl_percent
                        logger.info(
                            f"  Position {symbol}: "
                            f"${pnl:+.2f} ({pnl_pct:+.2f}%)"
                        )
                
                # 7. Log account summary
                account = paper_engine.get_account_summary()
                perf = paper_engine.get_performance_metrics()
                logger.info("")
                logger.info(f"💼 Account Summary:")
                logger.info(f"   Balance: ${account['balance']:.2f}")
                logger.info(f"   Equity: ${account['equity']:.2f}")
                logger.info(f"   Unrealized P&L: ${account.get('unrealized_pnl', 0):+.2f}")
                logger.info(f"   Open Positions: {len(paper_engine.positions)}/{paper_engine.max_positions}")
                logger.info(f"   Total Trades: {perf.get('total_trades', 0)}")
                logger.info(f"   Win Rate: {perf.get('win_rate', 0):.1f}%")
                logger.info("")
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"❌ Error in trading cycle: {str(e)}", exc_info=True)
            
            # Wait for next cycle
            logger.info(f"Waiting 60 seconds for next cycle...")
            logger.info("")
            
            for i in range(60):
                if shutdown_flag:
                    break
                await asyncio.sleep(1)
        
        logger.info("Shutting down gracefully...")
        
        # Stop FastAPI server
        if 'server_task' in locals():
            logger.info("Stopping FastAPI server...")
            server.should_exit = True
            try:
                await asyncio.wait_for(server_task, timeout=5.0)
            except asyncio.TimeoutError:
                server_task.cancel()
        
        # Close data client
        await data_client.close()
        
        # Close any open positions
        if paper_engine.positions:
            logger.info("Closing all open positions...")
            live_prices = {}
            for symbol in paper_engine.positions.keys():
                price_data = await data_client.get_latest_ohlcv_data(symbol, "1h", limit=1)
                if price_data is not None and not price_data.empty:
                    live_prices[symbol] = price_data['close'].iloc[-1]
            
            paper_engine.close_all_positions(live_prices, "Shutdown")
        
        # Final summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 60)
        perf = paper_engine.get_performance_metrics()
        logger.info(f"Total Trades: {perf['total_trades']}")
        logger.info(f"Winning Trades: {perf['winning_trades']}")
        logger.info(f"Losing Trades: {perf['losing_trades']}")
        logger.info(f"Win Rate: {perf['win_rate']:.1f}%")
        logger.info(f"Total P&L: ${perf['total_pnl']:+.2f}")
        logger.info(f"Profit Factor: {perf['profit_factor']:.2f}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nShutdown complete.")
        sys.exit(0)

