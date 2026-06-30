import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, colorchooser
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
TEMA_ACTUAL = "Dark Neon Vault"
CONFIG_DIAS_PURGA = "30"
frame_lista_global = None  
txt_buscar = None
lbl_header_global = None
PROMPTS_CACHE = []         
PALETAS = {}

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
# RUTINA DE CENTRADO PROFESIONAL DE VENTANAS
# ==========================================
def centrar_ventana(ventana, padre=None):
    ventana.update_idletasks()
    width = ventana.winfo_width()
    height = ventana.winfo_height()
    
    if padre:
        padre_x = padre.winfo_x()
        padre_y = padre.winfo_y()
        padre_w = padre.winfo_width()
        padre_h = padre.winfo_height()
        x = padre_x + (padre_w // 2) - (width // 2)
        y = padre_y + (padre_h // 2) - (height // 2)
    else:
        screen_width = ventana.winfo_screenwidth()
        screen_height = ventana.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
    ventana.geometry(f"+{x}+{y}")

# ==========================================
# CAPA DE DATOS E INFRAESTRUCTURA (SQLite3)
# ==========================================
def inicializar_db_y_config():
    DB_NAME = "prompts.sqlite"
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        
        cursor.execute("DROP TABLE IF EXISTS temas_comerciales")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL,
                eliminado_en TEXT DEFAULT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temas_comerciales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                modo TEXT NOT NULL,
                color_base TEXT NOT NULL,
                color_texto TEXT NOT NULL,
                btn_exito TEXT NOT NULL,
                btn_accion TEXT NOT NULL,
                btn_peligro TEXT NOT NULL,
                btn_neutral TEXT NOT NULL,
                prompt_usar_borde INTEGER NOT NULL,
                prompt_usar_bg INTEGER NOT NULL,
                prompt_color_borde TEXT NOT NULL,
                prompt_color_bg TEXT NOT NULL,
                prompt_color_hover TEXT NOT NULL
            )
        ''')
        
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tema', 'Dark Neon Vault')")
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('modo_deteccion', 'teclado')")
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('dias_purga', '30')")
        
        cursor.execute('''
            INSERT OR IGNORE INTO temas_comerciales 
            (nombre, modo, color_base, color_texto, btn_exito, btn_accion, btn_peligro, btn_neutral, prompt_usar_borde, prompt_usar_bg, prompt_color_borde, prompt_color_bg, prompt_color_hover)
            VALUES 
            ('Dark Neon Vault', 'dark', '#0A0E17', '#E2E8F0', '#10B981', '#06B6D4', '#EF4444', '#4B5563', 1, 1, '#10B981', '#111827', '#1F2937'),
            ('Slate Corporate', 'dark', '#1F2937', '#F3F4F6', '#2563EB', '#1D4ED8', '#DC2626', '#4B5563', 0, 1, '#374151', '#374151', '#4B5563'),
            ('Classic Light', 'light', '#F3F4F6', '#1F2937', '#16A34A', '#2563EB', '#DC2626', '#9CA3AF', 1, 0, '#D1D5DB', '#FFFFFF', '#E5E7EB')
        ''')
            
        conexion.commit()
    except sqlite3.Error as e:
        print(f"[Error DB Inicialización] {e}")
    finally:
        if conexion:
            conexion.close()

def cargar_configuracion_global():
    global TEMA_ACTUAL, CONFIG_MODO_DETECCION, CONFIG_DIAS_PURGA, PALETAS
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT nombre, modo, color_base, color_texto, btn_exito, btn_accion, btn_peligro, btn_neutral, 
                   prompt_usar_borde, prompt_usar_bg, prompt_color_borde, prompt_color_bg, prompt_color_hover
            FROM temas_comerciales
        ''')
        PALETAS = {}
        for row in cursor.fetchall():
            PALETAS[row[0]] = {
                "mode": row[1],
                "color_base": row[2],
                "color_texto": row[3],
                "btn_exito": row[4],
                "btn_accion": row[5],
                "btn_peligro": row[6],
                "btn_neutral": row[7],
                "prompt_usar_borde": int(row[8]),
                "prompt_usar_bg": int(row[9]),
                "prompt_color_borde": row[10],
                "prompt_color_bg": row[11],
                "prompt_color_hover": row[12]
            }
            
        cursor.execute("SELECT clave, valor FROM configuracion")
        for clave, valor in cursor.fetchall():
            if clave == "tema": 
                if valor in PALETAS:
                    TEMA_ACTUAL = valor
                else:
                    TEMA_ACTUAL = "Dark Neon Vault"
                    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('tema', 'Dark Neon Vault')")
                    conn.commit()
            if clave == "modo_deteccion": CONFIG_MODO_DETECCION = valor
            if clave == "dias_purga": CONFIG_DIAS_PURGA = valor
        conn.close()
    except Exception:
        pass

