# app/api/admin/kyc.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.db import get_db
from app.models.user import User
from app.core.security import get_current_admin_user

router = APIRouter(prefix="/api/v1/admin/kyc", tags=["admin-kyc"])

class KYCReviewRequest(BaseModel):
    user_id: int
    status: str  # verified, rejected
    rejection_reason: Optional[str] = None

class KYCUserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    kyc_status: str
    kyc_submitted_at: Optional[str]
    date_of_birth: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    documents: dict

@router.get("/pending", response_model=List[KYCUserResponse])
def get_pending_kyc_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get pending KYC applications for admin review"""
    
    offset = (page - 1) * page_size
    
    pending_users = db.query(User).filter(
        User.kyc_status == "submitted"
    ).offset(offset).limit(page_size).all()
    
    response = []
    for user in pending_users:
        response.append({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "kyc_status": user.kyc_status,
            "kyc_submitted_at": user.kyc_submitted_at.isoformat() if user.kyc_submitted_at else None,
            "date_of_birth": user.date_of_birth.date().isoformat() if user.date_of_birth else None,
            "address": user.address,
            "city": user.city,
            "country": user.country,
            "documents": {
                "id_front": user.id_document_front,
                "id_back": user.id_document_back,
                "proof_of_address": user.proof_of_address,
                "selfie": user.selfie_photo
            }
        })
    
    return response

@router.post("/review")
def review_kyc_application(
    review_data: KYCReviewRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Admin review of KYC application"""
    
    user = db.query(User).filter(User.id == review_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status != "submitted":
        raise HTTPException(status_code=400, detail="User KYC is not in submitted status")
    
    if review_data.status == "verified":
        user.kyc_status = "verified"
        user.kyc_verified_at = datetime.now()
        user.kyc_rejection_reason = None
        message = "KYC application approved"
        
        print(f"✅ KYC approved for user: {user.email} by admin: {current_admin.email}")
        
    elif review_data.status == "rejected":
        user.kyc_status = "rejected"
        user.kyc_rejection_reason = review_data.rejection_reason
        message = f"KYC application rejected: {review_data.rejection_reason}"
        
        print(f"❌ KYC rejected for user: {user.email} by admin: {current_admin.email}")
    else:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    db.commit()
    
    return {"message": message, "new_status": user.kyc_status}

@router.get("/users/{user_id}/kyc-status")
def get_user_kyc_status(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get KYC status for a specific user"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    documents = {
        "id_front": bool(user.id_document_front),
        "id_back": bool(user.id_document_back),
        "proof_of_address": bool(user.proof_of_address),
        "selfie": bool(user.selfie_photo)
    }
    
    return {
        "user_id": user.id,
        "email": user.email,
        "kyc_status": user.kyc_status,
        "kyc_submitted_at": user.kyc_submitted_at.isoformat() if user.kyc_submitted_at else None,
        "kyc_verified_at": user.kyc_verified_at.isoformat() if user.kyc_verified_at else None,
        "kyc_rejection_reason": user.kyc_rejection_reason,
        "documents": documents,
        "personal_info_complete": all([
            user.date_of_birth, user.address, user.city, 
            user.country, user.postal_code
        ])
    }