"""
Enterprise Invoice Generator (rewrite)
Dynamic categories, tax, logo, QR, save/delete, multi-format export
"""
import streamlit as st
import pandas as pd
import io, json, base64
from datetime import datetime, date, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import qrcode
from PIL import Image

# Optional image export
try:
    from pdf2image import convert_from_bytes
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def generate_upi_qr(upi_id, name, amount, ref):
    upi_str = f"upi://pay?pa={upi_id}&pn={name}&am={amount:.2f}&tn={ref}&cu=INR"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(upi_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def generate_bank_qr(text):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def build_pdf(invoice, page_size, logo_bytes):
    buf = io.BytesIO()
    pw, ph = page_size
    c = canvas.Canvas(buf, pagesize=page_size)
    w, h = pw, ph
    ml, mr, mt, mb = 25*mm, 25*mm, 20*mm, 20*mm
    usable_w = w - ml - mr

    # Logo
    if logo_bytes:
        logo_buf = io.BytesIO(logo_bytes)
        logo = ImageReader(logo_buf)
        lw, lh = 50*mm, 20*mm
        c.drawImage(logo, ml, h - mt - lh, width=lw, height=lh,
                    preserveAspectRatio=True, mask='auto')
        header_y = h - mt - 10*mm
    else:
        header_y = h - mt - 10*mm

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(ml, header_y, "INVOICE")

    # Sender
    c.setFont("Helvetica", 9)
    sender = invoice['sender']
    tx = w - mr - 80*mm
    ty = h - mt - 10*mm
    for line in [sender['company'], sender['address'], f"Phone: {sender['phone']}", f"Email: {sender['email']}"]:
        c.drawString(tx, ty, line)
        ty -= 4*mm

    # Bill To
    c.setFont("Helvetica-Bold", 10)
    ty = h - mt - (35*mm if logo_bytes else 28*mm)
    c.drawString(ml, ty, "Billed To")
    ty -= 5*mm
    c.setFont("Helvetica", 9)
    client = invoice['client']
    c.drawString(ml, ty, client['name'])
    ty -= 4*mm
    c.drawString(ml, ty, client['address'])
    ty -= 4*mm
    if client.get('city'):
        c.drawString(ml, ty, f"{client['city']}, {client.get('state','')} {client.get('zip','')}")
        ty -= 4*mm
    c.drawString(ml, ty, client.get('country',''))

    # Dates & Number
    c.setFont("Helvetica-Bold", 9)
    tx = w - mr - 80*mm
    ty = h - mt - 45*mm
    labels = [("Date Issued", invoice['date_issued']),
              ("Invoice Number", invoice['invoice_number']),
              ("Due Date", invoice['due_date']),
              ("Amount Due", f"INR {invoice['grand_total']:,.2f}")]
    for lbl, val in labels:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(tx, ty, lbl)
        c.setFont("Helvetica", 9)
        c.drawString(tx + 35*mm, ty, val)
        ty -= 5*mm

    # Items table
    table_top = h - mt - (95*mm if logo_bytes else 88*mm)
    data = [['Description', 'Rate', 'Qty', 'Amount']]
    for it in invoice['items']:
        data.append([it['description'], f"{it['rate']:,.2f}", str(it['qty']), f"{it['amount']:,.2f}"])
    if invoice.get('tax_enabled'):
        data.append(['', '', 'Taxable Amount', f"{invoice['taxable_amount']:,.2f}"])
        if invoice.get('cgst_rate',0) > 0:
            data.append(['', '', f"CGST @{invoice['cgst_rate']}%", f"{invoice['cgst_amount']:,.2f}"])
        if invoice.get('sgst_rate',0) > 0:
            data.append(['', '', f"SGST @{invoice['sgst_rate']}%", f"{invoice['sgst_amount']:,.2f}"])
        if invoice.get('igst_rate',0) > 0:
            data.append(['', '', f"IGST @{invoice['igst_rate']}%", f"{invoice['igst_amount']:,.2f}"])
    data.append(['', '', 'Grand Total', f"{invoice['grand_total']:,.2f}"])
    data.append(['', '', 'Balance Due', f"{invoice['balance_due']:,.2f}"])

    col_widths = [usable_w*0.55, usable_w*0.15, usable_w*0.1, usable_w*0.2]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
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
        ('BACKGROUND', (0,-3), (-1,-1), colors.white),
        ('FONTNAME', (0,-3), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,-3), (-1,-1), 'RIGHT'),
        ('LINEABOVE', (0,-3), (-1,-3), 1, colors.black),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.black),
    ]))
    tw, th = t.wrap(0, 0)
    t.drawOn(c, ml, table_top - th)

    # Notes & Terms
    ty = table_top - th - 10*mm
    if invoice.get('notes'):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(ml, ty, "Notes")
        ty -= 4*mm
        c.setFont("Helvetica", 8)
        for line in invoice['notes'].split('\n'):
            c.drawString(ml, ty, line.strip())
            ty -= 3.5*mm
    if invoice.get('terms'):
        ty -= 5*mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(ml, ty, "Terms")
        ty -= 4*mm
        c.setFont("Helvetica", 8)
        c.drawString(ml, ty, invoice['terms'])

    # QR codes
    upi_buf = generate_upi_qr(sender.get('upi_id',''), sender.get('upi_name',''),
                              invoice['balance_due'], f"INV-{invoice['invoice_number']}")
    upi_img = ImageReader(upi_buf)
    qr_size = 35*mm
    c.drawImage(upi_img, w - mr - qr_size - 5*mm, 20*mm, width=qr_size, height=qr_size)
    c.setFont("Helvetica", 6)
    c.drawString(w - mr - qr_size - 5*mm, 18*mm, "Scan to Pay (UPI)")
    if sender.get('bank_details'):
        bank_buf = generate_bank_qr(sender['bank_details'])
        bank_img = ImageReader(bank_buf)
        c.drawImage(bank_img, w - mr - 2*qr_size - 10*mm, 20*mm, width=qr_size, height=qr_size)
        c.setFont("Helvetica", 6)
        c.drawString(w - mr - 2*qr_size - 10*mm, 18*mm, "Bank Details")

    c.setFont("Helvetica", 7)
    c.drawString(ml, 10*mm, f"Generated by GrowLeafy | {invoice['date_issued']}")
    c.save()
    buf.seek(0)
    return buf

