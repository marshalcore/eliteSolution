# app/api/admin.py - COMPLETE UPDATED VERSION
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from app.db import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.schemas.admin import AdminCreate, AdminLogin
from app.schemas.otp import OTPVerify
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user_db,
)
from app.services.email_validator import validate_email_address

# ----------------------------
#  AUTH HELPERS
# ----------------------------
def get_current_admin(current_user: User = Depends(get_current_user_db)):
    """Ensure the logged-in user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized as admin")
    return current_user

def log_admin_action(admin_id: int, action: str, details: Dict = None, db: Session = None):
    """Log admin actions for audit trail"""
    audit_log = AuditLog(
        actor_id=admin_id,
        action=action,
        details=details or {}
    )
    if db:
        db.add(audit_log)
        db.commit()

# ----------------------------
#  ROUTER SETUP
# ----------------------------
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
)

# ==================== NEW REQUEST/RESPONSE MODELS ====================

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AnalyticsResponse(BaseModel):
    total_users: int
    total_transactions: int
    total_volume: float
    pending_kyc: int
    new_users_today: int
    revenue_today: float
    user_growth: List[Dict[str, Any]]
    transaction_volume: List[Dict[str, Any]]

class BulkActionRequest(BaseModel):
    user_ids: List[int]
    action: str  # suspend, activate, delete
    reason: Optional[str] = None

class BulkActionResponse(BaseModel):
    message: str
    processed: int
    failed: int
    details: Dict[str, Any]

class AdminPermissionRequest(BaseModel):
    email: EmailStr
    permissions: List[str]  # user_management, kyc_review, transactions, analytics

class SystemHealthResponse(BaseModel):
    status: str
    database: bool
    api_services: Dict[str, bool]
    performance_metrics: Dict[str, float]
    last_updated: datetime

class KYCAdditionalDocsRequest(BaseModel):
    user_id: int
    required_documents: List[str]
    reason: str
    deadline_days: int = 7

class UserExportRequest(BaseModel):
    export_type: str  # all, active, pending_kyc, suspended
    format: str = "json"  # json, csv

class IPRestrictionRequest(BaseModel):
    admin_id: int
    allowed_ips: List[str]
    enable_restriction: bool

# ==================== PUBLIC ROUTES (NO TOKEN REQUIRED) ====================

@router.post("/register")
def admin_register(data: AdminCreate, db: Session = Depends(get_db)):
    """Register a new admin with enhanced validation"""
    # ✅ Validate email before creating admin
    if not validate_email_address(data.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")

    hashed_pw = get_password_hash(data.password)
    admin = User(
        email=data.email,
        hashed_password=hashed_pw,
        first_name=data.first_name or "Admin",
        last_name=data.last_name or "Account",
        is_admin=True,
        is_verified=False,
        kyc_status="pending",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    from app.models.otp import OTPPurpose
    from app.services.otp_service import generate_otp, send_otp_email

    otp_code = generate_otp(admin.id, OTPPurpose.ADMIN_REGISTRATION, db)

    html_content = f"""
    <html>
      <body>
        <h2>Admin Verification</h2>
        <p>Welcome, Admin!</p>
        <p>Your OTP code is <b>{otp_code}</b></p>
      </body>
    </html>
    """
    send_otp_email(admin.email, otp_code, "admin registration", html_content=html_content)

    # Log admin registration
    log_admin_action(admin.id, "admin_registered", {"email": admin.email}, db)

    return {"message": "Admin registered. Please verify with OTP."}

@router.post("/verify-registration")
def verify_admin_registration(data: OTPVerify, db: Session = Depends(get_db)):
    from app.models.otp import OTPPurpose
    from app.services.otp_service import verify_otp

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized as admin")

    if not verify_otp(user.id, data.code, OTPPurpose.ADMIN_REGISTRATION, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user.is_verified = True
    db.commit()

    # Log admin verification
    log_admin_action(user.id, "admin_verified", {"email": user.email}, db)

    return {"message": "Admin registration verified successfully"}

@router.post("/login")
def admin_login(data: AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="This account is not an admin")

    from app.models.otp import OTPPurpose
    from app.services.otp_service import generate_otp, send_otp_email

    otp_code = generate_otp(user.id, OTPPurpose.ADMIN_LOGIN, db)

    html_content = f"""
    <html>
      <body>
        <h2>Admin Login Verification</h2>
        <p>Hi {user.first_name},</p>
        <p>Your OTP code is <b>{otp_code}</b></p>
      </body>
    </html>
    """
    send_otp_email(user.email, otp_code, "admin login", html_content=html_content)

    # Log admin login attempt
    log_admin_action(user.id, "admin_login_attempt", {"email": user.email}, db)

    return {"message": "Admin OTP sent to email. Verify to complete login."}

@router.post("/verify-login")
def verify_admin_login(data: OTPVerify, db: Session = Depends(get_db)):
    from app.models.otp import OTPPurpose
    from app.services.otp_service import verify_otp

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized as admin")

    if not verify_otp(user.id, data.code, OTPPurpose.ADMIN_LOGIN, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    token = create_access_token({"sub": user.email, "is_admin": True})
    
    # Log successful admin login
    log_admin_action(user.id, "admin_login_success", {"email": user.email}, db)

    return {"access_token": token, "token_type": "bearer"}

# ==================== ADVANCED ADMIN FEATURES ====================

@router.get("/analytics/dashboard", response_model=AnalyticsResponse)
def get_admin_analytics(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive admin analytics dashboard"""
    
    # Total users count
    total_users = db.query(User).count()
    
    # Total transactions count and volume
    total_transactions = db.query(Transaction).count()
    total_volume_result = db.query(func.sum(Transaction.amount_cents)).scalar() or 0
    total_volume = total_volume_result / 100  # Convert cents to dollars
    
    # Pending KYC applications
    pending_kyc = db.query(User).filter(User.kyc_status == "submitted").count()
    
    # New users today
    today = datetime.now().date()
    new_users_today = db.query(User).filter(
        func.date(User.created_at) == today
    ).count()
    
    # Revenue today (simplified - in real scenario, calculate from fees)
    revenue_today = 0.0  # Placeholder
    
    # User growth (last 30 days)
    user_growth = []
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        count = db.query(User).filter(
            func.date(User.created_at) == date
        ).count()
        user_growth.append({
            "date": date.isoformat(),
            "count": count
        })
    
    # Transaction volume (last 30 days)
    transaction_volume = []
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        volume = db.query(func.sum(Transaction.amount_cents)).filter(
            func.date(Transaction.created_at) == date
        ).scalar() or 0
        transaction_volume.append({
            "date": date.isoformat(),
            "volume": volume / 100
        })
    
    # Log analytics access
    log_admin_action(current_admin.id, "analytics_accessed", {}, db)
    
    return {
        "total_users": total_users,
        "total_transactions": total_transactions,
        "total_volume": total_volume,
        "pending_kyc": pending_kyc,
        "new_users_today": new_users_today,
        "revenue_today": revenue_today,
        "user_growth": user_growth,
        "transaction_volume": transaction_volume
    }

