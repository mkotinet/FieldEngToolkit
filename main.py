"""
Main CLI Application for Engineering Automation Toolkit.
Executes workflows combining:
1. cad-to-data + excel-automation (Duct & Tray Takeoff)
2. plc-wire-diagram + plc-io-list (From-To Schedule & Marshalling Pinmap)
3. oce-bim-takeoff + csv-excel-merger (P&ID Instrument Index & Cable Gland MTO)
"""

import os
import sys
import argparse
from core.cad_parser import CadDuctTrayParser
from core.plc_parser import PlcWiringIoParser
from core.pid_parser import PidTakeoffParser
from core.merger import EngineeringDataMerger
from core.excel_builder import EngineeringExcelBuilder

def run_duct_workflow(dxf_path="samples/sample_cable_tray.dxf", output_xlsx="output/Duct_Tray_MTO_Report.xlsx"):
    print(f"\n==================================================")
    print(f"[WORKFLOW 1] cad-to-data + excel-automation")
    print(f"Target: 제어 덕트 / 트레이 루트 도면 ({dxf_path})")
    print(f"==================================================")

    parser = CadDuctTrayParser(scale_ratio=1.0, unit="mm", hanger_interval_m=2.0)
    tray_mto, fittings_mto = parser.parse_dxf(dxf_path)

    builder = EngineeringExcelBuilder(title="케이블 트레이 & 제어 덕트 자재물량 집계표 (MTO)")
    
    # 1. Sheet 1: Tray & Duct Routes
    ws1 = builder.add_sheet("덕트_트레이_연장_중량집계")
    headers1 = [
        "No", "도면 레이어 (Layer)", "구분 (Category)", "규격 (Size WxH)", 
        "단위중량 (kg/m)", "총 연장 (Total Length m)", "총 중량 (Total Weight kg)", 
        "재질 및 마감", "적용 규격"
    ]
    data1 = [
        [row["No"], row["도면 레이어 (Layer)"], row["구분 (Category)"], row["규격 (Size WxH mm)"],
         row["단위중량 (kg/m)"], row["총 연장 (Total Length m)"], row["총 중량 (Total Weight kg)"],
         row["재질 및 마감 (Material/Finish)"], row["적용 규격 (Standard)"]]
        for row in tray_mto
    ]
    alignments1 = ["center", "left", "center", "center", "right", "right", "right", "center", "center"]
    formats1 = {4: "#,##0.00", 5: "#,##0.00", 6: "#,##0.00"}
    builder.build_styled_table(
        ws1, start_row=2, headers=headers1, data=data1, alignments=alignments1,
        number_formats=formats1, add_total=True, sum_cols=[5, 6],
        title="[산출물 1-1] 제어 덕트 / 케이블 트레이 규격별 총 연장(m) 및 단위중량 산출표",
        sub_title="* CAD 도면 내 폴리라인/선형 객체 적산 결과 (mm -> m 변환 및 단중 적용)"
    )

    # 2. Sheet 2: Fittings & Hangers
    ws2 = builder.add_sheet("피팅류_서포트행거_집계")
    headers2 = ["No", "품목명 (Item Description)", "수량 (Quantity)", "단위 (Unit)", "예상 단위중량 (kg/ea)", "예상 총중량 (kg)", "비고 (Remarks)"]
    data2 = [
        [row["No"], row["품목명 (Item Description)"], row["수량 (Quantity)"], row["단위 (Unit)"],
         row["예상 단위중량 (kg/ea)"], row["예상 총중량 (kg)"], row["비고 (Remarks)"]]
        for row in fittings_mto
    ]
    alignments2 = ["center", "left", "right", "center", "right", "right", "left"]
    formats2 = {2: "#,##0", 4: "#,##0.00", 5: "#,##0.00"}
    builder.build_styled_table(
        ws2, start_row=2, headers=headers2, data=data2, alignments=alignments2,
        number_formats=formats2, add_total=True, sum_cols=[2, 5],
        title="[산출물 1-2] 피팅류 (Elbow, Tee, Reducer, Support Hanger) 자재 집계표",
        sub_title="* CAD 블록 참조 및 루트 연장 기반 지지대(행거) 산출 집계"
    )

    os.makedirs(os.path.dirname(output_xlsx), exist_ok=True)
    builder.save(output_xlsx)
    print(f"[SUCCESS] 엑셀 보고서 생성 완료 -> {output_xlsx}")
    return output_xlsx

