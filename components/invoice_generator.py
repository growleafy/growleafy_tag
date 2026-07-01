"""
components/invoice_generator.py
Invoice Generator – Tax, Logo, Save, QR, Multi‑format Export
"""
import streamlit as st
import pandas as pd
import io
import json
import base64
from datetime import datetime, date, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.units import mm, inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import qrcode
from PIL import Image

# Optional: convert PDF to images
try:
    from pdf2image import convert_from_bytes
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

# -------------------------------------------------------------------
# Helper: UPI QR
# -------------------------------------------------------------------
def generate_upi_qr(upi_id: str, payee_name: str, amount: float, invoice_ref: str) -> io.BytesIO:
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
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(bank_details)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# -------------------------------------------------------------------
# PDF generation with logo + tax
# -------------------------------------------------------------------
def generate_invoice_pdf(invoice_data: dict, page_size, logo_bytes=None) -> io.BytesIO:
    buf = io.BytesIO()
    page_w, page_h = page_size
    c = canvas.Canvas(buf, pagesize=page_size)
    w, h = page_w, page_h

    # Margins
    ml, mr, mt, mb = 25*mm, 25*mm, 20*mm, 20*mm
    usable_w = w - ml - mr

    # ---- LOGO (top left) ----
    if logo_bytes:
        logo_buf = io.BytesIO(logo_bytes)
        logo = ImageReader(logo_buf)
        # logo size: max 60mm wide, 25mm high
        logo_w = 50*mm
        logo_h = 20*mm
        c.drawImage(logo, ml, h - mt - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
        # Adjust header position so text doesn't overlap logo
        header_y = h - mt - 10*mm
    else:
        header_y = h - mt - 10*mm

    # ---- HEADER ----
    c.setFont("Helvetica-Bold", 16)
    c.drawString(ml, header_y, "INVOICE")

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
    ty = h - mt - (35*mm if logo_bytes else 28*mm)  # adjust if logo present
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
    ty = h - mt - 45*mm
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
    c.drawString(tx + 35*mm, ty, f"INR {invoice_data['grand_total']:,.2f}")

    # ---- ITEMS TABLE ----
    table_top = h - mt - (95*mm if logo_bytes else 88*mm)
    header = ['Description', 'Rate', 'Qty', 'Amount']
    data = [header]
    for item in invoice_data['items']:
        data.append([
            item['description'],
            f"{item['rate']:,.2f}",
            str(item['qty']),
            f"{item['amount']:,.2f}"
        ])
    # Tax rows
    if invoice_data.get('tax_enabled'):
        data.append(['', '', 'Taxable Amount', f"{invoice_data['taxable_amount']:,.2f}"])
        if invoice_data.get('cgst_rate', 0) > 0:
            data.append(['', '', f"CGST @{invoice_data['cgst_rate']}%", f"{invoice_data['cgst_amount']:,.2f}"])
        if invoice_data.get('sgst_rate', 0) > 0:
            data.append(['', '', f"SGST @{invoice_data['sgst_rate']}%", f"{invoice_data['sgst_amount']:,.2f}"])
        if invoice_data.get('igst_rate', 0) > 0:
            data.append(['', '', f"IGST @{invoice_data['igst_rate']}%", f"{invoice_data['igst_amount']:,.2f}"])
    # Grand total
    data.append(['', '', 'Grand Total', f"{invoice_data['grand_total']:,.2f}"])
    data.append(['', '', 'Balance Due', f"{invoice_data['balance_due']:,.2f}"])

    col_widths = [usable_w*0.55, usable_w*0.15, usable_w*0.1, usable_w*0.2]
    t = Table(data, colWidths=col_widths)
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2e7d32")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-5), colors.beige),
        ('GRID', (0,0), (-1,-5), 0.5, colors.gray),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        # Subtotals
        ('BACKGROUND', (0,-3), (-1,-1), colors.white),
        ('FONTNAME', (0,-3), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,-3), (-1,-1), 'RIGHT'),
        ('LINEABOVE', (0,-3), (-1,-3), 1, colors.black),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.black),
    ])
    t.setStyle(style)
    tw, th = t.wrap(0, 0)
    t.drawOn(c, ml, table_top - th)

    # ---- NOTES and TERMS ----
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

    # ---- QR CODES ----
    # UPI QR (dynamic)
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

    # Bank QR (static)
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
    st.caption("Tax, Logo, Auto‑numbering, Save & WhatsApp‑ready output")

    # ------------------ Session state initialization ------------------
    if 'inv_sender' not in st.session_state:
        st.session_state.inv_sender = {
            'company': 'Biswas Ventures',
            'address': 'Madhabpur - Panpur Road\nPanpur, West Bengal, 743126, India',
            'phone': '9804939270',
            'email': 'biswas4trade@gmail.com',
            'bank_details': 'A/C name : Subhasis Biswas\nAccount No. : 32781178011\nIFSC : SBIN0006042\nBRANCH : RATHTALA\nSTATE BANK OF INDIA',
            'upi_id': 'subhasisboi@axl',
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
    if 'inv_items' not in st.session_state:
        st.session_state.inv_items = []
    if 'inv_tax_enabled' not in st.session_state:
        st.session_state.inv_tax_enabled = False
    if 'inv_logo_bytes' not in st.session_state:
        st.session_state.inv_logo_bytes = None
    if 'inv_prefix' not in st.session_state:
        st.session_state.inv_prefix = "BV/MLP"

    # ------------------ Page size & serial counter ------------------
    col_page, col_num = st.columns(2)
    with col_page:
        page_format = st.selectbox("Page Size", ["A4", "Letter"])
    with col_num:
        use_auto = st.checkbox("Auto‑generate invoice number", value=True)
        if use_auto:
            if st.button("🔄 Generate New Invoice Number"):
                if db:
                    invoice_number = db.get_next_invoice_number(st.session_state.inv_prefix)
                    st.session_state.inv_number = invoice_number
                    st.success(f"New number: {invoice_number}")
                else:
                    st.warning("Database not connected")
            inv_num = st.text_input("Invoice Number", value=st.session_state.get('inv_number', ''), key="inv_num_input")
        else:
            inv_num = st.text_input("Invoice Number", value="BV/MLP/2025/01")

    page_size = A4 if page_format == "A4" else LETTER

    # ------------------ Sender & Client details ------------------
    with st.expander("🏢 Company Details (Sender)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.inv_sender['company'] = st.text_input("Company Name", value=st.session_state.inv_sender['company'])
            st.session_state.inv_sender['address'] = st.text_area("Address", value=st.session_state.inv_sender['address'], height=80)
        with col2:
            st.session_state.inv_sender['phone'] = st.text_input("Phone", value=st.session_state.inv_sender['phone'])
            st.session_state.inv_sender['email'] = st.text_input("Email", value=st.session_state.inv_sender['email'])
            st.session_state.inv_sender['bank_details'] = st.text_area("Bank Account Details", value=st.session_state.inv_sender['bank_details'], height=80)
            st.session_state.inv_sender['upi_id'] = st.text_input("UPI ID", value=st.session_state.inv_sender.get('upi_id',''))
            st.session_state.inv_sender['upi_name'] = st.text_input("UPI Payee Name", value=st.session_state.inv_sender.get('upi_name',''))
        # Logo upload
        logo_file = st.file_uploader("Company Logo (PNG/JPG)", type=["png","jpg","jpeg"])
        if logo_file:
            st.session_state.inv_logo_bytes = logo_file.read()
            st.image(st.session_state.inv_logo_bytes, width=150)
        else:
            if st.button("Remove Logo"):
                st.session_state.inv_logo_bytes = None
                st.rerun()

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

    # ------------------ Items with tax settings ------------------
    st.subheader("📋 Invoice Items")
    col_tax_toggle, _ = st.columns([1,3])
    with col_tax_toggle:
        st.session_state.inv_tax_enabled = st.checkbox("Enable Tax (GST)", value=st.session_state.inv_tax_enabled)

    if st.session_state.inv_tax_enabled:
        tax_cols = st.columns(3)
        with tax_cols[0]:
            cgst_rate = st.number_input("CGST %", 0.0, 100.0, 9.0, 0.5)
        with tax_cols[1]:
            sgst_rate = st.number_input("SGST %", 0.0, 100.0, 9.0, 0.5)
        with tax_cols[2]:
            igst_rate = st.number_input("IGST %", 0.0, 100.0, 18.0, 0.5)
    else:
        cgst_rate = sgst_rate = igst_rate = 0.0

    # Item rows
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
        edited_items.append({'description': desc, 'rate': rate, 'qty': qty, 'amount': amount})

    if st.button("➕ Add Row", use_container_width=True):
        st.session_state.inv_items.append({'description': '', 'rate': 0.0, 'qty': 1, 'amount': 0.0})
        st.rerun()

    # Notes & Terms
    col_n, col_t = st.columns(2)
    with col_n:
        notes = st.text_area("Notes", value="A/C name : Subhasis Biswas\nAccount No. : 32781178011\nIFSC : SBIN0006042\nBRANCH : RATHTALA\nSTATE BANK OF INDIA", height=100)
    with col_t:
        terms = st.text_area("Terms", value="Payable within 30 days from the date of invoice. Applicable TDS may be deducted.", height=100)

    # ------------------ Calculations ------------------
    subtotal = sum(item['amount'] for item in edited_items) if edited_items else 0.0
    taxable_amount = subtotal
    cgst_amount = round(taxable_amount * cgst_rate / 100, 2)
    sgst_amount = round(taxable_amount * sgst_rate / 100, 2)
    igst_amount = round(taxable_amount * igst_rate / 100, 2)
    grand_total = taxable_amount + cgst_amount + sgst_amount + igst_amount
    balance_due = grand_total  # can be adjusted for partial payments later

    # Display summary
    st.subheader("💰 Summary")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("Sub Total", f"₹{subtotal:,.2f}")
    with col_s2:
        if st.session_state.inv_tax_enabled:
            st.metric("Tax", f"₹{cgst_amount+sgst_amount+igst_amount:,.2f}")
        else:
            st.metric("Tax", "₹0.00")
    with col_s3:
        st.metric("Grand Total", f"₹{grand_total:,.2f}")

    # ------------------ Generate & Output Options ------------------
    st.subheader("📄 Generate Invoice")
    output_format = st.radio("Output Format", ["PDF", "PNG Image", "WhatsApp Optimized Image"], horizontal=True)

    if st.button("🚀 Generate Invoice", type="primary", use_container_width=True):
        if not edited_items:
            st.error("Please add at least one item.")
        else:
            invoice_data = {
                'sender': st.session_state.inv_sender,
                'client': st.session_state.inv_client,
                'invoice_number': inv_num,
                'date_issued': date_issued.strftime("%B %d, %Y"),
                'due_date': due_date.strftime("%B %d, %Y"),
                'items': edited_items,
                'taxable_amount': taxable_amount,
                'cgst_rate': cgst_rate,
                'sgst_rate': sgst_rate,
                'igst_rate': igst_rate,
                'cgst_amount': cgst_amount,
                'sgst_amount': sgst_amount,
                'igst_amount': igst_amount,
                'tax_enabled': st.session_state.inv_tax_enabled,
                'grand_total': grand_total,
                'balance_due': balance_due,
                'notes': notes,
                'terms': terms
            }
            pdf_buffer = generate_invoice_pdf(invoice_data, page_size, st.session_state.inv_logo_bytes)

            # --- Save to database (optional) ---
            if db and st.button("💾 Save Invoice to Database"):
                success = db.save_invoice(invoice_data)
                if success:
                    st.success("Invoice saved!")
                else:
                    st.error("Failed to save.")

            # --- Output formats ---
            if output_format == "PDF":
                st.download_button("📥 Download PDF", data=pdf_buffer, file_name=f"Invoice_{inv_num}.pdf", mime="application/pdf")
            else:
                if not HAS_PDF2IMAGE:
                    st.error("pdf2image not installed. Run: pip install pdf2image")
                else:
                    # Convert PDF to images
                    images = convert_from_bytes(pdf_buffer.getvalue(), dpi=200)
                    if output_format == "PNG Image":
                        img_buf = io.BytesIO()
                        images[0].save(img_buf, format='PNG')
                        img_buf.seek(0)
                        st.download_button("📥 Download PNG", data=img_buf, file_name=f"Invoice_{inv_num}.png", mime="image/png")
                        st.image(images[0], caption="Invoice Preview")
                    elif output_format == "WhatsApp Optimized Image":
                        # Resize to 800px width, keep aspect ratio
                        img = images[0]
                        w_percent = 800 / float(img.size[0])
                        h_size = int(float(img.size[1]) * w_percent)
                        img = img.resize((800, h_size), Image.LANCZOS)
                        img_buf = io.BytesIO()
                        img.save(img_buf, format='JPEG', quality=85)
                        img_buf.seek(0)
                        st.download_button("📥 Download for WhatsApp", data=img_buf, file_name=f"Invoice_{inv_num}_wa.jpg", mime="image/jpeg")
                        st.image(img, caption="WhatsApp Preview (800px)")

            # UPI QR preview
            upi_preview = generate_upi_qr(
                st.session_state.inv_sender.get('upi_id',''),
                st.session_state.inv_sender.get('upi_name',''),
                balance_due,
                f"INV-{inv_num}"
            )
            st.image(upi_preview, caption="Dynamic UPI QR", width=150)

    # ------------------ Saved Invoices History ------------------
    if db:
        st.markdown("---")
        st.subheader("📚 Saved Invoices")
        invoices = db.get_invoices()
        if invoices:
            for inv in invoices:
                with st.expander(f"{inv.get('invoice_number','')} – {inv.get('created_at','')[:10]}"):
                    # Display basic info
                    data = json.loads(inv['data'])
                    st.write(f"**Client:** {data['client']['name']}")
                    st.write(f"**Total:** ₹{data['grand_total']:,.2f}")
                    st.write(f"**Date:** {data['date_issued']}")
                    if st.button("🗑️ Delete", key=f"del_inv_{inv['id']}"):
                        if db.delete_invoice(inv['id']):
                            st.success("Deleted!")
                            st.rerun()
        else:
            st.info("No saved invoices yet.")
