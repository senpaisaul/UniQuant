import streamlit as st
from services.credit_service import CreditRiskService

def render():
    st.header("🏦 Credit Risk Analysis")
    st.write("Enter applicant information to predict if the credit risk is good or bad")

    # Load resources
    model, encoders = CreditRiskService.load_resources()
    
    if model is None or encoders is None:
        st.error("Failed to load model assets.")
        return

    # Create Columns for better layout
    col1, col2 = st.columns(2)

    with col1:
        age = st.number_input("Age", min_value=18, max_value=80, value=30, key="cr_age")
        sex = st.selectbox("Sex", ["male", "female"], key="cr_sex")
        job = st.number_input("Job (0-3)", min_value=0, max_value=3, value=1, help="0 - unskilled and non-resident, 1 - unskilled and resident, 2 - skilled, 3 - highly skilled", key="cr_job")
        housing = st.selectbox("Housing", ["own", "rent", "free"], key="cr_housing")

    with col2:
        saving_accounts = st.selectbox("Saving Accounts", ["little", "moderate", "rich", "quite rich"], key="cr_saving")
        checking_accounts = st.selectbox("Checking Accounts", ["little", "moderate", "rich", "quite rich"], key="cr_checking")
        credit_amount = st.number_input("Credit Amount", min_value=0, value=1000, key="cr_amount")
        duration = st.number_input("Duration (months)", min_value=1, value=12, key="cr_duration")

    st.markdown("---")

    if st.button("Predict Risk", type="primary"):
        input_data = {
            "Age": age,
            "Sex": sex,
            "Job": job,
            "Housing": housing,
            "Saving accounts": saving_accounts,
            "Checking account": checking_accounts,
            "Credit amount": credit_amount,
            "Duration": duration
        }

        pred = CreditRiskService.predict(model, encoders, input_data)

        if pred is not None:
            if pred == 1:
                st.success("## The predicted credit risk is: **GOOD** ✅")
            else:
                st.error("## The predicted credit risk is: **BAD** ⚠️")