def guardar_config_db(clave, valor):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))
        conn.commit()
        conn.close()
    except Exception: pass

def ejecutar_purga_automatica():
    global CONFIG_DIAS_PURGA
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        dias = int(CONFIG_DIAS_PURGA)
        cursor.execute('''
            DELETE FROM prompts 
            WHERE eliminado_en IS NOT NULL 
              AND datetime(eliminado_en) <= datetime('now', ?, 'localtime')
        ''', (f'-{dias} days',))
        conn.commit()
        conn.close()
    except Exception: pass

def obtener_texto_prompt(prompt_id):
    DB_NAME = "prompts.sqlite" 
    texto_recuperado = ""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT contenido FROM prompts WHERE id = ?", (prompt_id,))
        res = cursor.fetchone()
        if res: texto_recuperado = res[0]
        conn.close()
    except Exception: pass
    return texto_recuperado

def actualizar_cache_prompts():
    global PROMPTS_CACHE
    DB_NAME = "prompts.sqlite"
    PROMPTS_CACHE = []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo FROM prompts WHERE eliminado_en IS NULL ORDER BY id ASC")
        for fila in cursor.fetchall():
            PROMPTS_CACHE.append({"id": fila[0], "etiqueta": fila[1]})
        conn.close()
    except Exception: pass

def guardar_nuevo_prompt(titulo, contenido):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO prompts (titulo, contenido) VALUES (?, ?)", (titulo, contenido))
        conn.commit()
        conn.close()
    except Exception: pass

def actualizar_prompt(prompt_id, titulo, contenido):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE prompts SET titulo = ?, contenido = ? WHERE id = ?", (titulo, contenido, prompt_id))
        conn.commit()
        conn.close()
    except Exception: pass

def ejecutar_borrado_logico_db(prompt_id):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE prompts SET eliminado_en = ? WHERE id = ?", (fecha_actual, prompt_id))
        conn.commit()
        conn.close()
    except Exception: pass

def ejecutar_restauracion_db(prompt_id):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE prompts SET eliminado_en = NULL WHERE id = ?", (prompt_id,))
        conn.commit()
        conn.close()
    except Exception: pass

# ==========================================
# MOTOR NATIVO DE INYECCIÓN POR HARDWARE
# ==========================================
def obtener_titulo_ventana_activa():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value.lower()
    except Exception: return ""

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
            if linea: keyboard.write(linea, delay=0.005)
            if i < len(lineas) - 1:
                keyboard.press_and_release('shift+enter')
                time.sleep(0.01)
    else:
        keyboard.write(texto, delay=0.005)

def ejecutar_disparo_dinamico(prompt_id, ocultar_ventana=True, forzar_modo_chat=False):
    def hilo_proceso():
        texto_raw = obtener_texto_prompt(prompt_id)
        if not texto_raw or not texto_raw.strip(): return
        if ocultar_ventana: root.withdraw()
        time.sleep(0.4)
        try:
            ejecutar_inyeccion_inteligente(texto_raw, forzar_modo_chat)
        except Exception: pass
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
        
        centrar_ventana(self, master)
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        ctk.CTkLabel(self, text="Título del Prompt:", text_color=t["color_texto"], font=("Arial", 12, "bold")).pack(pady=(15, 2), padx=20, anchor="w")
        self.txt_titulo = ctk.CTkEntry(self, width=360)
        self.txt_titulo.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self, text="Contenido:", text_color=t["color_texto"], font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        self.txt_contenido = ctk.CTkTextbox(self, width=360, height=220)
        self.txt_contenido.pack(pady=5, padx=20, fill="both", expand=True)
        
        btn_g = ctk.CTkButton(self, text="Guardar Cambios", fg_color=t["btn_accion"], command=self.procesar_datos)
        btn_g.pack(pady=20)
        
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
        if not titulo or not contenido: return
        if self.prompt_id:
            actualizar_prompt(self.prompt_id, titulo, contenido)
        else:
            guardar_nuevo_prompt(titulo, contenido)
        actualizar_cache_prompts()  
        filtrar_prompts_ui()         
        self.destroy()

