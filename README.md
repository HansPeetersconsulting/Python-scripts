How to execute Unused_columns_or_tables_measures.py:

start powershell paste below command; replace report / semantic layer folder. The setup needs to be PBIR.

py C:\Users\Peetha\Downloads\Unused_columns_or_tables_measures.py 
"C:\Users\Peetha\Downloads\Colorada\Colorado Usage Report v7\Colorado Usage Report v7.Report" 
--model-path "C:\Oce\source\repos\SISPRO_PowerBI\SISPRO_PowerBI-1\Workspaces\ServiceProductData\ServiceProductDataMonth_v2.SemanticModel"

----------------------------------------------------------------------------------------------------------------------------------------------

How to execute table_column_usage_tmdl.py

start powershell paste below command; replace report / semantic layer folder. The setup needs to be PBIR.

py "C:\Users\Peetha\Downloads\table_column_usage_tmdl.py" `
"C:\Users\Peetha\Downloads\Colorada\Colorado Usage Report v7\Colorado Usage Report v7.Report" `
--model-path "C:\Oce\source\repos\SISPRO_PowerBI\SISPRO_PowerBI-1\Workspaces\ServiceProductData\ServiceProductDataMonth_v2.SemanticModel" `
--table Security
