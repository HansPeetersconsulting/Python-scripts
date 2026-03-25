#!/usr/bin/env python3
"""
Remove unused report-level measures from Power BI PBIR files.
Detect unused tables & columns (detection only).
Support external semantic model folder (--model-path).

Usage:
    python remove_unused_measures.py <report_folder> [--model-path <path>] [--execute] [--ignore-unapplied-filters]
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import argparse


# =====================================================================
# ✅ CLASS: PBIR Cleaner (Measures + Tables + Columns)
# =====================================================================
class PBIRMeasureCleaner:
    """Remove unused report-level measures + detect unused tables/columns."""

    def __init__(self, report_path: str, model_path: Optional[str] = None):
        self.report_path = Path(report_path)
        if not self.report_path.exists():
            raise FileNotFoundError(f"Report path not found: {report_path}")

        self.definition_path = self.report_path / "definition"
        self.report_extensions_path = self.definition_path / "reportExtensions.json"
        self.report_json_path = self.definition_path / "report.json"

        if not self.definition_path.exists():
            raise FileNotFoundError(f"Definition folder not found: {self.definition_path}")

        # ✅ Optional semantic model path (PBIP .SemanticModel folder)
        if model_path:
            self.model_path = Path(model_path)
            if not self.model_path.exists():
                raise FileNotFoundError(f"Semantic model path not found: {model_path}")
        else:
            self.model_path = None

    # -----------------------------------------------------------------
    # ✅ JSON LOADERS
    # -----------------------------------------------------------------
    def _load_json_file(self, file_path: Path) -> dict:
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            print(f"⚠️  Error loading {file_path}: {e}")
            return {}

    def _save_json_file(self, file_path: Path, data: dict):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_all_report_parts(self) -> List[dict]:
        """Load all JSON fragments inside the PBIR folder."""
        parts = []

        # report.json
        if self.report_json_path.exists():
            parts.append({
                'path': 'definition/report.json',
                'payload': self._load_json_file(self.report_json_path)
            })

        # pages + visuals
        pages_path = self.definition_path / "pages"
        if pages_path.exists():
            for page_folder in pages_path.iterdir():
                if page_folder.is_dir():
                    page_json = page_folder / "page.json"
                    if page_json.exists():
                        parts.append({
                            'path': f'definition/pages/{page_folder.name}/page.json',
                            'payload': self._load_json_file(page_json)
                        })

                    visuals_path = page_folder / "visuals"
                    if visuals_path.exists():
                        for visual_folder in visuals_path.iterdir():
                            if visual_folder.is_dir():
                                visual_json = visual_folder / "visual.json"
                                if visual_json.exists():
                                    parts.append({
                                        'path': f'definition/pages/{page_folder.name}/visuals/{visual_folder.name}/visual.json',
                                        'payload': self._load_json_file(visual_json)
                                    })

        # bookmarks
        bookmarks_path = self.definition_path / "bookmarks"
        if bookmarks_path.exists():
            for bookmark_file in bookmarks_path.glob("*.bookmark.json"):
                parts.append({
                    'path': f'definition/bookmarks/{bookmark_file.name}',
                    'payload': self._load_json_file(bookmark_file)
                })

        return parts

    # -----------------------------------------------------------------
    # ✅ MEASURE LOGIC (Original)
    # -----------------------------------------------------------------
    def list_report_level_measures(self) -> List[Dict[str, str]]:
        if not self.report_extensions_path.exists():
            return []

        extensions_data = self._load_json_file(self.report_extensions_path)
        measures = []

        for entity in extensions_data.get("entities", []):
            table_name = entity.get("name")
            for measure in entity.get("measures", []):
                measures.append({
                    "Measure Name": measure.get("name"),
                    "Table Name": table_name,
                    "Expression": measure.get("expression"),
                    "Data Type": measure.get("dataType"),
                    "Format String": measure.get("formatString"),
                    "Data Category": measure.get("dataCategory"),
                })
        return measures

    def _is_measure_referenced(
        self, 
        json_data, 
        measure_name: str, 
        entity_name: str, 
        path: str = "", 
        pattern=None,
        ignore_unapplied_filters: bool = False
    ) -> bool:

        if isinstance(json_data, dict):

            # filter pane special case
            if ignore_unapplied_filters and "filterConfig" in path:
                if "field" in json_data and "Measure" in json_data.get("field", {}):
                    obj = json_data["field"]["Measure"]
                    if isinstance(obj, dict):
                        if (
                            obj.get("Property") == measure_name and
                            obj.get("Expression", {}).get("SourceRef", {}).get("Entity") == entity_name
                        ):
                            return "filter" in json_data

            # normal measure reference
            if "Measure" in json_data:
                obj = json_data["Measure"]
                if isinstance(obj, dict):
                    if (
                        obj.get("Property") == measure_name and
                        obj.get("Expression", {}).get("SourceRef", {}).get("Entity") == entity_name
                    ):
                        return True

            # expression string reference
            if "Expression" in json_data and isinstance(json_data["Expression"], str):
                if pattern and pattern.search(json_data["Expression"]):
                    return True

            # recurse
            for key, value in json_data.items():
                new_path = f"{path}.{key}" if path else key
                if self._is_measure_referenced(value, measure_name, entity_name, new_path, pattern, ignore_unapplied_filters):
                    return True

        elif isinstance(json_data, list):
            for item in json_data:
                if self._is_measure_referenced(item, measure_name, entity_name, path, pattern, ignore_unapplied_filters):
                    return True

        return False

    # -----------------------------------------------------------------
    # ✅ REMOVE UNUSED MEASURES
    # -----------------------------------------------------------------
    def remove_unused_measures(
        self, 
        dry_run: bool = True, 
        ignore_unapplied_filters: bool = False
    ) -> Tuple[List[Dict[str, str]], int]:

        measures = self.list_report_level_measures()
        if not measures:
            print("ℹ️  No report-level measures found.")
            return [], 0

        print(f"📊 Found {len(measures)} report-level measures")

        all_removed = []
        virtually_removed = set()
        iteration = 0
        max_iterations = 10

        report_parts = self._load_all_report_parts()

        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Iteration {iteration}...")

            current = [m for m in measures if m["Measure Name"] not in virtually_removed]
            if not current:
                break

            used = set()
            measure_map = {m["Measure Name"]: m["Table Name"] for m in current}

            # scan visuals + pages + bookmarks
            for m in current:
                pattern = re.compile(r"\[" + re.escape(m["Measure Name"]) + r"\]")
                for part in report_parts:
                    if part["path"] == str(self.report_extensions_path):
                        continue
                    if self._is_measure_referenced(
                        part["payload"],
                        m["Measure Name"],
                        m["Table Name"],
                        pattern=pattern,
                        ignore_unapplied_filters=ignore_unapplied_filters
                    ):
                        used.add(m["Measure Name"])
                        break

            # local dependencies in measure definitions
            if self.report_extensions_path.exists():
                ext = self._load_json_file(self.report_extensions_path)
                for entity in ext.get("entities", []):
                    for m in entity.get("measures", []):
                        if dry_run and m.get("name") in virtually_removed:
                            continue
                        expr = m.get("expression", "")
                        if isinstance(expr, str):
                            for ref in re.findall(r"\[([^\]]+)\]", expr):
                                if ref in measure_map:
                                    used.add(ref)

            unused = [m["Measure Name"] for m in current if m["Measure Name"] not in used]

            if not unused:
                print("✅ No unused measures this round.")
                break

            print(f"   Found {len(unused)} unused measure(s).")

            removed_this_round = [m for m in current if m["Measure Name"] in unused]

            if not dry_run:
                remove_set = {(m["Measure Name"], m["Table Name"]) for m in removed_this_round}
                self._remove_measures_from_file(unused)

                # clean filters that reference removed measures
                for part in report_parts:
                    if 'definition/reportExtensions.json' in part["path"]:
                        continue

                    payload = part["payload"]
                    if isinstance(payload, dict) and "filterConfig" in payload and "filters" in payload["filterConfig"]:
                        orig = payload["filterConfig"]["filters"]
                        cleaned = []
                        for f in orig:
                            if (
                                "field" in f and 
                                "Measure" in f.get("field", {}) and
                                isinstance(f["field"]["Measure"], dict)
                            ):
                                key = (
                                    f["field"]["Measure"].get("Property"),
                                    f["field"]["Measure"].get("Expression", {}).get("SourceRef", {}).get("Entity")
                                )
                                if key in remove_set:
                                    continue
                            cleaned.append(f)

                        if len(cleaned) < len(orig):
                            payload["filterConfig"]["filters"] = cleaned
                            file_path = self.definition_path / part["path"].replace("definition/", "")
                            self._save_json_file(file_path, payload)

                report_parts = self._load_all_report_parts()
                measures = self.list_report_level_measures()

            else:
                virtually_removed.update(unused)

            all_removed.extend(removed_this_round)

        return all_removed, iteration

    def _remove_measures_from_file(self, measure_names: List[str]):
        if not self.report_extensions_path.exists():
            return

        ext = self._load_json_file(self.report_extensions_path)

        for entity in ext.get("entities", []):
            entity["measures"] = [
                m for m in entity.get("measures", [])
                if m.get("name") not in measure_names
            ]

        ext["entities"] = [e for e in ext.get("entities", []) if e.get("measures")]

        if ext.get("entities"):
            self._save_json_file(self.report_extensions_path, ext)
        else:
            self.report_extensions_path.unlink()
            print("🗑️  Removed reportExtensions.json (all measures removed).")

    # =========================================================================
    # ✅ ✅ NEW: TABLE + COLUMN DETECTION (Semantic Model or PBIR)
    # =========================================================================

    def list_all_tables_and_columns(self):
        """Load tables + columns from model.json (semantic model)."""
        if self.model_path:
            model_file = self.model_path / "model.json"
            if model_file.exists():
                model_json = self._load_json_file(model_file)
                tables = []
                columns = []

                for table in model_json.get("tables", []):
                    tname = table.get("name")
                    tables.append(tname)

                    for col in table.get("columns", []):
                        columns.append({
                            "table": tname,
                            "column": col.get("name")
                        })

                return tables, columns

        # fallback to PBIR modelExtensions
        tables = []
        columns = []

        if self.report_json_path.exists():
            report = self._load_json_file(self.report_json_path)
            model_ext = report.get("modelExtensions", {})
            entities = model_ext.get("entities", [])

            for entity in entities:
                tname = entity.get("name")
                tables.append(tname)
                for col in entity.get("columns", []):
                    columns.append({
                        "table": tname,
                        "column": col.get("name")
                    })

        return tables, columns

    def _is_column_referenced(self, json_data, table_name: str, column_name: str) -> bool:

        if isinstance(json_data, dict):

            # Case 1: Standard Column reference
            if "Column" in json_data:
                c = json_data["Column"]
                if (
                    c.get("Property") == column_name and 
                    c.get("Expression", {}).get("SourceRef", {}).get("Entity") == table_name
                ):
                    return True

            # Case 2: entity/property references (common in visuals)
            if (
                json_data.get("entity") == table_name and
                json_data.get("property") == column_name
            ):
                return True

            # Case 3: Expression string pattern
            if isinstance(json_data.get("Expression"), str):
                expr = json_data.get("Expression")
                if f"[{table_name}].[{column_name}]" in expr:
                    return True

            # recurse
            for v in json_data.values():
                if self._is_column_referenced(v, table_name, column_name):
                    return True

        elif isinstance(json_data, list):
            for item in json_data:
                if self._is_column_referenced(item, table_name, column_name):
                    return True

        return False

    def detect_unused_tables_and_columns(self):
        """Return (unused_tables, unused_columns)."""
        tables, columns = self.list_all_tables_and_columns()
        report_parts = self._load_all_report_parts()

        used_tables = set()
        used_columns = set()

        # scan every PBIR part
        for col in columns:
            t = col["table"]
            c = col["column"]

            for part in report_parts:
                if self._is_column_referenced(part["payload"], t, c):
                    used_columns.add((t, c))
                    used_tables.add(t)
                    break

        # columns not used
        unused_columns = [
            col for col in columns
            if (col["table"], col["column"]) not in used_columns
        ]

        # tables with NO used columns
        unused_tables = [
            t for t in tables
            if t not in used_tables
        ]

        return unused_tables, unused_columns


# =====================================================================
# ✅ MAIN
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Remove unused report-level measures + detect unused tables/columns."
    )

    parser.add_argument("report_path", help="Path to the .Report folder")
    parser.add_argument("--model-path", help="Path to the semantic model folder (.SemanticModel)", required=False)
    parser.add_argument("--execute", action="store_true", help="Remove unused measures (default = dry run)")
    parser.add_argument("--ignore-unapplied-filters", action="store_true")

    args = parser.parse_args()

    try:
        cleaner = PBIRMeasureCleaner(
            report_path=args.report_path,
            model_path=args.model_path
        )

        print(f"🔍 Analyzing report: {args.report_path}")
        if args.model_path:
            print(f"   Using semantic model: {args.model_path}")
        print(f"   Mode: {'REMOVE' if args.execute else 'DRY RUN'}")

        # -------------------------------------------------------------
        # ✅ Remove unused measures
        # -------------------------------------------------------------
        removed_measures, iterations = cleaner.remove_unused_measures(
            dry_run=not args.execute,
            ignore_unapplied_filters=args.ignore_unapplied_filters
        )

        if removed_measures:
            action = "Removed" if args.execute else "Would remove"
            print(f"\n{'✅' if args.execute else 'ℹ️ '} {action} {len(removed_measures)} unused measure(s):")
            for m in removed_measures:
                print(f"   - {m['Table Name']}.{m['Measure Name']}")
        else:
            print("\n✅ No unused report-level measures found.")

        # -------------------------------------------------------------
        # ✅ Detect unused tables & columns
        # -------------------------------------------------------------
        print("\n🔎 Detecting unused tables & columns…")
        unused_tables, unused_columns = cleaner.detect_unused_tables_and_columns()

        print("\n📦 Unused Tables:")
        if unused_tables:
            for t in unused_tables:
                print(f"   - {t}")
        else:
            print("   ✅ None")

        print("\n📄 Unused Columns:")
        if unused_columns:
            for col in unused_columns:
                print(f"   - {col['table']}.{col['column']}")
        else:
            print("   ✅ None")

        if removed_measures and not args.execute:
            print("\n💡 Run with --execute to actually remove unused measures.")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())