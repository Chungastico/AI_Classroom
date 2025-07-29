# app.py
from flask import Flask, render_template, request, jsonify
import core_logic
import database

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    student_id = request.form['student_id']
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    message = core_logic.register_student_from_camera(student_id, nombre, apellido)
    return jsonify(message=message)

@app.route('/start_attendance_monitor', methods=['POST'])
def start_attendance_monitor():
    message = core_logic.start_attendance_monitoring()
    return jsonify(message=message)

@app.route('/stop_attendance_monitor', methods=['POST'])
def stop_attendance_monitor():
    message = core_logic.stop_attendance_monitoring()
    return jsonify(message=message)

@app.route('/start_pose_monitor', methods=['POST'])
def start_pose_monitor():
    message = core_logic.start_pose_gesture_monitoring()
    return jsonify(message=message)

@app.route('/stop_pose_monitor', methods=['POST'])
def stop_pose_monitor():
    message = core_logic.stop_pose_monitoring()
    return jsonify(message=message)

@app.route('/status')
def status():
    attendance_active = core_logic.get_attendance_monitor_status()
    pose_active = core_logic.get_pose_monitor_status()
    current_period_name, current_period_msg = core_logic.get_current_attendance_period()
    periodo_info = f"Período Actual: {current_period_name if current_period_name else current_period_msg}"
    return jsonify(
        attendance_active=attendance_active,
        pose_active=pose_active,
        periodo=periodo_info
    )

@app.route('/manage_desks')
def manage_desks():
    students = database.get_all_students_basic_info()
    desk_zones = core_logic.DESK_ZONES # Accede directamente a la constante
    current_assignments = core_logic.get_desk_assignments() # Usa la nueva función segura
    return render_template('manage_desks.html', students=students, desk_zones=desk_zones, current_assignments=current_assignments)

@app.route('/assign_desk', methods=['POST'])
def assign_desk():
    zone_name = request.form['zone_name']
    student_id = request.form['student_id']
    success, message = core_logic.assign_student_to_desk(zone_name, student_id)
    return jsonify(success=success, message=message)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# --- Rutas API para Dashboard ---
@app.route('/api/attendance_summary_today')
def api_attendance_summary_today():
    return jsonify(database.get_attendance_summary_by_period())

@app.route('/api/students_list')
def api_students_list():
    return jsonify(database.get_all_students_basic_info())

@app.route('/api/student_attendance_history/<student_id>')
def api_student_attendance_history(student_id):
    return jsonify(database.get_student_attendance_history(student_id))

if __name__ == '__main__':
    # 'use_reloader=False' es importante para evitar que los hilos se inicien dos veces en modo debug
    app.run(debug=True, use_reloader=False)