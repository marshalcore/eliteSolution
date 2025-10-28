# app/services/kyc_service.py
import os
import re
from datetime import datetime, date
from fastapi import HTTPException, UploadFile
from typing import Dict, List

class KYCService:
    def __init__(self):
        self.allowed_image_types = {'image/jpeg', 'image/png', 'image/jpg'}
        self.allowed_pdf_types = {'application/pdf'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        
    async def validate_kyc_document(self, file: UploadFile, document_type: str) -> Dict:
        """Validate KYC document with enhanced security checks"""
        
        # Read file contents for validation
        file_contents = await file.read()
        file_size = len(file_contents)
        
        # Reset file pointer
        await file.seek(0)
        
        # Check file size
        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {self.max_file_size // (1024*1024)}MB limit"
            )
        
        # Check file extension
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
        file_extension = os.path.splitext(file.filename.lower())[1]
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only JPG, JPEG, PNG, and PDF are allowed."
            )
        
        # Basic MIME type validation
        if file_extension in ['.jpg', '.jpeg', '.png']:
            if not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Invalid image file")
        elif file_extension == '.pdf':
            if file.content_type != 'application/pdf':
                raise HTTPException(status_code=400, detail="Invalid PDF file")
        
        return {
            "is_valid": True,
            "file_size": file_size,
            "file_extension": file_extension
        }
    
    def validate_personal_info(self, kyc_data: Dict) -> Dict:
        """Validate personal information for KYC compliance"""
        errors = []
        
        # Age validation (must be at least 18 years old)
        try:
            dob = datetime.strptime(kyc_data['date_of_birth'], "%Y-%m-%d").date()
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 18:
                errors.append("You must be at least 18 years old to register")
            elif age > 120:
                errors.append("Invalid date of birth")
        except ValueError:
            errors.append("Invalid date format. Use YYYY-MM-DD")
        
        # Address validation
        address = kyc_data.get('address', '').strip()
        if len(address) < 10:
            errors.append("Address must be at least 10 characters long")
        
        # City validation
        city = kyc_data.get('city', '').strip()
        if len(city) < 2:
            errors.append("City must be at least 2 characters long")
        
        # Country validation
        country = kyc_data.get('country', '').strip()
        if len(country) < 2:
            errors.append("Country must be at least 2 characters long")
        
        # Postal code validation
        postal_code = kyc_data.get('postal_code', '').strip()
        if not re.match(r'^[A-Z0-9\s-]{3,10}$', postal_code, re.IGNORECASE):
            errors.append("Invalid postal code format")
        
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"errors": errors}
            )
        
        return {
            "is_valid": True,
            "age": age,
            "date_of_birth": dob
        }
    
    def get_required_documents(self) -> List[str]:
        """Get list of required KYC documents"""
        return ['id_front', 'proof_of_address', 'selfie']
    
    def check_kyc_completion(self, user) -> bool:
        """Check if user has completed all KYC requirements"""
        required_docs = self.get_required_documents()
        
        # Check documents
        doc_checks = {
            'id_front': bool(user.id_document_front),
            'proof_of_address': bool(user.proof_of_address),
            'selfie': bool(user.selfie_photo)
        }
        
        # Check personal info
        info_checks = all([
            user.date_of_birth,
            user.address,
            user.city,
            user.country,
            user.postal_code
        ])
        
        return all(doc_checks.values()) and info_checks

kyc_service = KYCService()