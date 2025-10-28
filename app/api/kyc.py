# app/api/kyc.py - ADD THIS FILE
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os
import shutil
import uuid

from app.db import get_db
from app.models.user import User
from app.core.security import get_current_user
from app.services.kyc_service import kyc_service

router = APIRouter(prefix="/api/v1/auth", tags=["kyc"])

@router.get("/kyc-status")
def get_kyc_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's KYC status"""
    documents = {
        "id_front": bool(current_user.id_document_front),
        "id_back": bool(current_user.id_document_back),
        "proof_of_address": bool(current_user.proof_of_address),
        "selfie": bool(current_user.selfie_photo)
    }
    
    personal_info_complete = all([
        current_user.date_of_birth,
        current_user.address,
        current_user.city,
        current_user.country,
        current_user.postal_code
    ])
    
    return {
        "kyc_status": current_user.kyc_status,
        "can_transact": current_user.kyc_status == "verified",
        "kyc_submitted_at": current_user.kyc_submitted_at.isoformat() if current_user.kyc_submitted_at else None,
        "kyc_verified_at": current_user.kyc_verified_at.isoformat() if current_user.kyc_verified_at else None,
        "kyc_rejection_reason": current_user.kyc_rejection_reason,
        "documents": documents,
        "personal_info_complete": personal_info_complete
    }

@router.post("/upload-kyc-document")
async def upload_kyc_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload KYC document"""
    
    # Validate document type
    allowed_types = ['id_front', 'id_back', 'proof_of_address', 'selfie']
    if document_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid document type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Validate document
    validation_result = await kyc_service.validate_kyc_document(file, document_type)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename.lower())[1]
    unique_id = uuid.uuid4().hex[:8]
    filename = f"user_{current_user.id}_{document_type}_{unique_id}_{int(datetime.now().timestamp())}{file_extension}"
    
    # Save file
    KYC_DOCUMENTS_DIR = "static/kyc_documents"
    os.makedirs(KYC_DOCUMENTS_DIR, exist_ok=True)
    file_path = os.path.join(KYC_DOCUMENTS_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_url = f"/static/kyc_documents/{filename}"
    
    # Update user's document in database
    if document_type == 'id_front':
        current_user.id_document_front = file_url
    elif document_type == 'id_back':
        current_user.id_document_back = file_url
    elif document_type == 'proof_of_address':
        current_user.proof_of_address = file_url
    elif document_type == 'selfie':
        current_user.selfie_photo = file_url
    
    db.commit()
    
    # Check missing documents
    required_docs = ['id_front', 'proof_of_address', 'selfie']
    doc_status = {
        'id_front': bool(current_user.id_document_front),
        'proof_of_address': bool(current_user.proof_of_address),
        'selfie': bool(current_user.selfie_photo)
    }
    missing_docs = [doc for doc in required_docs if not doc_status.get(doc)]
    
    return {
        "message": f"{document_type.replace('_', ' ').title()} uploaded successfully",
        "kyc_status": current_user.kyc_status,
        "can_transact": current_user.kyc_status == "verified",
        "missing_documents": missing_docs if missing_docs else None
    }

@router.post("/submit-kyc")
async def submit_kyc_application(
    date_of_birth: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    country: str = Form(...),
    postal_code: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit KYC application for verification"""
    
    # Check if user is already verified
    if current_user.kyc_status == "verified":
        raise HTTPException(
            status_code=400,
            detail="Your KYC is already verified"
        )
    
    # Check if user is already submitted
    if current_user.kyc_status == "submitted":
        raise HTTPException(
            status_code=400,
            detail="Your KYC application is already under review"
        )
    
    # Validate personal information
    kyc_data = {
        "date_of_birth": date_of_birth,
        "address": address,
        "city": city,
        "state": state,
        "country": country,
        "postal_code": postal_code
    }
    
    kyc_service.validate_personal_info(kyc_data)
    
    # Check if all required documents are uploaded
    required_docs = ['id_front', 'proof_of_address', 'selfie']
    doc_status = {
        'id_front': bool(current_user.id_document_front),
        'proof_of_address': bool(current_user.proof_of_address),
        'selfie': bool(current_user.selfie_photo)
    }
    
    missing_docs = [doc for doc in required_docs if not doc_status.get(doc)]
    if missing_docs:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required documents",
                "missing_documents": missing_docs
            }
        )
    
    # Update user's KYC information
    try:
        current_user.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    current_user.address = address
    current_user.city = city
    current_user.state = state
    current_user.country = country
    current_user.postal_code = postal_code
    
    # Update KYC status
    current_user.kyc_status = "submitted"
    current_user.kyc_submitted_at = datetime.now()
    current_user.kyc_rejection_reason = None  # Clear any previous rejection
    
    db.commit()
    
    print(f"✅ KYC application submitted for user: {current_user.email}")
    
    return {
        "message": "KYC application submitted successfully. Your documents are under review. This may take 1-2 business days.",
        "kyc_status": current_user.kyc_status,
        "can_transact": current_user.kyc_status == "verified"
    }

@router.get("/kyc-documents-status")
def get_kyc_documents_status(
    current_user: User = Depends(get_current_user)
):
    """Get status of user's KYC documents"""
    return {
        "id_front": bool(current_user.id_document_front),
        "id_back": bool(current_user.id_document_back),
        "proof_of_address": bool(current_user.proof_of_address),
        "selfie": bool(current_user.selfie_photo)
    }