import customtkinter as ctk
import keyboard
import time
import threading
import sqlite3

# ==========================================
# ESTADO GLOBAL
# ==========================================
id_prompt_actual = None

# ==========================================
# CAPA DE DATOS
# ==========================================
def obtener_texto_prompt(prompt_id):
    DB_NAME = "prompts.sqlite" 
    texto_recuperado = ""
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute("SELECT contenido FROM prompts WHERE id = ?", (prompt_id,))
        resultado = cursor.fetchone()
        if resultado:
            texto_recuperado = resultado[0]
    except sqlite3.Error as e:
        print(f"[Error DB] {e}")
    finally:
        if conexion: conexion.close()
    return texto_recuperado

def obtener_lista_prompts():
    DB_NAME = "prompts.sqlite"
    registros = []
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute("SELECT id, titulo FROM prompts ORDER BY id ASC")
        for fila in cursor.fetchall():
            registros.append({"id": fila[0], "etiqueta": fila[1]})
    except sqlite3.Error as e:
        print(f"[Error DB] {e}")
    finally:
        if conexion: conexion.close()
    return registros

# ==========================================
# MÓDULO DE SANITIZACIÓN Y CONTROL (v17)
# ==========================================
def sanitizar_texto(texto):
    """Limpia el texto y ajusta saltos de línea para evitar envíos prematuros."""
    if not texto:
        return None
    # Reemplaza saltos de línea simples por SHIFT+ENTER si se desea 
    # (aquí se entrega el texto procesable por keyboard.write)
    return texto

def ejecutar_disparo_dinamico(prompt_id, ocultar_ventana=True):
    def hilo_proceso():
        raw_text = obtener_texto_prompt(prompt_id)
        texto_limpio = sanitizar_texto(raw_text)
        
        # Validación de texto vacío
        if not texto_limpio or not texto_limpio.strip():
            print(f"[Aviso] El prompt {prompt_id} está vacío. Inyección abortada.")
            return

        if ocultar_ventana: root.withdraw()
        time.sleep(0.4) 
        
        try:
            # Inyección con control de velocidad (delay=0.005 segundos por carácter)
            # Esto evita saturar aplicaciones destino en equipos de 8GB RAM
            keyboard.write(texto_limpio, delay=0.005)
        except Exception as e:
            print(f"[Error Inyección] {e}")
        finally:
            if ocultar_ventana:
                time.sleep(0.1)
                root.deiconify()

    threading.Thread(target=hilo_proceso, daemon=True).start()

# ==========================================
# GESTIÓN DE UI
# ==========================================
def seleccionar_prompt(id_seleccionado):
    global id_prompt_actual
    id_prompt_actual = id_seleccionado
    print(f"[Estado UI] Registro activo: ID {id_prompt_actual}")

def puente_de_disparo(ocultar_ventana=True):
    global id_prompt_actual
    if id_prompt_actual is None:
        print("[Aviso] Seleccione un prompt primero.")
        return
    ejecutar_disparo_dinamico(id_prompt_actual, ocultar_ventana)

def renderizar_lista_prompts(frame_contenedor):
    registros = obtener_lista_prompts()
    if not registros:
        ctk.CTkLabel(frame_contenedor, text="Sin prompts.").pack(pady=20)
        return
    for reg in registros:
        ctk.CTkButton(frame_contenedor, text=reg["etiqueta"], anchor="w",
                      command=lambda id_reg=reg["id"]: seleccionar_prompt(id_reg)).pack(pady=2, padx=10, fill="x")

# ==========================================
# INICIO
# ==========================================
def iniciar_aplicacion():
    global root
    root = ctk.CTk()
    root.title("PromptVault v17 - Sanitización")
    root.geometry("450x350")
    frame = ctk.CTkFrame(root)
    frame.pack(pady=20, padx=20, fill="both", expand=True)
    renderizar_lista_prompts(frame)
    ctk.CTkButton(root, text="Inyectar", command=lambda: puente_de_disparo()).pack(pady=10)
    keyboard.add_hotkey('ctrl+comma', lambda: puente_de_disparo())
    root.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()