# ============================================
# 🔥 DealMachine Advanced Search Presets
# ============================================

# --- Universal Base Filters (applied to ALL searches) ---
BASE_FILTERS = {
    # Quick Filters
    "Off Market": True,
    "High Equity": True,
    "Absentee Owners": True,
    "Out of State Owners": True,
    "Owner Occupied": False,

    # Equity / Value
    "Estimated Equity Percent": ">50",
    "Number of Mortgages": "<=2",
    "Estimated Loan Balance (Total)": "<1000000",

    # Contact Info
    "Contact Has Phone Number?": True,
    "Contact Has Email Address?": True,

    # Owner
    "Corporate Owned?": False,
    "Ownership Length (Years)": ">8",
    "Owner Has Multiple Properties": True,

    # Property
    "Year Built": "<=2005",
    "Living Area (sqft)": ">800",
    "Condition": "Fair or Poor",
}

# --- Tier 1: Kill-Shot Distress ---
# Short-supply but highest motivation
TIER_1 = {
    **BASE_FILTERS,
    "Preforeclosures": True,
    "Probates": True,
    "Tax Delinquent": True,
    "Vacant Homes": True,
    "Tired Landlords": True,
    "Zombie Properties": True,
}

# --- Tier 2: Predictive Fatigue / Aging Equity ---
TIER_2 = {
    **BASE_FILTERS,
    "Senior Owners": True,
    "Free and Clear": True,
    "Intrafamily Transfer": True,
    "Likely to Move": True,
    "Long Ownership (Years)": ">12",
}

# --- Tier 3: Income / Multifamily / Cashflow ---
TIER_3 = {
    **BASE_FILTERS,
    "Property Types": [
        "Duplex (2 Units, Any Combination)",
        "Triplex (3 Units, Any Combination)",
        "Quadruplex (4 Units, Any Combination)",
        "Multi-family Dwellings (generic, 2+)",
        "Garden Apt, Court Apt (5+ Units)",
        "Apartment House (5+ Units)",
        "Apartment House (100+ Units)",
    ],
    "Tired Landlords": True,
    "Absentee Owners": True,
}

# --- Tier 4: Commercial / Redevelopment ---
TIER_4 = {
    **BASE_FILTERS,
    "Property Types": [
        "Commercial (general)",
        "Commercial Building",
        "Retail/residential (mixed Use)",
        "Warehouse (industrial)",
        "Neighborhood Shopping Center, Strip Center/mall, Enterprise Zone",
        "Office Bldg (general)",
        "Vacant Land (general)",
        "Commercial-vacant Land",
        "Mixed Use",
    ],
    "Tax Delinquent": True,
    "Preforeclosures": True,
    "Vacant Homes": True,
}

# --- Combine all tiers into dictionary ---
SEARCH_TIERS = {
    "Tier 1 – Max Distress": TIER_1,
    "Tier 2 – Aging Equity": TIER_2,
    "Tier 3 – Cashflow": TIER_3,
    "Tier 4 – Commercial Redevelopment": TIER_4,
}

# --- Default property-type focus groups ---
PROPERTY_CLUSTERS = {
    "Residential Core": [
        "Single Family Residential",
        "Townhouse (residential)",
        "Zero Lot Line (residential)",
        "Patio Home",
        "Row House (residential)",
        "Cluster Home (residential)",
    ],
    "Multifamily": [
        "Duplex (2 Units, Any Combination)",
        "Triplex (3 Units, Any Combination)",
        "Quadruplex (4 Units, Any Combination)",
        "Multi-family Dwellings (generic, 2+)",
        "Apartment House (5+ Units)",
        "Garden Apt, Court Apt (5+ Units)",
        "Apartment House (100+ Units)",
    ],
    "Commercial": [
        "Commercial (general)",
        "Commercial/office/residential (mixed Use)",
        "Retail/residential (mixed Use)",
        "Warehouse (industrial)",
        "Office Bldg (general)",
        "Neighborhood Shopping Center, Strip Center/mall, Enterprise Zone",
        "Vacant Land (general)",
    ],
}