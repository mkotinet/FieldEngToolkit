"""
Generate realistic sample datasets for:
1. CAD DXF Cable Tray & Duct drawing (with polylines, lines, fittings, hangers)
2. PLC Wiring CSV
3. PLC I/O Excel file
4. P&ID Instrument Index CSV
"""

import os
import ezdxf
import pandas as pd

def generate_sample_dxf(output_path):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # Create layers
    doc.layers.add("TRAY_600x100", color=1) # Red
    doc.layers.add("TRAY_400x100", color=2) # Yellow
    doc.layers.add("TRAY_200x100", color=3) # Green
    doc.layers.add("DUCT_150x100", color=4) # Cyan
    doc.layers.add("DUCT_80x80", color=6)   # Magenta
    doc.layers.add("FITTINGS", color=7)     # White

    # Define Block definitions for fittings
    for blk_name in ["ELBOW_90", "ELBOW_45", "TEE", "REDUCER", "SUPPORT_HANGER"]:
        blk = doc.blocks.new(name=blk_name)
        blk.add_circle((0, 0), radius=50)
        blk.add_text(blk_name, dxfattribs={"height": 20}).set_placement((0, 0))

    # Add TRAY_600x100 routes (Main Backbone: approx 150m = 150000 mm)
    msp.add_lwpolyline(
        [(0, 0), (50000, 0), (50000, 40000), (90000, 40000), (90000, 70000), (120000, 70000)],
        dxfattribs={"layer": "TRAY_600x100"}
    )
    # Add parallel line
    msp.add_line((0, 1000), (30000, 1000), dxfattribs={"layer": "TRAY_600x100"})

    # Add TRAY_400x100 routes (Sub branches: approx 85m)
    msp.add_lwpolyline(
        [(50000, 0), (50000, -35000), (80000, -35000), (80000, -55000)],
        dxfattribs={"layer": "TRAY_400x100"}
    )

    # Add TRAY_200x100 routes (Local feeder: approx 55m)
    msp.add_lwpolyline(
        [(90000, 40000), (90000, 15000), (115000, 15000), (115000, -10000)],
        dxfattribs={"layer": "TRAY_200x100"}
    )

    # Add DUCT_150x100 routes (Control Ducts in electrical room: approx 40m)
    msp.add_lwpolyline(
        [(2000, 2000), (22000, 2000), (22000, 22000)],
        dxfattribs={"layer": "DUCT_150x100"}
    )

    # Add DUCT_80x80 routes (Local panel wiring ducts: approx 25m)
    msp.add_lwpolyline(
        [(2000, 5000), (15000, 5000), (15000, 17000)],
        dxfattribs={"layer": "DUCT_80x80"}
    )

    # Insert Fitting Blocks
    # Elbow 90s
    elbow_locs = [(50000, 0), (50000, 40000), (90000, 40000), (90000, 70000), (50000, -35000), (80000, -35000), (90000, 15000), (115000, 15000)]
    for loc in elbow_locs:
        msp.add_blockref("ELBOW_90", loc, dxfattribs={"layer": "FITTINGS"})

    # Elbow 45s
    msp.add_blockref("ELBOW_45", (10000, 0), dxfattribs={"layer": "FITTINGS"})
    msp.add_blockref("ELBOW_45", (35000, 0), dxfattribs={"layer": "FITTINGS"})
    msp.add_blockref("ELBOW_45", (70000, 40000), dxfattribs={"layer": "FITTINGS"})

    # Tees
    msp.add_blockref("TEE", (50000, 0), dxfattribs={"layer": "FITTINGS"})
    msp.add_blockref("TEE", (90000, 40000), dxfattribs={"layer": "FITTINGS"})
    msp.add_blockref("TEE", (22000, 2000), dxfattribs={"layer": "FITTINGS"})

    # Reducers
    msp.add_blockref("REDUCER", (50000, -10000), dxfattribs={"layer": "FITTINGS"})
    msp.add_blockref("REDUCER", (90000, 30000), dxfattribs={"layer": "FITTINGS"})

    # Hangers (15 explicit blocks)
    for x in range(5000, 45000, 5000):
        msp.add_blockref("SUPPORT_HANGER", (x, 0), dxfattribs={"layer": "FITTINGS"})

    doc.saveas(output_path)
    print(f"[OK] Generated Sample DXF: {output_path}")