def run_plc_workflow(wiring_path="samples/sample_plc_wiring.csv", io_path="samples/sample_plc_io.xlsx", output_xlsx="output/PLC_Wiring_Marshalling_Schedule.xlsx"):
    print(f"\n==================================================")
    print(f"[WORKFLOW 2] plc-wire-diagram + plc-io-list")
    print(f"Target: 제어반 결선도 & PLC I/O 할당표")
    print(f"==================================================")

    parser = PlcWiringIoParser()
    wiring_schedule = parser.parse_wiring_data(wiring_path)
    pinmap, channel_map, summary = parser.parse_io_and_build_pinmap(io_path)

    builder = EngineeringExcelBuilder(title="PLC 제어반 결선 스케줄 및 마샬링 TB 핀맵")

    # Sheet 1: From-To Wiring Schedule
    ws1 = builder.add_sheet("From-To_결선스케줄")
    headers1 = [
        "No", "선번 (Wire No)", "신호 구분", "선종 (Spec)", "심선 굵기", "색상",
        "출발 기기 (From)", "출발 단자", "도착 기기 (To)", "도착 단자", "배선 용도 / 설명"
    ]
    data1 = [
        [r["No"], r["선번 (Wire No)"], r["신호 구분 (Signal Type)"], r["선종 (Cable Spec)"],
         r["심선 굵기 (Size)"], r["심선 색상 (Color)"], r["출발 기기 (From Device)"],
         r["출발 단자 (From Pin)"], r["도착 기기 (To Device)"], r["도착 단자 (To Pin)"],
         r["용도 및 설명 (Description)"]]
        for r in wiring_schedule
    ]
    alignments1 = ["center", "center", "center", "center", "center", "center", "left", "center", "left", "center", "left"]
    builder.build_styled_table(
        ws1, start_row=2, headers=headers1, data=data1, alignments=alignments1,
        add_total=False,
        title="[산출물 2-1] 제어반 내부 From-To 결선 스케줄표",
        sub_title="* 전장 배선 기술자 시공용 선번, 심선 굵기, 피복 색상, 단자 연결 일람표"
    )

    # Sheet 2: Marshalling TB Pinmap & I/O Mapping
    ws2 = builder.add_sheet("마샬링TB_핀맵_IO매핑")
    headers2 = [
        "No", "마샬링 TB 그룹", "단자 핀 번호", "계기 태그 (Tag)", "신호 구분",
        "PLC H/W 주소", "소프트웨어 어드레스", "필드 케이블 번호", "기능 설명"
    ]
    data2 = [
        [r["No"], r["마샬링 TB (TB Group)"], r["단자 핀 번호 (Pin No)"], r["계기 태그 (Instrument Tag)"],
         r["신호 구분 (Signal Type)"], r["PLC 하드웨어 주소"], r["PLC 소프트웨어 어드레스"],
         r["필드 케이블 번호"], r["기능 설명 (Service Description)"]]
        for r in pinmap
    ]
    alignments2 = ["center", "center", "center", "center", "center", "center", "center", "center", "left"]
    builder.build_styled_table(
        ws2, start_row=2, headers=headers2, data=data2, alignments=alignments2,
        add_total=False,
        title="[산출물 2-2] 마샬링 단자대(TB) 핀맵 및 PLC I/O 카드 채널 매핑표",
        sub_title="* 필드 계기 신호선 인입 단자대와 PLC I/O 모듈 간 1:1 결선 대응표"
    )

    # Sheet 3: I/O Channel Capacity & Spare Analysis
    ws3 = builder.add_sheet("IO_용량_예비율분석")
    headers3 = ["구분 항목 (Category)", "수량 (Channels)", "단위 (Unit)", "비율 / 점유율", "비고"]
    data3 = [
        ["전체 I/O 채널 용량 (Total Channels)", summary["Total Channels"], "CH", "100.0%", "전체 모듈 슬롯 점유 합계"],
        ["사용중 채널 (Active Channels)", summary["Used Channels"], "CH", f"{100-summary['Spare Percentage (%)']:.1f}%", "실제 계기/기기 결선 채널"],
        ["예비 채널 (Spare Channels)", summary["Spare Channels"], "CH", f"{summary['Spare Percentage (%)']:.1f}%", "권장 Spare 기준: 15%~20% 확보 권장"],
        ["디지털 입력 (DI Channels)", summary["DI Count"], "CH", f"{summary['DI Count']/summary['Total Channels']*100:.1f}%", "접점/리미트/알람 신호"],
        ["디지털 출력 (DO Channels)", summary["DO Count"], "CH", f"{summary['DO Count']/summary['Total Channels']*100:.1f}%", "릴레이/솔레노이드 지령"],
        ["아날로그 입력 (AI Channels)", summary["AI Count"], "CH", f"{summary['AI Count']/summary['Total Channels']*100:.1f}%", "4~20mA 유량/압력/레벨/온도"],
        ["아날로그 출력 (AO Channels)", summary["AO Count"], "CH", f"{summary['AO Count']/summary['Total Channels']*100:.1f}%", "4~20mA 제어밸브 개도 지령"]
    ]
    alignments3 = ["left", "right", "center", "right", "left"]
    formats3 = {1: "#,##0"}
    builder.build_styled_table(
        ws3, start_row=2, headers=headers3, data=data3, alignments=alignments3,
        number_formats=formats3, add_total=False,
        title="[산출물 2-3] PLC I/O 모듈 채널 용량 및 Spare(예비율) 현황표",
        sub_title=f"* 현재 예비 채널 비율: {summary['Spare Percentage (%)']}% (총 {summary['Spare Channels']}개 예비 채널 확보)"
    )

    os.makedirs(os.path.dirname(output_xlsx), exist_ok=True)
    builder.save(output_xlsx)
    print(f"[SUCCESS] 엑셀 보고서 생성 완료 -> {output_xlsx}")
    return output_xlsx

