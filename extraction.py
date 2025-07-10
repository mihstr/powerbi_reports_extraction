import snowflake.connector
import requests
import os
import subprocess
import json
from datetime import datetime
from config import SNOWFLAKE_CONFIG, POWERBI_CONFIG, PATHS, TESTING

# Snowflake povezava
conn = snowflake.connector.connect(
    account = SNOWFLAKE_CONFIG["account"],
    user = SNOWFLAKE_CONFIG["user"],
    password = SNOWFLAKE_CONFIG["password"],
    role = SNOWFLAKE_CONFIG["role"],
    warehouse = SNOWFLAKE_CONFIG["warehouse"],
    database = SNOWFLAKE_CONFIG["database"],
    schema = SNOWFLAKE_CONFIG["schema"]
)

# Testna omejitev - nastavi na None za produkcijo
MAX_REPORTS_TO_DOWNLOAD = TESTING["max_reports"]  # Omeji poročil za testiranje
# MAX_REPORTS_TO_DOWNLOAD = TESTING["max_reports_production"]  # Odkomentiraj za produkcijo

def get_access_token(client_id, client_secret, tenant_id):
    """Pridobi dostopni žeton za Power BI API"""
    print("Pridobivam dostopni žeton...")
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
        "grant_type": "client_credentials"
    }
    response = requests.post(url, headers=headers, data=data)
    print("Dostopni žeton uspešno pridobljen.")
    return response.json()["access_token"]

def get_reports(token):
    """Pridobi seznam vseh poročil iz Power BI"""
    print("Pridobivam seznam delovnih prostorov...")
    headers = {"Authorization": f"Bearer {token}"}
    workspaces_url = "https://api.powerbi.com/v1.0/myorg/groups"
    workspaces = requests.get(workspaces_url, headers=headers).json()["value"]
    print(f"Najdenih {len(workspaces)} delovnih prostorov.")
    
    reports = []
    for ws in workspaces:
        reports_url = f"https://api.powerbi.com/v1.0/myorg/groups/{ws['id']}/reports"
        ws_reports = requests.get(reports_url, headers=headers).json()["value"]
        print(f"V delovnem prostoru '{ws['name']}' najdenih {len(ws_reports)} poročil.")
        for report in ws_reports:
            reports.append({
                "workspace_id": ws["id"], 
                "workspace_name": ws["name"],
                "report_id": report["id"], 
                "report_name": report["name"]
            })
    
    print(f"Skupno najdenih {len(reports)} poročil za prenos.")
    return reports

def export_pbix(token, workspace_id, report_id, report_name):
    """Prenesi PBIX datoteko"""
    headers = {"Authorization": f"Bearer {token}"}
    export_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/Export"
    response = requests.get(export_url, headers=headers)
    
    if response.status_code == 401:
        raise Exception(f"Napaka pri prenosu: HTTP 401 - Ni dovoljenja za dostop do poročila")
    elif response.status_code == 404:
        raise Exception(f"Napaka pri prenosu: HTTP 404 - Poročilo ni najdeno")
    elif response.status_code != 200:
        raise Exception(f"Napaka pri prenosu: HTTP {response.status_code}")
    
    with open(f"exports/{report_name}.pbix", "wb") as f:
        f.write(response.content)