def generate_sample_wiring_csv(output_path):
    data = [
        {"WireNo": "L1", "SignalType": "220V_L", "From_Device": "CP01 (메인차단기)", "From_Pin": "2", "To_Device": "SMPS01 (파워서플라이)", "To_Pin": "L", "Description": "AC 220V 전원 입력선 L상"},
        {"WireNo": "N1", "SignalType": "220V_N", "From_Device": "CP01 (메인차단기)", "From_Pin": "4", "To_Device": "SMPS01 (파워서플라이)", "To_Pin": "N", "Description": "AC 220V 전원 입력선 N상"},
        {"WireNo": "GND", "SignalType": "GND", "From_Device": "GROUND_BUS", "From_Pin": "1", "To_Device": "SMPS01 (파워서플라이)", "To_Pin": "PE", "Description": "외함 보호 접지 (PE)"},
        {"WireNo": "24V+", "SignalType": "24V+", "From_Device": "SMPS01 (파워서플라이)", "From_Pin": "+V", "To_Device": "FUSE01 (퓨즈블록)", "To_Pin": "IN", "Description": "DC 24V 메인 전원 버스"},
        {"WireNo": "24V-", "SignalType": "24V-", "From_Device": "SMPS01 (파워서플라이)", "From_Pin": "-V", "To_Device": "TB100 (공통단자)", "To_Pin": "COM", "Description": "DC 0V 공통 접지/리턴"},
        {"WireNo": "W101", "SignalType": "DI", "From_Device": "TB101", "From_Pin": "1", "To_Device": "PLC_DI_M01", "To_Pin": "CH0", "Description": "10-FIT-101 유량 정상 신호"},
        {"WireNo": "W102", "SignalType": "DI", "From_Device": "TB101", "From_Pin": "3", "To_Device": "PLC_DI_M01", "To_Pin": "CH1", "Description": "10-PIT-102 압력 하이 알람 접점"},
        {"WireNo": "W103", "SignalType": "DI", "From_Device": "TB101", "From_Pin": "5", "To_Device": "PLC_DI_M01", "To_Pin": "CH2", "Description": "10-LIT-103 레벨 하이 접점"},
        {"WireNo": "W104", "SignalType": "DI", "From_Device": "TB101", "From_Pin": "7", "To_Device": "PLC_DI_M01", "To_Pin": "CH3", "Description": "10-XV-105 밸브 Full Open 리미트"},
        {"WireNo": "W105", "SignalType": "DI", "From_Device": "TB101", "From_Pin": "9", "To_Device": "PLC_DI_M01", "To_Pin": "CH4", "Description": "10-XV-105 밸브 Full Close 리미트"},
        {"WireNo": "W201", "SignalType": "DO", "From_Device": "PLC_DO_M01", "From_Pin": "CH0", "To_Device": "RY01 (릴레이)", "To_Pin": "A1", "Description": "10-XV-105 밸브 구동 솔레노이드 출력"},
        {"WireNo": "W202", "SignalType": "DO", "From_Device": "PLC_DO_M01", "From_Pin": "CH1", "To_Device": "RY02 (릴레이)", "To_Pin": "A1", "Description": "PUMP-101 기동/정지 지령 출력"},
        {"WireNo": "W203", "SignalType": "DO", "From_Device": "PLC_DO_M01", "From_Pin": "CH2", "To_Device": "BZ01 (경보부저)", "To_Pin": "+", "Description": "이상 경보 부저 구동"},
        {"WireNo": "W301+", "SignalType": "AI", "From_Device": "TB201", "From_Pin": "1", "To_Device": "PLC_AI_M01", "To_Pin": "CH0+", "Description": "10-FIT-101 유량 4~20mA (+)"},
        {"WireNo": "W301-", "SignalType": "AI", "From_Device": "TB201", "From_Pin": "2", "To_Device": "PLC_AI_M01", "To_Pin": "CH0-", "Description": "10-FIT-101 유량 4~20mA (-)"},
        {"WireNo": "W302+", "SignalType": "AI", "From_Device": "TB201", "From_Pin": "4", "To_Device": "PLC_AI_M01", "To_Pin": "CH1+", "Description": "10-PIT-102 압력 4~20mA (+)"},
        {"WireNo": "W302-", "SignalType": "AI", "From_Device": "TB201", "From_Pin": "5", "To_Device": "PLC_AI_M01", "To_Pin": "CH1-", "Description": "10-PIT-102 압력 4~20mA (-)"},
        {"WireNo": "W303+", "SignalType": "AI", "From_Device": "TB201", "From_Pin": "7", "To_Device": "PLC_AI_M01", "To_Pin": "CH2+", "Description": "10-TIT-104 온도 4~20mA (+)"},
        {"WireNo": "W303-", "SignalType": "AI", "From_Device": "TB201", "From_Pin": "8", "To_Device": "PLC_AI_M01", "To_Pin": "CH2-", "Description": "10-TIT-104 온도 4~20mA (-)"},
        {"WireNo": "W401+", "SignalType": "AO", "From_Device": "PLC_AO_M01", "From_Pin": "CH0+", "To_Device": "TB202", "To_Pin": "1", "Description": "10-HCV-106 제어밸브 개도 지령 (+)"},
        {"WireNo": "W401-", "SignalType": "AO", "From_Device": "PLC_AO_M01", "From_Pin": "CH0-", "To_Device": "TB202", "To_Pin": "2", "Description": "10-HCV-106 제어밸브 개도 지령 (-)"}
    ]
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Generated Sample Wiring CSV: {output_path}")