# ==========================================
# INTERFAZ MODAL DE CONFIRMACIÓN SEGURA
# ==========================================
class ModalConfirmarEliminacion(ctk.CTkToplevel):
    def __init__(self, master, prompt_id, titulo_prompt, callback_exito, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.prompt_id = prompt_id
        self.callback_exito = callback_exito
        
        self.title("Confirmar Eliminación")
        self.geometry("420x170")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, master)
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        lbl_msg = ctk.CTkLabel(self, text=f"¿Estás seguro de enviar a la papelera el prompt?\n\n\"{titulo_prompt}\"", text_color=t["color_texto"], wraplength=380, justify="center")
        lbl_msg.pack(pady=20, padx=20)
        
        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=10)
        
        btn_cancelar = ctk.CTkButton(frame_botones, text="Cancelar", fg_color=t["btn_neutral"], command=self.destroy)
        btn_cancelar.pack(side="left", padx=10)
        btn_cancelar.focus_set()
        
        btn_confirmar = ctk.CTkButton(frame_botones, text="Eliminar", fg_color=t["btn_peligro"], command=self.confirmar)
        btn_confirmar.pack(side="left", padx=10)

    def confirmar(self):
        ejecutar_borrado_logico_db(self.prompt_id)
        self.callback_exito(self.prompt_id)
        self.destroy()

# ==========================================
# PAPELERA DE RECICLAJE (RESTAURACIÓN)
# ==========================================
class VentanaPapeleraReciclaje(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Papelera de Reciclaje")
        self.geometry("460x420")
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, master)
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        ctk.CTkLabel(self, text="Historial de Prompts Eliminados", text_color=t["color_texto"], font=("Arial", 14, "bold")).pack(pady=10)
        
        self.scroll_papelera = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_papelera.pack(fill="both", expand=True, padx=15, pady=10)
        
        frame_ctrl = ctk.CTkFrame(self, fg_color="transparent")
        frame_ctrl.pack(fill="x", side="bottom", pady=15, padx=15)
        
        btn_salir = ctk.CTkButton(frame_ctrl, text="Salir", fg_color=t["btn_neutral"], command=self.destroy)
        btn_salir.pack(side="right", padx=5)
        
        self.cargar_eliminados()

    def cargar_eliminados(self):
        t = PALETAS[TEMA_ACTUAL]
        for widget in self.scroll_papelera.winfo_children(): widget.destroy()
            
        try:
            conn = sqlite3.connect("prompts.sqlite")
            cursor = conn.cursor()
            cursor.execute("SELECT id, titulo, eliminado_en FROM prompts WHERE eliminado_en IS NOT NULL ORDER BY eliminado_en DESC")
            registros = cursor.fetchall()
            conn.close()
        except Exception: registros = []
            
        if not registros:
            ctk.CTkLabel(self.scroll_papelera, text="La papelera está vacía", text_color="gray", font=("Arial", 12, "italic")).pack(pady=30)
            return

        for r_id, r_titulo, r_fecha in registros:
            fila = ctk.CTkFrame(self.scroll_papelera, fg_color="transparent")
            fila.pack(fill="x", pady=4, padx=5)
            
            info_text = f"{r_titulo}\n(Eliminado: {r_fecha})"
            lbl_info = ctk.CTkLabel(fila, text=info_text, text_color=t["color_texto"], anchor="w", justify="left")
            lbl_info.pack(side="left", fill="x", expand=True)
            
            btn_restaurar = ctk.CTkButton(fila, text="↺ Restaurar", width=95, height=28, fg_color=t["btn_exito"],
                                           command=lambda id_p=r_id: self.restaurar_registro(id_p))
            btn_restaurar.pack(side="right", padx=5)

    def restaurar_registro(self, prompt_id):
        ejecutar_restauracion_db(prompt_id)
        actualizar_cache_prompts()
        filtrar_prompts_ui()
        self.cargar_eliminados()

