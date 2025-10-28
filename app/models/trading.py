# app/models/trading.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class TradingBot(Base):
    __tablename__ = "trading_bots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Bot configuration - EXISTING FIELDS
    status = Column(String, default="active")  # active, paused, stopped
    strategy = Column(String, nullable=True)
    amount_cents = Column(BigInteger, nullable=True)  # Existing field in cents
    
    # Bot configuration - NEW FIELDS
    currency_pair = Column(String, default="BTC-USDT")
    leverage = Column(Integer, default=1)
    
    # Financial data - EXISTING FIELDS
    current_profit_cents = Column(BigInteger, default=0)  # Existing field
    total_profit_cents = Column(BigInteger, default=0)    # Existing field
    
    # Financial data - NEW FIELDS
    initial_amount = Column(Float, nullable=True)  # In dollars
    current_balance = Column(Float, default=0.0)   # In dollars
    profit_loss = Column(Float, default=0.0)       # In dollars
    profit_loss_percentage = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships - FIXED: Changed 'trading_bots' to 'trades'
    user = relationship("User", back_populates="trading_bots")
    trades = relationship("Trade", back_populates="bot", cascade="all, delete-orphan")  # FIXED THIS LINE
    
    # Property for backward compatibility
    @property
    def amount(self):
        return self.initial_amount if self.initial_amount is not None else (self.amount_cents / 100.0 if self.amount_cents else 0.0)

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("trading_bots.id"), nullable=False)
    
    # Trade details - EXISTING FIELDS
    amount_cents = Column(BigInteger, nullable=True)  # Existing field
    profit_cents = Column(BigInteger, nullable=True)  # Existing field
    status = Column(String, nullable=True)            # Existing field
    
    # Trade details - NEW FIELDS
    type = Column(String, default="buy")  # buy, sell
    amount = Column(Float, nullable=True)  # In dollars
    price = Column(Float, nullable=True)   # Execution price
    currency_pair = Column(String, default="BTC-USDT")
    profit_loss = Column(Float, default=0.0)  # In dollars
    
    # Timestamps
    executed_at = Column(DateTime, server_default=func.now())  # Existing field
    timestamp = Column(DateTime, server_default=func.now())   # New field (alias)
    
    # Relationships - This is correct
    bot = relationship("TradingBot", back_populates="trades")
    
    # Property for backward compatibility
    @property
    def executed_price(self):
        return self.price if self.price is not None else 0.0