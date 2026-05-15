import re
from datetime import datetime
import pdfplumber
from logic import calculate_row

def _fmt_date(raw):
    for fmt in ["%d %b, %Y","%d %B, %Y"]:
        try: return datetime.strptime(raw.strip(), fmt).strftime("%#d-%b-%y")
        except: pass
    return raw.strip()

def _extract_ship_mode_map(po_pdf):
    """
    Parse the PO PDF to build a per-country ship mode map.

    In H&M PO PDFs the layout inside "Terms of Delivery" is:
        <country codes on one line>
        Transport by Air.  Packing Mode ...
        <country codes on next block>
        Transport by Sea.  Packing Mode ...

    So the country codes appear ON THE LINE(S) IMMEDIATELY BEFORE each
    "Transport by Air / Sea" label.  We scan every line of the full text,
    remember the most-recent "country-code line", and as soon as we hit a
    Transport line we assign that mode to those countries.

    A "country-code line" is a line that contains ONLY comma/space-separated
    2-letter uppercase codes — e.g. "DE, BE, US, JP, CH, CA, TR, MX, CO, EC, GB"
    or a single code like "IN".

    Returns dict like {"DE": "AIR", "IN": "SEA", ...}
    """
    ship_mode_map = {}
    try:
        with pdfplumber.open(po_pdf) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"

        lines = full_text.splitlines()

        # Regex: a line whose non-space content is ONLY 2-letter codes + commas
        country_line_re = re.compile(
            r"^\s*([A-Z]{2}(?:\s*,\s*[A-Z]{2})*)\s*$"
        )
        transport_re = re.compile(
            r"Transport\s+by\s+(Air|Sea)", re.IGNORECASE
        )

        pending_countries = set()   # country codes seen before the next Transport line

        for line in lines:
            m_transport = transport_re.search(line)
            if m_transport:
                mode = "AIR" if m_transport.group(1).lower() == "air" else "SEA"
                for code in pending_countries:
                    ship_mode_map[code] = mode
                pending_countries = set()
                continue

            m_codes = country_line_re.match(line)
            if m_codes:
                # replace pending with this fresh set of codes
                codes = {c.strip() for c in m_codes.group(1).split(",")}
                pending_countries = codes
            else:
                # Not a pure country-code line and not a Transport line —
                # keep pending_countries so multi-line code blocks still work,
                # but reset if line is clearly unrelated (has lowercase words)
                if re.search(r"[a-z]{3,}", line):
                    pending_countries = set()

        # Fallback: if parsing found nothing, check which mode dominates in text
        if not ship_mode_map:
            has_air = bool(re.search(r"Transport\s+by\s+Air", full_text, re.IGNORECASE))
            has_sea = bool(re.search(r"Transport\s+by\s+Sea", full_text, re.IGNORECASE))
            # store sentinels so caller knows something was found
            if has_air and not has_sea:
                ship_mode_map["__default__"] = "AIR"
            elif has_sea and not has_air:
                ship_mode_map["__default__"] = "SEA"

    except Exception:
        pass

    return ship_mode_map


