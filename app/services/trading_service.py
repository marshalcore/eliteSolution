# app/services/trading_service.py - NEW FILE
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.trading import TradingBot, Trade
from app.models.account import Account
from app.models.transaction import Transaction
import random

class TradingService:
    def __init__(self):
        self.min_amount = settings.TRADING_MIN_AMOUNT
        self.profit_rates = settings.TRADING_PROFIT_RATES
    
    async def start_trading_bot(self, user_id: int, amount: float, strategy: str, db: Session):
        """Start automated trading bot for user"""
        
        # Validate minimum amount
        if amount < self.min_amount:
            raise ValueError(f"Minimum trading amount is ${self.min_amount}")
        
        # Check user has sufficient balance
        account = db.query(Account).filter(Account.user_id == user_id).first()
        if not account or account.balance_cents < (amount * 100):
            raise ValueError("Insufficient balance for trading")
        
        # Deduct trading amount from balance
        account.balance_cents -= int(amount * 100)
        
        # Create trading bot record
        trading_bot = TradingBot(
            user_id=user_id,
            strategy=strategy,
            amount_cents=int(amount * 100),
            status="active"
        )
        db.add(trading_bot)
        db.commit()
        db.refresh(trading_bot)
        
        # Start background trading simulation
        asyncio.create_task(self.simulate_trading(trading_bot.id, db))
        
        return {
            "bot_id": trading_bot.id,
            "status": "active",
            "investment": amount,
            "strategy": strategy,
            "estimated_profit_rate": f"{self.profit_rates[strategy] * 100}% monthly"
        }
    
    async def simulate_trading(self, bot_id: int, db: Session):
        """Simulate trading activity (replace with real trading logic)"""
        while True:
            # Wait for random interval between trades (1-6 hours)
            await asyncio.sleep(random.randint(3600, 21600))
            
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot or bot.status != "active":
                break
            
            # Generate random profit/loss based on strategy
            base_rate = self.profit_rates[bot.strategy]
            volatility = 0.02  # 2% volatility
            
            # Random profit between -volatility and base_rate + volatility
            profit_rate = random.uniform(-volatility, base_rate + volatility)
            profit_cents = int(bot.amount_cents * profit_rate)
            
            # Create trade record
            trade = Trade(
                bot_id=bot_id,
                amount_cents=bot.amount_cents,
                profit_cents=profit_cents,
                status="completed"
            )
            
            # Update bot profit
            bot.current_profit_cents += profit_cents
            bot.total_profit_cents += profit_cents
            
            # If profit is positive, add to user's account and vault
            if profit_cents > 0:
                account = db.query(Account).filter(Account.user_id == bot.user_id).first()
                if account:
                    account.balance_cents += profit_cents
                    
                    # Also add to vault (simplified - in real scenario, transfer to OKX)
                    print(f"✅ Trading profit: ${profit_cents/100:.2f} added to user {bot.user_id}")
            
            db.add(trade)
            db.commit()
            
            print(f"🔄 Trade executed for bot {bot_id}: ${profit_cents/100:.2f}")
    
    async def stop_trading_bot(self, bot_id: int, db: Session):
        """Stop trading bot and return funds"""
        bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
        if bot:
            bot.status = "stopped"
            
            # Return remaining investment to user account
            account = db.query(Account).filter(Account.user_id == bot.user_id).first()
            if account:
                account.balance_cents += bot.amount_cents
            
            db.commit()
            
            return {
                "message": "Trading bot stopped",
                "total_profit": bot.total_profit_cents / 100,
                "investment_returned": bot.amount_cents / 100
            }