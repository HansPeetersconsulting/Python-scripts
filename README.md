**How to execute Scan_PBIB.ps1**
5. Voorbeelden
5.1 Alle tabellen tonen (platte lijst)
.\Scan_PBIB.ps1 -DefinitionPath "...\definition" -ShowTables
.\Scan_PBIB.ps1 -DefinitionPath "C:\Users\Peetha\Downloads\QT-CTS\Error-report-Rainbow\Error-report-Rainbow.Report\definition" -ShowTables

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

Met opties voor:

ParameterBeschrijving-ShowTablesToon alleen tabellen (geen kolommen/measures)-ShowColumnsToon kolommen-ShowMeasuresToon measures(combinaties mogelijk)Bijv. alleen kolommen + measures-FilterPrefix "abc"Toon alleen items die beginnen met "abc"-DebugModeVolledige JSON‑key logging tijdens parsing
Automatische gedrag:

Zonder FilterPrefix: geen pages/visuals tonen → enkel platte lijst
Met FilterPrefix: wel pages + visuals + matching results tonen
ShowTables alleen → toont alleen tabellen

-----------------------------------------------------------------------------------------------------------------------------------------------

**How to execute Unused_columns_or_tables_measures.py:**

start powershell paste below command; replace report / semantic layer folder. The setup needs to be PBIR.

py C:\Users\Peetha\Downloads\Unused_columns_or_tables_measures.py 
"C:\Users\Peetha\Downloads\Colorada\Colorado Usage Report v7\Colorado Usage Report v7.Report" 
--model-path "C:\Oce\source\repos\SISPRO_PowerBI\SISPRO_PowerBI-1\Workspaces\ServiceProductData\ServiceProductDataMonth_v2.SemanticModel"

----------------------------------------------------------------------------------------------------------------------------------------------

**How to execute table_column_usage_tmdl.py**

start powershell paste below command; replace report / semantic layer folder. The setup needs to be PBIR.

py "C:\Users\Peetha\Downloads\table_column_usage_tmdl.py" `
"C:\Users\Peetha\Downloads\Colorada\Colorado Usage Report v7\Colorado Usage Report v7.Report" `
--model-path "C:\Oce\source\repos\SISPRO_PowerBI\SISPRO_PowerBI-1\Workspaces\ServiceProductData\ServiceProductDataMonth_v2.SemanticModel" `
--table Security
