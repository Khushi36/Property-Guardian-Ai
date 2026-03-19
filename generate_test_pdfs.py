import os

from fpdf import FPDF


def create_property_pdf(
    filename,
    seller_name,
    seller_aadhaar,
    seller_pan,
    buyer_name,
    buyer_aadhaar,
    buyer_pan,
    plot_no,
    village,
    date,
):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "OFFICE OF THE SUB-REGISTRAR: MAHARASHTRA", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)

    pdf.cell(0, 10, f"Document Type: SALE DEED", ln=True)
    pdf.cell(0, 10, f"Registration Date: {date}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "SELLER DETAILS (First Party):", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Name: {seller_name}", ln=True)
    pdf.cell(0, 10, f"Seller Aadhaar Number: {seller_aadhaar}", ln=True)
    pdf.cell(0, 10, f"Seller PAN Number: {seller_pan}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "BUYER DETAILS (Second Party):", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Name: {buyer_name}", ln=True)
    pdf.cell(0, 10, f"Buyer Aadhaar Number: {buyer_aadhaar}", ln=True)
    pdf.cell(0, 10, f"Buyer PAN Number: {buyer_pan}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "PROPERTY DESCRIPTION:", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Village: {village}", ln=True)
    pdf.cell(0, 10, f"Plot Number: {plot_no}", ln=True)
    pdf.cell(0, 10, f"District: Pune", ln=True)
    pdf.ln(10)

    pdf.multi_cell(
        0,
        10,
        "This document confirms that the seller has transferred full ownership of the above-mentioned property to the buyer on the date of registration.",
    )

    pdf.output(filename)
    print(f"Generated {filename}")


# Ensure directory exists
os.makedirs("qa_test_files", exist_ok=True)

# 1. Valid First Transaction
create_property_pdf(
    "qa_test_files/valid_tx_1.pdf",
    "Rahul Sharma",
    "1234-5678-9012",
    "ABCPS1234A",
    "Sonal Gupta",
    "9876-5432-1098",
    "GHTPS9876S",
    "Plot 777",
    "Baner",
    "2024-01-15",
)

# 2. Fraudulent Transaction (Sonal Gupta selling, but with FRAUD Aadhaar)
# This tests the "Broken Chain" logic
create_property_pdf(
    "qa_test_files/fraud_tx_2_id_mismatch.pdf",
    "Sonal Gupta",
    "5555-5555-5555",
    "FAKEID111X",  # <--- Aadhaar mismatch with previous BUYER
    "Vikram Singh",
    "1111-2222-3333",
    "VKRAN5555V",
    "Plot 777",
    "Baner",
    "2024-03-20",
)

# 3. Double Selling Fraud (Rahul Sharma selling the SAME plot to TWO different people)
# Rahul Sharma (valid ID) sells to Sonal
# Now Rahul Sharma (valid ID) sells to ANOTHER person "Priya"
create_property_pdf(
    "qa_test_files/fraud_tx_3_double_sell.pdf",
    "Rahul Sharma",
    "1234-5678-9012",
    "ABCPS1234A",
    "Priya Das",
    "7777-8888-9999",
    "PDAS9999D",
    "Plot 777",
    "Baner",
    "2024-04-01",
)
