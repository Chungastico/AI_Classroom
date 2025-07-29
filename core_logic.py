# core_logic.py
import cv2
import os
import time
import numpy as np
import face_recognition
from database import (init_db, add_student, record_attendance, get_all_students, 
                      get_student_by_id, has_attended_today_in_period, 
                      record_participation, has_participated_recently)
import threading
import datetime

# --- Intenta importar TensorFlow y Hub ---
try:
    import tensorflow as tf
    import tensorflow_hub as hub
    MOVENET_MODEL = hub.load("https://tfhub.dev/google/movenet/multipose/lightning/1")
    INPUT_SIZE = 256
    print("✅ Modelo MoveNet MultiPose cargado exitosamente.")
except ImportError:
    print("🚨 ADVERTENCIA: TensorFlow no está instalado. El monitoreo de pose y gestos no funcionará.")
    MOVENET_MODEL = None
    INPUT_SIZE = 0

# --- Configuración Inicial y Variables Globales ---
REGISTRO_FACIAL_DIR = "rostros_registrados"
os.makedirs(REGISTRO_FACIAL_DIR, exist_ok=True)
init_db()

# --- Variables de Control y Hilos ---
attendance_monitoring_active = False
attendance_monitoring_thread = None

pose_monitoring_active = False
pose_monitoring_thread = None

desk_assignments_lock = threading.Lock()
desk_assignments = {}

# --- Definiciones de Horarios y Zonas ---
PERIODOS_REGISTRO = [
    ("Clase 1", "06:00", "07:50"), ("Clase 2", "08:00", "09:40"), ("Clase 3", "09:50", "11:30"),
    ("Clase 4", "16:40", "18:20"), ("Clase 5", "18:30", "19:50")
]
DESK_ZONES = {
    "Pupitre 1": [50, 100, 250, 300], "Pupitre 2": [350, 100, 550, 300],
    "Pupitre 3": [50, 350, 250, 450], "Pupitre 4": [350, 350, 550, 450]
}
with desk_assignments_lock:
    desk_assignments = {zone_name: None for zone_name in DESK_ZONES.keys()}

# --- Mapeo y Colores para Dibujar Esqueletos ---
KEYPOINT_DICT = { 'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4,
    'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8, 'left_wrist': 9,
    'right_wrist': 10, 'left_hip': 11, 'right_hip': 12, 'left_knee': 13, 'right_knee': 14,
    'left_ankle': 15, 'right_ankle': 16 }

EDGES = [ (0, 1), (0, 2), (1, 3), (2, 4), (0, 5), (0, 6), (5, 7), (7, 9), (6, 8),
    (8, 10), (5, 6), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16) ]

# --- Funciones de Lógica Principal (Sin cambios) ---
def get_current_attendance_period():
    now = datetime.datetime.now()
    if not (0 <= now.weekday() <= 3): return None, "Hoy no hay clases."
    for name, start_str, end_str in PERIODOS_REGISTRO:
        start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.datetime.strptime(end_str, "%H:%M").time()
        if start_time <= now.time() <= end_time:
            return name, None
    return None, "No hay período de clase activo."

