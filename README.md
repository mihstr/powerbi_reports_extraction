# Power BI Reports Extraction Tool

Avtomatizirana rešitev za masovno ekstrakcijo Power BI poročil iz cloud storitve, ki prenese vse poročila (PBIX) iz Power BI Service preko REST API-ja, jih konvertira v PBIR format z orodjem pbi-tools, shrani fizične datoteke v organizirane mape (exports/ za PBIX, pbir/ za PBIR strukture), izlušči seznam vseh vizualizacij in metapodatkov ter shrani vse informacije v Snowflake bazo za nadaljnjo analizo.

## Namestitev

1. **Namesti Python odvisnosti:**
   ```bash
   pip install snowflake-connector-python requests
   ```

2. **Namesti pbi-tools:**
   - Prenesi z [pbi.tools](https://pbi.tools/)
   - Razpakiraj v mapo `pbi-tools.1.2.0/`

3. **Konfiguracija:**
   ```bash
   cp config_template.py config.py
   ```
   - Odpri `config.py` in izpolni svoje podatke:
     - Snowflake povezava
     - Power BI API ključi
     - Pot do pbi-tools.exe

## Uporaba

```bash
python extraction.py
```

## Struktura datotek

```
powerbi_reports_extraction/
├── extraction.py          # Glavni program
├── config.py              # Konfiguracija (občutljivi podatki)
├── config_template.py     # Template za konfiguracijo
├── README.md              # To datoteka
├── exports/               # Prenesene PBIX datoteke
├── pbir/                  # Ekstrahirane PBIR strukture
└── pbi-tools.1.2.0/       # pbi-tools orodje
```

## Varnost

- `config.py` vsebuje občutljive podatke - **nikoli ne deli te datoteke**
- Dodaj `config.py` v `.gitignore`
- Deli samo `config_template.py` kot primer

## Nastavitve

V `config.py` lahko nastaviš:
- `max_reports`: omejitev števila poročil za testiranje
- `max_reports_production`: None za vse poročila

## Rezultat

Program ustvari:
- Fizične PBIX datoteke v `exports/`
- PBIR strukture v `pbir/`
- Podatke v Snowflake tabeli `Reports` z vizualizacijami in metapodatki 
