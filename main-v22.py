import customtkinter as ctk
import keyboard
import time
import threading
import sqlite3
import ctypes

# ==========================================
# ESTADO GLOBAL DE LA APLICACIÓN
# ==========================================
id_prompt_actual = None
CONFIG_MODO_DETECCION = "teclado"
frame_lista_global = None  
PROMPTS_CACHE = []         

DESCRIPCIONES = {
    "teclado": (
        "MÉTODO RECOMENDADO (Bajo Consumo - 100% Preciso)\n\n"
        "Usa atajos del teclado para controlar el envío:\n"
        "• Ctrl + , -> Inyección estándar (Modo Documento).\n"
        "• Ctrl + Shift + , -> Inyección segura para Chat (Shift+Enter).\n\n"
        "Ventajas: Consume 0% CPU, es instantáneo y libre de errores."
    ),
    "automatico": (
        "MÉTODO AUTOMÁTICO (Consumo Medio)\n\n"
        "El sistema analiza la ventana de Windows en primer plano.\n"
        "Si detecta aplicaciones de mensajería (WhatsApp, Slack, Telegram),\n"
        "conmuta de forma inteligente a Modo Chat.\n\n"
        "Nota: Consume un poco más de recursos y puede fallar en entornos web."
    )
}

# ==========================================
# CAPA DE DATOS (SQLite3 + CACHÉ LOCAL)
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

def actualizar_cache_prompts():
    global PROMPTS_CACHE
    DB_NAME = "prompts.sqlite"
    conexion = None
    PROMPTS_CACHE = []
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute("SELECT id, titulo FROM prompts ORDER BY id ASC")
        for fila in cursor.fetchall():
            PROMPTS_CACHE.append({"id": fila[0], "etiqueta": fila[1]})
    except sqlite3.Error as e:
        print(f"[Error al actualizar caché] {e}")
    finally:
        if conexion: conexion.close()

def guardar_nuevo_prompt(titulo, contenido):
    DB_NAME = "prompts.sqlite"
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO prompts (titulo, contenido) VALUES (?, ?)", (titulo, contenido))
        conexion.commit()
    except sqlite3.Error as e:
        print(f"[Error DB] {e}")
    finally:
        if conexion: conexion.close()

def actualizar_prompt(prompt_id, titulo, contenido):
    DB_NAME = "prompts.sqlite"
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute("UPDATE prompts SET titulo = ?, contenido = ? WHERE id = ?", (titulo, contenido, prompt_id))
        conexion.commit()
    except sqlite3.Error as e:
        print(f"[Error DB] {e}")
    finally:
        if conexion: conexion.close()

# ==========================================
# MOTOR NATIVO DE INYECCIÓN
# ==========================================
def obtener_titulo_ventana_activa():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value.lower()
    except Exception:
        return ""

def ejecutar_inyeccion_inteligente(texto, forzar_modo_chat=False):
    palabras_clave_chat = ["whatsapp", "slack", "telegram", "teams", "discord"]
    es_entorno_chat = forzar_modo_chat

    if CONFIG_MODO_DETECCION == "automatico" and not es_entorno_chat:
        titulo_ventana = obtener_titulo_ventana_activa()
        if any(app in titulo_ventana for app in palabras_clave_chat):
            es_entorno_chat = True

    if es_entorno_chat:
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            if linea:
                keyboard.write(linea, delay=0.005)
            if i < len(lineas) - 1:
                keyboard.press_and_release('shift+enter')
                time.sleep(0.01)
    else:
        keyboard.write(texto, delay=0.005)