@router.post("/users/bulk-actions", response_model=BulkActionResponse)
def bulk_user_actions(
    request: BulkActionRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Perform bulk actions on users"""
    
    processed = 0
    failed = 0
    details = {}
    
    for user_id in request.user_ids:
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                failed += 1
                details[str(user_id)] = "User not found"
                continue
            
            if request.action == "suspend":
                user.is_active = False
                details[str(user_id)] = "Suspended"
            elif request.action == "activate":
                user.is_active = True
                details[str(user_id)] = "Activated"
            elif request.action == "delete":
                db.delete(user)
                details[str(user_id)] = "Deleted"
            else:
                failed += 1
                details[str(user_id)] = "Invalid action"
                continue
            
            processed += 1
            
        except Exception as e:
            failed += 1
            details[str(user_id)] = f"Error: {str(e)}"
    
    db.commit()
    
    # Log bulk action
    log_admin_action(
        current_admin.id, 
        "bulk_user_action", 
        {
            "action": request.action,
            "processed": processed,
            "failed": failed,
            "reason": request.reason
        }, 
        db
    )
    
    return {
        "message": f"Bulk action completed: {processed} processed, {failed} failed",
        "processed": processed,
        "failed": failed,
        "details": details
    }

@router.get("/system/health", response_model=SystemHealthResponse)
def get_system_health(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get system health and performance metrics"""
    
    # Check database connection
    try:
        db.execute("SELECT 1")
        database_healthy = True
    except Exception:
        database_healthy = False
    
    # Check external services (simplified - in real scenario, ping actual services)
    api_services = {
        "payment_gateway": True,
        "email_service": True,
        "sms_service": True,
        "kyc_service": True
    }
    
    # Performance metrics (simplified)
    performance_metrics = {
        "response_time_ms": 45.2,
        "database_latency_ms": 12.1,
        "active_connections": 8,
        "memory_usage_percent": 65.3
    }
    
    status = "healthy" if database_healthy and all(api_services.values()) else "degraded"
    
    return {
        "status": status,
        "database": database_healthy,
        "api_services": api_services,
        "performance_metrics": performance_metrics,
        "last_updated": datetime.now()
    }

@router.post("/kyc/request-additional-docs")
def request_additional_kyc_docs(
    request: KYCAdditionalDocsRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Request additional documents from user for KYC"""
    
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status != "submitted":
        raise HTTPException(status_code=400, detail="User KYC is not in submitted status")
    
    # In a real implementation, you would:
    # 1. Send notification to user
    # 2. Update KYC status to indicate additional docs needed
    # 3. Set deadline
    
    deadline_date = datetime.now() + timedelta(days=request.deadline_days)
    
    # Log the request
    log_admin_action(
        current_admin.id,
        "kyc_additional_docs_requested",
        {
            "user_id": request.user_id,
            "required_documents": request.required_documents,
            "reason": request.reason,
            "deadline": deadline_date.isoformat()
        },
        db
    )
    
    return {
        "message": f"Additional documents requested from user. Deadline: {deadline_date.strftime('%Y-%m-%d')}",
        "deadline": deadline_date.isoformat(),
        "required_documents": request.required_documents
    }

@router.get("/users/export")
def export_users_data(
    export_type: str = Query(..., description="Export type: all, active, pending_kyc, suspended"),
    format: str = Query("json", description="Export format: json, csv"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Export users data in various formats"""
    
    # Build query based on export type
    query = db.query(User)
    
    if export_type == "active":
        query = query.filter(User.is_active == True)
    elif export_type == "pending_kyc":
        query = query.filter(User.kyc_status == "submitted")
    elif export_type == "suspended":
        query = query.filter(User.is_active == False)
    # "all" returns all users
    
    users = query.all()
    
    # Prepare data for export
    export_data = []
    for user in users:
        user_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "kyc_status": user.kyc_status,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        export_data.append(user_data)
    
    # Log export action
    log_admin_action(
        current_admin.id,
        "users_data_exported",
        {
            "export_type": export_type,
            "format": format,
            "record_count": len(export_data)
        },
        db
    )
    
    if format == "csv":
        # Generate CSV (simplified - in real scenario, use proper CSV library)
        csv_content = "id,email,first_name,last_name,phone,kyc_status,is_active,created_at\n"
        for user in export_data:
            csv_content += f"{user['id']},{user['email']},{user['first_name']},{user['last_name']},{user['phone']},{user['kyc_status']},{user['is_active']},{user['created_at']}\n"
        
        return {
            "format": "csv",
            "data": csv_content,
            "filename": f"users_export_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    
    else:  # json
        return {
            "format": "json",
            "data": export_data,
            "filename": f"users_export_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }

@router.get("/audit-logs")
def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    actor_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get audit logs with filtering and pagination"""
    
    query = db.query(AuditLog)
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()
    
    # Format response
    log_data = []
    for log in logs:
        log_data.append({
            "id": log.id,
            "actor_id": log.actor_id,
            "action": log.action,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })
    
    return {
        "logs": log_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    }

# ==================== EXISTING PROTECTED ROUTES (ENHANCED) ====================

@router.post("/logout")
def admin_logout(current_admin: User = Depends(get_current_admin)):
    """Admin logout with enhanced logging"""
    log_admin_action(current_admin.id, "admin_logout", {})
    return {"message": "Admin logged out successfully"}

@router.delete("/user/{user_id}")
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete user with enhanced logging"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_email = user.email
    db.delete(user)
    db.commit()
    
    # Log user deletion
    log_admin_action(
        current_admin.id,
        "user_deleted",
        {
            "deleted_user_id": user_id,
            "deleted_user_email": user_email
        },
        db
    )
    
    return {"message": f"User {user_email} deleted"}

@router.get("/users")
def get_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kyc_status: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all users with enhanced filtering and pagination"""
    query = db.query(User)
    
    # Apply filters
    if kyc_status:
        query = query.filter(User.kyc_status == kyc_status)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Apply pagination
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()
    
    return users

@router.get("/transactions")
def get_transactions(
    status: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get transactions with enhanced filtering and pagination"""
    q = db.query(Transaction)
    
    if status:
        q = q.filter(Transaction.status == status)
    
    # Date filtering
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            q = q.filter(Transaction.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            q = q.filter(Transaction.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    # Apply pagination
    offset = (page - 1) * page_size
    transactions = q.order_by(desc(Transaction.created_at)).offset(offset).limit(page_size).all()
    
    return transactions

@router.post("/transactions/{txn_id}/approve")
def approve_transaction(
    txn_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Approve transaction with enhanced logging"""
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    old_status = txn.status
    txn.status = "approved"
    db.commit()
    
    # Log transaction approval
    log_admin_action(
        current_admin.id,
        "transaction_approved",
        {
            "transaction_id": txn_id,
            "old_status": old_status,
            "new_status": "approved"
        },
        db
    )
    
    return {"message": f"Transaction {txn.id} approved"}

@router.post("/transactions/{txn_id}/reject")
def reject_transaction(
    txn_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Reject transaction with enhanced logging"""
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    old_status = txn.status
    txn.status = "rejected"
    db.commit()
    
    # Log transaction rejection
    log_admin_action(
        current_admin.id,
        "transaction_rejected",
        {
            "transaction_id": txn_id,
            "old_status": old_status,
            "new_status": "rejected"
        },
        db
    )
    
    return {"message": f"Transaction {txn.id} rejected"}

@router.put("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    new_password: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Reset user password with enhanced logging"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_password_hash = user.hashed_password  # For logging (don't log actual password)
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # Log password reset
    log_admin_action(
        current_admin.id,
        "user_password_reset",
        {
            "user_id": user_id,
            "user_email": user.email
        },
        db
    )
    
    return {"message": f"Password reset for user {user.email}"}

@router.put("/users/{user_id}/update")
def update_user_details(
    user_id: int,
    email: str = None,
    phone: str = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update user details with enhanced logging"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = {}
    
    if email:
        # ✅ validate before updating
        if not validate_email_address(email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        changes["old_email"] = user.email
        changes["new_email"] = email
        user.email = email

    if phone:
        changes["old_phone"] = user.phone
        changes["new_phone"] = phone
        user.phone = phone

    db.commit()
    db.refresh(user)
    
    # Log user details update
    if changes:
        log_admin_action(
            current_admin.id,
            "user_details_updated",
            {
                "user_id": user_id,
                "changes": changes
            },
            db
        )
    
    return {"message": f"User {user.id} updated", "user": {"email": user.email, "phone": user.phone}}

@router.put("/users/{user_id}/suspend")
def suspend_user(
    user_id: int,
    reason: str = "Administrative action",
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Temporarily suspend a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is already suspended")
    
    user.is_active = False
    db.commit()
    
    # Log user suspension
    log_admin_action(
        current_admin.id,
        "user_suspended",
        {
            "user_id": user_id,
            "user_email": user.email,
            "reason": reason
        },
        db
    )
    
    return {"message": f"User {user.email} suspended", "reason": reason}

@router.put("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Activate a suspended user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_active:
        raise HTTPException(status_code=400, detail="User is already active")
    
    user.is_active = True
    db.commit()
    
    # Log user activation
    log_admin_action(
        current_admin.id,
        "user_activated",
        {
            "user_id": user_id,
            "user_email": user.email
        },
        db
    )
    
    return {"message": f"User {user.email} activated"}