# -------------------------------------------------------------------
# Main UI
# -------------------------------------------------------------------
def render(db=None):
    st.title("🧾 Invoice Generator")
    st.caption("Dynamic categories · Tax · QR · Save & export")

    # Session state defaults
    for key, val in {
        'sender': {
            'company': 'Biswas Ventures',
            'address': 'Madhabpur - Panpur Road\nPanpur, WB 743126',
            'phone': '9903026500',
            'email': 'biswas4trade@gmail.com',
            'bank_details': 'A/C: Subhasis Biswas\nA/C No: 32781178011\nIFSC: SBIN0006042\nBranch: RATHTALA\nSBI',
            'upi_id': '9903026500@upi',
            'upi_name': 'Subhasis Biswas'
        },
        'client': {'name':'','address':'','city':'','state':'','zip':'','country':'India'},
        'items': [],
        'tax_enabled': False,
        'logo_bytes': None,
        'prefix': 'BV/MLP',
    }.items():
        if key not in st.session_state: st.session_state[key] = val

    # Page size & Invoice number
    col1, col2 = st.columns(2)
    with col1: page_format = st.selectbox("Page Size", ["A4", "Letter"])
    with col2:
        auto = st.checkbox("Auto invoice number", True)
        if auto:
            if st.button("🔄 New Number"):
                if db: st.session_state['inv_num'] = db.get_next_invoice_number(st.session_state.prefix); st.rerun()
                else: st.warning("No DB")
            inv_num = st.text_input("Invoice Number", value=st.session_state.get('inv_num',''))
        else:
            inv_num = st.text_input("Invoice Number", value="BV/MLP/2025/01")
    page_size = A4 if page_format == "A4" else LETTER

    # Sender & Client
    with st.expander("🏢 Sender Details", False):
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.sender['company'] = st.text_input("Company", st.session_state.sender['company'])
            st.session_state.sender['address'] = st.text_area("Address", st.session_state.sender['address'], height=80)
        with c2:
            st.session_state.sender['phone'] = st.text_input("Phone", st.session_state.sender['phone'])
            st.session_state.sender['email'] = st.text_input("Email", st.session_state.sender['email'])
            st.session_state.sender['bank_details'] = st.text_area("Bank Details", st.session_state.sender['bank_details'], height=80)
            st.session_state.sender['upi_id'] = st.text_input("UPI ID", st.session_state.sender.get('upi_id',''))
            st.session_state.sender['upi_name'] = st.text_input("Payee Name", st.session_state.sender.get('upi_name',''))
        logo_file = st.file_uploader("Logo", type=["png","jpg","jpeg"])
        if logo_file: st.session_state.logo_bytes = logo_file.read()
        elif st.session_state.logo_bytes and st.button("Remove logo"): st.session_state.logo_bytes = None; st.rerun()

    with st.expander("🧾 Client Details", True):
        c3, c4 = st.columns(2)
        with c3:
            st.session_state.client['name'] = st.text_input("Client Name", st.session_state.client['name'])
            st.session_state.client['address'] = st.text_area("Address", st.session_state.client['address'], height=80)
        with c4:
            st.session_state.client['city'] = st.text_input("City", st.session_state.client['city'])
            st.session_state.client['state'] = st.text_input("State", st.session_state.client['state'])
            st.session_state.client['zip'] = st.text_input("ZIP", st.session_state.client['zip'])
            st.session_state.client['country'] = st.text_input("Country", st.session_state.client['country'])

    d1, d2 = st.columns(2)
    with d1: date_issued = st.date_input("Date Issued", date.today())
    with d2: due_date = st.date_input("Due Date", date.today()+timedelta(days=30))

    # Tax
    tax_on = st.checkbox("Enable Tax (GST)", st.session_state.tax_enabled)
    st.session_state.tax_enabled = tax_on
    cgst = sgst = igst = 0.0
    if tax_on:
        t1,t2,t3 = st.columns(3)
        with t1: cgst = st.number_input("CGST %", 0.0, 100.0, 9.0, 0.5)
        with t2: sgst = st.number_input("SGST %", 0.0, 100.0, 9.0, 0.5)
        with t3: igst = st.number_input("IGST %", 0.0, 100.0, 18.0, 0.5)

    # --- Item import from DB (dynamic categories) ---
    if db:
        with st.expander("📦 Import from database", False):
            # Category -> table mapping
            cat_table = {
                "Plants": "plants",
                "Potting Mix & Fertilizers": "fertilizers",
                "Pest Control": "insecticides",   # or merged table
                "Pots & Planters": "pots_planters",
                "Seeds": "seeds",
                "Garden Tools": "garden_tools",
                "Watering Tools": "watering_tools",
                "Garden Decor": "garden_decor",
            }
            sel_cat = st.selectbox("Category", list(cat_table.keys()))
            table = cat_table[sel_cat]
            subs = db.get_distinct_subcategories(table)
            subs.insert(0, "All")
            sel_sub = st.selectbox("Subcategory", subs)

            if st.button("🔍 Fetch"):
                try:
                    data = db.fetch_all(table)
                    if data:
                        df = pd.DataFrame(data)
                        if sel_sub != "All" and "subcategory" in df.columns:
                            df = df[df["subcategory"] == sel_sub]
                        if not df.empty:
                            idx = st.selectbox("Item", df.index,
                                format_func=lambda x: f"{df.iloc[x].get('name', df.iloc[x].get('product_name','?'))} (SKU: {df.iloc[x].get('sku','')})")
                            if st.button("➕ Add to invoice"):
                                row = df.iloc[idx]
                                st.session_state.items.append({
                                    'description': f"{row.get('name', row.get('product_name','Item'))} ({row.get('sku','')})",
                                    'rate': row.get('mrp',0.0),
                                    'qty': 1,
                                    'amount': row.get('mrp',0.0)
                                })
                                st.rerun()
                        else: st.info("No items match.")
                    else: st.info("Table empty.")
                except Exception as e: st.error(f"Error: {e}")

    # Manual items
    st.subheader("📋 Items")
    edited = []
    for i, it in enumerate(st.session_state.items):
        cols = st.columns([4,1.5,1,1.5,0.8])
        with cols[0]: desc = st.text_input(f"Desc {i+1}", it['description'], key=f"d{i}")
        with cols[1]: rate = st.number_input(f"Rate {i+1}", float(it['rate']), min_value=0.0, format="%.2f", key=f"r{i}")
        with cols[2]: qty = st.number_input(f"Qty {i+1}", int(it['qty']), min_value=1, key=f"q{i}")
        with cols[3]: st.write(f"₹{rate*qty:,.2f}")
        with cols[4]:
            if st.button("🗑", key=f"del{i}"):
                del st.session_state.items[i]; st.rerun()
        edited.append({'description': desc, 'rate': rate, 'qty': qty, 'amount': rate*qty})
    if st.button("➕ Add Row", use_container_width=True):
        st.session_state.items.append({'description':'','rate':0.0,'qty':1,'amount':0.0}); st.rerun()

    n1, n2 = st.columns(2)
    with n1: notes = st.text_area("Notes", "A/C name : Subhasis Biswas\nAccount No. : 32781178011\nIFSC : SBIN0006042\nBRANCH : RATHTALA\nSTATE BANK OF INDIA", height=100)
    with n2: terms = st.text_area("Terms", "Payable within 30 days. TDS may be deducted.", height=100)

    # Calculations
    subtotal = sum(it['amount'] for it in edited)
    taxable = subtotal
    cgst_amt = round(taxable * cgst / 100, 2)
    sgst_amt = round(taxable * sgst / 100, 2)
    igst_amt = round(taxable * igst / 100, 2)
    total = taxable + cgst_amt + sgst_amt + igst_amt
    balance = total

    st.subheader("💰 Summary")
    c1,c2,c3 = st.columns(3)
    c1.metric("Subtotal", f"₹{subtotal:,.2f}")
    c2.metric("Tax", f"₹{cgst_amt+sgst_amt+igst_amt:,.2f}" if tax_on else "₹0.00")
    c3.metric("Grand Total", f"₹{total:,.2f}")

    # Export options
    st.subheader("📄 Export")
    formats = ["PDF"]
    if HAS_PDF2IMAGE: formats += ["PNG Image", "WhatsApp Image"]
    out_fmt = st.radio("Format", formats, horizontal=True)

    if st.button("🚀 Generate Invoice", type="primary", use_container_width=True):
        if not edited: st.error("Add at least one item."); return
        inv = {
            'sender': st.session_state.sender,
            'client': st.session_state.client,
            'invoice_number': inv_num,
            'date_issued': date_issued.strftime("%B %d, %Y"),
            'due_date': due_date.strftime("%B %d, %Y"),
            'items': edited,
            'taxable_amount': taxable,
            'cgst_rate': cgst, 'sgst_rate': sgst, 'igst_rate': igst,
            'cgst_amount': cgst_amt, 'sgst_amount': sgst_amt, 'igst_amount': igst_amt,
            'tax_enabled': tax_on,
            'grand_total': total,
            'balance_due': balance,
            'notes': notes, 'terms': terms
        }
        pdf_buf = build_pdf(inv, page_size, st.session_state.logo_bytes)

        # Save
        if db and st.button("💾 Save to database"):
            if db.save_invoice(inv): st.success("Saved")
            else: st.error("Failed")

        # Deliver
        if out_fmt == "PDF":
            st.download_button("📥 Download PDF", pdf_buf, f"Invoice_{inv_num}.pdf", "application/pdf")
        else:
            try:
                imgs = convert_from_bytes(pdf_buf.getvalue(), dpi=200)
                if out_fmt == "PNG Image":
                    buf = io.BytesIO(); imgs[0].save(buf, format='PNG'); buf.seek(0)
                    st.download_button("📥 Download PNG", buf, f"Invoice_{inv_num}.png", "image/png")
                    st.image(imgs[0])
                else:
                    img = imgs[0].resize((800, int(imgs[0].size[1]*800/imgs[0].size[0])), Image.LANCZOS)
                    buf = io.BytesIO(); img.save(buf, format='JPEG', quality=85); buf.seek(0)
                    st.download_button("📥 WhatsApp Image", buf, f"Invoice_{inv_num}_wa.jpg", "image/jpeg")
                    st.image(img)
            except Exception as e:
                st.error("Image conversion failed. Missing poppler? Use PDF.")

        # UPI QR preview
        upi_buf = generate_upi_qr(st.session_state.sender.get('upi_id',''),
                                  st.session_state.sender.get('upi_name',''), balance, inv_num)
        st.image(upi_buf, "Payment QR (amount pre‑filled)", width=150)

    # Saved invoices
    if db:
        st.markdown("---")
        st.subheader("📚 Saved Invoices")
        invs = db.get_invoices()
        if invs:
            for inv in invs:
                with st.expander(f"{inv.get('invoice_number','')} – {inv.get('created_at','')[:10]}"):
                    d = json.loads(inv['data'])
                    st.write(f"Client: {d['client']['name']}, Total: ₹{d['grand_total']:,.2f}")
                    if st.button("🗑 Delete", key=f"delinv{inv['id']}"):
                        if db.delete_invoice(inv['id']): st.success("Deleted"); st.rerun()
        else:
            st.info("No saved invoices.")
