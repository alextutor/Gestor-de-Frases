import customtkinter as ctk
import keyboard
import time
import threading
import sqlite3
import ctypes
from datetime import datetime

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
# CAPA DE DATOS (SQLite3 + CACHÉ LOCAL + MIGRACIÓN)
# ==========================================
def inicializar_db_y_migrar():
    DB_NAME = "prompts.sqlite"
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        
        # Crear tabla si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL,
                eliminado_en TEXT DEFAULT NULL
            )
        ''')
        
        # Verificar e inyectar columna eliminado_en si no existe (Migración limpia)
        cursor.execute("PRAGMA table_info(prompts)")
        columnas = [col[1] for col in cursor.fetchall()]
        if "eliminado_en" not in columnas:
            cursor.execute("ALTER TABLE prompts ADD COLUMN eliminado_en TEXT DEFAULT NULL")
            conexion.commit()
            
        # Índice parcial optimizado para bajo consumo de RAM y lecturas veloces
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prompts_activos 
            ON prompts(id) WHERE eliminado_en IS NULL
        ''')
        conexion.commit()
    except sqlite3.Error as e:
        print(f"[Error Inicialización DB] {e}")
    finally:
        if conexion:
            conexion.close()

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
        # Filtrado estricto por índice parcial (Excluye registros eliminados lógicamente)
        cursor.execute("SELECT id, titulo FROM prompts WHERE eliminado_en IS NULL ORDER BY id ASC")
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

def ejecutar_borrado_logico_db(prompt_id):
    DB_NAME = "prompts.sqlite"
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE prompts SET eliminado_en = ? WHERE id = ?", (fecha_actual, prompt_id))
        conexion.commit()
    except sqlite3.Error as e:
        print(f"[Error DB Borrado Lógico] {e}")
    finally:
        if conexion: conexion.close()

