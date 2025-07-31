# Instalación y Ejecución de Proyecto Python 3.10.0

A continuación, se detallan los pasos para configurar y ejecutar este proyecto utilizando Python 3.10.0.

---

## Instalación

Sigue estos pasos para la instalación inicial del entorno virtual y las dependencias del proyecto:

1.  Abre el **Símbolo del sistema (CMD) como administrador**.
2.  Navega al directorio donde descargaste el archivo del proyecto:
    ```bash
    cd C:\Users\La_ruta_adonde_descargaste_el_archivo
    ```
    (Reemplaza `C:\Users\La_ruta_adonde_descargaste_el_archivo` con la ruta real de tu proyecto).
3.  Crea un nuevo entorno virtual (reemplaza `nombre_del_entorno` por el nombre que prefieras para tu entorno):
    ```bash
    python -m venv nombre_del_entorno
    ```
4.  Actualiza `pip` dentro de tu entorno virtual:
    ```bash
    pip install --upgrade pip
    ```
5.  Activa el entorno virtual:
    ```bash
    .\nombre_del_entorno\Scripts\activate
    ```
6.  Instala las dependencias del proyecto listadas en `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

---

## Ejecución

Una vez que el entorno está configurado, puedes ejecutar el proyecto siguiendo estos pasos:

1.  Abre el **Símbolo del sistema (CMD) normal**.
2.  Navega al directorio donde se encuentra el proyecto:
    ```bash
    cd C:\Users\La_ruta_adonde_descargaste_el_archivo
    ```
3.  Activa el entorno virtual (usa el mismo `nombre_del_entorno` que usaste durante la instalación):
    ```bash
    .\nombre_del_entorno\Scripts\activate
    ```
4.  Ejecuta la aplicación principal:
    ```bash
    python app.py
    ```

---

## Cerrar el Servidor

Para detener el servidor o la aplicación que se está ejecutando en la consola, presiona las teclas:
1.  Desactivar el entorno virtual:
    ```bash
    deactivade
    ```