def generate_sample_plc_io_excel(output_path):
    data = [
        {"Tag": "10-FIT-101_DI", "SignalType": "DI", "Address": "%I0.0", "Rack": 0, "Slot": 1, "Channel": 0, "Description": "주원료 유량계 정상 가동 신호"},
        {"Tag": "10-PIT-102_DI", "SignalType": "DI", "Address": "%I0.1", "Rack": 0, "Slot": 1, "Channel": 1, "Description": "반응기 압력 트립 알람 접점"},
        {"Tag": "10-LIT-103_DI", "SignalType": "DI", "Address": "%I0.2", "Rack": 0, "Slot": 1, "Channel": 2, "Description": "저장탱크 고액위 경보 신호"},
        {"Tag": "10-XV-105_ZSO",  "SignalType": "DI", "Address": "%I0.3", "Rack": 0, "Slot": 1, "Channel": 3, "Description": "긴급차단밸브 전개(Open) 리미트"},
        {"Tag": "10-XV-105_ZSC",  "SignalType": "DI", "Address": "%I0.4", "Rack": 0, "Slot": 1, "Channel": 4, "Description": "긴급차단밸브 전폐(Close) 리미트"},
        {"Tag": "PUMP-101_RUN",   "SignalType": "DI", "Address": "%I0.5", "Rack": 0, "Slot": 1, "Channel": 5, "Description": "공정 피드 펌프 가동 확인"},
        {"Tag": "PUMP-101_TRIP",  "SignalType": "DI", "Address": "%I0.6", "Rack": 0, "Slot": 1, "Channel": 6, "Description": "공정 피드 펌프 과부하 트립"},
        {"Tag": "SPARE_DI_07",    "SignalType": "DI", "Address": "%I0.7", "Rack": 0, "Slot": 1, "Channel": 7, "Description": "예비 채널 (Spare DI)"},
        
        {"Tag": "10-XV-105_CMD",  "SignalType": "DO", "Address": "%Q0.0", "Rack": 0, "Slot": 2, "Channel": 0, "Description": "긴급차단밸브 Open/Close 지령"},
        {"Tag": "PUMP-101_CMD",   "SignalType": "DO", "Address": "%Q0.1", "Rack": 0, "Slot": 2, "Channel": 1, "Description": "피드 펌프 기동/정지 출력"},
        {"Tag": "ALARM_HORN",     "SignalType": "DO", "Address": "%Q0.2", "Rack": 0, "Slot": 2, "Channel": 2, "Description": "현장 비상 사이렌 출력"},
        {"Tag": "SPARE_DO_03",    "SignalType": "DO", "Address": "%Q0.3", "Rack": 0, "Slot": 2, "Channel": 3, "Description": "예비 채널 (Spare DO)"},

        {"Tag": "10-FIT-101",     "SignalType": "AI", "Address": "%IW100", "Rack": 0, "Slot": 3, "Channel": 0, "Description": "원료 공급 라인 순간 유량 (0~150 m3/h)"},
        {"Tag": "10-PIT-102",     "SignalType": "AI", "Address": "%IW102", "Rack": 0, "Slot": 3, "Channel": 1, "Description": "반응탑 내부 압력 (0~10 barG)"},
        {"Tag": "10-LIT-103",     "SignalType": "AI", "Address": "%IW104", "Rack": 0, "Slot": 3, "Channel": 2, "Description": "반응탑 하부 레벨 (0~100 %)"},
        {"Tag": "10-TIT-104",     "SignalType": "AI", "Address": "%IW106", "Rack": 0, "Slot": 3, "Channel": 3, "Description": "반응 공정 구역 온도 (-20~180 C)"},
        {"Tag": "SPARE_AI_04",    "SignalType": "AI", "Address": "%IW108", "Rack": 0, "Slot": 3, "Channel": 4, "Description": "예비 채널 (Spare AI)"},

        {"Tag": "10-HCV-106",     "SignalType": "AO", "Address": "%QW100", "Rack": 0, "Slot": 4, "Channel": 0, "Description": "반응탑 배출 제어밸브 개도 (4~20mA)"},
        {"Tag": "SPARE_AO_01",    "SignalType": "AO", "Address": "%QW102", "Rack": 0, "Slot": 4, "Channel": 1, "Description": "예비 채널 (Spare AO)"}
    ]
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)
    print(f"[OK] Generated Sample PLC I/O Excel: {output_path}")

