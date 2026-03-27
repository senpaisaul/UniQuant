import joblib
import pandas as pd
from functools import lru_cache
from pathlib import Path
from app.core.config import settings

class CreditRiskService:
    @classmethod
    @lru_cache()
    def load_resources(cls):
        """
        Load the model and encoders. Cached to avoid reloading on every run.
        """
        # NO TRY/EXCEPT - Let it fail so we see why
        model_path = Path(settings.MODELS_DIR_CREDIT) / "extra_trees_credit_model.pkl"
        
        # Verify existence explicitly
        if not model_path.exists():
             raise FileNotFoundError(f"Model not found at: {model_path.absolute()}")

        model = joblib.load(model_path)

        encoders = {}
        for col in ["Sex", "Housing", "Saving accounts", "Checking account"]:
            enc_path = Path(settings.MODELS_DIR_CREDIT) / f"{col}_encoder.pkl"
            if not enc_path.exists():
                raise FileNotFoundError(f"Encoder not found at: {enc_path.absolute()}")
            encoders[col] = joblib.load(enc_path)
        
        return model, encoders

    @staticmethod
    def predict(model, encoders, input_data: dict):
        """
        Make a prediction based on input data.
        """
        # Transform inputs using encoders
        try:
            input_df = pd.DataFrame({
                "Age": [input_data["Age"]],
                "Sex": [encoders["Sex"].transform([input_data["Sex"]])[0]],
                "Job": [input_data["Job"]],
                "Housing": [encoders["Housing"].transform([input_data["Housing"]])[0]],
                "Saving accounts": [encoders["Saving accounts"].transform([input_data["Saving accounts"]])[0]],
                "Checking account": [encoders["Checking account"].transform([input_data["Checking account"]])[0]],
                "Credit amount": [input_data["Credit amount"]],
                "Duration": [input_data["Duration"]]
            })
            
            prediction = model.predict(input_df)[0]
            return prediction  # 1 (Good) or 0 (Bad)
        except Exception as e:
            print(f"Prediction error: {e}")
            return None
