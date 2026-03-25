#!/usr/bin/env python3
"""
TMDL Semantic Model + PBIR Usage Analyzer

✅ Supports TMDL-based models (no model.json required)
✅ Reads tables/columns from: definition/tables/<table>/columns/*.tmdl
✅ Scans PBIR report JSON to detect:
   - Where each table is used
   - Where each column is used

Usage:
    python table_column_usage_tmdl.py <Report.Report> --model-path <SemanticModelFolder> --table DimCustomer
    python table_column_usage_tmdl.py <Report.Report> --model-path <SemanticModelFolder> --column DimCustomer.CustomerName
"""

import json
import sys
import argparse
from pathlib import Path


# =====================================================================
# ✅ Utility JSON Loader
# =====================================================================
def load_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except:
        return {}


# =====================================================================
# ✅ TMDL + PBIR Scanner
# =====================================================================
class TMDLUsageScanner:

    def __init__(self, report_path: str, model_path: str):
        self.report_path = Path(report_path)
        self.definition = self.report_path / "definition"

        if not self.report_path.exists():
            raise FileNotFoundError(f"Report folder not found: {report_path}")

        # TMDL model path
        self.model_path = Path(model_path)
        self.tmdl_tables = self.model_path / "definition" / "tables"

        if not self.tmdl_tables.exists():
            raise FileNotFoundError(
                f"TMDL tables folder not found: {self.tmdl_tables}"
            )

    # -----------------------------------------------------------------
    # ✅ Load PBIR report parts
    # -----------------------------------------------------------------
    def load_pbir_parts(self):
        parts = []

        # report.json
        report_json = self.definition / "report.json"
        if report_json.exists():
            parts.append((str(report_json), load_json(report_json)))

        # Pages + Visuals
        pages = self.definition / "pages"
        if pages.exists():
            for page_folder in pages.iterdir():
                if not page_folder.is_dir():
                    continue

                # Page.json
                page_json = page_folder / "page.json"
                if page_json.exists():
                    parts.append((str(page_json), load_json(page_json)))

                # Visuals
                visuals = page_folder / "visuals"
                if visuals.exists():
                    for visual_folder in visuals.iterdir():
                        visual_json = visual_folder / "visual.json"
                        if visual_json.exists():
                            parts.append((str(visual_json), load_json(visual_json)))

        # Bookmarks
        bookmarks = self.definition / "bookmarks"
        if bookmarks.exists():
            for bm in bookmarks.glob("*.bookmark.json"):
                parts.append((str(bm), load_json(bm)))

        return parts

    # -----------------------------------------------------------------
    # ✅ Load ALL tables & columns from TMDL
    # -----------------------------------------------------------------
    def load_tmdl_model(self):
        """
        TMDL structure:
            definition/tables/<TableName>.tmdl
            definition/tables/<TableName>/columns/<Column>.tmdl
        """
        tables = []
        columns = []

        for item in self.tmdl_tables.iterdir():
            # TMDL allows tables as .tmdl files (not just folders)
            if item.is_file() and item.suffix == ".tmdl":
                table_name = item.stem
                tables.append(table_name)
                continue

            # Or full folder structure
            if item.is_dir():
                table_name = item.name
                tables.append(table_name)

                cols_folder = item / "columns"
                if cols_folder.exists():
                    for col_file in cols_folder.glob("*.tmdl"):
                        columns.append({
                            "table": table_name,
                            "column": col_file.stem
                        })

        return tables, columns

    # -----------------------------------------------------------------
    # ✅ Recursive JSON search
    # -----------------------------------------------------------------
    def _scan_json(self, data, table_name, column_name=None, path=""):
        hits = []

        if isinstance(data, dict):

            # Table / column reference via entity/property
            if data.get("entity") == table_name:
                if column_name is None or data.get("property") == column_name:
                    hits.append(path)

            # "Column": {} style reference
            if "Column" in data:
                c = data["Column"]
                src = c.get("Expression", {}).get("SourceRef", {})
                if src.get("Entity") == table_name:
                    if column_name is None or c.get("Property") == column_name:
                        hits.append(path)

            # DAX expression search
            if isinstance(data.get("Expression"), str):
                expr = data["Expression"]
                if f"'{table_name}'" in expr or f"[{table_name}]" in expr:
                    hits.append(path)
                if column_name and f"[{column_name}]" in expr:
                    hits.append(path)

            # recursion
            for k, v in data.items():
                newpath = f"{path}.{k}" if path else k
                hits.extend(self._scan_json(v, table_name, column_name, newpath))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                hits.extend(self._scan_json(item, table_name, column_name, f"{path}[{i}]"))

        return hits

    # -----------------------------------------------------------------
    # ✅ Public API: find table usage
    # -----------------------------------------------------------------
    def find_table_usage(self, table):
        parts = self.load_pbir_parts()
        matches = []

        for (filename, payload) in parts:
            found = self._scan_json(payload, table)
            for f in found:
                matches.append((filename, f))

        return matches

    # -----------------------------------------------------------------
    # ✅ Public API: find column usage
    # -----------------------------------------------------------------
    def find_column_usage(self, table, column):
        parts = self.load_pbir_parts()
        matches = []

        for (filename, payload) in parts:
            found = self._scan_json(payload, table, column)
            for f in found:
                matches.append((filename, f))

        return matches


# =====================================================================
# ✅ CLI
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="Find table/column usage in PBIR using TMDL semantic model.")
    parser.add_argument("report_path", help="Path to *.Report folder")
    parser.add_argument("--model-path", required=True, help="Path to TMDL model folder (folder containing 'definition/tables')")
    parser.add_argument("--table", help="Table name to check")
    parser.add_argument("--column", help="Column name in Table.Column format")

    args = parser.parse_args()
    scanner = TMDLUsageScanner(args.report_path, args.model_path)

    # ✅ Print all tables (debugging support)
    tables, cols = scanner.load_tmdl_model()
    print("\n📋 Tables found in TMDL model:")
    for t in tables:
        print("  -", t)

    # ✅ Table usage
    if args.table:
        if args.table not in tables:
            print(f"\n❌ Table '{args.table}' does NOT exist in the semantic model.")
            return

        print(f"\n🔍 Checking usage of TABLE: {args.table}")
        matches = scanner.find_table_usage(args.table)

        if not matches:
            print(f"❌ Table '{args.table}' is NOT used anywhere in the report.")
        else:
            print(f"✅ Table '{args.table}' IS used in:")
            for file, loc in matches:
                print(f"  - {file} → {loc}")

    # ✅ Column usage
    if args.column:
        if "." not in args.column:
            print("❌ Column must be in Table.Column format")
            return

        table, col = args.column.split(".", 1)

        if table not in tables:
            print(f"\n❌ Table '{table}' does NOT exist in the semantic model.")
            return

        print(f"\n🔍 Checking usage of COLUMN: {table}.{col}")
        matches = scanner.find_column_usage(table, col)

        if not matches:
            print(f"❌ Column '{table}.{col}' is NOT used anywhere.")
        else:
            print(f"✅ Column '{table}.{col}' IS used in:")
            for file, loc in matches:
                print(f"  - {file} → {loc}")


if __name__ == "__main__":
    sys.exit(main())