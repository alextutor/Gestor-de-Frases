import customtkinter as ctk
import keyboard
import time
import threading
import sqlite3
import ctypes

# ==========================================
# ESTADO GLOBAL DE CONFIGURACIÓN
# ==========================================
id_prompt_actual = None

# Modos disponibles: "teclado" (Recomendado) o "automatico" (Experimental)
CONFIG_MODO_DETECCION = "teclado" 

# Descripciones informativas para guiar al usuario
DESCRIPCIONES = {
    "teclado": (
        "MÉTODO RECOMENDADO (Bajo Consumo - 100% Preciso)\n\n"
        "Usa atajos del teclado para controlar el envío:\n"
        "• Ctrl + , -> Inyección estándar (Modo Documento/Word/Código).\n"
        "• Ctrl + Shift + , -> Inyección segura para Chat (Aplica Shift+Enter).\n\n"
        "Ventajas: Consume 0% CPU, no genera demoras y nunca falla."
    ),
    "automatico": (
        "MÉTODO AUTOMÁTICO (Consumo Medio - Riesgo de contexto)\n\n"
        "El sistema analiza activamente la ventana de Windows en primer plano.\n"
        "Si detecta aplicaciones de mensajería (WhatsApp, Slack, Telegram, Teams),\n"
        "conmuta de forma inteligente a Modo Chat.\n\n"
        "Nota: Consume un poco más de CPU/RAM y puede fallar en entornos web."
    )
}

