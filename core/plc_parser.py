"""
PLC Wire Diagram & I/O List Parser and Marshalling Scheduler.
Generates From-To wiring schedules, Marshalling Terminal Block (TB) pinmaps,
and PLC Rack/Slot/Channel mapping tables with spare capacity analysis.
"""

import os
import re
import pandas as pd

class PlcWiringIoParser:
    def __init__(self):
        # Color mapping heuristics
        self.color_map = {
            "24V+": ("BLUE", "0.75 SQ", "KIV"),
            "24V-": ("WHITE/BLUE", "0.75 SQ", "KIV"),
            "220V_L": ("BLACK", "1.5 SQ", "KIV"),
            "220V_N": ("WHITE", "1.5 SQ", "KIV"),
            "GND": ("GREEN/YELLOW", "2.5 SQ", "GV"),
            "DI": ("YELLOW", "0.75 SQ", "KIV"),
            "DO": ("ORANGE", "0.75 SQ", "KIV"),
            "AI": ("PAIR (BLK/WHT)", "1.25 SQ", "CVV-S (Shielded)"),
            "AO": ("PAIR (BLK/WHT)", "1.25 SQ", "CVV-S (Shielded)")
        }

    def infer_wire_properties(self, wire_no, signal_type="DI"):
        """Infer recommended color, size, and cable type from wire number or signal type"""
        wn = str(wire_no).upper()
        st = str(signal_type).upper()

        if "24V+" in wn or "P24" in wn or "DC+" in wn:
            return self.color_map["24V+"]
        elif "24V-" in wn or "N24" in wn or "DC-" in wn or "0V" in wn:
            return self.color_map["24V-"]
        elif "GND" in wn or "PE" in wn or "FG" in wn:
            return self.color_map["GND"]
        elif "220" in wn or "L1" in wn or "AC" in wn:
            return self.color_map["220V_L"]
        elif "AI" in st:
            return self.color_map["AI"]
        elif "AO" in st:
            return self.color_map["AO"]
        elif "DO" in st:
            return self.color_map["DO"]
        else:
            return self.color_map["DI"]

    def parse_wiring_data(self, wiring_source):
        """
        Parses wiring CSV/Excel or list of dicts.
        Returns standardized From-To wiring schedule.
        """
        if isinstance(wiring_source, str) and os.path.exists(wiring_source):
            if wiring_source.endswith(".csv"):
                df = pd.read_csv(wiring_source, encoding="utf-8-sig")
            else:
                df = pd.read_excel(wiring_source)
            records = df.to_dict(orient="records")
        elif isinstance(wiring_source, list):
            records = wiring_source
        else:
            records = []

        from_to_schedule = []
        for idx, row in enumerate(records, start=1):
            wire_no = str(row.get("선번 (Wire No)", row.get("WireNo", f"W-{100+idx}")))
            sig_type = str(row.get("신호구분", row.get("SignalType", "DI")))
            color, size, spec = self.infer_wire_properties(wire_no, sig_type)

            # Override if given in source
            color = row.get("색상", row.get("Color", color))
            size = row.get("규격", row.get("Size", size))
            spec = row.get("선종", row.get("CableSpec", spec))

            from_to_schedule.append({
                "No": idx,
                "선번 (Wire No)": wire_no,
                "신호 구분 (Signal Type)": sig_type,
                "선종 (Cable Spec)": spec,
                "심선 굵기 (Size)": size,
                "심선 색상 (Color)": color,
                "출발 기기 (From Device)": row.get("From_Device", row.get("출발기기", "SMPS1")),
                "출발 단자 (From Pin)": row.get("From_Pin", row.get("출발단자", "L+")),
                "도착 기기 (To Device)": row.get("To_Device", row.get("도착기기", "TB101")),
                "도착 단자 (To Pin)": row.get("To_Pin", row.get("도착단자", str(idx))),
                "용도 및 설명 (Description)": row.get("Description", row.get("용도", "제어 배선"))
            })

        return from_to_schedule

    def parse_io_and_build_pinmap(self, io_source):
        """
        Parses PLC I/O assignments and generates:
        1. Marshalling TB Pinmap
        2. PLC Module Channel Mapping
        3. I/O Summary Statistics (Total, DI, DO, AI, AO, Spares)
        """
        if isinstance(io_source, str) and os.path.exists(io_source):
            if io_source.endswith(".csv"):
                df = pd.read_csv(io_source, encoding="utf-8-sig")
            else:
                df = pd.read_excel(io_source)
            records = df.to_dict(orient="records")
        elif isinstance(io_source, list):
            records = io_source
        else:
            records = []

        marshalling_pinmap = []
        plc_channel_map = []
        io_stats = {"DI": 0, "DO": 0, "AI": 0, "AO": 0, "SPARE": 0}

        # Marshalling TB allocation tracking
        tb_counters = {"TB101_DI": 1, "TB102_DO": 1, "TB201_AI": 1, "TB202_AO": 1}

        for idx, row in enumerate(records, start=1):
            tag = str(row.get("태그명 (Tag)", row.get("Tag", f"TAG-{idx}")))
            sig_type = str(row.get("신호구분", row.get("SignalType", "DI"))).upper()
            plc_addr = str(row.get("PLC주소 (Address)", row.get("Address", f"%I0.{idx-1}")))
            rack = row.get("Rack", 0)
            slot = row.get("Slot", 1)
            channel = row.get("Channel", (idx-1) % 16)
            desc = str(row.get("설명 (Description)", row.get("Description", "")))
            is_spare = "SPARE" in tag.upper() or "예비" in desc

            # Update stats
            if is_spare:
                io_stats["SPARE"] += 1
            elif sig_type in io_stats:
                io_stats[sig_type] += 1

            # Determine Marshalling TB Block
            if sig_type == "DI":
                tb_name = "TB101 (DI)"
                pin_no = tb_counters["TB101_DI"]
                tb_counters["TB101_DI"] += 2  # Signal & Common
                field_terminals = f"{pin_no} (+), {pin_no+1} (COM)"
            elif sig_type == "DO":
                tb_name = "TB102 (DO)"
                pin_no = tb_counters["TB102_DO"]
                tb_counters["TB102_DO"] += 2
                field_terminals = f"{pin_no} (+), {pin_no+1} (COM)"
            elif sig_type == "AI":
                tb_name = "TB201 (AI)"
                pin_no = tb_counters["TB201_AI"]
                tb_counters["TB201_AI"] += 3  # (+), (-), Shield
                field_terminals = f"{pin_no} (+), {pin_no+1} (-), {pin_no+2} (SH)"
            else: # AO
                tb_name = "TB202 (AO)"
                pin_no = tb_counters["TB202_AO"]
                tb_counters["TB202_AO"] += 3
                field_terminals = f"{pin_no} (+), {pin_no+1} (-), {pin_no+2} (SH)"

            marshalling_pinmap.append({
                "No": idx,
                "마샬링 TB (TB Group)": tb_name,
                "단자 핀 번호 (Pin No)": field_terminals,
                "계기 태그 (Instrument Tag)": tag,
                "신호 구분 (Signal Type)": sig_type,
                "PLC 하드웨어 주소": f"Rack {rack} / Slot {slot} / Ch {channel}",
                "PLC 소프트웨어 어드레스": plc_addr,
                "필드 케이블 번호": f"CBL-{tag.replace('-', '')}",
                "기능 설명 (Service Description)": desc if desc else ("예비 채널 (Spare)" if is_spare else "현장 제어 신호")
            })

            plc_channel_map.append({
                "Index": idx,
                "Rack": rack,
                "Slot": slot,
                "Channel": channel,
                "PLC Address": plc_addr,
                "Signal Type": sig_type,
                "Connected Tag": tag,
                "Marshalling TB Reference": f"{tb_name} [{field_terminals}]",
                "Status": "Spare (예비)" if is_spare else "Active (사용중)"
            })

        total_channels = len(records)
        used_channels = total_channels - io_stats["SPARE"]
        spare_pct = round((io_stats["SPARE"] / total_channels * 100), 1) if total_channels > 0 else 0.0

        summary = {
            "Total Channels": total_channels,
            "Used Channels": used_channels,
            "Spare Channels": io_stats["SPARE"],
            "Spare Percentage (%)": spare_pct,
            "DI Count": io_stats["DI"],
            "DO Count": io_stats["DO"],
            "AI Count": io_stats["AI"],
            "AO Count": io_stats["AO"]
        }

        return marshalling_pinmap, plc_channel_map, summary
