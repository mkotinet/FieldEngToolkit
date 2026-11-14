"""
Web Dashboard Application for Field Engineering Automation Toolkit.
Provides interactive UI to upload files, preview takeoff metrics,
and download production-grade Excel reports.
"""

import os
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from core.cad_parser import CadDuctTrayParser
from core.plc_parser import PlcWiringIoParser
from core.pid_parser import PidTakeoffParser
from core.merger import EngineeringDataMerger
from core.excel_builder import EngineeringExcelBuilder
import main

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.getcwd(), 'output')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run-sample/<workflow_id>', methods=['POST'])
def run_sample(workflow_id):
    if workflow_id == 'duct':
        out = main.run_duct_workflow()
        return jsonify({"status": "success", "file": "Duct_Tray_MTO_Report.xlsx", "message": "덕트/트레이 자재물량 산출 완료"})
    elif workflow_id == 'plc':
        out = main.run_plc_workflow()
        return jsonify({"status": "success", "file": "PLC_Wiring_Marshalling_Schedule.xlsx", "message": "결선 스케줄 및 마샬링 핀맵 생성 완료"})
    elif workflow_id == 'pid':
        out = main.run_pid_workflow()
        return jsonify({"status": "success", "file": "PID_Instrument_Index_and_MTO.xlsx", "message": "계기 인덱스 및 방폭 그랜드 MTO 생성 완료"})
    elif workflow_id == 'all':
        main.run_duct_workflow()
        main.run_plc_workflow()
        main.run_pid_workflow()
        return jsonify({"status": "success", "message": "3대 실무 워크플로우 엑셀 생성 전체 완료"})
    return jsonify({"status": "error", "message": "Unknown workflow"})

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Engineering Automation Web Server on http://0.0.0.0:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=False)
