from datetime import datetime, timedelta
from config import COUNTRY_CUTOFF

def calculate_row(row: dict) -> dict:
    r = dict(row)
    def _i(k):
        try: return int(str(r.get(k,"") or "0").replace(",","").strip())
        except (ValueError, TypeError): return 0
    nop  = _i("no_of_pcs") or 1
    oset = _i("order_qty_set")
    sset = _i("ship_qty_set")
    r["order_qty_pcs"] = str(oset * nop) if oset else r.get("order_qty_pcs","")
    r["ship_qty_pcs"]  = str(sset * nop) if sset else ""
    r["short_excess"]  = str(sset - oset) if sset else ""
    tod = str(r.get("tod","") or "")
    if tod:
        for fmt in ["%d-%b-%y","%d-%b-%Y","%Y-%m-%d"]:
            try:
                dt = datetime.strptime(tod, fmt)
                # Calculate the Monday of that week for a clearer label
                monday = dt - timedelta(days=dt.weekday())
                r["week"] = f"Week-{dt.isocalendar()[1]:02d} [{monday.strftime('%d-%b-%y')}]"
                break
            except ValueError: pass
    c = str(r.get("country","") or "").strip().upper()
    if c in COUNTRY_CUTOFF: r["cut_off"] = COUNTRY_CUTOFF[c]
    
    if str(r.get("ship_mode","")).strip().upper() == "AIR":
        r["cut_off"] = "1st"
        
    return r

def auto_first_last(orders: list) -> list:
    def _p(s):
        for fmt in ["%d-%b-%y","%d-%b-%Y","%Y-%m-%d"]:
            try: return datetime.strptime(str(s).strip(), fmt)
            except ValueError: pass
        return None
    grp = {}
    for i, o in enumerate(orders): grp.setdefault(o.get("order_no",""), []).append(i)
    res = [dict(o) for o in orders]
    for _, idxs in grp.items():
        valid = [(dt, i) for i in idxs for dt in [_p(res[i].get("tod",""))] if dt]
        if not valid:
            for i in idxs: res[i]["first_last"] = ""; continue
        dg = {}
        for dt, i in valid: dg.setdefault(dt, []).append(i)
        ud = sorted(dg); n = len(ud)
        for pos, dt in enumerate(ud):
            lbl = "1st Shipment" if pos == 0 else "Last Shipment" if (pos == n-1 and n > 1) else ""
            for idx_idx, i in enumerate(dg[dt]):
                if idx_idx == 0 and lbl != "":
                    res[i]["first_last"] = lbl
                else:
                    res[i]["first_last"] = ""
        valid_idxs = {i for _, i in valid}
        for i in idxs:
            if i not in valid_idxs: res[i]["first_last"] = ""
    return res

def build_analytics(orders: list) -> dict:
    """Returns style-level and order-level summaries."""
    styles = {}   # style_name → dict
    ord_mp = {}   # order_no  → dict

    for o in orders:
        sn  = o.get("style_name","") or "(Unknown)"
        ono = o.get("order_no","")   or ""
        st  = o.get("shipped_status","") or ""
        co  = o.get("country","")    or ""
        def _i(k):
            try: return int(str(o.get(k,"") or "0").replace(",",""))
            except (ValueError, TypeError): return 0
        oq = _i("order_qty_set"); sq = _i("ship_qty_set")
        is_shipped   = st == "Shipped"
        is_cancelled = st == "Cancelled"
        is_pending   = not is_shipped and not is_cancelled

        # ── style ──
        if sn not in styles:
            styles[sn] = {"order_nos":set(),"total_oq":0,"total_sq":0,
                          "rows_shipped":0,"rows_pending":0,"rows_cancelled":0,"rows":[]}
        s = styles[sn]
        s["order_nos"].add(ono); s["total_oq"]+=oq; s["total_sq"]+=sq
        s["rows"].append(o)
        if is_shipped: s["rows_shipped"]+=1
        elif is_cancelled: s["rows_cancelled"]+=1
        else: s["rows_pending"]+=1

        # ── order ──
        if ono not in ord_mp:
            ord_mp[ono] = {"style_name":sn,"total_oq":0,"total_sq":0,
                           "rows_shipped":0,"rows_pending":0,"rows_cancelled":0,
                           "countries_pending":[],"countries_shipped":[],"rows":[]}
        od = ord_mp[ono]
        od["total_oq"]+=oq; od["total_sq"]+=sq; od["rows"].append(o)
        if is_shipped:   od["rows_shipped"]+=1;   od["countries_shipped"].append(co)
        elif is_cancelled: od["rows_cancelled"]+=1
        else:            od["rows_pending"]+=1;   od["countries_pending"].append(co)

    return {"styles": styles, "orders": ord_mp}
