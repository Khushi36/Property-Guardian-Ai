import os

from reportlab.pdfgen import canvas


def create_pdf(filename, content):
    c = canvas.Canvas(filename)
    y = 750
    for line in content:
        c.drawString(100, y, line)
        y -= 20
    c.save()


# Directory for test files
test_dir = "qa_test_files"
if not os.path.exists(test_dir):
    os.makedirs(test_dir)

# Transaction 1: Alice -> Bob (Original)
create_pdf(
    os.path.join(test_dir, "tx1_alice_to_bob.pdf"),
    [
        "State: Himachal Pradesh",
        "District: Shimla",
        "Tehsil: Kumharsain",
        "Village Name: Wakad",
        "Plot No: 101",
        "Seller Name: Alice Alice",
        "Buyer Name: Bob Bob",
        "Document Registration Date: 01-01-2024",
        "This is a valid registration document for Plot 101 in Wakad.",
    ],
)

# Transaction 2: Charlie -> Dave (Fraud Discrepancy)
# Bob is the current owner, but Charlie is selling it.
create_pdf(
    os.path.join(test_dir, "tx2_charlie_to_dave_fraud.pdf"),
    [
        "State: Himachal Pradesh",
        "District: Shimla",
        "Tehsil: Kumharsain",
        "Village Name: Wakad",
        "Plot No: 101",
        "Seller Name: Charlie Charlie",
        "Buyer Name: Dave Dave",
        "Document Registration Date: 01-02-2024",
        "This document represents a fraudulent transaction where Charlie sells Bob's property.",
    ],
)

# Transaction 3: Bob -> Eve (Valid Chain)
create_pdf(
    os.path.join(test_dir, "tx3_bob_to_eve_valid.pdf"),
    [
        "State: Himachal Pradesh",
        "District: Shimla",
        "Tehsil: Kumharsain",
        "Village Name: Wakad",
        "Plot No: 101",
        "Seller Name: Bob Bob",
        "Buyer Name: Eve Eve",
        "Document Registration Date: 01-03-2024",
        "This is a valid follow-up transaction where the actual owner Bob sells the property.",
    ],
)

print(f"Test PDFs created in {test_dir}")
