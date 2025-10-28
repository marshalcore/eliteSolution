# app/models/card.py - UPDATED
from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Card(Base):
    __tablename__ = "cards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Card details
    card_number = Column(String, unique=True, index=True)
    card_holder_name = Column(String, nullable=False)
    expiry_date = Column(String, nullable=False)
    cvv = Column(String, nullable=False)
    
    # Marqeta integration
    marqeta_card_token = Column(String, unique=True)  # Marqeta's card token
    marqeta_user_token = Column(String)  # Marqeta's user token
    card_program = Column(String, default="elite_premium")
    
    # Card status and balance
    balance_cents = Column(BigInteger, default=0)
    currency = Column(String, default="USD")
    status = Column(String, default="active")  # active, suspended, terminated
    card_type = Column(String, default="virtual")  # virtual, physical
    
    # Vault linking
    linked_to_vault = Column(Boolean, default=True)
    vault_funding_enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="cards")