# ==========================================
# CAPA DE DATOS (SQLite3)
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
# MOTOR DE DETECCIÓN NATIVA (API WINDOWS)
# ==========================================
def obtener_titulo_ventana_activa():
    """Obtiene el título de la ventana activa de forma ligera usando ctypes."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value.lower()
    except Exception:
        return ""

# ==========================================
# MOTOR DE SANITIZACIÓN E INYECCIÓN AVANZADA
# ==========================================
def ejecutar_inyeccion_inteligente(texto, forzar_modo_chat=False):
    """Escribe el texto controlando el tipo de salto de línea según el entorno."""
    palabras_clave_chat = ["whatsapp", "slack", "telegram", "teams", "discord"]
    es_entorno_chat = forzar_modo_chat

    # Si está activado el modo automático, analizamos la ventana actual antes de escribir
    if CONFIG_MODO_DETECCION == "automatico" and not es_entorno_chat:
        titulo_ventana = obtener_titulo_ventana_activa()
        if any(app in titulo_ventana for app in palabras_clave_chat):
            es_entorno_chat = True
            print("[Motor Auto] Entorno de CHAT detectado en ventana activa.")

    if es_entorno_chat:
        print("[Motor] Ejecutando inyección optimizada para CHATS.")
        # Segmentamos por saltos de línea para inyectar Shift+Enter de forma controlada
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            if linea:
                keyboard.write(linea, delay=0.005)
            if i < len(lineas) - 1:
                keyboard.press_and_release('shift+enter')
                time.sleep(0.01) # Pequeña pausa para asegurar la estabilidad del buffer
    else:
        print("[Motor] Ejecutando inyección ESTÁNDAR (Documento).")
        keyboard.write(texto, delay=0.005)

def ejecutar_disparo_dinamico(prompt_id, ocultar_ventana=True, forzar_modo_chat=False):
    def hilo_proceso():
        texto_raw = obtener_texto_prompt(prompt_id)
        
        if not texto_raw or not texto_raw.strip():
            print(f"[Aviso] El prompt ID {prompt_id} está vacío. Operación cancelada.")
            return

        if ocultar_ventana: 
            root.withdraw()
        
        time.sleep(0.4) # Retraso crítico para asegurar la transferencia segura de foco
        
        try:
            ejecutar_inyeccion_inteligente(texto_raw, forzar_modo_chat)
        except Exception as e:
            print(f"[Error Inyección] {e}")
        finally:
            if ocultar_ventana:
                time.sleep(0.1)
                root.deiconify()

    threading.Thread(target=hilo_proceso, daemon=True).start()

# ==========================================
# GESTIÓN DE UI Y CONFIGURACIÓN
# ==========================================
def seleccionar_prompt(id_seleccionado):
    global id_prompt_actual
    id_prompt_actual = id_seleccionado
    print(f"[Estado UI] Prompt activo: ID {id_prompt_actual}")

def puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=False):
    global id_prompt_actual
    if id_prompt_actual is None:
        print("[Aviso] Selecciona un prompt en la lista primero.")
        return
    ejecutar_disparo_dinamico(id_prompt_actual, ocultar_ventana, forzar_modo_chat)

def cambiar_modo_deteccion(nuevo_modo, txt_descripcion):
    global CONFIG_MODO_DETECCION
    CONFIG_MODO_DETECCION = nuevo_modo
    txt_descripcion.configure(state="normal")
    txt_descripcion.delete("1.0", ctk.END)
    txt_descripcion.insert("1.0", DESCRIPCIONES[nuevo_modo])
    txt_descripcion.configure(state="disabled")
    print(f"[Configuración] Modo cambiado a: {CONFIG_MODO_DETECCION.upper()}")

def renderizar_lista_prompts(frame_contenedor):
    registros = obtener_lista_prompts()
    if not registros:
        ctk.CTkLabel(frame_contenedor, text="Sin registros en prompts.sqlite", text_color="gray").pack(pady=20)
        return
    for reg in registros:
        ctk.CTkButton(
            frame_contenedor, 
            text=reg["etiqueta"], 
            anchor="w",
            command=lambda id_reg=reg["id"]: seleccionar_prompt(id_reg)
        ).pack(pady=2, padx=10, fill="x")

# ==========================================
# ENSAMBLAJE DE LA INTERFAZ DE USUARIO
# ==========================================
def iniciar_aplicacion():
    global root
    root = ctk.CTk()
    root.title("PromptVault v18 - Configuración de Inyección")
    root.geometry("700x420") # Ampliado para dar espacio al panel de configuración
    
    # Grid Principal (2 Columnas: Izquierda = Lista, Derecha = Configuración)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)
    
    # --- COLUMNA IZQUIERDA: PANEL DE PROMPTS ---
    frame_izq = ctk.CTkFrame(root)
    frame_izq.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
    
    lbl_lista = ctk.CTkLabel(frame_izq, text="Tus Prompts Registrados", font=("Arial", 14, "bold"))
    lbl_lista.pack(pady=10)
    
    frame_lista = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_lista.pack(fill="both", expand=True)
    renderizar_lista_prompts(frame_lista)
    
    btn_inyectar = ctk.CTkButton(frame_izq, text="Inyectar (Manual)", command=lambda: puente_de_disparo())
    btn_inyectar.pack(pady=15)

    # --- COLUMNA DERECHA: PANEL DE CONFIGURACIÓN ---
    frame_der = ctk.CTkFrame(root)
    frame_der.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
    
    lbl_config = ctk.CTkLabel(frame_der, text="Modo de Control de Chats", font=("Arial", 14, "bold"))
    lbl_config.pack(pady=10)
    
    var_modo = ctk.StringVar(value="teclado")
    
    # Cuadro de texto descriptivo
    txt_desc = ctk.CTkTextbox(frame_der, height=150, width=280, wrap="word")
    txt_desc.pack(pady=10, padx=10)
    txt_desc.insert("1.0", DESCRIPCIONES["teclado"])
    txt_desc.configure(state="disabled")
    
    rb_teclado = ctk.CTkRadioButton(
        frame_der, text="Tecla Modificadora (Recomendado)", 
        variable=var_modo, value="teclado",
        command=lambda: cambiar_modo_deteccion("teclado", txt_desc)
    )
    rb_teclado.pack(anchor="w", padx=20, pady=5)
    
    rb_auto = ctk.CTkRadioButton(
        frame_der, text="Detección de Ventana Activa", 
        variable=var_modo, value="automatico",
        command=lambda: cambiar_modo_deteccion("automatico", txt_desc)
    )
    rb_auto.pack(anchor="w", padx=20, pady=5)

    # --- REGISTRO DE ATAJOS GLOBALES DE HARDWARE ---
    # Atajo 1: Estándar / Documento
    keyboard.add_hotkey('ctrl+comma', lambda: puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=False))
    # Atajo 2: Modificador manual para forzar Modo Chat (Eficiente)
    keyboard.add_hotkey('ctrl+shift+comma', lambda: puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=True))
    
    print("[Sistema] PromptVault v18 iniciado.")
    print("  -> Escuchando 'Ctrl + ,' para Modo Estándar.")
    print("  -> Escuchando 'Ctrl + Shift + ,' para Modo Chat (Tecla modificadora).")
    
    root.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()