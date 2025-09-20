from pydantic import BaseModel, Field
from typing import Annotated
from decimal import Decimal

# Define provider type with validation
ProviderType = Annotated[str, Field(pattern="^(okx|paystack|flutterwave)$")]

class DepositRequest(BaseModel):
    user_id: int
    amount: Decimal
    provider: ProviderType

    def normalize_provider(self) -> str:
        """Normalize provider input (strip + lowercase)."""
        return self.provider.strip().lower()
