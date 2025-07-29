# database.py
import sqlite3
import datetime
import json # Necesario para guardar y cargar los embeddings
import numpy as np # Necesario para convertir el embedding de vuelta a numpy array

DATABASE_NAME = 'asistencia_ia.db'

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Tabla para registrar estudiantes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estudiantes (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            registro_facial_path TEXT UNIQUE,
            facial_embedding TEXT
        )
    ''')

    # Tabla para registrar asistencia
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id TEXT,
            timestamp TEXT NOT NULL,
            periodo_clase TEXT NOT NULL,
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
        )
    ''')

    # Tabla para registrar participación
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id TEXT,
            timestamp TEXT NOT NULL,
            periodo_clase TEXT NOT NULL,
            puntos INTEGER DEFAULT 1,
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Base de datos '{DATABASE_NAME}' inicializada.")

def add_student(student_id, nombre, apellido, registro_facial_path, facial_embedding):
    """Agrega un nuevo estudiante a la base de datos con su ID y embedding facial."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        embedding_str = json.dumps(facial_embedding)
        cursor.execute("INSERT INTO estudiantes (id, nombre, apellido, registro_facial_path, facial_embedding) VALUES (?, ?, ?, ?, ?)",
                       (student_id, nombre, apellido, registro_facial_path, embedding_str))
        conn.commit()
        print(f"Estudiante {nombre} {apellido} (ID: {student_id}) agregado con embedding.")
        return True
    except sqlite3.IntegrityError as e:
        print(f"Error al agregar estudiante: {e}. Posiblemente el ID o el registro facial ya existe.")
        return False
    finally:
        conn.close()

def record_attendance(estudiante_id, periodo_clase):
    """Registra la asistencia de un estudiante para un período específico."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute("INSERT INTO asistencia (estudiante_id, timestamp, periodo_clase) VALUES (?, ?, ?)",
                   (estudiante_id, timestamp, periodo_clase))
    conn.commit()
    conn.close()
    print(f"Asistencia registrada para estudiante ID: {estudiante_id} en el período '{periodo_clase}' a las {timestamp}.")

def get_student_by_id(estudiante_id):
    """Obtiene la información de un estudiante por su ID."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, apellido, registro_facial_path, facial_embedding FROM estudiantes WHERE id = ?", (estudiante_id,))
    student_raw = cursor.fetchone()
    conn.close()
    
    if student_raw:
        est_id, nombre, apellido, path, embedding_str = student_raw
        embeddings_list = []
        if embedding_str:
            try:
                loaded_list = json.loads(embedding_str)
                for emb_array in loaded_list:
                    embeddings_list.append(np.array(emb_array))
            except (json.JSONDecodeError, TypeError):
                embeddings_list = []
        return {'id': est_id, 'nombre': nombre, 'apellido': apellido, 'path': path, 'embeddings': embeddings_list}
    return None

def get_all_students():
    """Obtiene la información de todos los estudiantes registrados, incluyendo sus embeddings."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, apellido, registro_facial_path, facial_embedding FROM estudiantes")
    students_raw = cursor.fetchall()
    conn.close()

    students = []
    for est_id, nombre, apellido, path, embedding_str in students_raw:
        embeddings_list = []
        if embedding_str:
            try:
                loaded_list = json.loads(embedding_str)
                for emb_array in loaded_list:
                    embeddings_list.append(np.array(emb_array))
            except (json.JSONDecodeError, TypeError):
                embeddings_list = []
        students.append({'id': est_id, 'nombre': nombre, 'apellido': apellido, 'path': path, 'embeddings': embeddings_list})
    return students

def has_attended_today_in_period(estudiante_id, periodo_clase):
    """Verifica si un estudiante ya registró asistencia para el día actual en un período de clase específico."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    today_start = datetime.datetime.now().strftime('%Y-%m-%d 00:00:00')
    today_end = datetime.datetime.now().strftime('%Y-%m-%d 23:59:59')

    cursor.execute("""
        SELECT COUNT(*) FROM asistencia
        WHERE estudiante_id = ? AND periodo_clase = ? AND timestamp BETWEEN ? AND ?
    """, (estudiante_id, periodo_clase, today_start, today_end))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def record_participation(estudiante_id, periodo_clase, puntos=1):
    """Registra puntos de participación para un estudiante en un período específico."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute("INSERT INTO participacion (estudiante_id, timestamp, periodo_clase, puntos) VALUES (?, ?, ?, ?)",
                   (estudiante_id, timestamp, periodo_clase, puntos))
    conn.commit()
    conn.close()
    print(f"Participación registrada para estudiante ID: {estudiante_id} en el período '{periodo_clase}'. Puntos: {puntos}.")

