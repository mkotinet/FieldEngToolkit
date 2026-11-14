"""
Data Merger and Cross-Validation Engine (csv-excel-merger).
Merges instrumentation lists, PLC I/O lists, and wiring schedules by primary key.
Performs data integrity verification and identifies missing tags or mismatched signals.
"""

import os
import pandas as pd

class EngineeringDataMerger:
    def __init__(self):
        pass

    def load_data(self, source):
        """Helper to load dataframe from CSV or Excel or list of dicts"""
        if isinstance(source, pd.DataFrame):
            return source
        elif isinstance(source, list):
            return pd.DataFrame(records) if (records := source) else pd.DataFrame()
        elif isinstance(source, str) and os.path.exists(source):
            if source.endswith(".csv"):
                return pd.read_csv(source, encoding="utf-8-sig")
            else:
                return pd.read_excel(source)
        return pd.DataFrame()

    def correlate_pid_and_plc(self, pid_data, plc_data):
        """
        Correlates P&ID Instrument Index with PLC I/O list.
        Detects missing I/O points and generates integrated Master Sheet.
        """
        df_pid = self.load_data(pid_data)
        df_plc = self.load_data(plc_data)

        if df_pid.empty or df_plc.empty:
            return pd.DataFrame(), {"matched": 0, "missing_in_plc": 0, "missing_in_pid": 0}

        # Find key column for Tag
        pid_tag_col = next((c for c in df_pid.columns if "태그" in c or "TAG" in c.upper()), df_pid.columns[1])
        plc_tag_col = next((c for c in df_plc.columns if "태그" in c or "TAG" in c.upper()), df_plc.columns[0])

        df_pid["JOIN_TAG"] = df_pid[pid_tag_col].astype(str).str.strip().str.upper()
        df_plc["JOIN_TAG"] = df_plc[plc_tag_col].astype(str).str.strip().str.upper()

        # Outer join to find discrepancies
        merged = pd.merge(df_pid, df_plc, on="JOIN_TAG", how="outer", suffixes=("_PID", "_PLC"))

        # Status categorization
        def determine_status(row):
            in_pid = pd.notna(row.get(pid_tag_col))
            in_plc = pd.notna(row.get(plc_tag_col))
            if in_pid and in_plc:
                return "정상 매칭 (Matched)"
            elif in_pid and not in_plc:
                return "PLC I/O 누락 주의 (Missing in PLC)"
            else:
                return "P&ID 도면 누락 주의 (Missing in P&ID)"

        merged["검증 상태 (Verification Status)"] = merged.apply(determine_status, axis=1)

        counts = merged["검증 상태 (Verification Status)"].value_counts().to_dict()
        stats = {
            "matched": counts.get("정상 매칭 (Matched)", 0),
            "missing_in_plc": counts.get("PLC I/O 누락 주의 (Missing in PLC)", 0),
            "missing_in_pid": counts.get("P&ID 도면 누락 주의 (Missing in P&ID)", 0),
            "total_records": len(merged)
        }

        # Drop temporary column
        merged = merged.drop(columns=["JOIN_TAG"])
        return merged, stats
