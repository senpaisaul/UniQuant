from fastapi import APIRouter, HTTPException, Depends
from app.schemas.credit import CreditInput, CreditPrediction
from app.services.credit_service import CreditRiskService

router = APIRouter()

@router.post("/predict", response_model=CreditPrediction)
def predict_credit_risk(input_data: CreditInput):
    try:
        model, encoders = CreditRiskService.load_resources()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Model Loading Failed: {str(e)}")

    if not model or not encoders:
        raise HTTPException(status_code=503, detail="Credit Scoring Model not available (Unknown Reason)")

    # Convert Pydantic model to dict for service compatibility
    data = input_data.dict(by_alias=True)
    
    prediction = CreditRiskService.predict(model, encoders, data)
    
    if prediction is None:
        raise HTTPException(status_code=500, detail="Prediction failed")

    return {
        "risk_score": int(prediction),
        "label": "Good" if prediction == 1 else "Bad"
    }
