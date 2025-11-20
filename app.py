import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Invoice Reconciliation Tool", layout="wide")
st.title("💰 Invoice Reconciliation Tool")

st.markdown("### Step 1: Download Templates")

col1, col2 = st.columns(2)
with col1:
    # Submission template with Month column
    st.download_button(
        "📥 Download Submission Template",
        data="Invoice,Member ID,Amount,Month\nINV001,12345,1000,2025-01\nINV002,56789,2000,2025-02\nINV003,11111,1500,2025-03",
        file_name="submission_template.csv",
        mime="text/csv"
    )

with col2:
    # Remittance template
    st.download_button(
        "📥 Download Remittance Template (with Transaction Date)",
        data="Invoice,Transaction Date,Amount\nINV001,2025-10-22 09:30,800\nINV002,2025-10-23 12:15,2000",
        file_name="remittance_template.csv",
        mime="text/csv"
    )

st.markdown("### Step 2: Upload Your Files")

sub_file = st.file_uploader("Upload Submission File", type=["xlsx", "csv"])
rem_file = st.file_uploader("Upload Remittance File (with Transaction Date)", type=["xlsx", "csv"])

if sub_file and rem_file:
    try:
        # Read Submission
        if sub_file.name.lower().endswith('.csv'):
            submission_df = pd.read_csv(sub_file)
        else:
            submission_df = pd.read_excel(sub_file)

        # Read Remittance
        if rem_file.name.lower().endswith('.csv'):
            remittance_df = pd.read_csv(rem_file)
        else:
            remittance_df = pd.read_excel(rem_file)

        # Clean column names
        submission_df.columns = submission_df.columns.str.strip().str.title()
        remittance_df.columns = remittance_df.columns.str.strip().str.title()

        # Validate required columns
        required_sub_cols = {"Invoice", "Amount", "Month"}
        required_rem_cols = {"Invoice", "Transaction Date", "Amount"}

        if not required_sub_cols.issubset(submission_df.columns):
            st.error("❌ Submission file must have columns: Invoice, Amount, Month")
        elif not required_rem_cols.issubset(remittance_df.columns):
            st.error("❌ Remittance file must have columns: Invoice, Transaction Date, Amount")
        else:
            # Convert data types
            submission_df["Amount"] = pd.to_numeric(submission_df["Amount"], errors="coerce").fillna(0)
            remittance_df["Amount"] = pd.to_numeric(remittance_df["Amount"], errors="coerce").fillna(0)
            remittance_df["Transaction Date"] = pd.to_datetime(remittance_df["Transaction Date"], errors="coerce").dt.date

            # Aggregate Submission by Invoice & Month
            submission_agg = submission_df.groupby(["Invoice", "Month"], as_index=False)["Amount"].sum()
            submission_agg.rename(columns={"Amount": "Total_Submitted"}, inplace=True)

            # Aggregate Remittance
            remittance_agg = remittance_df.groupby("Invoice", as_index=False).agg({
                "Amount": "sum",
                "Transaction Date": "max"
            })
            remittance_agg.rename(columns={"Amount": "Total_Received", "Transaction Date": "Transaction_Date"}, inplace=True)

            # Merge
            result = pd.merge(
                submission_agg,
                remittance_agg,
                on="Invoice",
                how="left"
            )

            # Calculate difference
            result["Total_Received"] = pd.to_numeric(result["Total_Received"], errors="coerce").fillna(0)
            result["Difference"] = result["Total_Submitted"] - result["Total_Received"]

            # Status column
            def get_status(row):
                if pd.isna(row["Transaction_Date"]):
                    return "❌ Not Received"
                elif row["Difference"] == 0:
                    return "✅ Matched"
                elif row["Difference"] > 0:
                    return "⚠️ Underpaid"
                else:
                    return "⚠️ Overpaid"

            result["Status"] = result.apply(get_status, axis=1)

            # Reorder columns
            result = result[[
                "Invoice", "Month", "Total_Submitted", "Total_Received",
                "Difference", "Transaction_Date", "Status"
            ]]

            # Sort by Status
            status_order = {"❌ Not Received": 0, "⚠️ Underpaid": 1, "⚠️ Overpaid": 2, "✅ Matched": 3}
            result["_sort"] = result["Status"].map(status_order)
            result = result.sort_values("_sort").drop("_sort", axis=1).reset_index(drop=True)

            # Summary Metrics
            st.markdown("### 📊 Summary Statistics")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Submitted", f"${result['Total_Submitted'].sum():,.2f}")

            with col2:
                st.metric("Total Received", f"${result['Total_Received'].sum():,.2f}")

            with col3:
                st.metric("Total Difference", f"${result['Difference'].sum():,.2f}")

            with col4:
                matched_count = len(result[result["Status"] == "✅ Matched"])
                st.metric("Matched Invoices", f"{matched_count}/{len(result)}")

            # Color-coded Table
            st.markdown("### 🔍 Reconciliation Result")
            def highlight_status(row):
                if row["Status"] == "❌ Not Received":
                    return ['background-color: #ffcccc'] * len(row)
                elif row["Status"] in ["⚠️ Underpaid", "⚠️ Overpaid"]:
                    return ['background-color: #fff3cd'] * len(row)
                elif row["Status"] == "✅ Matched":
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)

            st.dataframe(result.style.apply(highlight_status, axis=1), use_container_width=True)

            # Download Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                result.to_excel(writer, index=False, sheet_name="Reconciliation")
            buffer.seek(0)

            st.download_button(
                label="📊 Download Reconciliation Result (With Month)",
                data=buffer.getvalue(),
                file_name="Reconciliation_Result_With_Month.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.exception(e)
