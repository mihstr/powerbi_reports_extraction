# Template konfiguracije za Power BI Reports Extraction
# Kopiraj to datoteko kot config.py in izpolni svoje podatke

# Snowflake povezava
SNOWFLAKE_CONFIG = {
    "account": "YOUR_SNOWFLAKE_ACCOUNT",
    "user": "YOUR_SNOWFLAKE_USER", 
    "password": "YOUR_SNOWFLAKE_PASSWORD",
    "role": "YOUR_SNOWFLAKE_ROLE",
    "warehouse": "YOUR_SNOWFLAKE_WAREHOUSE",
    "database": "YOUR_SNOWFLAKE_DATABASE",
    "schema": "YOUR_SNOWFLAKE_SCHEMA"
}

# Power BI API konfiguracija
POWERBI_CONFIG = {
    "client_id": "YOUR_POWERBI_CLIENT_ID",
    "client_secret": "YOUR_POWERBI_CLIENT_SECRET",
    "tenant_id": "YOUR_POWERBI_TENANT_ID"
}

# Poti do orodij
PATHS = {
    "pbi_tools": r"PATH_TO_YOUR_PBI_TOOLS_EXE"
}

# Nastavitve za testiranje
TESTING = {
    "max_reports": 2,  # Omeji poročil za testiranje, nastavi na None za produkcijo
    "max_reports_production": None
} 