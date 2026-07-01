"""
components/invoice_generator.py
Enterprise Invoice Generator with UPI QR, Bank QR, and Database Integration
"""
import streamlit as st
import pandas as pd
import io
from datetime import date, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.units import mm, inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import qrcode
from PIL import Image

# -------------------------------------------------------------------
# Helper: Generate UPI QR code with dynamic amount
# -------------------------------------------------------------------
def generate_upi_qr(upi_id: str, payee_name: str, amount: float, invoice_ref: str) -> io.BytesIO:
    """
    Create a UPI payment QR containing amount, payee, and reference.
    Returns a BytesIO PNG image.
    """
    # Construct UPI intent string (PhonePe / Google Pay compatible)
    upi_string = f"upi://pay?pa={upi_id}&pn={payee_name}&am={amount:.2f}&tn={invoice_ref}&cu=INR"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(upi_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def generate_bank_qr(bank_details: str) -> io.BytesIO:
    """Static QR containing bank account info (text)."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(bank_details)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# -------------------------------------------------------------------
# PDF rendering
# -------------------------------------------------------------------
def generate_invoice_pdf(invoice_data: dict, page_size) -> io.BytesIO:
    """
    Draw a professional invoice on the selected page size.
    invoice_data keys:
        sender: dict(company, address, phone, email, bank_details, upi_id, upi_name)
        client: dict(name, address, city, state, zip, country)
        invoice_number, date_issued, due_date
        items: list of dicts (description, rate, qty, amount)
        subtotal, total, balance_due, notes, terms
    """
    buf = io.BytesIO()
    page_w, page_h = page_size
    c = canvas.Canvas(buf, pagesize=page_size)
    w, h = page_w, page_h

    # Margins
    ml, mr, mt, mb = 25*mm, 25*mm, 20*mm, 20*mm
    usable_w = w - ml - mr

    # ---- HEADER ----
    c.setFont("Helvetica-Bold", 16)
    c.drawString(ml, h - mt - 10*mm, "INVOICE")

    # Sender info (top right)
    c.setFont("Helvetica", 9)
    sender = invoice_data['sender']
    lines = [
        sender['company'],
        sender['address'],
        f"Phone: {sender['phone']}",
        f"Email: {sender['email']}"
    ]
    tx = w - mr - 80*mm
    ty = h - mt - 10*mm
    for line in lines:
        c.drawString(tx, ty, line)
        ty -= 4*mm

    # Bill To section (left)
    c.setFont("Helvetica-Bold", 10)
    ty = h - mt - 28*mm
    c.drawString(ml, ty, "Billed To")
    ty -= 5*mm
    c.setFont("Helvetica", 9)
    client = invoice_data['client']
    c.drawString(ml, ty, client['name'])
    ty -= 4*mm
    c.drawString(ml, ty, client['address'])
    ty -= 4*mm
    if client.get('city'):
        c.drawString(ml, ty, f"{client['city']}, {client.get('state','')} {client.get('zip','')}")
        ty -= 4*mm
    c.drawString(ml, ty, client.get('country',''))

    # Dates and Invoice number (right side)
    c.setFont("Helvetica-Bold", 9)
    tx = w - mr - 80*mm
    ty = h - mt - 40*mm
    c.drawString(tx, ty, "Date Issued")
    c.setFont("Helvetica", 9)
    c.drawString(tx + 35*mm, ty, invoice_data['date_issued'])
    ty -= 5*mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(tx, ty, "Invoice Number")
    c.setFont("Helvetica", 9)
    c.drawString(tx + 35*mm, ty, invoice_data['invoice_number'])
    ty -= 5*mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(tx, ty, "Due Date")
    c.setFont("Helvetica", 9)
    c.drawString(tx + 35*mm, ty, invoice_data['due_date'])
    ty -= 5*mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(tx, ty, "Amount Due")
    c.setFont("Helvetica", 9)
    c.drawString(tx + 35*mm, ty, f"INR {invoice_data['total']:,.2f}")

    # ---- ITEMS TABLE ----
    table_top = h - mt - 80*mm
    # Table header
    header = ['Description', 'Rate', 'Qty', 'Amount']
    # Data rows
    data = [header]
    for item in invoice_data['items']:
        data.append([
            item['description'],
            f"{item['rate']:,.2f}",
            str(item['qty']),
            f"{item['amount']:,.2f}"
        ])
    # Add subtotal row
    data.append(['', '', 'SubTotal', f"{invoice_data['subtotal']:,.2f}"])
    data.append(['', '', 'Total', f"{invoice_data['total']:,.2f}"])
    data.append(['', '', 'Balance Due', f"{invoice_data['balance_due']:,.2f}"])

    # Create table with style
    col_widths = [usable_w*0.55, usable_w*0.15, usable_w*0.1, usable_w*0.2]
    t = Table(data, colWidths=col_widths)
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2e7d32")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-4), colors.beige),
        ('GRID', (0,0), (-1,-4), 0.5, colors.gray),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        # Subtotal/total rows
        ('BACKGROUND', (0,-3), (-1,-1), colors.white),
        ('FONTNAME', (0,-3), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,-3), (-1,-1), 'RIGHT'),
        ('LINEABOVE', (0,-3), (-1,-3), 1, colors.black),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.black),
    ])
    t.setStyle(style)

    # Calculate table dimensions and draw
    tw, th = t.wrap(0, 0)
    t.drawOn(c, ml, table_top - th)

    # ---- NOTES and TERMS (below table) ----
    ty = table_top - th - 10*mm
    if invoice_data.get('notes'):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(ml, ty, "Notes")
        ty -= 4*mm
        c.setFont("Helvetica", 8)
        for line in invoice_data['notes'].split('\n'):
            c.drawString(ml, ty, line.strip())
            ty -= 3.5*mm
    if invoice_data.get('terms'):
        ty -= 5*mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(ml, ty, "Terms")
        ty -= 4*mm
        c.setFont("Helvetica", 8)
        c.drawString(ml, ty, invoice_data['terms'])

    # ---- QR CODES (bottom right) ----
    # Dynamic UPI QR (payment link)
    upi_buf = generate_upi_qr(
        sender.get('upi_id',''),
        sender.get('upi_name',''),
        invoice_data['balance_due'],
        f"INV-{invoice_data['invoice_number']}"
    )
    upi_img = ImageReader(upi_buf)
    qr_size = 35*mm
    c.drawImage(upi_img, w - mr - qr_size - 5*mm, 20*mm, width=qr_size, height=qr_size)
    c.setFont("Helvetica", 6)
    c.drawString(w - mr - qr_size - 5*mm, 18*mm, "Scan to Pay (UPI)")

    # Bank account QR (static)
    if sender.get('bank_details'):
        bank_buf = generate_bank_qr(sender['bank_details'])
        bank_img = ImageReader(bank_buf)
        c.drawImage(bank_img, w - mr - 2*qr_size - 10*mm, 20*mm, width=qr_size, height=qr_size)
        c.setFont("Helvetica", 6)
        c.drawString(w - mr - 2*qr_size - 10*mm, 18*mm, "Bank Details")

    # Footer
    c.setFont("Helvetica", 7)
    c.drawString(ml, 10*mm, f"Generated by GrowLeafy Invoice System | {invoice_data['date_issued']}")

    c.save()
    buf.seek(0)
    return buf

# -------------------------------------------------------------------
# Streamlit UI
# -------------------------------------------------------------------
def render(db=None):
    st.title("🧾 Invoice Generator")
    st.caption("Fully customizable professional invoices with UPI QR codes")

    # Initialize session state for invoice template
    if 'inv_sender' not in st.session_state:
        st.session_state.inv_sender = {
            'company': 'Biswas Ventures',
            'address': 'Madhabpur - Panpur Road\nPanpur, West Bengal, 743126, India',
            'phone': '9903026500',
            'email': 'biswas4trade@gmail.com',
            'bank_details': 'A/C name : Subhasis Biswas\nAccount No. : 32781178011\nIFSC : SBIN0006042\nBRANCH : RATHTALA\nSTATE BANK OF INDIA',
            'upi_id': '9903026500@upi',      # Replace with actual UPI ID
            'upi_name': 'Subhasis Biswas'
        }
    if 'inv_client' not in st.session_state:
        st.session_state.inv_client = {
            'name': '',
            'address': '',
            'city': '',
            'state': '',
            'zip': '',
            'country': 'India'
        }

    # ---- Page size selector ----
    col_page, col_num = st.columns(2)
    with col_page:
        page_format = st.selectbox("Page Size", ["A4", "Letter"])
    with col_num:
        invoice_number = st.text_input("Invoice Number", value="BV/MLP/2025/01")

    page_size = A4 if page_format == "A4" else LETTER

    # ---- Sender & Client info in expandable sections ----
    with st.expander("🏢 Your Company Details (Sender)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.inv_sender['company'] = st.text_input("Company Name", value=st.session_state.inv_sender['company'])
            st.session_state.inv_sender['address'] = st.text_area("Address", value=st.session_state.inv_sender['address'], height=80)
        with col2:
            st.session_state.inv_sender['phone'] = st.text_input("Phone", value=st.session_state.inv_sender['phone'])
            st.session_state.inv_sender['email'] = st.text_input("Email", value=st.session_state.inv_sender['email'])
            st.session_state.inv_sender['bank_details'] = st.text_area("Bank Account Details (for QR)", value=st.session_state.inv_sender['bank_details'], height=80)
            st.session_state.inv_sender['upi_id'] = st.text_input("UPI ID (e.g., name@upi)", value=st.session_state.inv_sender.get('upi_id',''))
            st.session_state.inv_sender['upi_name'] = st.text_input("UPI Payee Name", value=st.session_state.inv_sender.get('upi_name',''))

    with st.expander("🧾 Client Details (Bill To)", expanded=True):
        colc1, colc2 = st.columns(2)
        with colc1:
            st.session_state.inv_client['name'] = st.text_input("Client Name", value=st.session_state.inv_client['name'])
            st.session_state.inv_client['address'] = st.text_area("Address", value=st.session_state.inv_client['address'], height=80)
        with colc2:
            st.session_state.inv_client['city'] = st.text_input("City", value=st.session_state.inv_client['city'])
            st.session_state.inv_client['state'] = st.text_input("State", value=st.session_state.inv_client['state'])
            st.session_state.inv_client['zip'] = st.text_input("ZIP", value=st.session_state.inv_client['zip'])
            st.session_state.inv_client['country'] = st.text_input("Country", value=st.session_state.inv_client['country'])

    # Dates
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        date_issued = st.date_input("Date Issued", value=date.today())
    with col_d2:
        due_date = st.date_input("Due Date", value=date.today() + timedelta(days=30))

    # ---- Items (manual input + optional fetch from DB) ----
    st.subheader("📋 Invoice Items")
    # Option to import from database (if db provided)
    if db:
        import_option = st.checkbox("Load item from database (Plants/Inventory)")
        if import_option:
            # Select table
            table = st.selectbox("Select table", ["plants", "fertilizers", "insecticides", "pesticides"])
            try:
                data = db.fetch_all(table)
                if data:
                    # Convert to DataFrame for selection
                    df = pd.DataFrame(data)
                    # Let user pick a row
                    selected_index = st.selectbox("Choose an item", df.index, format_func=lambda x: f"{df.at[x,'name']} (SKU: {df.at[x,'sku']})")
                    if st.button("Add to Invoice"):
                        row = df.iloc[selected_index]
                        # Add to items list in session state
                        if 'inv_items' not in st.session_state:
                            st.session_state.inv_items = []
                        st.session_state.inv_items.append({
                            'description': f"{row.get('name','')} ({row.get('sku','')})",
                            'rate': row.get('mrp', 0.0),
                            'qty': 1,
                            'amount': row.get('mrp', 0.0)
                        })
                        st.rerun()
                else:
                    st.info("No data in selected table.")
            except Exception as e:
                st.warning(f"Could not load data: {e}")

    # Manual items editor
    if 'inv_items' not in st.session_state:
        st.session_state.inv_items = []

    # Show editable items table
    edited_items = []
    for i, item in enumerate(st.session_state.inv_items):
        cols = st.columns([4,1.5,1,1.5,1])
        with cols[0]:
            desc = st.text_input(f"Description {i+1}", value=item['description'], key=f"desc_{i}")
        with cols[1]:
            rate = st.number_input(f"Rate {i+1}", value=float(item['rate']), min_value=0.0, format="%.2f", key=f"rate_{i}")
        with cols[2]:
            qty = st.number_input(f"Qty {i+1}", value=int(item['qty']), min_value=1, key=f"qty_{i}")
        with cols[3]:
            amount = rate * qty
            st.text(f"₹{amount:,.2f}")
        with cols[4]:
            if st.button("🗑️", key=f"del_{i}"):
                del st.session_state.inv_items[i]
                st.rerun()
        edited_items.append({'description': desc, 'rate': rate, 'qty': qty, 'amount': rate * qty})

    # Add new empty row
    if st.button("➕ Add Row", use_container_width=True):
        st.session_state.inv_items.append({'description': '', 'rate': 0.0, 'qty': 1, 'amount': 0.0})
        st.rerun()

    # ---- Notes and Terms ----
    col_n, col_t = st.columns(2)
    with col_n:
        notes = st.text_area("Notes", value="A/C name : Subhasis Biswas\nAccount No. : 32781178011\nIFSC : SBIN0006042\nBRANCH : RATHTALA\nSTATE BANK OF INDIA", height=100)
    with col_t:
        terms = st.text_area("Terms", value="Payable within 30 days from the date of invoice. Applicable TDS may be deducted.", height=100)

    # ---- Calculation ----
    subtotal = sum(item['amount'] for item in edited_items) if edited_items else 0.0
    total = subtotal  # You could add tax fields later
    balance_due = total  # Assuming full amount due

    # ---- Preview & Download ----
    st.subheader("📄 Preview & Download")
    if st.button("🚀 Generate PDF Invoice", type="primary", use_container_width=True):
        if not edited_items:
            st.error("Please add at least one item.")
        else:
            invoice_data = {
                'sender': st.session_state.inv_sender,
                'client': st.session_state.inv_client,
                'invoice_number': invoice_number,
                'date_issued': date_issued.strftime("%B %d, %Y"),
                'due_date': due_date.strftime("%B %d, %Y"),
                'items': edited_items,
                'subtotal': subtotal,
                'total': total,
                'balance_due': balance_due,
                'notes': notes,
                'terms': terms
            }
            pdf_buffer = generate_invoice_pdf(invoice_data, page_size)
            st.success("Invoice generated successfully!")
            st.download_button(
                label="📥 Download Invoice PDF",
                data=pdf_buffer,
                file_name=f"Invoice_{invoice_number}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            # Show a preview of the UPI QR
            upi_preview_buf = generate_upi_qr(
                st.session_state.inv_sender.get('upi_id',''),
                st.session_state.inv_sender.get('upi_name',''),
                balance_due,
                f"INV-{invoice_number}"
            )
            st.image(upi_preview_buf, caption="Dynamic UPI QR Code", width=150)