def run_pid_workflow(pid_path="samples/sample_pid_instruments.csv", plc_io_path="samples/sample_plc_io.xlsx", output_xlsx="output/PID_Instrument_Index_and_MTO.xlsx"):
    print(f"\n==================================================")
    print(f"[WORKFLOW 3] oce-bim-takeoff + csv-excel-merger")
    print(f"Target: 계장 P&ID 및 배치도 ({pid_path})")
    print(f"==================================================")

    pid_parser = PidTakeoffParser()
    inst_index, gland_mto, cat_counts = pid_parser.parse_pid_data(pid_path)

    # Perform Cross Verification with PLC I/O
    merger = EngineeringDataMerger()
    merged_df, merge_stats = merger.correlate_pid_and_plc(inst_index, plc_io_path)

    builder = EngineeringExcelBuilder(title="P&ID 계기 인덱스 및 방폭 케이블 그랜드 MTO")

    # Sheet 1: Instrument Index
    ws1 = builder.add_sheet("계기_인덱스_수량표")
    headers1 = [
        "No", "계기 태그번호 (Tag)", "루프 번호", "계기 분류", "형식", "측정/제어 용도",
        "설치 구역", "방폭 등급 (Ex Rating)", "케이블 엔트리", "신호 사양", "그랜드(EA)"
    ]
    data1 = [
        [r["No"], r["계기 태그번호 (Tag No)"], r["루프 번호 (Loop No)"], r["계기 분류 (Category)"],
         r["계기 형식 (Type)"], r["측정/제어 용도 (Service)"], r["설치 구역 (Area / Zone)"],
         r["방폭 등급 (Ex Rating)"], r["엔트리 규격 (Cable Entry)"], r["적용 신호 사양 (Signal)"],
         r["그랜드 수량 (Gland Qty)"]]
        for r in inst_index
    ]
    alignments1 = ["center", "center", "center", "center", "center", "left", "left", "center", "center", "left", "right"]
    formats1 = {10: "#,##0"}
    builder.build_styled_table(
        ws1, start_row=2, headers=headers1, data=data1, alignments=alignments1,
        number_formats=formats1, add_total=True, sum_cols=[10],
        title="[산출물 3-1] P&ID 계기 태그(FIT, PIT, LIT, TIT 등) 인덱스 및 수량표",
        sub_title="* ISA-5.1 규격 분류, 방폭 등급, 케이블 엔트리 규격 자동 집계"
    )

    # Sheet 2: Cable Glands & Ex Accessories MTO
    ws2 = builder.add_sheet("케이블그랜드_방폭자재_MTO")
    headers2 = [
        "No", "품목명 (Item Description)", "나사 규격 (Thread)", "그랜드 형식 (Type)",
        "재질 (Material)", "수량 (Quantity)", "단위 (Unit)", "인증 규격", "비고 (Remarks)"
    ]
    data2 = [
        [r["No"], r["품목명 (Item Description)"], r["나사 규격 (Thread Size)"], r["그랜드 형식 (Gland Type)"],
         r["재질 (Material)"], r["수량 (Quantity)"], r["단위 (Unit)"], r["인증 규격 (Certification)"],
         r["비고 (Remarks)"]]
        for r in gland_mto
    ]
    alignments2 = ["center", "left", "center", "left", "center", "right", "center", "center", "left"]
    formats2 = {5: "#,##0"}
    builder.build_styled_table(
        ws2, start_row=2, headers=headers2, data=data2, alignments=alignments2,
        number_formats=formats2, add_total=True, sum_cols=[5],
        title="[산출물 3-2] 케이블 그랜드 및 방폭 자재 규격 일람표 (MTO)",
        sub_title="* 현장 방폭 구역별 내압(Ex d), 본안(Ex ia) 케이블 그랜드 및 블라인드 플러그 적산"
    )

    # Sheet 3: Cross Verification with PLC I/O (csv-excel-merger)
    ws3 = builder.add_sheet("P&ID_PLC_데이터정합성검증")
    headers3 = ["No", "계기 태그", "P&ID 용도", "PLC H/W 주소", "PLC I/O 태그", "검증 상태 (Verification Status)"]
    data3 = []
    for idx, (_, row) in enumerate(merged_df.iterrows(), start=1):
        tag_disp = row.get("계기 태그번호 (Tag No)") or row.get("Tag") or row.get("JOIN_TAG", "")
        service_disp = row.get("측정/제어 용도 (Service)", "-")
        plc_addr_disp = row.get("Address", "-")
        plc_tag_disp = row.get("Tag", "-")
        status_disp = row.get("검증 상태 (Verification Status)", "검증됨")
        data3.append([idx, tag_disp, service_disp, plc_addr_disp, plc_tag_disp, status_disp])

    alignments3 = ["center", "center", "left", "center", "center", "center"]
    builder.build_styled_table(
        ws3, start_row=2, headers=headers3, data=data3, alignments=alignments3,
        add_total=False,
        title="[산출물 3-3] P&ID 계기 태그 vs PLC I/O 리스트 상호 교차 검증표",
        sub_title=f"* 정상 매칭: {merge_stats.get('matched', 0)}건 | PLC 누락: {merge_stats.get('missing_in_plc', 0)}건 | P&ID 누락: {merge_stats.get('missing_in_pid', 0)}건"
    )

    os.makedirs(os.path.dirname(output_xlsx), exist_ok=True)
    builder.save(output_xlsx)
    print(f"[SUCCESS] 엑셀 보고서 생성 완료 -> {output_xlsx}")
    return output_xlsx

def main():
    parser = argparse.ArgumentParser(description="현장 실무 엔지니어링 자동화 도구")
    parser.add_argument("mode", choices=["all", "duct", "plc", "pid"], default="all", nargs="?",
                        help="실행할 워크플로우 (all, duct, plc, pid)")
    args = parser.parse_args()

    print("\n[엔지니어링 실무 자동화 시스템 시작]")
    if args.mode in ["all", "duct"]:
        run_duct_workflow()
    if args.mode in ["all", "plc"]:
        run_plc_workflow()
    if args.mode in ["all", "pid"]:
        run_pid_workflow()
    print("\n[모든 지정된 실무 워크플로우가 성공적으로 완료되었습니다!]")

if __name__ == "__main__":
    main()
