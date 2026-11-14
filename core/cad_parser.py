"""
CAD to Data Parser for Cable Trays, Control Ducts, and Raceways.
Uses ezdxf to parse DXF drawings, calculate total linear run lengths,
determine sizes (W x H), look up unit weights (kg/m), and count fittings/hangers.
"""

import math
import re
import os
import ezdxf

# Default Unit Weights (kg/m) for HDG Steel Cable Trays & Ducts
DEFAULT_UNIT_WEIGHTS = {
    "TRAY_150x100": 4.80,
    "TRAY_200x100": 5.40,
    "TRAY_300x100": 6.80,
    "TRAY_400x100": 8.10,
    "TRAY_450x100": 8.90,
    "TRAY_600x100": 11.20,
    "TRAY_800x100": 13.80,
    "TRAY_900x100": 15.50,
    "DUCT_60x60":   0.45,
    "DUCT_80x80":   0.65,
    "DUCT_100x100": 0.95,
    "DUCT_150x100": 1.40,
    "DUCT_200x100": 2.10,
    "DUCT_300x100": 3.20,
}

class CadDuctTrayParser:
    def __init__(self, scale_ratio=1.0, unit="mm", hanger_interval_m=2.0):
        """
        - scale_ratio: drawing scale (e.g. 1.0 for 1:1, 0.01 for 1:100 if drawn in cm)
        - unit: 'mm' or 'm' (drawing unit)
        - hanger_interval_m: Support hanger auto-calc interval (default: every 2 meters)
        """
        self.scale_ratio = scale_ratio
        self.unit = unit
        self.unit_to_meter = 0.001 if unit.lower() == "mm" else 1.0
        self.hanger_interval_m = hanger_interval_m

    def parse_size_from_text(self, text):
        """Extract W x H dimensions from layer names or annotations (e.g. 'TRAY_600x100' -> (600, 100))"""
        pattern = r"(\d{2,4})\s*[*xX/]\s*(\d{2,4})"
        match = re.search(pattern, text)
        if match:
            w, h = int(match.group(1)), int(match.group(2))
            return max(w, h), min(w, h)
        return None, None

    def estimate_unit_weight(self, width, height, is_duct=False):
        """Estimate or lookup kg/m unit weight"""
        if width and height:
            key = f"{'DUCT' if is_duct else 'TRAY'}_{width}x{height}"
            if key in DEFAULT_UNIT_WEIGHTS:
                return DEFAULT_UNIT_WEIGHTS[key]
            # Empirical formula if not found
            # Tray: approx (2 * H + W) * thickness * steel density + safety
            perimeter_m = (2 * height + width) / 1000.0
            return round(perimeter_m * 1.6 * 7.85 * 0.9, 2)
        return 5.0 # fallback default

    def parse_dxf(self, dxf_filepath):
        """
        Parses DXF file and returns:
        - tray_mto: list of dicts with route details (Layer, Category, Size, Length_m, UnitWeight_kg_m, TotalWeight_kg)
        - fitting_mto: list of dicts with fittings (Elbow 90, Elbow 45, Tee, Reducer, Hanger)
        """
        if not os.path.exists(dxf_filepath):
            raise FileNotFoundError(f"CAD file not found: {dxf_filepath}")

        doc = ezdxf.readfile(dxf_filepath)
        msp = doc.modelspace()

        layer_lengths = {}      # layer_name -> total length in meters
        layer_elements = {}     # layer_name -> count of entities
        fitting_counts = {}     # (layer/spec, fitting_type) -> count

        # 1. Parse linear entities (Lines, LWPolylines, Arcs)
        for entity in msp:
            layer = entity.dxf.layer.upper()
            etype = entity.dxftype()

            length_m = 0.0

            if etype == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                dist = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2 + (end[2] - start[2])**2)
                length_m = dist * self.scale_ratio * self.unit_to_meter

            elif etype == "LWPOLYLINE":
                points = entity.get_points()
                if len(points) > 1:
                    total_dist = 0.0
                    for i in range(len(points) - 1):
                        p1, p2 = points[i], points[i+1]
                        total_dist += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                    if entity.is_closed:
                        p1, p2 = points[-1], points[0]
                        total_dist += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                    length_m = total_dist * self.scale_ratio * self.unit_to_meter

            elif etype == "ARC":
                radius = entity.dxf.radius
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                diff_angle = (end_angle - start_angle) % (2 * math.pi)
                arc_len = radius * diff_angle
                length_m = arc_len * self.scale_ratio * self.unit_to_meter

            elif etype == "INSERT":
                # Block reference (Fitting / Hanger)
                block_name = entity.dxf.name.upper()
                fitting_type = "기타 부속 (Misc Fitting)"

                if "ELBOW" in block_name or "ELB" in block_name:
                    if "45" in block_name:
                        fitting_type = "수평 엘보 45° (Horizontal Elbow 45°)"
                    else:
                        fitting_type = "수평 엘보 90° (Horizontal Elbow 90°)"
                elif "TEE" in block_name:
                    fitting_type = "수평 티 (Horizontal Tee)"
                elif "RED" in block_name:
                    fitting_type = "레듀셔 (Reducer)"
                elif "HANGER" in block_name or "SUPPORT" in block_name:
                    fitting_type = "서포트 행거 (Support Hanger)"
                elif "COVER" in block_name:
                    fitting_type = "트레이 커버 (Cover Plate)"

                fitting_counts[fitting_type] = fitting_counts.get(fitting_type, 0) + 1

            if length_m > 0.0001:
                layer_lengths[layer] = layer_lengths.get(layer, 0.0) + length_m
                layer_elements[layer] = layer_elements.get(layer, 0) + 1

        # 2. Build Route MTO Table
        tray_mto = []
        item_no = 1
        total_length_all = 0.0

        for layer, length_m in sorted(layer_lengths.items()):
            w, h = self.parse_size_from_text(layer)
            is_duct = "DUCT" in layer or "덕트" in layer
            category = "제어 덕트 (Control Duct)" if is_duct else "케이블 트레이 (Cable Tray)"
            
            size_str = f"{w}W x {h}H" if w and h else "표준 규격 (Standard)"
            unit_wt = self.estimate_unit_weight(w, h, is_duct)
            total_wt = round(length_m * unit_wt, 2)
            round_len = round(length_m, 2)
            total_length_all += round_len

            tray_mto.append({
                "No": item_no,
                "도면 레이어 (Layer)": layer,
                "구분 (Category)": category,
                "규격 (Size WxH mm)": size_str,
                "단위중량 (kg/m)": unit_wt,
                "총 연장 (Total Length m)": round_len,
                "총 중량 (Total Weight kg)": total_wt,
                "재질 및 마감 (Material/Finish)": "PVC 난연" if is_duct else "용융아연도금강판 (HDG)",
                "적용 규격 (Standard)": "KS C 8460 / NEMA VE 1"
            })
            item_no += 1

        # 3. Build Fittings MTO Table
        fittings_mto = []
        f_no = 1

        # If no explicit hanger block found, auto-calculate hangers based on total length
        explicit_hangers = fitting_counts.get("서포트 행거 (Support Hanger)", 0)
        auto_hangers = max(math.ceil(total_length_all / self.hanger_interval_m), 1) if total_length_all > 0 else 0
        final_hangers = max(explicit_hangers, auto_hangers)
        fitting_counts["서포트 행거 (Support Hanger)"] = final_hangers

        for f_type, count in sorted(fitting_counts.items()):
            unit_wt_approx = 4.5 if "티" in f_type else (3.2 if "엘보" in f_type else 2.5)
            fittings_mto.append({
                "No": f_no,
                "품목명 (Item Description)": f_type,
                "수량 (Quantity)": count,
                "단위 (Unit)": "EA",
                "예상 단위중량 (kg/ea)": unit_wt_approx,
                "예상 총중량 (kg)": round(count * unit_wt_approx, 2),
                "비고 (Remarks)": "자동 적산 (Auto-Takeoff)" if f_type == "서포트 행거 (Support Hanger)" and explicit_hangers == 0 else "도면 추출"
            })
            f_no += 1

        return tray_mto, fittings_mto
