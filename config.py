import os

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_FILE   = os.path.join(BASE_DIR, "garment_data.dat")
AUTH_FILE = os.path.join(BASE_DIR, "auth.dat")
REMEMBER_FILE = os.path.join(BASE_DIR, "remember.dat")
CHANGELOG_FILE = os.path.join(BASE_DIR, "changelog.json")

VERSION = "1.4.1"
GITHUB_REPO = "https://github.com/rubeltechcom/garment-tracking-system"
REPO_OWNER = "rubeltechcom"
REPO_NAME = "garment-tracking-system"

DEFAULT_COUNTRY_CUTOFF = {
    "US":"1st","OU":"1st","DK":"1st","NZ":"1st","DE":"1st",
    "ES":"1st","OF":"1st","AU":"1st","OO":"1st","CL":"1st",
    "CO":"1st","HK":"1st","HR":"1st","JP":"1st","OJ":"1st",
    "LH":"1st","KR":"1st","OK":"1st","TR":"1st","OT":"1st",
    "RS":"1st","BE":"1st","SE":"1st","SW":"1st","ME":"1st",
    "OD":"1st","DC":"1st","MX":"2nd","LD":"2nd","CN":"2nd",
    "OB":"2nd","GB":"2nd","OG":"2nd","CA":"2nd","DR":"2nd",
    "CH":"2nd","PL":"2nd","OE":"2nd","IN":"2nd","OI":"2nd",
    "ZA":"2nd","TW":"2nd","UY":"1st","TH":"2nd","OL":"2nd",
    "IX":"2nd","PH":"2nd","PA":"1st","PE":"2nd","MY":"2nd",
    "AZ":"2nd","DB":"2nd","VN":"2nd","ID":"2nd","EC":"2nd",
    "NH":"2nd","EN":"1st","BR":"1st",
}
COUNTRY_CUTOFF = dict(DEFAULT_COUNTRY_CUTOFF)

COLUMNS = [
    {"key":"order_no",        "label":"Order No",          "type":"pdf_auto","width":110},
    {"key":"style_name",      "label":"Style Name",         "type":"pdf_auto","width":135},
    {"key":"total_order_qty", "label":"Total Qty",          "type":"pdf_auto","width":85},
    {"key":"hm_merch",        "label":"H&M Merch",          "type":"manual",  "width":90},
    {"key":"hm_tech",         "label":"H&M Tech",           "type":"manual",  "width":90},
    {"key":"factory_merch",   "label":"Factory Merch",      "type":"manual",  "width":110},
    {"key":"colour",          "label":"Colour",             "type":"pdf_auto","width":150},
    {"key":"order_qty",       "label":"Order Qty",          "type":"pdf_auto","width":82},
    {"key":"tod",             "label":"ToD",                "type":"pdf_auto","width":92},
    {"key":"country",         "label":"Country",            "type":"pdf_auto","width":65},
    {"key":"order_qty_set",   "label":"Qty / Set",          "type":"pdf_auto","width":82},
    {"key":"no_of_pcs",       "label":"Pcs",                "type":"pdf_auto","width":50},
    {"key":"order_qty_pcs",   "label":"Qty / Pcs",          "type":"calc",    "width":82},
    {"key":"ship_qty_set",    "label":"Ship Qty Set",       "type":"manual",  "width":90},
    {"key":"ship_qty_pcs",    "label":"Ship Qty Pcs",       "type":"calc",    "width":90},
    {"key":"short_excess",    "label":"Short/Excess",       "type":"calc",    "width":90},
    {"key":"carton_qty",      "label":"Cartons",            "type":"manual",  "width":72},
    {"key":"ship_mode",       "label":"Mode",               "type":"pdf_auto","width":72},
    {"key":"season",          "label":"Season",             "type":"pdf_auto","width":72},
    {"key":"cut_off",         "label":"Cut Off",            "type":"auto_co", "width":72},
    {"key":"first_last",      "label":"1st & Last",         "type":"auto_fl", "width":110},
    {"key":"week",            "label":"Week",               "type":"calc",    "width":68},
    {"key":"shipped_status",  "label":"Status",             "type":"status",  "width":110},
    {"key":"sales_mode",      "label":"Sales",              "type":"pdf_auto","width":60},
    {"key":"date_added",      "label":"Date Added",         "type":"auto",    "width":90},
    {"key":"added_by",        "label":"Added By",           "type":"auto",    "width":80},
]
COL_KEYS = [c["key"] for c in COLUMNS]

STATUS_OPTIONS  = ["","Pending","1st Shipment","Last Shipment","Shipped","Cancelled"]
SHIPPED_DONE    = {"Shipped","Cancelled"}

# ── Premium deep-navy dark theme ─────────────────────────────────────────────
T = {
    # Backgrounds — Deep, modern darks
    "bg":       "#010409",  # Deepest Black
    "surf":     "#0D1117",  # Modern Surface
    "surf2":    "#161B22",  # Secondary Surface
    "surf3":    "#21262D",  # Tertiary Surface
    "surf4":    "#30363D",  # Hover / Active Surface
    "border":   "#30363D",  # Subtle Border
    "border2":  "#484F58",  # High-Visibility Border

    # Text — Pure white and high-contrast grays
    "text":     "#FFFFFF",  # Pure White for readability
    "muted":    "#8B949E",  # Muted Gray
    "dim":      "#484F58",  # Dim Gray

    # Brand accent — Electric Blue & Teal
    "accent":   "#58A6FF",  # Electric Blue
    "accent2":  "#1F6FEB",  # Strong Blue
    "accent3":  "#1158C7",  # Deep Blue

    # Semantic colours — Vibrant Status
    "green":    "#3FB950",  # Success Green
    "green2":   "#2EA043",  # Strong Green
    "green_bg": "#0D2418",
    "red":      "#F85149",  # Danger Red
    "red2":     "#DA3633",  # Strong Red
    "red_bg":   "#260D0D",
    "gold":     "#D29922",  # Warning Gold
    "gold2":    "#BB8009",  # Strong Gold
    "gold_bg":  "#251A05",
    "blue":     "#58A6FF",
    "blue2":    "#1F6FEB",
    "blue_bg":  "#0A1530",
    "purple":   "#BC8CFF",
    "purple2":  "#A371F7",
    "purple_bg":"#160A24",
    "teal":     "#39D353",  # Neon Green/Teal
    "teal2":    "#26A641",
    "orange":   "#FF7B72",
    "nav_btn":    "#0D1117",
    "nav_hover":  "#21262D",
    "nav_active": "#58A6FF",

    # Glass / Transparency (Simulated)
    "glass":      "#0D1117CC", # 80% opacity
    "glass_hov":  "#21262DCC",
    "glass_act":  "#30363DCC",
    
    # Fonts — Modern UI Stack
    "font":   "Segoe UI",
    "mono":   "Consolas",
}

PERMISSIONS = {
    "admin":   {"import_pdf","add_row","edit_row","delete_row","export","manage_users","manage_cutoff"},
    "manager": {"import_pdf","add_row","edit_row","delete_row","export","manage_cutoff"},
    "user":    {"add_row","edit_row"},
}

def can(user, action): return action in PERMISSIONS.get(user.get("role","user"), set())

def bind_hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    try:
        nfg = normal_fg or widget.cget("fg")
    except Exception:
        nfg = normal_fg or "#ffffff"
    hfg = hover_fg or nfg
    widget.bind("<Enter>", lambda _: widget.config(bg=hover_bg, fg=hfg))
    widget.bind("<Leave>", lambda _: widget.config(bg=normal_bg, fg=nfg))