# ==========================================
# CONFIGURACIÓN: PERÍODO DE RETENCIÓN / PURGA
# ==========================================
class VentanaConfigurarPurga(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        global CONFIG_DIAS_PURGA
        self.title("Configurar Purga Automática")
        self.geometry("360x180")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, master)
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        ctk.CTkLabel(self, text="Plazo de Purga Automática", text_color=t["color_texto"], font=("Arial", 13, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(self, text="Días de retención antes del borrado definitivo:", text_color=t["color_texto"], font=("Arial", 11)).pack(pady=2)
        
        self.entry_dias = ctk.CTkEntry(self, width=100, justify="center")
        self.entry_dias.pack(pady=10)
        self.entry_dias.insert(0, CONFIG_DIAS_PURGA)
        
        btn_g = ctk.CTkButton(self, text="Guardar Plazo", fg_color=t["btn_accion"], command=self.guardar_plazo)
        btn_g.pack(pady=5)

    def guardar_plazo(self):
        val = self.entry_dias.get().strip()
        if val.isdigit() and int(val) > 0:
            global CONFIG_DIAS_PURGA
            CONFIG_DIAS_PURGA = val
            guardar_config_db("dias_purga", val)
            self.destroy()

# ==========================================
# VENTANA CONFIGURACIÓN: DETECCIÓN DE CHATS
# ==========================================
class VentanaControlPreventivo(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Configuración Detección de Chats")
        self.geometry("390x340")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, master)
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        ctk.CTkLabel(self, text="Mecanismo de Control Preventivo", text_color=t["color_texto"], font=("Arial", 14, "bold")).pack(pady=10)
        
        self.txt_desc = ctk.CTkTextbox(self, height=120, width=350, wrap="word")
        self.txt_desc.pack(pady=5, padx=15)
        self.txt_desc.insert("1.0", DESCRIPCIONES[CONFIG_MODO_DETECCION])
        self.txt_desc.configure(state="disabled")
        
        self.var_modo = ctk.StringVar(value=CONFIG_MODO_DETECCION)
        
        ctk.CTkRadioButton(self, text="Tecla Modificadora (Recomendado)", text_color=t["color_texto"], variable=self.var_modo, value="teclado",
                           command=self.actualizar_modo).pack(anchor="w", padx=25, pady=5)
        ctk.CTkRadioButton(self, text="Detección Automática de Ventanas", text_color=t["color_texto"], variable=self.var_modo, value="automatico",
                           command=self.actualizar_modo).pack(anchor="w", padx=25, pady=5)
        
        frame_btns = ctk.CTkFrame(self, fg_color="transparent")
        frame_btns.pack(fill="x", side="bottom", pady=15, padx=25)
        
        btn_salir = ctk.CTkButton(frame_btns, text="Salir", fg_color=t["btn_neutral"], width=100, command=self.destroy)
        btn_salir.pack(side="right", padx=(10, 0))
        
        btn_aceptar = ctk.CTkButton(frame_btns, text="Aceptar", fg_color=t["btn_accion"], width=100, command=self.confirmar_guardado)
        btn_aceptar.pack(side="right")
                           
    def actualizar_modo(self):
        nuevo_modo = self.var_modo.get()
        self.txt_desc.configure(state="normal")
        self.txt_desc.delete("1.0", ctk.END)
        self.txt_desc.insert("1.0", DESCRIPCIONES[nuevo_modo])
        self.txt_desc.configure(state="disabled")

    def confirmar_guardado(self):
        nuevo_modo = self.var_modo.get()
        guardar_config_db("modo_deteccion", nuevo_modo)
        global CONFIG_MODO_DETECCION
        CONFIG_MODO_DETECCION = nuevo_modo
        self.destroy()

# ==========================================
# CRUD DE TEMAS COMERCIALES OPTIMIZADO
# ==========================================
class VentanaCrudTemas(ctk.CTkToplevel):
    def __init__(self, master, callback_recargar_menu, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.callback_recargar_menu = callback_recargar_menu
        self.title("Optimizar Administrar Temas")
        self.geometry("820x600")
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, master)
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.id_tema_seleccionado = None
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)
        
        # --- PANEL IZQUIERDO: FORMULARIO ATÓMICO ---
        frame_form = ctk.CTkScrollableFrame(self)
        frame_form.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="Paleta Atómica de Componentes", font=("Arial", 13, "bold")).pack(pady=5)
        
        def crear_input_color(parent, label_text, placeholder):
            ctk.CTkLabel(parent, text=label_text, font=("Arial", 10, "bold") if "Color" not in label_text else None).pack(anchor="w", padx=10, pady=(5,0))
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=2)
            ent = ctk.CTkEntry(f, placeholder_text=placeholder)
            ent.pack(side="left", fill="x", expand=True)
            btn = ctk.CTkButton(f, text="🎨", width=28, fg_color=t["btn_neutral"], command=lambda e=ent: self.invocar_selector_color(e))
            btn.pack(side="right", padx=(5,0))
            return ent

        ctk.CTkLabel(frame_form, text="Nombre del Tema:").pack(anchor="w", padx=10)
        self.ent_nombre = ctk.CTkEntry(frame_form)
        self.ent_nombre.pack(fill="x", padx=10, pady=2)
        
        self.ent_base = crear_input_color(frame_form, "Color Base (Fondo Ventana):", "#0A0E17")
        self.ent_texto = crear_input_color(frame_form, "Color Texto General:", "#E2E8F0")
        
        self.ent_exito = crear_input_color(frame_form, "Color Éxito (Nuevo, Guardar):", "#10B981")
        self.ent_accion = crear_input_color(frame_form, "Color Acción (Inyectar, Activo):", "#06B6D4")
        self.ent_peligro = crear_input_color(frame_form, "Color Peligro (Eliminar):", "#EF4444")
        self.ent_neutral = crear_input_color(frame_form, "Color Neutral (Salir, Editar):", "#4B5563")
        
        ctk.CTkLabel(frame_form, text="Diseño Contenedor Listado (Tarjetas)", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(8,2))
        
        self.chk_borde = ctk.CTkCheckBox(frame_form, text="Habilitar Contorno/Borde")
        self.chk_borde.pack(anchor="w", padx=10, pady=2)
        
        self.chk_bg = ctk.CTkCheckBox(frame_form, text="Habilitar Fondo (Background)")
        self.chk_bg.pack(anchor="w", padx=10, pady=2)
        
        self.ent_p_borde = crear_input_color(frame_form, "Color del Contorno:", "#10B981")
        self.ent_p_bg = crear_input_color(frame_form, "Color del Fondo Tarjeta:", "#111827")
        self.ent_p_hover = crear_input_color(frame_form, "Color Hover (Al pasar el ratón):", "#1F2937")
        
        self.btn_guardar = ctk.CTkButton(frame_form, text="Registrar Tema", fg_color=t["btn_exito"], command=self.guardar_tema)
        self.btn_guardar.pack(fill="x", padx=10, pady=10)
        
        btn_l = ctk.CTkButton(frame_form, text="Limpiar / Nuevo", fg_color=t["btn_neutral"], command=self.limpiar_formulario)
        btn_l.pack(fill="x", padx=10, pady=2)
        
        self.btn_eliminar = ctk.CTkButton(frame_form, text="Eliminar Tema", fg_color=t["btn_peligro"], command=self.eliminar_tema)
        self.btn_eliminar.pack(fill="x", padx=10, pady=5)
        self.btn_eliminar.configure(state="disabled")

        ctk.CTkFrame(frame_form, height=2, fg_color="gray").pack(fill="x", padx=10, pady=10)
        self.btn_salir = ctk.CTkButton(frame_form, text="Salir", fg_color=t["btn_neutral"], command=self.destroy)
        self.btn_salir.pack(fill="x", padx=10, pady=(0, 10))
        
        # --- PANEL DERECHO: TREEVIEW DE CONFIGURACIONES ---
        frame_lista = ctk.CTkFrame(self)
        frame_lista.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(frame_lista, text="Esquemas de Interfaz Disponibles", font=("Arial", 12, "bold")).pack(pady=10)
        
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("Treeview", background="#1E293B", foreground="white", fieldbackground="#1E293B", rowheight=24)
        self.tabla = ttk.Treeview(frame_lista, columns=("Nombre", "Base", "BordePrompt"), show="headings")
        self.tabla.heading("Nombre", text="Esquema")
        self.tabla.heading("Base", text="Color Base")
        self.tabla.heading("BordePrompt", text="Borde Listado")
        self.tabla.column("Nombre", width=150)
        self.tabla.column("Base", width=90)
        self.tabla.column("BordePrompt", width=90)
        self.tabla.pack(fill="both", expand=True, padx=10, pady=5)
        self.tabla.bind("<<TreeviewSelect>>", self.al_seleccionar_registro)
        
        self.actualizar_tabla_ui()

    def invocar_selector_color(self, entry_widget):
        color_actual = entry_widget.get().strip()
        if not color_actual.startswith("#"): color_actual = None
        color_elegido = colorchooser.askcolor(title="Selecciona un color", initialcolor=color_actual)
        if color_elegido[1]:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, color_elegido[1])

    def actualizar_tabla_ui(self):
        for item in self.tabla.get_children(): self.tabla.delete(item)
        try:
            conn = sqlite3.connect("prompts.sqlite")
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, color_base, prompt_color_borde FROM temas_comerciales ORDER BY id ASC")
            for fila in cursor.fetchall():
                nombre_visual = f"{fila[1]} (Activo)" if fila[1] == TEMA_ACTUAL else fila[1]
                self.tabla.insert("", "end", iid=fila[0], values=(nombre_visual, fila[2], fila[3]))
            conn.close()
        except Exception: pass

    def al_seleccionar_registro(self, event):
        seleccion = self.tabla.selection()
        if not seleccion: return
        self.id_tema_seleccionado = seleccion[0]
        
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM temas_comerciales WHERE id=?", (self.id_tema_seleccionado,))
        r = cursor.fetchone()
        conn.close()
        
        if r:
            self.ent_nombre.delete(0, tk.END); self.ent_nombre.insert(0, r[1])
            self.ent_base.delete(0, tk.END); self.ent_base.insert(0, r[3])
            self.ent_texto.delete(0, tk.END); self.ent_texto.insert(0, r[4])
            self.ent_exito.delete(0, tk.END); self.ent_exito.insert(0, r[5])
            self.ent_accion.delete(0, tk.END); self.ent_accion.insert(0, r[6])
            self.ent_peligro.delete(0, tk.END); self.ent_peligro.insert(0, r[7])
            self.ent_neutral.delete(0, tk.END); self.ent_neutral.insert(0, r[8])
            
            if r[9] == 1: self.chk_borde.select()
            else: self.chk_borde.deselect()
            
            if r[10] == 1: self.chk_bg.select()
            else: self.chk_bg.deselect()
            
            self.ent_p_borde.delete(0, tk.END); self.ent_p_borde.insert(0, r[11])
            self.ent_p_bg.delete(0, tk.END); self.ent_p_bg.insert(0, r[12])
            self.ent_p_hover.delete(0, tk.END); self.ent_p_hover.insert(0, r[13])
            
            self.btn_guardar.configure(text="Actualizar Configuración")
            self.btn_eliminar.configure(state="normal")

    def limpiar_formulario(self):
        self.id_tema_seleccionado = None
        self.ent_nombre.delete(0, tk.END)
        self.ent_base.delete(0, tk.END)
        self.ent_texto.delete(0, tk.END)
        self.ent_exito.delete(0, tk.END)
        self.ent_accion.delete(0, tk.END)
        self.ent_peligro.delete(0, tk.END)
        self.ent_neutral.delete(0, tk.END)
        self.chk_borde.select()
        self.chk_bg.select()
        self.ent_p_borde.delete(0, tk.END)
        self.ent_p_bg.delete(0, tk.END)
        self.ent_p_hover.delete(0, tk.END)
        self.btn_guardar.configure(text="Registrar Tema")
        self.btn_eliminar.configure(state="disabled")

    def guardar_tema(self):
        nombre = self.ent_nombre.get().strip()
        base = self.ent_base.get().strip() or "#0A0E17"
        texto = self.ent_texto.get().strip() or "#E2E8F0"
        exito = self.ent_exito.get().strip() or "#10B981"
        accion = self.ent_accion.get().strip() or "#06B6D4"
        peligro = self.ent_peligro.get().strip() or "#EF4444"
        neutral = self.ent_neutral.get().strip() or "#4B5563"
        borde_flag = 1 if self.chk_borde.get() else 0
        bg_flag = 1 if self.chk_bg.get() else 0
        p_borde = self.ent_p_borde.get().strip() or "#10B981"
        p_bg = self.ent_p_bg.get().strip() or "#111827"
        p_hover = self.ent_p_hover.get().strip() or "#1F2937"
        
        if not nombre: return
        
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        if self.id_tema_seleccionado:
            cursor.execute('''
                UPDATE temas_comerciales SET nombre=?, color_base=?, color_texto=?, btn_exito=?, btn_accion=?, 
                                             btn_peligro=?, btn_neutral=?, prompt_usar_borde=?, prompt_usar_bg=?, 
                                             prompt_color_borde=?, prompt_color_bg=?, prompt_color_hover=? WHERE id=?
            ''', (nombre, base, texto, exito, accion, peligro, neutral, borde_flag, bg_flag, p_borde, p_bg, p_hover, self.id_tema_seleccionado))
        else:
            cursor.execute('''
                INSERT OR IGNORE INTO temas_comerciales 
                (nombre, modo, color_base, color_texto, btn_exito, btn_accion, btn_peligro, btn_neutral, prompt_usar_borde, prompt_usar_bg, prompt_color_borde, prompt_color_bg, prompt_color_hover)
                VALUES (?, 'dark', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, base, texto, exito, accion, peligro, neutral, borde_flag, bg_flag, p_borde, p_bg, p_hover))
        conn.commit()
        conn.close()
        
        cargar_configuracion_global()
        self.callback_recargar_menu()
        self.actualizar_tabla_ui()
        self.limpiar_formulario()
        filtrar_prompts_ui()

    def eliminar_tema(self):
        if not self.id_tema_seleccionado: return
        nombre_tema = self.ent_nombre.get().strip()
        global TEMA_ACTUAL
        if nombre_tema == TEMA_ACTUAL or nombre_tema == "Dark Neon Vault": return
            
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM temas_comerciales WHERE id=?", (self.id_tema_seleccionado,))
        conn.commit()
        conn.close()
        
        cargar_configuracion_global()
        self.callback_recargar_menu()
        self.actualizar_tabla_ui()
        self.limpiar_formulario()

# ==========================================
# INTERFAZ Y LOGICA COMPLEMENTARIA (FILTRADO UI)
# ==========================================
def seleccionar_prompt(id_seleccionado, frame_asociado, frame_contenedor):
    global id_prompt_actual
    id_prompt_actual = id_seleccionado
    t = PALETAS[TEMA_ACTUAL]
    
    for child in frame_contenedor.winfo_children():
        if isinstance(child, ctk.CTkFrame):
            # Asegura restaurar el color del fondo guardado o el base
            orig_bg = t["prompt_color_bg"] if t["prompt_usar_bg"] else t["color_base"]
            child.configure(fg_color=orig_bg)
            
    frame_asociado.configure(fg_color="#1E293B")

def al_eliminar_exitoso(prompt_id):
    global id_prompt_actual
    if id_prompt_actual == prompt_id: id_prompt_actual = None
    actualizar_cache_prompts()
    filtrar_prompts_ui()

def abrir_editor_directo(prompt_id):
    VentanaFormulario(root, prompt_id=prompt_id)

def abrir_confirmacion_directa(prompt_id, titulo_prompt):
    ModalConfirmarEliminacion(root, prompt_id, titulo_prompt, al_eliminar_exitoso)

def filtrar_prompts_ui(event=None):
    global frame_lista_global, txt_buscar
    if frame_lista_global is None: return
    
    for widget in frame_lista_global.winfo_children(): widget.destroy()
    texto_busqueda = txt_buscar.get().strip().lower() if txt_buscar else ""
    resultados = [p for p in PROMPTS_CACHE if texto_busqueda in p["etiqueta"].lower()]
    
    t = PALETAS[TEMA_ACTUAL]
    
    if not resultados:
        ctk.CTkLabel(frame_lista_global, text="Sin coincidencias", text_color="gray", font=("Arial", 12, "italic")).pack(pady=20)
        return

    for reg in resultados:
        reg_id = reg["id"]
        reg_titulo = reg["etiqueta"]
        
        # SOLUCIÓN DE SEGURIDAD EXCLUSIVA CUSTOMTKINTER:
        # Si 'prompt_usar_borde' es 0, asignamos None y border_width=0.
        # Nunca se inyectará "transparent" al border_color.
        b_width = 2 if t["prompt_usar_borde"] else 0
        b_color = t["prompt_color_borde"] if t["prompt_usar_borde"] else None
        
        card_bg = t["prompt_color_bg"] if t["prompt_usar_bg"] else t["color_base"]
        card_hover = t.get("prompt_color_hover", "#1F2937")
        
        color_inicial = "#1E293B" if id_prompt_actual == reg_id else card_bg
        
        # Pasamos b_color de forma segura (si es None, CTk usa el por defecto pero b_width=0 lo oculta)
        card_frame = ctk.CTkFrame(frame_lista_global, fg_color=color_inicial, border_width=b_width, border_color=b_color, corner_radius=8)
        card_frame.pack(fill="x", pady=4, padx=5)
        
        lbl_titulo = ctk.CTkLabel(card_frame, text=reg_titulo, text_color=t["color_texto"], font=("Arial", 12, "bold"), anchor="w", cursor="hand2")
        lbl_titulo.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        
        # Lógica Hover Dinámica
        def al_entrar_mouse(e, frm=card_frame, hover_c=card_hover):
            frm.configure(fg_color=hover_c)

        def al_salir_mouse(e, r_id=reg_id, frm=card_frame, def_bg=card_bg):
            if id_prompt_actual == r_id:
                frm.configure(fg_color="#1E293B")
            else:
                frm.configure(fg_color=def_bg)

        card_frame.bind("<Enter>", al_entrar_mouse)
        card_frame.bind("<Leave>", al_salir_mouse)
        lbl_titulo.bind("<Enter>", al_entrar_mouse)
        lbl_titulo.bind("<Leave>", al_salir_mouse)
        
        lbl_titulo.bind("<Button-1>", lambda e, r_id=reg_id, f=card_frame: seleccionar_prompt(r_id, f, frame_lista_global))
        card_frame.bind("<Button-1>", lambda e, r_id=reg_id, f=card_frame: seleccionar_prompt(r_id, f, frame_lista_global))
        
        btn_edit = ctk.CTkButton(card_frame, text="✎", width=32, height=26, fg_color=t["btn_neutral"], hover_color="#374151",
                                 command=lambda r_id=reg_id: abrir_editor_directo(r_id))
        btn_edit.pack(side="left", padx=2)
        
        btn_del = ctk.CTkButton(card_frame, text="✕", width=32, height=26, fg_color=t["btn_peligro"], hover_color="#991B1B",
                                command=lambda r_id=reg_id, t_p=reg_titulo: abrir_confirmacion_directa(r_id, t_p))
        btn_del.pack(side="left", padx=(2, 8))

def cambiar_tema_aplicacion(nombre_tema):
    if nombre_tema in PALETAS:
        guardar_config_db("tema", nombre_tema)
        global TEMA_ACTUAL
        TEMA_ACTUAL = nombre_tema
        
        t = PALETAS[nombre_tema]
        ctk.set_appearance_mode(t["mode"])
        
        if lbl_header_global:
            lbl_header_global.configure(text=f"Mis Frases | Tema: {TEMA_ACTUAL}")
        
        if root:
            root.configure(fg_color=t["color_base"])
            frame_izq.configure(fg_color=t["color_base"])
            btn_nuevo.configure(fg_color=t["btn_exito"])
            btn_inyectar.configure(fg_color=t["btn_accion"])
        filtrar_prompts_ui()

def recargar_menu_temas_dinamico():
    global submenu_temas
    submenu_temas.delete(0, tk.END)
    for tema in PALETAS.keys():
        indicador = " ✓" if tema == TEMA_ACTUAL else ""
        submenu_temas.add_command(label=f"{tema}{indicador}", command=lambda t=tema: cambiar_tema_aplicacion(t))

def alternar_visibilidad_ventana(event=None):
    try:
        if root.state() == "iconic" or not root.focus_displayof():
            root.deiconify()
            root.state("normal")
            root.attributes("-topmost", True)
            root.attributes("-topmost", False)
            if txt_buscar: txt_buscar.focus_set()
        else:
            root.iconify()
    except Exception: pass

def ocultar_por_escape(event=None):
    root.iconify()

def abrir_creador():
    VentanaFormulario(root, prompt_id=None)

def puente_de_disparo():
    if id_prompt_actual is not None:
        ejecutar_disparo_dinamico(id_prompt_actual, ocultar_ventana=True)

# ==========================================
# ENSAMBLAJE FINAL DEL SOFTWARE COMERCIAL
# ==========================================
def iniciar_aplicacion():
    global root, frame_lista_global, txt_buscar, submenu_temas, frame_izq, btn_nuevo, btn_inyectar, lbl_header_global
    
    inicializar_db_y_config()
    cargar_configuracion_global()
    ejecutar_purga_automatica() 
    
    t = PALETAS[TEMA_ACTUAL]
    ctk.set_appearance_mode(t["mode"])
    
    root = ctk.CTk()
    root.title("PromptVault Premium v27")
    root.geometry("460x560")
    root.configure(fg_color=t["color_base"])
    
    centrar_ventana(root)
    actualizar_cache_prompts()
    
    menu_barra = tk.Menu(root)
    
    menu_archivo = tk.Menu(menu_barra, tearoff=0)
    menu_archivo.add_command(label="Ver Papelera de Reciclaje", command=lambda: VentanaPapeleraReciclaje(root))
    menu_archivo.add_separator()
    menu_archivo.add_command(label="Salir de la App", command=root.quit)
    menu_barra.add_cascade(label="Archivo", menu=menu_archivo)
    
    menu_config = tk.Menu(menu_barra, tearoff=0)
    submenu_temas = tk.Menu(menu_config, tearoff=0)
    recargar_menu_temas_dinamico()
    
    menu_config.add_cascade(label="Temas Comerciales", menu=submenu_temas)
    menu_config.add_command(label="Administrar Temas...", command=lambda: VentanaCrudTemas(root, recargar_menu_temas_dinamico))
    menu_config.add_separator()
    menu_config.add_command(label="Días de Purga...", command=lambda: VentanaConfigurarPurga(root))
    menu_config.add_command(label="Control Preventivo de Chats...", command=lambda: VentanaControlPreventivo(root))
    
    menu_barra.add_cascade(label="Configuración", menu=menu_config)
    root.config(menu=menu_barra)
    
    frame_izq = ctk.CTkFrame(root, fg_color=t["color_base"])
    frame_izq.pack(fill="both", expand=True, padx=15, pady=15)
    
    frame_header = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_header.pack(fill="x", pady=(5, 5), padx=5)
    
    lbl_header_global = ctk.CTkLabel(frame_header, text=f"Mis Frases | Tema: {TEMA_ACTUAL}", text_color=t["color_texto"], font=("Arial", 14, "bold"))
    lbl_header_global.pack(side="left")
    
    txt_buscar = ctk.CTkEntry(frame_izq, placeholder_text="Buscar prompt...")
    txt_buscar.pack(fill="x", padx=5, pady=5)
    txt_buscar.bind("<KeyRelease>", filtrar_prompts_ui)
    
    frame_lista_global = ctk.CTkScrollableFrame(frame_izq, fg_color="transparent")
    frame_lista_global.pack(fill="both", expand=True, padx=0, pady=5)
    
    filtrar_prompts_ui()
    
    frame_acciones = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_acciones.pack(fill="x", pady=(10, 5), padx=5)
    
    btn_nuevo = ctk.CTkButton(frame_acciones, text="[+] Nuevo Prompt", fg_color=t["btn_exito"], width=140, command=abrir_creador)
    btn_nuevo.pack(side="left")
    
    btn_inyectar = ctk.CTkButton(frame_acciones, text="Inyectar Selección", fg_color=t["btn_accion"], command=puente_de_disparo)
    btn_inyectar.pack(side="right", fill="x", expand=True, padx=(10, 0))
    
    keyboard.add_hotkey('ctrl+comma', lambda: alternar_visibilidad_ventana())
    root.bind("<Escape>", ocultar_por_escape)
    
    root.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()