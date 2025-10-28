# app/services/payment_router.py - COMPLETE NEW FILE
from typing import Union
from pydantic import BaseModel
from enum import Enum

class PaymentRoute(BaseModel):
    processor: str
    min_amount: float
    max_amount: float
    fee_percentage: float

class PaymentProcessor(Enum):
    OKX = "okx"
    TRUST_WALLET = "trust_wallet"

class OKXProcessor:
    def __init__(self):
        self.name = PaymentProcessor.OKX.value
        self.min_amount = 10.0
        self.max_amount = 9999.0
        self.fee_percentage = 0.02  # 2% fee

class TrustWalletProcessor:
    def __init__(self):
        self.name = PaymentProcessor.TRUST_WALLET.value
        self.min_amount = 10000.0
        self.max_amount = 1000000.0  # $1M max
        self.fee_percentage = 0.01  # 1% fee

class PaymentRouter:
    def route_payment(self, amount: float, currency: str = "USD") -> PaymentRoute:
        """
        Route payment based on amount thresholds
        $10 - $9,999: OKX Processor
        $10,000+: Trust Wallet Processor
        """
        if 10 <= amount <= 9999:
            processor = OKXProcessor()
        else:
            processor = TrustWalletProcessor()
        
        return PaymentRoute(
            processor=processor.name,
            min_amount=processor.min_amount,
            max_amount=processor.max_amount,
            fee_percentage=processor.fee_percentage
        )
    
    def can_process_amount(self, amount: float) -> bool:
        """Check if amount can be processed"""
        return amount >= 10.0

    def get_processing_fee(self, amount: float) -> float:
        """Calculate processing fee"""
        route = self.route_payment(amount)
        return amount * route.fee_percentage

    def get_net_amount(self, amount: float) -> float:
        """Calculate net amount after fees"""
        fee = self.get_processing_fee(amount)
        return amount - fee

    def validate_payment_route(self, amount: float, currency: str = "USD") -> dict:
        """Validate payment route and return details"""
        route = self.route_payment(amount, currency)
        fee = self.get_processing_fee(amount)
        net_amount = self.get_net_amount(amount)
        
        return {
            "processor": route.processor,
            "amount": amount,
            "currency": currency,
            "processing_fee": fee,
            "net_amount": net_amount,
            "fee_percentage": route.fee_percentage,
            "min_amount": route.min_amount,
            "max_amount": route.max_amount,
            "is_valid": route.min_amount <= amount <= route.max_amount
        }