def extract_hm_records(bd_pdf, po_pdf):
    order_no=style_no=""
    season=no_of_pieces=sales_mode=total_qty=""
    delivery_map={}; country_qty={}
    color_cols={}

    with pdfplumber.open(bd_pdf) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if not order_no:
                m = re.search(r"(\d{6}-\d{4})", txt)
                if m: order_no = m.group(1)
            if not style_no:
                m = re.search(r"Product Name:\s*(.+)", txt)
                if m: style_no = m.group(1).strip()
            for tbl in page.extract_tables() or []:
                for row in tbl:
                    for i, cell in enumerate(row):
                        if cell:
                            m = re.search(r"(\d{2}-\d{3})", str(cell))
                            if m: color_cols[i] = m.group(1)

                for row in tbl:
                    if not row: continue
                    first  = str(row[0]).strip() if row[0] else ""
                    second = str(row[1]).strip() if len(row)>1 and row[1] else ""
                    if re.match(r"^[A-Z]{2}$", first):
                        if not re.match(r"^[A-Z]{2}", second): continue
                        if color_cols:
                            for i, color_code in color_cols.items():
                                if i < len(row) and row[i]:
                                    v = str(row[i]).replace(" ","").replace(",","").strip()
                                    if v.isdigit() and int(v) > 0:
                                        if first not in country_qty:
                                            country_qty[first] = []
                                        country_qty[first].append({"color_code": color_code, "qty": v})
                        else:
                            for cell in row[1:]:
                                if not cell: continue
                                v = str(cell).replace(" ","").replace(",","").strip()
                                if v.isdigit() and int(v) > 0:
                                    if first not in country_qty: country_qty[first] = []
                                    country_qty[first].append({"color_code": None, "qty": v})
                                    break

    color_names = {}
    with pdfplumber.open(po_pdf) as pdf:
        for page in pdf.pages:
            for tbl in page.extract_tables() or []:
                for row in tbl:
                    if not row: continue
                    row_j = " ".join(str(c) for c in row if c)
                    if not season:
                        for cell in row:
                            if cell and "\n" in str(cell):
                                for ln in str(cell).split("\n"):
                                    if re.match(r"^\d+-\d{4}$", ln.strip()):
                                        season = ln.strip(); break
                    if not no_of_pieces and "No of Pieces:" in row_j:
                        for ci, cell in enumerate(row):
                            if cell and "No of Pieces:" in str(cell):
                                for vc in row[ci+1:]:
                                    if vc and str(vc).strip():
                                        lines = str(vc).strip().split("\n")
                                        if lines[0].strip().isdigit(): no_of_pieces = lines[0].strip()
                                        if len(lines) >= 2: sales_mode = lines[1].strip()
                                        break
                                break
                    dc = str(row[1]).strip() if len(row)>1 and row[1] else ""
                    mc = str(row[4]).strip() if len(row)>4 and row[4] else ""
                    dm = re.match(r"^(\d{1,2}\s+\w+,\s+\d{4})$", dc)
                    if dm and mc:
                        fmt = _fmt_date(dm.group(1))
                        for match in re.finditer(r"\b([A-Z]{2})\s*\(", mc):
                            delivery_map[match.group(1)] = fmt
                        if not any(c in delivery_map for c in re.findall(r"\b([A-Z]{2})\b", mc)):
                            for code in re.findall(r"\b([A-Z]{2})\b", mc):
                                if code not in ("PM","OL","OE","OF","SW"):
                                    delivery_map[code] = fmt
                    if not total_qty:
                        for cell in row:
                            if cell and str(cell).strip() == "Total:":
                                for c2 in row:
                                    if c2 and str(c2).strip() != "Total:":
                                        cl = str(c2).replace(" ","").replace(",","").strip()
                                        if cl.isdigit() and int(cl)>100: total_qty=cl; break
                                break
                    
                    for ci, cell in enumerate(row):
                        if cell and re.match(r"^\d{2}-\d{3}$", str(cell).strip()):
                            code = str(cell).strip()
                            for rv in row[ci+1:]:
                                rv_s = str(rv).strip() if rv else ""
                                if rv_s and not re.match(r"^\d",rv_s) and "SQ" not in rv_s and "USD" not in rv_s:
                                    color_names[code] = rv_s; break

    # ── Build per-country ship mode from PO PDF ────────────────────────────────
    ship_mode_map = _extract_ship_mode_map(po_pdf)
    # If only a __default__ sentinel exists, apply it to all countries
    default_mode = ship_mode_map.pop("__default__", None)

    records = []
    for country, qty_list in country_qty.items():
        # Look up this country; fall back to __default__ if set, else SEA
        if country in ship_mode_map:
            ship_mode = ship_mode_map[country]
        elif default_mode:
            ship_mode = default_mode
        else:
            ship_mode = "SEA"  # absolute last resort

        for item in qty_list:
            qty = item["qty"]
            ccode = item["color_code"]
            cname = color_names.get(ccode, "") if ccode else (list(color_names.values())[0] if color_names else "")
            c_code_str = ccode if ccode else (list(color_names.keys())[0] if color_names else "")
            
            colour = f"{cname} {c_code_str}".strip()
            
            row = {
                "order_no":order_no,"style_name":style_no,"colour":colour,"order_qty":qty,
                "tod":delivery_map.get(country,""),"country":country,"order_qty_set":qty,
                "no_of_pcs":no_of_pieces,"ship_mode":ship_mode,"season":season,
                "sales_mode":sales_mode,"total_order_qty":total_qty,
                "hm_merch":"","hm_tech":"","factory_merch":"",
                "ship_qty_set":"","carton_qty":"","first_last":"","shipped_status":"",
            }
            records.append(calculate_row(row))
    return records