def generate_sample_pid_csv(output_path):
    data = [
        {"TagNo": "10-FIT-101", "LoopNo": "1001", "Service": "반응 원료 유입량 측정", "Area": "반응공정 메인 배관동 (Zone 1)", "Signal": "4~20mA HART"},
        {"TagNo": "10-PIT-102", "LoopNo": "1002", "Service": "반응기 상부 돔 압력", "Area": "반응기 상부 Deck (Zone 1)", "Signal": "4~20mA HART"},
        {"TagNo": "10-LIT-103", "LoopNo": "1003", "Service": "원료 회수 탱크 레벨", "Area": "옥외 탱크 팜 (Zone 2)", "Signal": "4~20mA HART"},
        {"TagNo": "10-TIT-104", "LoopNo": "1004", "Service": "반응기 내부 촉매층 온도", "Area": "반응기 중간 노즐 (Zone 1)", "Signal": "RTD Pt100 / HART"},
        {"TagNo": "10-XV-105",  "LoopNo": "1005", "Service": "원료 공급 긴급 차단 (ESD)", "Area": "반응공정 인입 밸브 스테이션 (Zone 1)", "Signal": "24VDC Solenoid & LS"},
        {"TagNo": "10-HCV-106", "LoopNo": "1006", "Service": "공정 배출 유량 제어", "Area": "반응공정 배출 배관 (Zone 1)", "Signal": "4~20mA 스마트 포지셔너"},
        {"TagNo": "10-PIT-201", "LoopNo": "2001", "Service": "열교환기 냉각수 입구 압력", "Area": "유틸리티 설비동 (Zone 2)", "Signal": "4~20mA HART"},
        {"TagNo": "10-TIT-202", "LoopNo": "2002", "Service": "열교환기 냉각수 출구 온도", "Area": "유틸리티 설비동 (Zone 2)", "Signal": "RTD Pt100 / 4~20mA"},
        {"TagNo": "10-FIT-301", "LoopNo": "3001", "Service": "질소 퍼지 공급 라인 유량", "Area": "가스 공급 유닛 (Zone 1)", "Signal": "4~20mA HART"},
        {"TagNo": "10-PSV-101", "LoopNo": "1099", "Service": "반응탑 과압 방출 안전밸브 리미트", "Area": "반응기 최상부 (Zone 1)", "Signal": "Dry Contact (SPDT)"},
        {"TagNo": "10-AIT-101", "LoopNo": "1010", "Service": "반응탑 배출가스 O2 농도 분석", "Area": "분석계 Shelter (Safe Area)", "Signal": "4~20mA / Modbus RS485"},
        {"TagNo": "10-LIT-401", "LoopNo": "4001", "Service": "폐수 처리조 수위 측정", "Area": "수처리 설비 구역 (Non-Ex / Safe Area)", "Signal": "4~20mA 초음파식"}
    ]
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Generated Sample P&ID CSV: {output_path}")

if __name__ == "__main__":
    os.makedirs("samples", exist_ok=True)
    generate_sample_dxf("samples/sample_cable_tray.dxf")
    generate_sample_wiring_csv("samples/sample_plc_wiring.csv")
    generate_sample_plc_io_excel("samples/sample_plc_io.xlsx")
    generate_sample_pid_csv("samples/sample_pid_instruments.csv")
    print("All sample files generated successfully!")
