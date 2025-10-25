ACRONYM_TOKENS = {"APN", "HOA", "ID", "UI", "DNC", "LLC", "LP", "LLP", "INC", "CPA", "CEO", "CFO", "COO", "VP", "SQFT", "AOD"}


def to_title_case(field: str) -> str:
    """Convert snake_case field names to Title Case strings."""
    if not field:
        return field

    parts = field.replace("-", " ").replace("_", " ").split()
    titled = []
    for part in parts:
        upper = part.upper()
        if part.isnumeric():
            titled.append(part)
        elif upper in ACRONYM_TOKENS:
            titled.append(upper)
        else:
            titled.append(part.capitalize())
    return " ".join(titled)


# PROPERTY TABLE
PROPERTY_FIELDS = [
    "Full Address",
    "Street Address",
    "Property City",
    "Seller Name",
    "Property State",
    "Property Zip Code",
    "Property County",
    "Property ID",
    "First Name",
    "Last Name",
    "Corporate Owned",
    "Market Status",
    "Sale Date",
    "Last Sale Price",
    "Estimated Equity Amount",
    "Equity Percent",
    "Estimated Value",
    "Property Type",
    "Living Area SQFT",
    "Bedrooms",
    "Bathrooms",
    "Year Built",
    "Effective Year Built",
    "Construction Type",
    "Building Style",
    "Number Of Units",
    "Number Of Commercial Units",
    "Number Of Buildings",
    "Stories",
    "Garage Area",
    "Heating Type",
    "Heating Fuel",
    "Air Conditioning",
    "Basement",
    "Deck",
    "Exterior Walls",
    "Interior Walls",
    "Number Of Fireplaces",
    "Floor Cover",
    "Garage",
    "Driveway",
    "Other Rooms",
    "Pool",
    "Patio",
    "Porch",
    "Roof Cover",
    "Roof Type",
    "Sewer",
    "Topography",
    "Water",
    "Geographic Features",
    "Active Lien",
    "APN Number",
    "Lot Size Acres",
    "Lot Size SQFT",
    "Legal Description",
    "Subdivision Name",
    "Property Class",
    "County Land Use Code",
    "County Name",
    "Census Tract",
    "Lot Number",
    "School District",
    "Zoning",
    "Flood Zone",
    "Tax Delinquent",
    "Tax Delinquent Year",
    "Tax Year",
    "Tax Amount",
    "Assessment Year",
    "Total Assessed Value",
    "Assessed Land Value",
    "Assessed Improvement Value",
    "Total Market Value",
    "Market Land Value",
    "Market Improvement Value",
    "Estimated Repair Cost",
    "Building Condition",
    "Repair Cost Per SQFT",
    "Building Quality",
    "Property Flag 1",
    "Property Flag 2",
    "Property Flag 3",
    "Property Flag 4",
    "Property Flag 5",
    "Property Flag 6",
    "Property Flag 7",
    "Property Flag 8",
    "Property Flag 9",
    "Property Flag 10",
    "Property Flags",
    "Tax Mailing Address",
    "Tax Mailing City",
    "Tax Mailing State",
    "Tax Mailing Zip Code",
    "HOA Name",
    "HOA Type",
    "HOA Fee",
    "HOA Fee Frequency",
    "Second HOA Name",
    "Second HOA Type",
    "Second HOA Fee",
    "Second HOA Fee Frequency",
]

# SELLER / OWNER TABLE
SELLER_FIELDS = [
    "Full Name",
    "Date Of Birth",
    "Age",
    "Gender",
    "Marital Status",
    "Preferred Language",
    "Number Of Children",
    "Household Size",
    "Pet Owner",
    "Previous Address",
    "Mailing Address",
    "Length Of Residence",
    "Education",
    "Occupation Group",
    "Occupation",
    "Income Tier",
    "Estimated Household Income",
    "Net Asset Value",
    "Consumer Type",
    "Spender Type",
    "Card Balance",
    "Investment Type",
    "Buying Power",
    "Total Properties Owned",
    "Portfolio Value",
    "Total Equity",
    "Total Mortgage Balance",
    "Tag 1",
    "Tag 2",
    "Tag 3",
    "Tag 4",
    "Tag 5",
    "Tag 6",
    "Tag 7",
]

# MORTGAGE INFO TABLE
MORTGAGE_FIELDS = [
    "Mortgage Position",
    "Original Loan Amount",
    "Estimated Interest Rate",
    "Estimated Loan Payment",
    "Last Recording Date",
    "Estimated Loan Balance",
    "Loan Term",
    "Loan Type",
    "Financing Type",
    "Loan Maturity Date",
    "Lender Name",
]

# COMPANY TABLE
COMPANY_FIELDS = [
    "Company Name",
    "Total Properties Owned",
    "Total Portfolio Value",
    "Total Mortgage Balance",
    "Total Equity",
    "Mailing Address",
]

# COMPANY CONTACTS TABLE
COMPANY_CONTACT_FIELDS = [
    "Full Name",
    "Company Name",
    "Title Or Role",
    "Phone Number",
    "Email Address",
]

# PHONE NUMBERS TABLE
PHONE_FIELDS = [
    "Phone Number",
    "Active Status",
    "Phone Type",
    "Usage Type",
    "Carrier",
    "Prepaid Line",
    "DNC",
    "Phone 1 Contacted",
    "Last Contacted Date",
    "Last Contact Method",
    "Response Type",
]

# EMAILS TABLE
EMAIL_FIELDS = [
    "Email Address",
    "Email Deliverability",
]

# AOD TABLE
AOD_FIELDS = [
    "Document Type",
    "Document Title",
    "Document Title Text",
    "Primary Party Role",
    "Primary Party Name",
    "Secondary Party Role",
    "Secondary Party Name",
    "Trust Name",
    "Date Of Death",
]

# PROBATE TABLE
PROBATE_FIELDS = [
    "Document Type",
    "Document Title",
    "Document Title Text",
    "Deceased Or Estate",
    "Survivor Or Heir",
    "Administrator Or Executor",
]

# LIENS TABLE
LIEN_FIELDS = [
    "Document Type",
    "Document Title",
    "Document Title Text",
    "Deceased Or Estate",
    "Survivor Or Heir",
    "Administrator Or Executor",
]

# FORECLOSURE TABLE
FORECLOSURE_FIELDS = [
    "Default Date",
    "Unpaid Balance",
    "Past Due Amount",
    "Due Date",
    "Lender Name",
    "Foreclosure Document Recording Date",
    "Document Type",
    "Auction Date",
    "Auction Time",
    "Auction Location",
    "Auction Minimum Bid Amount",
    "Auction City",
    "Trustee Name",
    "Trustee Address",
    "Trustee Phone Number",
    "Trustee Case Number",
]
# Export all field groups for cleaner imports
__all__ = [
    "to_title_case",
    "PROPERTY_FIELDS",
    "SELLER_FIELDS",
    "MORTGAGE_FIELDS",
    "COMPANY_FIELDS",
    "COMPANY_CONTACT_FIELDS",
    "PHONE_FIELDS",
    "EMAIL_FIELDS",
    "AOD_FIELDS",
    "PROBATE_FIELDS",
    "LIEN_FIELDS",
    "FORECLOSURE_FIELDS",
]