# ==========================================
# MOTOR NATIVO DE INYECCIÓN BY HARDWARE
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
# FORMULARIO MODAL INTERACTIVO (CREAR / EDITAR)
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
# MODAL DE CONFIRMACIÓN DE BORRADO LÓGICO
# ==========================================
class ModalConfirmarEliminacion(ctk.CTkToplevel):
    def __init__(self, master, prompt_id, titulo_prompt, callback_exito, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.prompt_id = prompt_id
        self.callback_exito = callback_exito
        
        self.title("Confirmar Eliminación Segura")
        self.geometry("420x170")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        # Centrado geométrico relativo a la app principal
        x = master.winfo_x() + (master.winfo_width() // 2) - 210
        y = master.winfo_y() + (master.winfo_height() // 2) - 85
        self.geometry(f"+{x}+{y}")
        
        lbl_msg = ctk.CTkLabel(
            self, 
            text=f"¿Estás seguro de que deseas enviar a la papelera el prompt?\n\n\"{titulo_prompt}\"",
            wraplength=380, 
            justify="center",
            font=("Arial", 12)
        )
        lbl_msg.pack(pady=20, padx=20)
        
        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=10)
        
        btn_cancelar = ctk.CTkButton(
            frame_botones, 
            text="Cancelar", 
            fg_color="#555555", 
            hover_color="#444444",
            command=self.destroy
        )
        btn_cancelar.pack(side="left", padx=10)
        btn_cancelar.focus_set()  # Enfoque seguro por teclado
        
        btn_confirmar = ctk.CTkButton(
            frame_botones, 
            text="Eliminar (Borrado Lógico)", 
            fg_color="#D32F2F", 
            hover_color="#B71C1C",
            command=self.confirmar
        )
        btn_confirmar.pack(side="left", padx=10)

    def confirmar(self):
        ejecutar_borrado_logico_db(self.prompt_id)
        self.callback_exito(self.prompt_id)
        self.destroy()

# ==========================================
# MOTOR DE FILTRADO Y RECONSTRUCCIÓN INLINE
# ==========================================
def seleccionar_prompt(id_seleccionado, boton_asociado, frame_contenedor):
    global id_prompt_actual
    id_prompt_actual = id_seleccionado
    for child in frame_contenedor.winfo_children():
        if isinstance(child, ctk.CTkFrame):
            for sub_child in child.winfo_children():
                if isinstance(sub_child, ctk.CTkButton) and sub_child.cget("anchor") == "w":
                    sub_child.configure(fg_color="transparent")
    boton_asociado.configure(fg_color="#1f538d")

def al_eliminar_exitoso(prompt_id):
    global id_prompt_actual
    if id_prompt_actual == prompt_id:
        id_prompt_actual = None
    actualizar_cache_prompts()
    filtrar_prompts_ui()

def abrir_editor_directo(prompt_id):
    VentanaFormulario(root, prompt_id=prompt_id)

def abrir_confirmacion_directa(prompt_id, titulo_prompt):
    ModalConfirmarEliminacion(root, prompt_id, titulo_prompt, al_eliminar_exitoso)

def filtrar_prompts_ui(event=None):
    """Filtra reactivamente la caché y renderiza la lista usando filas horizontales."""
    global frame_lista_global, txt_buscar
    
    for widget in frame_lista_global.winfo_children():
        widget.destroy()
        
    texto_busqueda = txt_buscar.get().strip().lower()
    resultados = [p for p in PROMPTS_CACHE if texto_busqueda in p["etiqueta"].lower()]
    
    if not resultados:
        lbl_vacio = ctk.CTkLabel(
            frame_lista_global, 
            text="No se encontraron coincidencias", 
            text_color="gray",
            font=("Arial", 12, "italic")
        )
        lbl_vacio.pack(pady=40, fill="x")
        return

    for reg in resultados:
        reg_id = reg["id"]
        reg_titulo = reg["etiqueta"]
        
        # Fila contenedora limpia
        fila_frame = ctk.CTkFrame(frame_lista_global, fg_color="transparent")
        fila_frame.pack(fill="x", pady=2, padx=5)
        
        # Botón Azul de Selección Izquierda
        btn_sel = ctk.CTkButton(fila_frame, text=reg_titulo, anchor="w", fg_color="transparent")
        if id_prompt_actual == reg_id:
            btn_sel.configure(fg_color="#1f538d")
            
        btn_sel.configure(command=lambda r_id=reg_id, b=btn_sel: seleccionar_prompt(r_id, b, frame_lista_global))
        btn_sel.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        # Botón Inline Oscuro [✎]
        btn_edit = ctk.CTkButton(
            fila_frame, 
            text="✎", 
            width=32, 
            height=28, 
            fg_color="#2b2b2b", 
            hover_color="#3e3e3e",
            command=lambda r_id=reg_id: abrir_editor_directo(r_id)
        )
        btn_edit.pack(side="left", padx=2)
        
        # Botón Inline Rojo de Alerta [✕]
        btn_del = ctk.CTkButton(
            fila_frame, 
            text="✕", 
            width=32, 
            height=28, 
            fg_color="#D32F2F", 
            hover_color="#B71C1C",
            command=lambda r_id=reg_id, t=reg_titulo: abrir_confirmacion_directa(r_id, t)
        )
        btn_del.pack(side="left", padx=(2, 0))

def cambiar_modo_deteccion(nuevo_modo, txt_descripcion):
    global CONFIG_MODO_DETECCION
    CONFIG_MODO_DETECCION = nuevo_modo
    txt_descripcion.configure(state="normal")
    txt_descripcion.delete("1.0", ctk.END)
    txt_descripcion.insert("1.0", DESCRIPCIONES[nuevo_modo])
    txt_descripcion.configure(state="disabled")

def abrir_creador():
    VentanaFormulario(root, prompt_id=None)

def puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=False):
    global id_prompt_actual
    if id_prompt_actual is None: return
    ejecutar_disparo_dinamico(id_prompt_actual, ocultar_ventana, forzar_modo_chat)

# ==========================================
# ENSAMBLAJE VENTANA PRINCIPAL
# ==========================================
def iniciar_aplicacion():
    global root, frame_lista_global, txt_buscar
    
    inicializar_db_y_migrar()
    
    root = ctk.CTk()
    root.title("PromptVault v23 - Edición y Eliminación Segura Inline")
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
    
    frame_lista_global = ctk.CTkScrollableFrame(frame_izq, fg_color="transparent", label_text="")
    frame_lista_global.pack(fill="both", expand=True, padx=5, pady=5)
    
    filtrar_prompts_ui()
    
    frame_acciones = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_acciones.pack(fill="x", pady=15, padx=10)
    ctk.CTkButton(frame_acciones, text="Inyectar (Manual)", command=lambda: puente_de_disparo()).pack(fill="x", expand=True)

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

    # Hotkeys Globales por Hardware de v22
    keyboard.add_hotkey('ctrl+comma', lambda: puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=False))
    keyboard.add_hotkey('ctrl+shift+comma', lambda: puente_de_disparo(ocultar_ventana=True, forzar_modo_chat=True))
    
    root.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()