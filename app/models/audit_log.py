from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from app.db.base_class import Base

class AuditLog(Base):  # ✅ Make sure it's AuditLog (not Audit_log)
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())