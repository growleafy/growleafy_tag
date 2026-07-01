"""
components/invoice_generator.py
Enterprise Invoice Generator – Tax, Logo, QR, Save/Delete, Multi‑table Import, Multi‑format Export
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

# Optional imports for image conversion
try:
    from pdf2image import convert_from_bytes
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------
def generate_upi_qr(upi_id: str, payee_name: str, amount: float, invoice_ref: str) -> io.BytesIO:
    """Generate a UPI intent QR code as a PNG in memory."""
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
    """Static QR containing bank account text."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(bank_details)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ------------------------------------------------------------------------------
# PDF RENDERING
# ------------------------------------------------------------------------------
def generate_invoice_pdf(invoice_data: dict, page_size, logo_bytes=None) -> io.BytesIO:
    """
    Build a professional invoice PDF with logo, items, tax rows, and QR codes.
    """
    buf = io.BytesIO()
    page_w, page_h = page_size
    c = canvas.Canvas(buf, pagesize=page_size)
    w, h = page_w, page_h

    # Margins
    ml, mr, mt, mb = 25*mm, 25*mm, 20*mm, 20*mm
    usable_w = w - ml - mr

    # --- Logo (top left) ---
    if logo_bytes:
        logo_buf = io.BytesIO(logo_bytes)
        logo = ImageReader(logo_buf)
        logo_w = 50*mm
        logo_h = 20*mm
        c.drawImage(logo, ml, h - mt - logo_h, width=logo_w, height=logo_h,
                    preserveAspectRatio=True, mask='auto')
        header_y = h - mt - 10*mm
    else:
        header_y = h - mt - 10*mm

    # --- HEADER ---
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

    # Bill To (left)
    c.setFont("Helvetica-Bold", 10)
    ty = h - mt - (35*mm if logo_bytes else 28*mm)
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

    # Dates & Invoice No (right side)
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

    # --- ITEMS TABLE ---
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

    # --- NOTES & TERMS ---
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

    # --- QR CODES (bottom right) ---
    # Dynamic UPI QR
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

