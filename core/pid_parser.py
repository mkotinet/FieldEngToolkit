"""
P&ID and Layout Takeoff Parser (oce-bim-takeoff).
Extracts ISA-5.1 instrumentation tags (FIT, PIT, TIT, LIT, HCV, etc.),
classifies explosion-proof (Ex) ratings, and calculates Cable Gland & Ex Accessories MTO.
"""

import os
import re
import pandas as pd

INSTRUMENT_TYPES = {
    "F": {"name": "Flow (유량)", "tags": ["FIT", "FT", "FE", "FCV", "FIC", "FS"]},
    "P": {"name": "Pressure (압력)", "tags": ["PIT", "PT", "PI", "PIC", "PSV", "PSH", "PSL"]},
    "L": {"name": "Level (액위/레벨)", "tags": ["LIT", "LT", "LG", "LIC", "LSH", "LSL"]},
    "T": {"name": "Temperature (온도)", "tags": ["TIT", "TT", "TE", "TI", "TIC", "TSH"]},
    "A": {"name": "Analyzer (분석계)", "tags": ["AIT", "AT", "AI"]},
    "V": {"name": "Valve / Actuator (밸브/구동기)", "tags": ["HCV", "XV", "MOV", "FCV", "PCV", "TCV"]}
}

class PidTakeoffParser:
    def __init__(self):
        # Default Ex Cable Gland specs
        self.gland_rules = {
            "ANALOG_TRANSMITTER": {"thread": 'NPT 1/2"', "ex_type": "Ex d IIC", "gland_type": "Double Compression (Armoured)", "mat": "SS316"},
            "TEMPERATURE_TRANSMITTER": {"thread": 'M20 x 1.5', "ex_type": "Ex ia IIC", "gland_type": "Single Compression", "mat": "Nickel-plated Brass"},
            "ON_OFF_VALVE": {"thread": 'NPT 3/4"', "ex_type": "Ex d IIB+H2", "gland_type": "Barrier Gland (Ex d)", "mat": "SS316"},
            "CONTROL_VALVE": {"thread": 'NPT 1/2"', "ex_type": "Ex ia IIC", "gland_type": "Double Compression", "mat": "SS316"},
            "DISCRETE_SWITCH": {"thread": 'NPT 1/2"', "ex_type": "Ex d IIC", "gland_type": "Single Compression", "mat": "Brass"},
            "SAFE_AREA": {"thread": 'M20 x 1.5', "ex_type": "Non-Ex / IP66", "gland_type": "Industrial Standard", "mat": "Polyamide/Brass"}
        }

    def classify_instrument(self, tag_name):
        """Classify instrument category from tag name (e.g. FIT-101 -> Flow, FIT)"""
        clean_tag = tag_name.upper().strip()
        # Regex to extract letters e.g. 10-FIT-101 -> FIT
        match = re.search(r"([A-Z]{2,4})", clean_tag)
        type_letters = match.group(1) if match else "GEN"

        category = "기타 계기 (General Instrument)"
        inst_type = type_letters

        for first_char, info in INSTRUMENT_TYPES.items():
            if any(type_letters.startswith(t) or t in type_letters for t in info["tags"]):
                category = info["name"]
                inst_type = type_letters
                break

        return category, inst_type

    def determine_ex_and_gland(self, tag_name, category, zone="Zone 1"):
        """Determine hazardous area classification, Ex rating and cable gland specification"""
        tag_up = tag_name.upper()

        if "SAFE" in zone.upper() or "NON" in zone.upper():
            spec = self.gland_rules["SAFE_AREA"]
            ex_rating = "Non-Ex (Safe Area)"
        elif "TIT" in tag_up or "TT" in tag_up:
            spec = self.gland_rules["TEMPERATURE_TRANSMITTER"]
            ex_rating = "Ex ia IIC T4 Ga (본질안전)"
        elif "XV" in tag_up or "MOV" in tag_up:
            spec = self.gland_rules["ON_OFF_VALVE"]
            ex_rating = "Ex d IIB+H2 T4 Gb (내압방폭)"
        elif "HCV" in tag_up or "CV" in tag_up:
            spec = self.gland_rules["CONTROL_VALVE"]
            ex_rating = "Ex ia IIC T4 (본질안전/스마트포지셔너)"
        elif "FIT" in tag_up or "PIT" in tag_up or "LIT" in tag_up:
            spec = self.gland_rules["ANALOG_TRANSMITTER"]
            ex_rating = "Ex d IIC T6 Gb (내압방폭)"
        else:
            spec = self.gland_rules["DISCRETE_SWITCH"]
            ex_rating = "Ex d IIC T5 (내압방폭)"

        return ex_rating, spec

    def parse_pid_data(self, source):
        """
        Parses P&ID tags dataset (CSV/Excel or list) and returns:
        1. Instrument Index Table
        2. Cable Gland & Ex Accessories Takeoff (MTO)
        3. Instrument Tag Count Summary by Category
        """
        if isinstance(source, str) and os.path.exists(source):
            if source.endswith(".csv"):
                df = pd.read_csv(source, encoding="utf-8-sig")
            else:
                df = pd.read_excel(source)
            records = df.to_dict(orient="records")
        elif isinstance(source, list):
            records = source
        else:
            records = []

        instrument_index = []
        gland_takeoff_dict = {}
        category_counts = {}

        for idx, row in enumerate(records, start=1):
            tag = str(row.get("태그번호 (Tag No)", row.get("TagNo", f"10-FIT-{100+idx}")))
            loop_no = str(row.get("루프번호 (Loop No)", row.get("LoopNo", re.sub(r"[^\d]", "", tag))))
            area = str(row.get("설치구역 (Area/Location)", row.get("Area", "석유화학 반응공정동 (Zone 1)")))
            zone = "Zone 1" if "Zone 1" in area or "1" in area else ("Zone 2" if "Zone 2" in area else "Safe Area")
            service = str(row.get("측정대상/용도 (Service)", row.get("Service", "공정 유체 유량 측정")))
            signal = str(row.get("신호방식 (Signal)", row.get("Signal", "4~20mA HART (2-Wire)")))

            category, inst_type = self.classify_instrument(tag)
            category_counts[category] = category_counts.get(category, 0) + 1

            ex_rating, gland_spec = self.determine_ex_and_gland(tag, category, zone)

            # Gland count per instrument (Valves usually 2 glands for signal + limit switch, transmitters 1 or 2)
            gland_qty = 2 if ("XV" in tag or "MOV" in tag or "HCV" in tag) else 1
            gland_key = (gland_spec["thread"], gland_spec["ex_type"], gland_spec["gland_type"], gland_spec["mat"])
            gland_takeoff_dict[gland_key] = gland_takeoff_dict.get(gland_key, 0) + gland_qty

            instrument_index.append({
                "No": idx,
                "계기 태그번호 (Tag No)": tag,
                "루프 번호 (Loop No)": loop_no,
                "계기 분류 (Category)": category,
                "계기 형식 (Type)": inst_type,
                "측정/제어 용도 (Service)": service,
                "설치 구역 (Area / Zone)": area,
                "방폭 등급 (Ex Rating)": ex_rating,
                "엔트리 규격 (Cable Entry)": gland_spec["thread"],
                "적용 신호 사양 (Signal)": signal,
                "그랜드 수량 (Gland Qty)": gland_qty
            })

        # Build Gland MTO List
        gland_mto = []
        g_idx = 1
        for (thread, ex_type, g_type, mat), qty in sorted(gland_takeoff_dict.items()):
            gland_mto.append({
                "No": g_idx,
                "품목명 (Item Description)": f"방폭 케이블 그랜드 ({ex_type})",
                "나사 규격 (Thread Size)": thread,
                "그랜드 형식 (Gland Type)": g_type,
                "재질 (Material)": mat,
                "수량 (Quantity)": qty,
                "단위 (Unit)": "EA",
                "인증 규격 (Certification)": "KCs / IECEx / ATEX",
                "비고 (Remarks)": "방폭 악세서리 실링 와셔 & 락너트 포함"
            })
            g_idx += 1

        # Also add Stopping Plugs and Breather/Drain Drains
        stopping_plugs = max(len(instrument_index) // 2, 5)
        gland_mto.append({
            "No": g_idx,
            "품목명 (Item Description)": "방폭 블라인드 플러그 (Stopping Plug - Ex d)",
            "나사 규격 (Thread Size)": 'NPT 1/2"',
            "그랜드 형식 (Gland Type)": "Hex Head Blind Plug",
            "재질 (Material)": "SS316",
            "수량 (Quantity)": stopping_plugs,
            "단위 (Unit)": "EA",
            "인증 규격 (Certification)": "IECEx / KCs Ex d IIC",
            "비고 (Remarks)": "미사용 케이블 엔트리 밀폐용"
        })

        return instrument_index, gland_mto, category_counts