def extract_pbix_to_pbir(pbix_path, output_dir):
    """Ekstraktira PBIX datoteko v PBIR format"""
    result = subprocess.run([
        PATHS["pbi_tools"], "extract", pbix_path, "-extractFolder", output_dir
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        raise Exception(f"Napaka pri ekstrakciji: {result.stderr}")
    
    return True

def read_pbir_metadata(pbir_folder):
    """Prebere metapodatke iz PBIR datoteke"""
    metadata = {}
    
    # Preberi osnovne metapodatke
    try:
        with open(f"{pbir_folder}/ReportMetadata.json", 'r', encoding='utf-8') as f:
            metadata['report_metadata'] = json.load(f)
    except FileNotFoundError:
        metadata['report_metadata'] = None
    
    try:
        with open(f"{pbir_folder}/Connections.json", 'r', encoding='utf-8') as f:
            metadata['connections'] = json.load(f)
    except FileNotFoundError:
        metadata['connections'] = None
    
    try:
        with open(f"{pbir_folder}/Version.txt", 'r', encoding='utf-8') as f:
            metadata['version'] = f.read().strip()
    except FileNotFoundError:
        metadata['version'] = None
    
    return metadata

def read_visuals_from_pbir(pbir_folder):
    """Prebere vsa imena vizualizacij iz vseh sekcij v PBIR mapi."""
    visuals = []
    sections_root = os.path.join(pbir_folder, 'Report', 'sections')
    if not os.path.isdir(sections_root):
        return visuals
    for section in os.listdir(sections_root):
        section_path = os.path.join(sections_root, section, 'visualContainers')
        if os.path.isdir(section_path):
            for visual in os.listdir(section_path):
                # Ime vizuala je ime mape (lahko še dodatno očistiš, če želiš)
                visuals.append(visual)
    return visuals

def save_to_snowflake(reports_data):
    """Shrani podatke v Snowflake (vključno z metapodatki)."""
    print("Začenjam shranjevanje podatkov v Snowflake...")
    cursor = conn.cursor()
    for report_data in reports_data:
        try:
            cursor.execute("""
                MERGE INTO Reports AS target
                USING (SELECT 
                    %s as report_id,
                    %s as report_name,
                    %s as visuals,
                    %s as workspace_id,
                    %s as workspace_name,
                    %s as metadata
                ) AS source
                ON target.report_id = source.report_id
                WHEN MATCHED THEN
                    UPDATE SET
                        report_name = source.report_name,
                        visuals = source.visuals,
                        workspace_name = source.workspace_name,
                        metadata = source.metadata,
                        extraction_date = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN
                    INSERT (report_id, report_name, visuals, workspace_id, workspace_name, metadata)
                    VALUES (source.report_id, source.report_name, source.visuals, source.workspace_id, source.workspace_name, source.metadata)
            """,
            (
                report_data['report_id'],
                report_data['report_name'],
                json.dumps(report_data.get('visuals')) if report_data.get('visuals') else None,
                report_data['workspace_id'],
                report_data['workspace_name'],
                json.dumps(report_data.get('metadata')) if report_data.get('metadata') else None
            )
            )
            print(f"Uspešno shranjeno: {report_data['report_name']}")
        except Exception as e:
            print(f"Napaka pri shranjevanju {report_data['report_name']}: {e}")
            continue
    conn.commit()
    cursor.close()
    print("Podatki uspešno shranjeni v Snowflake.")

def main():
    """Glavna funkcija"""
    # Ustvari potrebne mape
    os.makedirs("exports", exist_ok=True)
    os.makedirs("pbir", exist_ok=True)
    
    # Pridobi poročila
    token = get_access_token(POWERBI_CONFIG["client_id"], POWERBI_CONFIG["client_secret"], POWERBI_CONFIG["tenant_id"])
    reports = get_reports(token)
    
    # Uporabi omejitev za testiranje
    if MAX_REPORTS_TO_DOWNLOAD:
        reports = reports[:MAX_REPORTS_TO_DOWNLOAD]
        print(f"TESTNI NAČIN: Omejeno na {MAX_REPORTS_TO_DOWNLOAD} poročil")
    else:
        print("PRODUKCIJSKI NAČIN: Prenos vseh poročil")
    
    # Prenesi in ekstraktiraj poročila
    reports_data = []
    total = len(reports)
    
    for idx, report in enumerate(reports, 1):
        print(f"Obdelujem poročilo ({idx}/{total}): {report['report_name']} ...")
        
        try:
            # Prenesi PBIX
            export_pbix(token, report["workspace_id"], report["report_id"], report["report_name"])
            
            # Ekstraktiraj v PBIR
            pbix_path = f"exports/{report['report_name']}.pbix"
            output_dir = f"pbir/{report['report_name'].replace(' ', '_')}"
            
            extract_pbix_to_pbir(pbix_path, output_dir)
            
            # Preberi metapodatke
            try:
                metadata = read_pbir_metadata(output_dir)
                print(f"  Metapodatki uspešno prebrani za: {report['report_name']}")
            except Exception as e:
                print(f"  Napaka pri branju metapodatkov za {report['report_name']}: {e}")
                metadata = {}
            
            # Preberi vizualizacije
            visuals = read_visuals_from_pbir(output_dir)
            # Dodaj podatke za Snowflake
            report_data = {
                **report,
                'visuals': visuals,
                'metadata': metadata
            }
            reports_data.append(report_data)
            
            print(f"Uspešno obdelano ({idx}/{total}): {report['report_name']}")
            
        except Exception as e:
            print(f"Napaka pri obdelavi ({idx}/{total}) {report['report_name']}: {e}")
            continue
    
    # Shrani v Snowflake
    save_to_snowflake(reports_data)
    
    print("Vsa poročila uspešno obdelana!")

if __name__ == "__main__":
    main()
    conn.close()