# ------------------------------------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------------------------------------
def render(db=None):
    st.title("🧾 Enterprise Invoice Generator")
    st.caption("Professional invoices with tax, QR, multi‑table item import, and export options")

    # --- Session state initialisation ---
    defaults = {
        'inv_sender': {
            'company': 'Biswas Ventures',
            'address': 'Madhabpur - Panpur Road\nPanpur, West Bengal, 743126, India',
            'phone': '9903026500',
            'email': 'biswas4trade@gmail.com',
            'bank_details': 'A/C name : Subhasis Biswas\nAccount No. : 32781178011\nIFSC : SBIN0006042\nBRANCH : RATHTALA\nSTATE BANK OF INDIA',
            'upi_id': '9903026500@upi',
            'upi_name': 'Subhasis Biswas'
        },
        'inv_client': {
            'name': '',
            'address': '',
            'city': '',
            'state': '',
            'zip': '',
            'country': 'India'
        },
        'inv_items': [],
        'inv_tax_enabled': False,
        'inv_logo_bytes': None,
        'inv_prefix': "BV/MLP",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # --- Page size & Invoice number ---
    col1, col2 = st.columns(2)
    with col1:
        page_format = st.selectbox("Page Size", ["A4", "Letter"], index=0)
    with col2:
        use_auto = st.checkbox("Auto‑generate invoice number", value=True)
        if use_auto:
            if st.button("🔄 New Invoice Number"):
                if db:
                    inv_num = db.get_next_invoice_number(st.session_state.inv_prefix)
                    st.session_state.inv_number = inv_num
                    st.success(f"New number: {inv_num}")
                else:
                    st.warning("Database not connected")
            inv_num = st.text_input("Invoice Number", value=st.session_state.get('inv_number', ''),
                                    key="inv_num_auto")
        else:
            inv_num = st.text_input("Invoice Number", value="BV/MLP/2025/01")

    page_size = A4 if page_format == "A4" else LETTER

    # --- Sender & Client ---
    with st.expander("🏢 Company Details (Sender)", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.session_state.inv_sender['company'] = st.text_input("Company Name",
                                                                   st.session_state.inv_sender['company'])
            st.session_state.inv_sender['address'] = st.text_area("Address",
                                                                  st.session_state.inv_sender['address'], height=80)
        with col_b:
            st.session_state.inv_sender['phone'] = st.text_input("Phone",
                                                                 st.session_state.inv_sender['phone'])
            st.session_state.inv_sender['email'] = st.text_input("Email",
                                                                 st.session_state.inv_sender['email'])
            st.session_state.inv_sender['bank_details'] = st.text_area("Bank Details",
                                                                       st.session_state.inv_sender['bank_details'], height=80)
            st.session_state.inv_sender['upi_id'] = st.text_input("UPI ID",
                                                                  st.session_state.inv_sender.get('upi_id',''))
            st.session_state.inv_sender['upi_name'] = st.text_input("UPI Payee Name",
                                                                    st.session_state.inv_sender.get('upi_name',''))
        # Logo upload
        logo_file = st.file_uploader("Company Logo", type=["png","jpg","jpeg"])
        if logo_file:
            st.session_state.inv_logo_bytes = logo_file.read()
            st.image(st.session_state.inv_logo_bytes, width=150)
        elif st.session_state.inv_logo_bytes:
            st.image(st.session_state.inv_logo_bytes, width=150)
            if st.button("Remove Logo"):
                st.session_state.inv_logo_bytes = None
                st.rerun()

    with st.expander("🧾 Client Details (Bill To)", expanded=True):
        col_c, col_d = st.columns(2)
        with col_c:
            st.session_state.inv_client['name'] = st.text_input("Client Name",
                                                                st.session_state.inv_client['name'])
            st.session_state.inv_client['address'] = st.text_area("Address",
                                                                  st.session_state.inv_client['address'], height=80)
        with col_d:
            st.session_state.inv_client['city'] = st.text_input("City",
                                                                st.session_state.inv_client['city'])
            st.session_state.inv_client['state'] = st.text_input("State",
                                                                 st.session_state.inv_client['state'])
            st.session_state.inv_client['zip'] = st.text_input("ZIP",
                                                               st.session_state.inv_client['zip'])
            st.session_state.inv_client['country'] = st.text_input("Country",
                                                                   st.session_state.inv_client['country'])

    # Dates
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        date_issued = st.date_input("Date Issued", value=date.today())
    with col_d2:
        due_date = st.date_input("Due Date", value=date.today() + timedelta(days=30))

    # --- Items & Tax ---
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

    # Database import (optional)
    if db:
        with st.expander("📦 Import item from database", expanded=False):
            table_labels = {
                "Plants": "plants",
                "Fertilizers": "fertilizers",
                "Insecticides": "insecticides",
                "Pesticides": "pesticides",
                "Pots & Planters": "pots_planters",  # adjust actual table name if different
                "Other (custom)": "__custom__"
            }
            selected_label = st.selectbox("Source table", list(table_labels.keys()))
            table_name = table_labels[selected_label]
            if table_name == "__custom__":
                table_name = st.text_input("Enter table name", value="pots_planters")

            if st.button("🔍 Fetch items"):
                try:
                    data = db.fetch_all(table_name)
                    if data:
                        df = pd.DataFrame(data)
                        selected_idx = st.selectbox(
                            "Choose item",
                            df.index,
                            format_func=lambda x: f"{df.iloc[x].get('name', df.iloc[x].get('product_name', '?'))} "
                                                  f"(SKU: {df.iloc[x].get('sku','N/A')})"
                        )
                        if st.button("➕ Add to Invoice"):
                            row = df.iloc[selected_idx]
                            st.session_state.inv_items.append({
                                'description': f"{row.get('name', row.get('product_name', 'Item'))} ({row.get('sku','')})",
                                'rate': row.get('mrp', 0.0),
                                'qty': 1,
                                'amount': row.get('mrp', 0.0)
                            })
                            st.rerun()
                    else:
                        st.info("No data in this table.")
                except Exception as e:
                    st.warning(f"Could not read table `{table_name}`: {e}")

    # Manual item rows
    edited_items = []
    for i, item in enumerate(st.session_state.inv_items):
        cols = st.columns([4, 1.5, 1, 1.5, 1])
        with cols[0]:
            desc = st.text_input(f"Desc {i+1}", item['description'], key=f"desc_{i}")
        with cols[1]:
            rate = st.number_input(f"Rate {i+1}", value=float(item['rate']), min_value=0.0, format="%.2f", key=f"rate_{i}")
        with cols[2]:
            qty = st.number_input(f"Qty {i+1}", value=int(item['qty']), min_value=1, key=f"qty_{i}")
        with cols[3]:
            amount = rate * qty
            st.text(f"₹{amount:,.2f}")
        with cols[4]:
            if st.button("🗑", key=f"del_{i}"):
                del st.session_state.inv_items[i]
                st.rerun()
        edited_items.append({'description': desc, 'rate': rate, 'qty': qty, 'amount': amount})

    if st.button("➕ Add Row", use_container_width=True):
        st.session_state.inv_items.append({'description': '', 'rate': 0.0, 'qty': 1, 'amount': 0.0})
        st.rerun()

    # Notes & Terms
    col_n, col_t = st.columns(2)
    with col_n:
        notes = st.text_area("Notes", value="A/C name : Subhasis Biswas\nAccount No. : 32781178011\n"
                                             "IFSC : SBIN0006042\nBRANCH : RATHTALA\nSTATE BANK OF INDIA", height=100)
    with col_t:
        terms = st.text_area("Terms", value="Payable within 30 days from the date of invoice. "
                                            "Applicable TDS may be deducted.", height=100)

    # --- Calculations ---
    subtotal = sum(it['amount'] for it in edited_items) if edited_items else 0.0
    taxable_amount = subtotal
    cgst_amount = round(taxable_amount * cgst_rate / 100, 2)
    sgst_amount = round(taxable_amount * sgst_rate / 100, 2)
    igst_amount = round(taxable_amount * igst_rate / 100, 2)
    grand_total = taxable_amount + cgst_amount + sgst_amount + igst_amount
    balance_due = grand_total

    st.subheader("💰 Summary")
    s1, s2, s3 = st.columns(3)
    s1.metric("Subtotal", f"₹{subtotal:,.2f}")
    if st.session_state.inv_tax_enabled:
        total_tax = cgst_amount + sgst_amount + igst_amount
        s2.metric("Total Tax", f"₹{total_tax:,.2f}")
    else:
        s2.metric("Tax", "₹0.00")
    s3.metric("Grand Total", f"₹{grand_total:,.2f}")

    # --- Output format & Generate ---
    st.subheader("📄 Generate & Export")
    # Determine available formats
    available_formats = ["PDF"]
    can_img = HAS_PDF2IMAGE and False  # we'll test later
    # Test poppler availability by actually trying a tiny conversion later,
    # but we can just allow image options if pdf2image is imported.
    if HAS_PDF2IMAGE:
        available_formats += ["PNG Image", "WhatsApp Optimized Image"]

    output_format = st.radio("Output Format", available_formats, horizontal=True)

    if st.button("🚀 Generate Invoice", type="primary", use_container_width=True):
        if not edited_items:
            st.error("Add at least one item.")
            return

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

        pdf_buffer = generate_invoice_pdf(invoice_data, page_size,
                                          st.session_state.inv_logo_bytes)

        # Save to DB
        if db:
            if st.button("💾 Save Invoice to Database"):
                ok = db.save_invoice(invoice_data)
                if ok:
                    st.success("Invoice saved!")
                else:
                    st.error("Could not save invoice.")

        # Deliver chosen format
        if output_format == "PDF":
            st.download_button("📥 Download PDF", data=pdf_buffer,
                               file_name=f"Invoice_{inv_num}.pdf", mime="application/pdf")
        elif output_format.startswith("PNG") or "WhatsApp" in output_format:
            if not HAS_PDF2IMAGE:
                st.error("pdf2image not installed. Install it with `pip install pdf2image`.")
            else:
                try:
                    images = convert_from_bytes(pdf_buffer.getvalue(), dpi=200)
                    if output_format == "PNG Image":
                        img_buf = io.BytesIO()
                        images[0].save(img_buf, format='PNG')
                        img_buf.seek(0)
                        st.download_button("📥 Download PNG", data=img_buf,
                                           file_name=f"Invoice_{inv_num}.png", mime="image/png")
                        st.image(images[0], caption="Invoice Preview")
                    else:  # WhatsApp optimised
                        img = images[0]
                        w_percent = 800 / float(img.size[0])
                        h_size = int(float(img.size[1]) * w_percent)
                        img = img.resize((800, h_size), Image.LANCZOS)
                        img_buf = io.BytesIO()
                        img.save(img_buf, format='JPEG', quality=85)
                        img_buf.seek(0)
                        st.download_button("📥 Download for WhatsApp", data=img_buf,
                                           file_name=f"Invoice_{inv_num}_wa.jpg", mime="image/jpeg")
                        st.image(img, caption="WhatsApp Preview (800px)")
                except Exception as e:
                    st.error("❌ Could not convert PDF to image. This usually means `poppler` is missing.")
                    st.info("Please add `poppler-utils` to `packages.txt` or use PDF format.")

        # UPI QR preview
        upi_preview = generate_upi_qr(
            st.session_state.inv_sender.get('upi_id',''),
            st.session_state.inv_sender.get('upi_name',''),
            balance_due,
            f"INV-{inv_num}"
        )
        st.image(upi_preview, caption="Dynamic UPI QR", width=150)

    # --- Saved Invoices (if DB connected) ---
    if db:
        st.markdown("---")
        st.subheader("📚 Saved Invoices")
        invoices = db.get_invoices()
        if invoices:
            for inv in invoices:
                with st.expander(f"{inv.get('invoice_number','')} – {inv.get('created_at','')[:10]}"):
                    # Parse the stored JSON
                    data = json.loads(inv['data'])
                    st.write(f"**Client:** {data['client']['name']}")
                    st.write(f"**Total:** ₹{data['grand_total']:,.2f}")
                    st.write(f"**Date:** {data['date_issued']}")
                    if st.button("🗑 Delete", key=f"del_inv_{inv['id']}"):
                        if db.delete_invoice(inv['id']):
                            st.success("Deleted!")
                            st.rerun()
        else:
            st.info("No saved invoices yet.")