def extract_store_breakdown_records(pdf_path):
    """
    Parses 'Size / Colour Breakdown - Store' PDF format with extreme robustness.
    Uses a hybrid text and table approach to handle fragmented data.
    """
    records = []
    order_no = style_name = season = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            
            # 1. Extract Header Info
            if not order_no:
                m = re.search(r"Order No:\s*(\d{6}-\d{4})", txt)
                if m: order_no = m.group(1)
            if not style_name:
                m = re.search(r"Product Name:\s*(.+)", txt)
                if m: style_name = m.group(1).strip()
            if not season:
                m = re.search(r"Season:\s*(\d+-\d{4})", txt)
                if m: season = m.group(1).strip()
            
            # 2. Extract Country (e.g., Japan JP (PM-JP) or Ecuador EC (PM-EC))
            country_code = ""
            m_country = re.search(r"Size / Colour breakdown\s*\n?\s*(.+?)\s+([A-Z]{2})\s*\(", txt, re.IGNORECASE)
            if m_country:
                country_code = m_country.group(2)
            else:
                # Broader search for country-like line
                m_fallback = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([A-Z]{2})\s*\(", txt)
                if m_fallback:
                    country_code = m_fallback.group(2)
            
            if not country_code: continue

            # 3. Extract Colors from Text (more reliable than tables for headers)
            # Find the color codes
            color_codes = []
            m_codes = re.search(r"H&M Colour Code:\s*(.+)", txt)
            if m_codes:
                color_codes = re.findall(r"(\d{2}-\d{3})", m_codes.group(1))
            
            # Find the color names (this is tricky, so we'll use the codes count)
            # We'll try to extract them from the "Colour Name:" line
            color_names = []
            m_names = re.search(r"Colour Name:\s*(.+)", txt)
            if m_names:
                # A bit of a hack: if we have the codes, we know how many names to expect
                raw_names = m_names.group(1).strip()
                # If there's only one code, the whole line is the name
                if len(color_codes) == 1:
                    color_names = [raw_names]
                else:
                    # For multiple, it's harder. Let's look for known color name patterns 
                    # or just split and hope for the best, or just use the code.
                    # Actually, let's just use the codes as the "name" if we can't split safely.
                    color_names = [raw_names] # Fallback
            
            # 4. Extract Quantities from Tables
            quantities = []
            tables = page.extract_tables()
            if tables:
                for tbl in tables:
                    for row in tbl:
                        row_str = [str(c).strip() if c else "" for c in row]
                        if any("Quantity" in cell for cell in row_str):
                            # Clean row to find numeric values
                            vals = []
                            for cell in row_str:
                                v = cell.replace(" ", "").replace(",", "").strip()
                                if v.isdigit() and int(v) > 0:
                                    vals.append(v)
                            # If we found values, these are likely our quantities
                            if vals:
                                quantities = vals
                                break
                    if quantities: break
            
            # 5. Map and Build Records
            # We match quantities to color codes by index
            for i, qty in enumerate(quantities):
                if i < len(color_codes):
                    code = color_codes[i]
                    name = color_names[0] if len(color_names) == 1 else (color_names[i] if i < len(color_names) else "")
                    colour = f"{name} {code}".strip()
                    
                    rec = {
                        "order_no": order_no,
                        "style_name": style_name,
                        "colour": colour,
                        "order_qty": qty,
                        "tod": "", 
                        "country": country_code,
                        "order_qty_set": qty,
                        "no_of_pcs": "",
                        "ship_mode": "SEA",
                        "season": season,
                        "sales_mode": "",
                        "total_order_qty": "",
                        "hm_merch": "", "hm_tech": "", "factory_merch": "",
                        "ship_qty_set": "", "carton_qty": "", "first_last": "", "shipped_status": "",
                    }
                    records.append(calculate_row(rec))
    
    # 6. Post-process Totals
    total_all = sum(int(r["order_qty"]) for r in records if r["order_qty"].isdigit())
    for r in records:
        r["total_order_qty"] = str(total_all)
        
    return records