def register_student_from_camera(student_id, nombre, apellido):
    if get_student_by_id(student_id):
        return f"Error: El ID '{student_id}' ya está registrado."
    cap = cv2.VideoCapture(0)
    if not cap.isOpened(): return "Error: Cámara no disponible."
    captured_embeddings = []
    required_embeddings = 5
    start_time = time.time()
    while len(captured_embeddings) < required_embeddings and (time.time() - start_time) < 20:
        ret, frame = cap.read()
        if not ret: continue
        frame_display = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame_display, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        text = f"Mire a la camara. {len(captured_embeddings)}/{required_embeddings}"
        cv2.putText(frame_display, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        if face_locations:
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            if face_encodings:
                captured_embeddings.append(face_encodings[0].tolist())
                time.sleep(0.5)
        cv2.imshow('Registro Facial', frame_display)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()
    if len(captured_embeddings) >= required_embeddings:
        filename = f"{student_id}_{nombre}.jpg"
        filepath = os.path.join(REGISTRO_FACIAL_DIR, filename)
        add_student(student_id, nombre, apellido, filepath, captured_embeddings)
        return f"Estudiante '{nombre}' registrado exitosamente."
    return "Registro fallido. No se capturaron suficientes rostros."

# --- Monitoreo de ASISTENCIA (VERSIÓN FINAL CON VISUALIZACIÓN) ---
def _run_attendance_monitoring_loop():
    global attendance_monitoring_active
    
    students_data = get_all_students()
    known_face_encodings = [emb for s in students_data for emb in s['embeddings']]
    # Creamos una lista paralela con nombres para la visualización
    known_face_metadata = [{'id': s['id'], 'nombre': s['nombre']} for s in students_data for _ in s['embeddings']]

    if not known_face_encodings:
        print("🚨 No hay rostros registrados. Registre estudiantes primero.")
        attendance_monitoring_active = False
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("🚨 Error: No se pudo acceder a la cámara para asistencia.")
        attendance_monitoring_active = False
        return

    print("🚀 Monitoreo de ASISTENCIA (Visual y Optimizado) INICIADO")
    
    last_process_time = 0
    PROCESS_INTERVAL = 1.0  # Procesar rostros 1 vez por segundo
    
    # Variables para mantener los resultados entre inferencias y tener una visualización fluida
    face_locations = []
    face_names = []

    try:
        while attendance_monitoring_active:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.5)
                continue

            frame_display = cv2.flip(frame, 1)
            
            if time.time() - last_process_time > PROCESS_INTERVAL:
                last_process_time = time.time()
                
                small_frame = cv2.resize(frame_display, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                # Detecta rostros y calcula sus encodings en el frame pequeño
                current_face_locations = face_recognition.face_locations(rgb_small_frame)
                current_face_encodings = face_recognition.face_encodings(rgb_small_frame, current_face_locations)
                
                face_locations = current_face_locations
                face_names = []
                for face_encoding in current_face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
                    name = "Desconocido"
                    
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        metadata = known_face_metadata[best_match_index]
                        student_id = metadata['id']
                        name = metadata['nombre']
                        
                        periodo, _ = get_current_attendance_period()
                        if periodo and not has_attended_today_in_period(student_id, periodo):
                            record_attendance(student_id, periodo)
                            print(f"✅ Asistencia registrada para {name} (ID: {student_id}) en {periodo}")
                    
                    face_names.append(name)
            
            # --- DIBUJA LOS RESULTADOS EN CADA FRAME (para una visualización fluida) ---
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                # Escalar las coordenadas de vuelta al tamaño original del frame
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                # Asignar color basado en si fue reconocido o no
                box_color = (0, 0, 255) # Rojo para Desconocido
                if name != "Desconocido":
                    box_color = (0, 255, 0) # Verde para Reconocido
                
                # Dibujar la caja y el nombre
                cv2.rectangle(frame_display, (left, top), (right, bottom), box_color, 2)
                cv2.rectangle(frame_display, (left, bottom - 35), (right, bottom), box_color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame_display, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            cv2.imshow('Monitoreo de Asistencia (Visual)', frame_display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        attendance_monitoring_active = False
        cap.release()
        cv2.destroyAllWindows()
        print("Monitoreo de ASISTENCIA detenido y recursos liberados.")


# --- Lógica de Monitoreo de Clase (Pose) OPTIMIZADA (Sin cambios) ---
def _run_movenet_inference(image):
    input_image = tf.expand_dims(image, axis=0)
    input_image = tf.cast(input_image, dtype=tf.int32)
    return MOVENET_MODEL.signatures['serving_default'](input_image)['output_0'].numpy()

def _draw_skeletons(frame, keypoints_with_scores, confidence_threshold=0.35):
    y, x, _ = frame.shape
    shaped = np.squeeze(keypoints_with_scores)
    for person in shaped:
        if person[55] < confidence_threshold: continue
        keypoints = person[:51].reshape((17, 3))
        for edge in EDGES:
            p1, p2 = edge
            y1, x1, c1 = keypoints[p1]
            y2, x2, c2 = keypoints[p2]
            if c1 > confidence_threshold and c2 > confidence_threshold:
                cv2.line(frame, (int(x1 * x), int(y1 * y)), (int(x2 * x), int(y2 * y)), (255, 255, 0), 2)
        for kp in keypoints:
            ky, kx, kp_conf = kp
            if kp_conf > confidence_threshold:
                cv2.circle(frame, (int(kx * x), int(ky * y)), 4, (0, 0, 255), -1)

def _is_hand_raised_movenet(keypoints, confidence_threshold=0.3):
    l_shoulder, l_wrist = keypoints[KEYPOINT_DICT['left_shoulder']], keypoints[KEYPOINT_DICT['left_wrist']]
    r_shoulder, r_wrist = keypoints[KEYPOINT_DICT['right_shoulder']], keypoints[KEYPOINT_DICT['right_wrist']]
    if l_wrist[2] > confidence_threshold and l_shoulder[2] > confidence_threshold and l_wrist[0] < l_shoulder[0]: return True
    if r_wrist[2] > confidence_threshold and r_shoulder[2] > confidence_threshold and r_wrist[0] < r_shoulder[0]: return True
    return False

def _run_pose_gesture_monitoring_loop():
    global pose_monitoring_active
    if not MOVENET_MODEL:
        print("🚨 Monitoreo de pose detenido: Modelo no disponible.")
        pose_monitoring_active = False
        return
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("🚨 Error: No se pudo acceder a la cámara.")
        pose_monitoring_active = False
        return
    print("🚀 Monitoreo de CLASE (MoveNet Optimizado) INICIADO")
    student_info_map = {s['id']: s for s in get_all_students()}
    INFERENCE_INTERVAL = 0.2
    last_inference_time = 0
    keypoints_with_scores = np.zeros((1, 6, 56))
    try:
        while pose_monitoring_active:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.5)
                continue
            frame = cv2.flip(frame, 1)
            frame_display = frame.copy()
            h, w, _ = frame_display.shape
            current_time = time.time()
            if (current_time - last_inference_time) > INFERENCE_INTERVAL:
                last_inference_time = current_time
                input_frame = cv2.resize(frame, (INPUT_SIZE, INPUT_SIZE))
                keypoints_with_scores = _run_movenet_inference(input_frame)
                for person in np.squeeze(keypoints_with_scores):
                    if person[55] < 0.35: continue
                    keypoints = person[:51].reshape((17, 3))
                    l_hip, r_hip = keypoints[KEYPOINT_DICT['left_hip']], keypoints[KEYPOINT_DICT['right_hip']]
                    if l_hip[2] < 0.3 or r_hip[2] < 0.3: continue
                    hip_x, hip_y = int(((l_hip[1] + r_hip[1]) / 2) * w), int(((l_hip[0] + r_hip[0]) / 2) * h)
                    current_zone = next((z for z, c in DESK_ZONES.items() if c[0] < hip_x < c[2] and c[1] < hip_y < c[3]), None)
                    if _is_hand_raised_movenet(keypoints):
                        cv2.putText(frame_display, "MANO ARRIBA", (hip_x, hip_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        with desk_assignments_lock: assigned_student_id = desk_assignments.get(current_zone)
                        if assigned_student_id:
                            periodo, _ = get_current_attendance_period()
                            if periodo and not has_participated_recently(assigned_student_id, periodo, 5):
                                record_participation(assigned_student_id, periodo)
                                print(f"✅ Participación registrada para el estudiante en {current_zone}.")
            _draw_skeletons(frame_display, keypoints_with_scores)
            with desk_assignments_lock: current_assignments = desk_assignments.copy()
            for zone, coords in DESK_ZONES.items():
                cv2.rectangle(frame_display, (coords[0], coords[1]), (coords[2], coords[3]), (255, 0, 0), 2)
                student_id = current_assignments.get(zone)
                name = student_info_map.get(student_id, {}).get('nombre', 'Vacío')
                cv2.putText(frame_display, f"{zone}: {name}", (coords[0], coords[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            cv2.imshow('Monitoreo de CLASE (MoveNet Optimizado)', frame_display)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
    finally:
        pose_monitoring_active = False
        cap.release()
        cv2.destroyAllWindows()
        print("Monitoreo de CLASE detenido y recursos liberados.")

# --- Funciones de Control (Wrappers) (Sin cambios) ---
def start_attendance_monitoring():
    global attendance_monitoring_active, attendance_monitoring_thread
    if pose_monitoring_active: return "Detén el monitoreo de CLASE primero."
    if attendance_monitoring_active: return "Monitoreo de ASISTENCIA ya activo."
    attendance_monitoring_active = True
    attendance_monitoring_thread = threading.Thread(target=_run_attendance_monitoring_loop, daemon=True)
    attendance_monitoring_thread.start()
    return "Monitoreo de ASISTENCIA optimizado iniciado."

def stop_attendance_monitoring():
    global attendance_monitoring_active
    if not attendance_monitoring_active: return "Monitoreo de ASISTENCIA no estaba activo."
    attendance_monitoring_active = False
    return "Señal de detención enviada al monitoreo de ASISTENCIA."

def start_pose_gesture_monitoring():
    global pose_monitoring_active, pose_monitoring_thread
    if attendance_monitoring_active: return "Detén el monitoreo de ASISTENCIA primero."
    if pose_monitoring_active: return "Monitoreo de CLASE ya activo."
    pose_monitoring_active = True
    pose_monitoring_thread = threading.Thread(target=_run_pose_gesture_monitoring_loop, daemon=True)
    pose_monitoring_thread.start()
    return "Monitoreo de CLASE optimizado iniciado."

def stop_pose_monitoring():
    global pose_monitoring_active
    if not pose_monitoring_active: return "El monitoreo de CLASE no estaba activo."
    pose_monitoring_active = False
    return "Señal de detención enviada al monitoreo de CLASE."

def get_attendance_monitor_status(): return attendance_monitoring_active
def get_pose_monitor_status(): return pose_monitoring_active

def get_desk_assignments():
    with desk_assignments_lock:
        return desk_assignments.copy()

def assign_student_to_desk(zone_name, student_id):
    if zone_name not in DESK_ZONES: return False, "Zona no válida."
    with desk_assignments_lock:
        for desk, assigned_id in desk_assignments.items():
            if assigned_id == student_id: desk_assignments[desk] = None
        desk_assignments[zone_name] = student_id if student_id != 'None' else None
    student_info = get_student_by_id(student_id) if student_id != 'None' else None
    name = student_info['nombre'] if student_info else "nadie"
    return True, f"Estudiante {name} asignado a {zone_name}."