def has_participated_recently(estudiante_id, periodo_clase, cooldown_seconds=30):
    """Verifica si un estudiante ya registró participación recientemente para evitar registros masivos."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp FROM participacion
        WHERE estudiante_id = ? AND periodo_clase = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (estudiante_id, periodo_clase))
    
    last_timestamp_str = cursor.fetchone()
    conn.close()

    if last_timestamp_str:
        last_timestamp = datetime.datetime.fromisoformat(last_timestamp_str[0])
        if (datetime.datetime.now() - last_timestamp).total_seconds() < cooldown_seconds:
            return True
    return False

def get_all_students_basic_info():
    """Obtiene la ID, nombre y apellido de todos los estudiantes registrados."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, apellido FROM estudiantes ORDER BY nombre, apellido")
    students = [{'id': row[0], 'nombre': row[1], 'apellido': row[2]} for row in cursor.fetchall()]
    conn.close()
    return students

# --- Funciones para el Dashboard (no se modifican) ---
def get_attendance_summary_by_period(date_str=None):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    target_date = date_str if date_str else datetime.datetime.now().strftime('%Y-%m-%d')
    today_start = f'{target_date} 00:00:00'
    today_end = f'{target_date} 23:59:59'
    cursor.execute("SELECT periodo_clase, COUNT(DISTINCT estudiante_id) FROM asistencia WHERE timestamp BETWEEN ? AND ? GROUP BY periodo_clase", (today_start, today_end))
    summary = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return summary

def get_all_attendance_records_for_date(date_str=None):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    target_date = date_str if date_str else datetime.datetime.now().strftime('%Y-%m-%d')
    today_start = f'{target_date} 00:00:00'
    today_end = f'{target_date} 23:59:59'
    cursor.execute("SELECT a.estudiante_id, e.nombre, e.apellido, a.timestamp, a.periodo_clase FROM asistencia a JOIN estudiantes e ON a.estudiante_id = e.id WHERE a.timestamp BETWEEN ? AND ? ORDER BY a.timestamp DESC", (today_start, today_end))
    records = [{'student_id': r[0], 'nombre': r[1], 'apellido': r[2], 'timestamp': r[3], 'periodo_clase': r[4]} for r in cursor.fetchall()]
    conn.close()
    return records

def get_student_attendance_history(student_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, periodo_clase FROM asistencia WHERE estudiante_id = ? ORDER BY timestamp DESC", (student_id,))
    history = [{'timestamp': row[0], 'periodo_clase': row[1]} for row in cursor.fetchall()]
    conn.close()
    return history

def get_participation_summary_by_period(date_str=None):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    target_date = date_str if date_str else datetime.datetime.now().strftime('%Y-%m-%d')
    today_start = f'{target_date} 00:00:00'
    today_end = f'{target_date} 23:59:59'
    cursor.execute("SELECT periodo_clase, estudiante_id, SUM(puntos) FROM participacion WHERE timestamp BETWEEN ? AND ? GROUP BY periodo_clase, estudiante_id", (today_start, today_end))
    summary = {}
    for row in cursor.fetchall():
        periodo, student_id, puntos = row
        if periodo not in summary: summary[periodo] = {}
        summary[periodo][student_id] = puntos
    conn.close()
    return summary

def get_all_participation_records_for_date(date_str=None):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    target_date = date_str if date_str else datetime.datetime.now().strftime('%Y-%m-%d')
    today_start = f'{target_date} 00:00:00'
    today_end = f'{target_date} 23:59:59'
    cursor.execute("SELECT p.estudiante_id, e.nombre, e.apellido, p.timestamp, p.periodo_clase, p.puntos FROM participacion p JOIN estudiantes e ON p.estudiante_id = e.id WHERE p.timestamp BETWEEN ? AND ? ORDER BY p.timestamp DESC", (today_start, today_end))
    records = [{'student_id': r[0], 'nombre': r[1], 'apellido': r[2], 'timestamp': r[3], 'periodo_clase': r[4], 'puntos': r[5]} for r in cursor.fetchall()]
    conn.close()
    return records

if __name__ == '__main__':
    init_db()