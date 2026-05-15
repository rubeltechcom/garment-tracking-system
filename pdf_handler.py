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
    Parses 'Size / Colour Breakdown - Store' PDF format.
    Extracts data per page (usually one country per page).
    """
    records = []
    order_no = style_name = season = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            
            # Extract header info once
            if not order_no:
                m = re.search(r"Order No:\s*(\d{6}-\d{4})", txt)
                if m: order_no = m.group(1)
            if not style_name:
                m = re.search(r"Product Name:\s*(.+)", txt)
                if m: style_name = m.group(1).strip()
            if not season:
                m = re.search(r"Season:\s*(\d+-\d{4})", txt)
                if m: season = m.group(1).strip()
            
            # Extract Country
            # Format: Japan - JP (PM - IP)
            country_code = ""
            # More flexible search for the breakdown header and country line
            m_country = re.search(r"Size / Colour breakdown\s*\n?\s*(.+)\s+-\s+([A-Z]{2})\s*\(", txt, re.IGNORECASE)
            if m_country:
                country_code = m_country.group(2)
            else:
                # Fallback: just look for the pattern "Name - XX ("
                m_fallback = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+-\s+([A-Z]{2})\s*\(", txt)
                if m_fallback:
                    country_code = m_fallback.group(2)
            
            # Extract Table Data
            tables = page.extract_tables()
            if not tables: continue
            
            for tbl in tables:
                color_map = {} # col_index -> {code, name}
                quantity_row = None
                
                # Normalize table rows: strip and handle None
                clean_tbl = []
                for row in tbl:
                    clean_tbl.append([str(c).strip() if c else "" for c in row])
                
                for row_idx, row_str in enumerate(clean_tbl):
                    # Identify Color Columns
                    if any("Colour Name" in cell for cell in row_str):
                        # Find the color code row (usually 1-2 rows above)
                        code_row = None
                        for i in range(max(0, row_idx-3), row_idx):
                            if any("Colour Code" in c for c in clean_tbl[i]):
                                code_row = clean_tbl[i]; break
                        
                        for i, cell in enumerate(row_str):
                            # Skip the first column (labels)
                            if i > 0 and cell and cell.lower() != "colour name":
                                color_map[i] = {
                                    "name": cell,
                                    "code": code_row[i] if code_row and i < len(code_row) else ""
                                }
                    
                    # Find Quantity Row - specifically the one that has numbers matching our colors
                    if any("Quantity" in cell for cell in row_str):
                        # We want the one that likely corresponds to the Total section
                        # (Usually the last one or one with large numbers)
                        quantity_row = row_str
                
                if quantity_row and color_map and country_code:
                    for col_idx, color_info in color_map.items():
                        if col_idx < len(quantity_row):
                            qty_val = quantity_row[col_idx].replace(" ", "").replace(",", "").strip()
                            if qty_val.isdigit() and int(qty_val) > 0:
                                colour = f"{color_info['name']} {color_info['code']}".strip()
                                rec = {
                                    "order_no": order_no,
                                    "style_name": style_name,
                                    "colour": colour,
                                    "order_qty": qty_val,
                                    "tod": "", 
                                    "country": country_code,
                                    "order_qty_set": qty_val,
                                    "no_of_pcs": "",
                                    "ship_mode": "SEA",
                                    "season": season,
                                    "sales_mode": "",
                                    "total_order_qty": "",
                                    "hm_merch": "", "hm_tech": "", "factory_merch": "",
                                    "ship_qty_set": "", "carton_qty": "", "first_last": "", "shipped_status": "",
                                }
                                records.append(calculate_row(rec))
    
    # Post-process to set total_order_qty as sum of all colors
    total_all = sum(int(r["order_qty"]) for r in records if r["order_qty"].isdigit())
    for r in records:
        r["total_order_qty"] = str(total_all)
        
    return records
