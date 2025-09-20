from email_validator import validate_email, EmailNotValidError
from fastapi import HTTPException

def validate_email_address(email: str) -> str:
    """
    Validate email syntax and check deliverability (MX records).
    Raises HTTPException if invalid.
    """
    try:
        v = validate_email(email, check_deliverability=True)
        return v.email
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=f"Invalid email: {str(e)}")
