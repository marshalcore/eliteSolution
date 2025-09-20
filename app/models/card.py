# app/models/card.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    card_number = Column(String, unique=True, index=True, nullable=False)
    card_holder_name = Column(String, nullable=False)  # ✅ Added card holder name
    expiry_date = Column(String, nullable=False)
    cvv = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="cards")