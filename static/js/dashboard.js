// static/js/dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a elementos del DOM ---
    const attendanceChartCanvas = document.getElementById('attendanceChart').getContext('2d');
    const studentListContainer = document.getElementById('student-list');
    const studentDetailsCard = document.getElementById('student-details-card');
    const studentDetailsContent = document.getElementById('student-details-content');

    let attendanceChart; // Variable para mantener la instancia del gráfico

    /**
     * Función genérica para hacer peticiones a la API
     * @param {string} url - El endpoint de la API
     * @returns {Promise<any>} - La data en formato JSON
     */
    const fetchData = async (url) => {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Error en la petición: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error("No se pudo obtener la data:", error);
            return null;
        }
    };

    /**
     * Carga y renderiza el gráfico de resumen de asistencia
     */
    const loadAttendanceSummary = async () => {
        const data = await fetchData('/api/attendance_summary_today');
        if (!data) return;

        const labels = Object.keys(data);
        const values = Object.values(data);

        if (attendanceChart) {
            attendanceChart.destroy(); // Destruir gráfico anterior para evitar duplicados
        }

        attendanceChart = new Chart(attendanceChartCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Estudiantes Presentes',
                    data: values,
                    backgroundColor: 'rgba(106, 90, 205, 0.6)', // Morado semi-transparente
                    borderColor: 'rgba(106, 90, 205, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#a8a8b3', // Color de texto de los ejes
                            stepSize: 1
                        },
                         grid: {
                            color: '#323238' // Color de las líneas del grid
                        }
                    },
                    x: {
                         ticks: {
                            color: '#a8a8b3'
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    };
    
    /**
     * Carga la lista de estudiantes y añade listeners para ver detalles
     */
    const loadStudentList = async () => {
        const students = await fetchData('/api/students_list');
        if (!students) return;

        studentListContainer.innerHTML = ''; // Limpiar lista
        students.forEach(student => {
            const li = document.createElement('li');
            li.textContent = `${student.nombre} ${student.apellido} (ID: ${student.id})`;
            li.dataset.studentId = student.id;
            li.style.cursor = 'pointer';
            li.addEventListener('click', () => loadStudentDetails(student.id, `${student.nombre} ${student.apellido}`));
            studentListContainer.appendChild(li);
        });
    };
    
    /**
     * Carga y muestra el historial de asistencia de un estudiante específico
     * @param {string} studentId - El ID del estudiante
     * @param {string} studentName - El nombre del estudiante para mostrarlo en el título
     */
    const loadStudentDetails = async (studentId, studentName) => {
        const history = await fetchData(`/api/student_attendance_history/${studentId}`);
        if (!history) return;

        let content = `<h3>Historial de Asistencia de ${studentName}</h3>`;
        if (history.length > 0) {
            content += '<ul>';
            history.forEach(record => {
                const date = new Date(record.timestamp);
                content += `<li>${date.toLocaleString()} - <strong>${record.periodo_clase}</strong></li>`;
            });
            content += '</ul>';
        } else {
            content += '<p>No hay registros de asistencia para este estudiante.</p>';
        }

        studentDetailsContent.innerHTML = content;
        studentDetailsCard.style.display = 'block'; // Mostrar la tarjeta de detalles
    };


    // --- Carga inicial de datos ---
    loadAttendanceSummary();
    loadStudentList();

    // Actualizar datos periódicamente (opcional)
    setInterval(() => {
        loadAttendanceSummary();
    }, 30000); // Cada 30 segundos
});