def ejecutar_disparo_dinamico(prompt_id, ocultar_ventana=True, forzar_modo_chat=False):
    def hilo_proceso():
        texto_raw = obtener_texto_prompt(prompt_id)
        if not texto_raw or not texto_raw.strip():
            return
        if ocultar_ventana: root.withdraw()
        time.sleep(0.4)
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
# FORMULARIO MODAL (CREAR / EDITAR)
# ==========================================
class VentanaFormulario(ctk.CTkToplevel):
    def __init__(self, master, prompt_id=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.prompt_id = prompt_id
        self.title("Nuevo Prompt" if not prompt_id else "Editar Prompt")
        self.geometry("400x450")
        self.transient(master)
        self.grab_set()
        
        ctk.CTkLabel(self, text="Título del Prompt:", font=("Arial", 12, "bold")).pack(pady=(15, 2), padx=20, anchor="w")
        self.txt_titulo = ctk.CTkEntry(self, width=360)
        self.txt_titulo.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self, text="Contenido:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        self.txt_contenido = ctk.CTkTextbox(self, width=360, height=220)
        self.txt_contenido.pack(pady=5, padx=20, fill="both", expand=True)
        
        ctk.CTkButton(self, text="Guardar Cambios", command=self.procesar_datos).pack(pady=20)
        
        if self.prompt_id:
            self.cargar_datos_existentes()

    def cargar_datos_existentes(self):
        titulo_actual = next((r["etiqueta"] for r in PROMPTS_CACHE if r["id"] == self.prompt_id), "")
        contenido_actual = obtener_texto_prompt(self.prompt_id)
        self.txt_titulo.insert(0, titulo_actual)
        self.txt_contenido.insert("1.0", contenido_actual)

    def procesar_datos(self):
        titulo = self.txt_titulo.get().strip()
        contenido = self.txt_contenido.get("1.0", ctk.END).strip()
        
        if not titulo or not contenido:
            return
            
        if self.prompt_id:
            actualizar_prompt(self.prompt_id, titulo, contenido)
        else:
            guardar_nuevo_prompt(titulo, contenido)
            
        actualizar_cache_prompts()  
        filtrar_prompts_ui()         
        self.destroy()

# ==========================================
# MOTOR DE FILTRADO Y GESTIÓN DE UI
# ==========================================
def seleccionar_prompt(id_seleccionado, boton_asociado, frame_contenedor):
    global id_prompt_actual
    id_prompt_actual = id_seleccionado
    for child in frame_contenedor.winfo_children():
        if isinstance(child, ctk.CTkButton):
            child.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
    boton_asociado.configure(fg_color="#1f538d")

def filtrar_prompts_ui(event=None):
    """Filtra los prompts en memoria y los dibuja usando el argumento estándar 'anchor'."""
    global frame_lista_global, txt_buscar
    
    for widget in frame_lista_global.winfo_children():
        widget.destroy()
        
    texto_busqueda = txt_buscar.get().strip().lower()
    resultados = [p for p in PROMPTS_CACHE if texto_busqueda in p["etiqueta"].lower()]
    
    if not resultados:
        # CORRECCIÓN: CustomTkinter usa 'anchor' en lugar de 'text_anchor'
        lbl_vacio = ctk.CTkLabel(
            frame_lista_global, 
            text="No se encontraron開coincidencias", 
            text_color="gray",
            font=("Arial", 12, "italic"),
            anchor="center"
        )
        lbl_vacio.pack(pady=40, fill="x")
        return

    for reg in resultados:
        btn = ctk.CTkButton(frame_lista_global, text=reg["etiqueta"], anchor="w")
        btn.configure(command=lambda r_id=reg["id"], b=btn: seleccionar_prompt(r_id, b, frame_lista_global))
        btn.pack(pady=2, padx=10, fill="x")

def cambiar_modo_deteccion(nuevo_modo, txt_descripcion):
    global CONFIG_MODO_DETECCION
    CONFIG_MODO_DETECCION = nuevo_modo
    txt_descripcion.configure(state="normal")
    txt_descripcion.delete("1.0", ctk.END)
    txt_descripcion.insert("1.0", DESCRIPCIONES[nuevo_modo])
    txt_descripcion.configure(state="disabled")

def abrir_creador():
    VentanaFormulario(root, prompt_id=None)

def abrir_editor():
    global id_prompt_actual
    if id_prompt_actual is None: return
    VentanaFormulario(root, prompt_id=id_prompt_actual)

def puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=False):
    global id_prompt_actual
    if id_prompt_actual is None: return
    ejecutar_disparo_dinamico(id_prompt_actual, ocultar_ventana, forzar_modo_chat)

# ==========================================
# ENSAMBLAJE FINAL DE LA APLICACIÓN
# ==========================================
def iniciar_aplicacion():
    global root, frame_lista_global, txt_buscar
    root = ctk.CTk()
    root.title("PromptVault v22 - Solución de Argumento")
    root.geometry("780x480")
    
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)
    
    actualizar_cache_prompts()
    
    # --- COLUMNA IZQUIERDA ---
    frame_izq = ctk.CTkFrame(root)
    frame_izq.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
    
    frame_header_lista = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_header_lista.pack(fill="x", pady=(10, 5), padx=10)
    ctk.CTkLabel(frame_header_lista, text="Mis Prompts", font=("Arial", 14, "bold")).pack(side="left")
    ctk.CTkButton(frame_header_lista, text="[+] Nuevo", width=80, command=abrir_creador).pack(side="right")
    
    txt_buscar = ctk.CTkEntry(frame_izq, placeholder_text="Buscar por título...")
    txt_buscar.pack(fill="x", padx=10, pady=5)
    txt_buscar.bind("<KeyRelease>", filtrar_prompts_ui)
    
    frame_lista_global = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_lista_global.pack(fill="both", expand=True)
    
    filtrar_prompts_ui()
    
    frame_acciones = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_acciones.pack(fill="x", pady=15, padx=10)
    ctk.CTkButton(frame_acciones, text="[✎] Editar", width=90, fg_color="#2b2b2b", command=abrir_editor).pack(side="left")
    ctk.CTkButton(frame_acciones, text="Inyectar (Manual)", command=lambda: puente_de_disparo()).pack(side="right", fill="x", expand=True, padx=(10, 0))

    # --- COLUMNA DERECHA ---
    frame_der = ctk.CTkFrame(root)
    frame_der.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
    ctk.CTkLabel(frame_der, text="Control Preventivo de Chats", font=("Arial", 14, "bold")).pack(pady=10)
    
    var_modo = ctk.StringVar(value="teclado")
    txt_desc = ctk.CTkTextbox(frame_der, height=160, width=320, wrap="word")
    txt_desc.pack(pady=10, padx=10)
    txt_desc.insert("1.0", DESCRIPCIONES["teclado"])
    txt_desc.configure(state="disabled")
    
    ctk.CTkRadioButton(frame_der, text="Tecla Modificadora (Recomendado)", variable=var_modo, value="teclado",
                       command=lambda: cambiar_modo_deteccion("teclado", txt_desc)).pack(anchor="w", padx=20, pady=5)
    ctk.CTkRadioButton(frame_der, text="Detección de Ventana Activa", variable=var_modo, value="automatico",
                       command=lambda: cambiar_modo_deteccion("automatico", txt_desc)).pack(anchor="w", padx=20, pady=5)

    keyboard.add_hotkey('ctrl+comma', lambda: puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=False))
    keyboard.add_hotkey('ctrl+shift+comma', lambda: puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=True))
    
    root.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()