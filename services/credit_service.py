import joblib
import pandas as pd
import streamlit as st
from pathlib import Path

class CreditRiskService:
    MODELS_DIR = Path("assets/models/credit_risk")

    @classmethod
    @st.cache_resource
    def load_resources(cls):
        """
        Load the model and encoders. Cached to avoid reloading on every run.
        """
        try:
            model_path = cls.MODELS_DIR / "extra_trees_credit_model.pkl"
            model = joblib.load(model_path)

            encoders = {}
            for col in ["Sex", "Housing", "Saving accounts", "Checking account"]:
                enc_path = cls.MODELS_DIR / f"{col}_encoder.pkl"
                encoders[col] = joblib.load(enc_path)
            
            return model, encoders
        except FileNotFoundError as e:
            st.error(f"Critical Error: Model file not found at {e.filename}. Please check asset migration.")
            return None, None
        except Exception as e:
            st.error(f"Error loading credit risk models: {e}")
            return None, None

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
            return prediction  # 1 (Good) or 0 (Bad) - double check original
        except Exception as e:
            st.error(f"Prediction error: {e}")
            return None
