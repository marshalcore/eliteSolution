# app/api/trading.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import json

from app.db import get_db
from app.models.user import User
from app.models.trading import Trade, TradingBot
from app.core.security import get_current_user
from app.services.trading_service import TradingService

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])

# ----------------------------
# REQUEST/RESPONSE MODELS
# ----------------------------

class StartTradingRequest(BaseModel):
    amount: float
    strategy: str  # conservative, moderate, aggressive
    currency_pair: str = "BTC-USDT"
    leverage: Optional[int] = 1

class StopTradingRequest(BaseModel):
    bot_id: int

class TradingHistoryRequest(BaseModel):
    page: int = 1
    page_size: int = 20
    status: Optional[str] = None

class TradingBotResponse(BaseModel):
    id: int
    user_id: int
    status: str
    strategy: str
    initial_amount: float
    current_balance: float
    profit_loss: float
    profit_loss_percentage: float
    currency_pair: str
    leverage: int
    created_at: str
    updated_at: str

class TradeResponse(BaseModel):
    id: int
    bot_id: int
    type: str  # buy, sell
    amount: float
    price: float
    currency_pair: str
    profit_loss: float
    timestamp: str

class TradingAnalyticsResponse(BaseModel):
    total_profit_loss: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    success_rate: float
    average_trade_amount: float
    best_trade: Optional[TradeResponse]
    worst_trade: Optional[TradeResponse]

class MarketDataResponse(BaseModel):
    symbol: str
    price: float
    change_24h: float
    change_percentage_24h: float
    volume_24h: float
    high_24h: float
    low_24h: float

# ----------------------------
# TRADING ENDPOINTS
# ----------------------------

@router.post("/start", response_model=TradingBotResponse)
async def start_trading_bot(
    request: StartTradingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start automated trading bot"""
    
    # Check KYC verification
    if current_user.kyc_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,  # ✅ FIXED: Added status import
            detail="KYC verification required for trading"
        )
    
    trading_service = TradingService()
    
    try:
        # Start trading bot
        bot = await trading_service.start_trading_bot(
            user_id=current_user.id,
            amount=request.amount,
            strategy=request.strategy,
            currency_pair=request.currency_pair,
            leverage=request.leverage,
            db=db
        )
        
        # Start background trading task
        background_tasks.add_task(
            trading_service.run_trading_strategy,
            bot.id,
            db
        )
        
        return {
            "id": bot.id,
            "user_id": bot.user_id,
            "status": bot.status,
            "strategy": bot.strategy,
            "initial_amount": float(bot.initial_amount),
            "current_balance": float(bot.current_balance),
            "profit_loss": float(bot.profit_loss),
            "profit_loss_percentage": float(bot.profit_loss_percentage),
            "currency_pair": bot.currency_pair,
            "leverage": bot.leverage,
            "created_at": bot.created_at.isoformat(),
            "updated_at": bot.updated_at.isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start trading: {str(e)}")

@router.post("/stop")
async def stop_trading_bot(
    request: StopTradingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop trading bot"""
    
    trading_service = TradingService()
    
    try:
        success = await trading_service.stop_trading_bot(
            bot_id=request.bot_id,
            user_id=current_user.id,
            db=db
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Trading bot not found")
        
        return {"message": "Trading bot stopped successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop trading: {str(e)}")

@router.get("/bots", response_model=List[TradingBotResponse])
def get_trading_bots(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's trading bots"""
    
    query = db.query(TradingBot).filter(TradingBot.user_id == current_user.id)
    
    if status:
        query = query.filter(TradingBot.status == status)
    
    bots = query.order_by(TradingBot.created_at.desc()).all()
    
    return [
        {
            "id": bot.id,
            "user_id": bot.user_id,
            "status": bot.status,
            "strategy": bot.strategy,
            "initial_amount": float(bot.initial_amount),
            "current_balance": float(bot.current_balance),
            "profit_loss": float(bot.profit_loss),
            "profit_loss_percentage": float(bot.profit_loss_percentage),
            "currency_pair": bot.currency_pair,
            "leverage": bot.leverage,
            "created_at": bot.created_at.isoformat(),
            "updated_at": bot.updated_at.isoformat()
        }
        for bot in bots
    ]

@router.get("/history", response_model=List[TradeResponse])
def get_trading_history(
    page: int = 1,
    page_size: int = 20,
    bot_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trading history"""
    
    query = db.query(Trade).join(TradingBot).filter(TradingBot.user_id == current_user.id)
    
    if bot_id:
        query = query.filter(Trade.bot_id == bot_id)
    
    trades = query.order_by(Trade.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return [
        {
            "id": trade.id,
            "bot_id": trade.bot_id,
            "type": trade.type,
            "amount": float(trade.amount),
            "price": float(trade.price),
            "currency_pair": trade.currency_pair,
            "profit_loss": float(trade.profit_loss),
            "timestamp": trade.timestamp.isoformat()
        }
        for trade in trades
    ]

@router.get("/analytics", response_model=TradingAnalyticsResponse)
def get_trading_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trading analytics and performance metrics"""
    
    trading_service = TradingService()
    
    try:
        analytics = trading_service.get_trading_analytics(current_user.id, db)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@router.get("/market-data", response_model=List[MarketDataResponse])
async def get_market_data(
    symbols: str = "BTC-USDT,ETH-USDT,ADA-USDT,XRP-USDT",
    current_user: User = Depends(get_current_user)
):
    """Get real-time market data for trading"""
    
    trading_service = TradingService()
    
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        market_data = await trading_service.get_market_data(symbol_list)
        return market_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get market data: {str(e)}")

@router.get("/supported-pairs")
async def get_supported_trading_pairs(current_user: User = Depends(get_current_user)):
    """Get supported trading pairs"""
    
    trading_service = TradingService()
    pairs = await trading_service.get_supported_trading_pairs()
    
    return {"supported_pairs": pairs}

# ----------------------------
# WEB SOCKET FOR REAL-TIME TRADING DATA
# ----------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket)
    trading_service = TradingService()
    
    try:
        while True:
            # Send real-time trading updates every 5 seconds
            bots = trading_service.get_user_bots(user_id)
            market_data = await trading_service.get_market_data(["BTC-USDT", "ETH-USDT"])
            
            update_data = {
                "type": "trading_update",
                "bots": bots,
                "market_data": market_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send_text(json.dumps(update_data))
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)