## How to execute Scan_PBIB.ps1

### 5. Voorbeelden

#### 5.1 Alle tabellen tonen (platte lijst)

```powershell
.\Scan_PBIB.ps1 -DefinitionPath "...\definition" -ShowTables
.\Scan_PBIB.ps1 -DefinitionPath "C:\Users\Peetha\Downloads\QT-CTS\Error-report-Rainbow\Error-report-Rainbow.Report\definition" -ShowTables
``

Output:
Table: Configuration
Table: ServiceOrganization
Table: Deliveries
Table: Date

3. Functionaliteit van het script
Het script:
Extracteert volledig:

Tabellen (Entities)
Kolommen
Measures
Sort‑velden
Filter‑velden
Sparkline‑velden
Per Page
Per Visual

Met opties voor
Parameterbeschrijving


-ShowTables
Toon alleen tabellen (geen kolommen/measures)


-ShowColumns
Toon kolommen


-ShowMeasures
Toon measures
(combinaties mogelijk – bijv. alleen kolommen + measures)


-FilterPrefix "abc"
Toon alleen items die beginnen met "abc"


-DebugMode
Volledige JSON‑key logging tijdens parsing

Automatisch gedrag


Zonder FilterPrefix
Geen pages/visuals tonen → enkel platte lijst


Met FilterPrefix
Wel pages + visuals + matching results tonen


ShowTables alleen
Toont alleen tabellen




How to execute Unused_columns_or_tables_measures.py
Start PowerShell, plak onderstapy C:\Users\Peetha\Downloads\Unused_columns_or_tables_measures.py
"C:\Users\Peetha\Downloads\Colorada\Colorado Usage Report v7\Colorado Usage Report v7.Report" 
--model-path "C:\Oce\source\repos\SISPRO_PowerBI\SISPRO_PowerBI-1\Workspaces\ServiceProductData\ServiceProductDataMonth_v2.SemanticModel"
``and commando en vervang het report‑ en semantic‑layer‑pad.
De setup moet PBIR zijn.

How to execute table_column_usage_tmdl.py
Start PowerShell, plak onderstaand commando en vervang het report‑ en semantic‑layer‑pad.
De setup moet PBIR zijn.

py "C:\Users\Peetha\Downloads\table_column_usage_tmdl.py" `
"C:\Users\Peetha\Downloads\Colorada\Colorado Usage Report v7\Colorado Usage Report v7.Report" `
--model-path "C:\Oce\source\repos\SISPRO_PowerBI\SISPRO_PowerBI-1\Workspaces\ServiceProductData\ServiceProductDataMonth_v2.SemanticModel" `
--table Security
