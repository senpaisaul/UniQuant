from pydantic import BaseModel, Field

class CreditInput(BaseModel):
    Age: int = Field(..., ge=18, le=100)
    Sex: str = Field(..., pattern="^(male|female)$")
    Job: int = Field(..., ge=0, le=3, description="0: unskilled/non-res, 1: unskilled/res, 2: skilled, 3: highly skilled")
    Housing: str = Field(..., pattern="^(own|rent|free)$")
    Saving_accounts: str = Field(..., alias="Saving accounts")
    Checking_account: str = Field(..., alias="Checking account")
    Credit_amount: int = Field(..., gt=0, alias="Credit amount")
    Duration: int = Field(..., gt=0)

class CreditPrediction(BaseModel):
    risk_score: int
    label: str
