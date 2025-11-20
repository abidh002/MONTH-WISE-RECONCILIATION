import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Invoice Reconciliation Tool", layout="wide")
st.title("💰 Invoice Reconciliation Tool")

st.markdown("### Step 1: Download Templates")

col1, col2 = st.columns(2)

with col1:
    # Submission template
    st.download_button(
        "📥 Download Submission Template",
        data="Month,Invoice,Member ID,Transaction Date,Amount\n2025-01,INV001,12345,22-10-2025,1000\n2025-02,INV002,56789,23-10-2025,2000\n2025-03,INV003,11111,24-10-2025,1500",
        file_name="submission_template.csv",
        mime="text/csv"
    )

with col2:
    # Remittance template
    st.download_button(
        "📥 Download Remittance Template",
        data="Invoice,Payment Reference,Settlement Date,Amount\nINV001,REF001,24-10-2025,800\nINV002,REF002,25-10-2025,2000",
        file_name="remittance_template.csv",
        mime="text/csv"
    )

st.markdown("### Step 2: Upload Your Files")

sub_file = st.file_uploader("Upload Submission File", type=["xlsx", "csv"])
rem_file = st.file_uploader("Upload Remittance File", type=["xlsx", "csv"])

if sub_file and rem_file:
    try:
        # Read Submission
        if sub_file.name.lower().endswith(".csv"):
            submission_df = pd.read_csv(sub_file, dtype=str)
        else:
            submission_df = pd.read_excel(sub_file, dtype=str)

        # Read Remittance
        if rem_file.name.lower().endswith(".csv"):
            remittance_df = pd.read_csv(rem_file, dtype=str)
        else:
            remittance_df = pd.read_excel(rem_file, dtype=str)

        # Clean column names
        submission_df.columns = submission_df.columns.str.strip().str.title()
        remittance_df.columns = remittance_df.columns.str.strip().str.title()

        # Validate required columns
        required_sub_cols = {"Month", "Invoice", "Member Id", "Transaction Date", "Amount"}
        required_rem_cols = {"Invoice", "Payment Reference", "Settlement Date", "Amount"}

        if not required_sub_cols.issubset(submission_df.columns):
            st.error("❌ Submission file must have columns: Month, Invoice, Member ID, Transaction Date, Amount")
        elif not required_rem_cols.issubset(remittance_df.columns):
            st.error("❌ Remittance file must have columns: Invoice, Payment Reference, Settlement Date, Amount")
        else:
            # Convert Amount to numeric
            submission_df["Amount"] = pd.to_numeric(submission_df["Amount"], errors="coerce").fillna(0)
            remittance_df["Amount"] = pd.to_numeric(remittance_df["Amount"], errors="coerce").fillna(0)

            # Parse dates in DDMMYYYY format
            submission_df["Transaction Date"] = pd.to_datetime(submission_df["Transaction Date"], dayfirst=True, errors="coerce").dt.date
            remittance_df["Settlement Date"] = pd.to_datetime(remittance_df["Settlement Date"], dayfirst=True, errors="coerce").dt.date

            # Merge on Invoice
            result = pd.merge(
                submission_df[["Month", "Invoice", "Amount"]],
                remittance_df[["Invoice", "Payment Reference", "Settlement Date", "Amount"]],
                on="Invoice",
                how="left",
                suffixes=("_Submitted", "_Received")
            )

            # Use received amount in result
            result["Amount"] = result["Amount_Received"].fillna(0)

            # Keep only required columns
            result = result[["Month", "Invoice", "Payment Reference", "Settlement Date", "Amount"]]

            # Display result
            st.markdown("### 🔍 Reconciliation Result")
            st.dataframe(result, use_container_width=True)

            # Download Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                result.to_excel(writer, index=False, sheet_name="Reconciliation")
            buffer.seek(0)

            st.download_button(
                label="📊 Download Reconciliation Result",
                data=buffer.getvalue(),
                file_name="Reconciliation_Result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.exception(e)

