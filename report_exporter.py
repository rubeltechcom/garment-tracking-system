import os
import json
import ast
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def export_store_pdf(records, output_path, settings):
    """
    Exports records to a specialized 'Tasniah Fabric Ltd' PDF report.
    Groups data by Order No and Colour.
    """
    # 1. Group records
    groups = {}
    for r in records:
        key = (r.get("order_no", ""), r.get("colour", ""))
        if key not in groups: groups[key] = []
        groups[key].append(r)

    c = canvas.Canvas(output_path, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    for (order_no, colour), group_recs in groups.items():
        # Each group gets its own page(s)
        # We'll assume a single page per group for now, or handle pagination
        _draw_page(c, order_no, colour, group_recs, settings, width, height)
        c.showPage()
        
    c.save()

def _draw_page(c, order_no, colour, records, settings, w, h):
    # Company Header
    margin = 30
    curr_y = h - margin
    
    # Logo (if exists)
    logo_path = settings.get("logo_path")
    if logo_path and os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, margin, curr_y - 40, width=50, height=40, preserveAspectRatio=True)
        except: pass

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w/2, curr_y - 10, settings.get("company_name", "Tasniah Fabric Ltd").upper())
    c.setFont("Helvetica", 10)
    c.drawCentredString(w/2, curr_y - 25, settings.get("company_subtitle", "Nayapara, Kashimpur, Gazipur"))
    
    curr_y -= 50
    
    # Top Fields Bar
    c.setLineWidth(1)
    c.rect(margin, curr_y - 60, w - 2*margin, 60)
    
    # Field Labels
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin + 5, curr_y - 15, "Buyer :")
    c.drawString(margin + 5, curr_y - 30, "Order No.")
    c.drawString(margin + 5, curr_y - 45, "Style :")
    c.drawString(margin + 5, curr_y - 58, "Order Qty :")
    
    # Field Values (Left side)
    c.setFont("Helvetica", 10)
    c.drawString(margin + 80, curr_y - 15, "H&M")
    c.drawString(margin + 80, curr_y - 30, order_no)
    c.drawString(margin + 80, curr_y - 45, records[0].get("style_name", ""))
    c.drawString(margin + 80, curr_y - 58, f"{records[0].get('total_order_qty', '0')}  Set")
    
    # Right side fields
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w/2 + 50, curr_y - 15, "Mode")
    c.drawString(w/2 + 50, curr_y - 30, "Update :")
    c.drawString(w/2 + 50, curr_y - 45, "No of Pieces:")
    c.drawString(w/2 + 50, curr_y - 58, "Season:")
    
    c.setFont("Helvetica", 10)
    c.drawString(w/2 + 130, curr_y - 15, records[0].get("ship_mode", "SEA"))
    c.drawString(w/2 + 130, curr_y - 30, datetime.now().strftime("%d-%b-%y"))
    c.drawString(w/2 + 130, curr_y - 45, records[0].get("no_of_pcs", ""))
    c.drawString(w/2 + 130, curr_y - 58, records[0].get("season", ""))
    
    curr_y -= 80
    
    # Table Content
    # First, identify ALL sizes across this group
    all_sizes = set()
    for r in records:
        bd_str = r.get("breakdown", "{}")
        try:
            bd = ast.literal_eval(bd_str)
            all_sizes.update(bd.keys())
        except: pass
    
    # Sort sizes (if they follow a pattern like numbers or ranges)
    sorted_sizes = sorted(list(all_sizes))
    
    # Table Headers
    cols = ["COUNTRY"] + sorted_sizes + ["CUT-OFF TOTAL", "CUT OFF", "SHIP DATE", "MODE"]
    data = [cols]
    
    # Group Totals Logic
    # We'll follow the user's template: row, then Cut Off Total=, then Sub Total=
    grand_total_sizes = {sz: 0 for sz in sorted_sizes}
    
    for r in records:
        bd_str = r.get("breakdown", "{}")
        try: bd = ast.literal_eval(bd_str)
        except: bd = {}
        
        row = [r.get("country", "")]
        row_total = 0
        for sz in sorted_sizes:
            v = int(bd.get(sz, 0))
            row.append(str(v))
            row_total += v
            grand_total_sizes[sz] += v
            
        row += [str(row_total), r.get("cut_off", ""), r.get("tod", ""), r.get("ship_mode", "")]
        data.append(row)
        
        # Add a 'Cut Off Total' row after each entry? 
        # In the image, it seems grouped. Let's just add one at the end for now.
    
    # Grand Totals
    total_row = ["Sub Total="]
    gt = 0
    for sz in sorted_sizes:
        v = grand_total_sizes[sz]
        total_row.append(str(v))
        gt += v
    total_row += [str(gt), "", "", ""]
    data.append(total_row)
    
    # Draw Table
    # Calculate column widths
    cw = [70] # Country (narrower)
    num_sizes = len(sorted_sizes)
    # Available width for sizes and other cols
    # w is ~842 for A4 landscape. margin is 30. rem_w = 842 - 60 - 70 - 70 - 60 - 70 - 40 = 472
    rem_w = w - 2*margin - 70 - 70 - 60 - 70 - 40 
    size_w = max(25, rem_w / num_sizes) if num_sizes > 0 else 40
    for _ in sorted_sizes: cw.append(size_w)
    cw += [70, 60, 70, 40] # CUT-OFF TOTAL, CUT OFF, SHIP DATE, MODE
    
    # We'll use Paragraphs for headers to allow wrapping or smaller fonts
    header_style = ParagraphStyle('Hdr', fontName='Helvetica-Bold', fontSize=7, alignment=1, leading=8)
    styled_headers = [Paragraph(cols[0], header_style)]
    for sz in sorted_sizes:
        # If size name is long, it will wrap
        styled_headers.append(Paragraph(sz, header_style))
    for h in cols[num_sizes+1:]:
        styled_headers.append(Paragraph(h, header_style))
    
    data[0] = styled_headers
    
    t = Table(data, colWidths=cw, repeatRows=1)
    
    # Professional Styling
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")), # Navy Header
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
    ]
    
    # Highlight Totals rows
    for i, row in enumerate(data):
        if i == 0: continue
        if str(row[0]).startswith("Sub Total="):
            ts.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#60A5FA")))
            ts.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
        elif str(row[0]).startswith("Cut Off Total="):
            ts.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#93C5FD")))
            ts.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
            
    t.setStyle(TableStyle(ts))
    
    # Calculate table height and draw
    tw, th = t.wrap(w - 2*margin, h)
    t.drawOn(c, margin, curr_y - th)

