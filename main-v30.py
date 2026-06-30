import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import keyboard
import time
import threading
import sqlite3
import ctypes
import re
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

# CENTRADO ROBUSTO DE VENTANAS CON MARGEN DE SEGURIDAD
def centrar_ventana(ventana, ancho_ventana=None, alto_ventana=None):
    ventana.update_idletasks()
    ancho = ancho_ventana if ancho_ventana else ventana.winfo_width()
    alto = alto_ventana if alto_ventana else ventana.winfo_height()
    
    if ancho <= 200: ancho = 460
    if alto <= 200: alto = 560

    pantalla_ancho = ventana.winfo_screenwidth()
    pantalla_alto = ventana.winfo_screenheight()
    margen_barra_tareas = 100

    x = (pantalla_ancho // 2) - (ancho // 2)
    y = ((pantalla_alto - margen_barra_tareas) // 2) - (alto // 2)
    
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

# VALIDACIÓN Y AUTOCOMPLETADO DE COLORES HEXADECIMALES
def normalizar_y_validar_color(hex_str):
    hex_str = hex_str.strip()
    if not hex_str:
        return "#000000"
    if not hex_str.startswith('#'):
        hex_str = '#' + hex_str
    match = re.match(r'^#([A-Fa-f0-9]{3}|[A-Fa-f0-9]{6})$', hex_str)
    if match:
        return hex_str.upper()
    else:
        return None

# ==========================================
# CAPA DE DATOS E INFRAESTRUCTURA (SQLite3)
# ==========================================
def inicializar_db_y_config():
    DB_NAME = "prompts.sqlite"
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        
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
        
        # MIGRACIÓN SEGURA PARA LOS NUEVOS CAMPOS DE HOVER EN BOTONES
        columnas_nuevas = {
            "btn_exito_hover": "'#059669'",
            "btn_accion_hover": "'#0891B2'",
            "btn_peligro_hover": "'#DC2626'",
            "btn_neutral_hover": "'#374151'"
        }
        
        cursor.execute("PRAGMA table_info(temas_comerciales)")
        columnas_existentes = [col[1] for col in cursor.fetchall()]
        
        for col_name, val_defecto in columnas_nuevas.items():
            if col_name not in columnas_existentes:
                cursor.execute(f"ALTER TABLE temas_comerciales ADD COLUMN {col_name} TEXT DEFAULT {val_defecto}")
        
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tema', 'Dark Neon Vault')")
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('modo_deteccion', 'teclado')")
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('dias_purga', '30')")
        
        cursor.execute('''
            SELECT count(*) FROM temas_comerciales WHERE nombre='Dark Neon Vault'
        ''')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO temas_comerciales 
                (nombre, modo, color_base, color_texto, btn_exito, btn_accion, btn_peligro, btn_neutral, 
                 prompt_usar_borde, prompt_usar_bg, prompt_color_borde, prompt_color_bg, prompt_color_hover,
                 btn_exito_hover, btn_accion_hover, btn_peligro_hover, btn_neutral_hover)
                VALUES 
                ('Dark Neon Vault', 'dark', '#0A0E17', '#E2E8F0', '#10B981', '#06B6D4', '#EF4444', '#4B5563', 
                 1, 1, '#10B981', '#111827', '#1F2937', '#059669', '#0891B2', '#DC2626', '#374151')
            ''')
        conexion.commit()
    except sqlite3.Error as e:
        print(f"[Error DB] {e}")
    finally:
        if conexion: conexion.close()

def cargar_configuracion_global():
    global TEMA_ACTUAL, CONFIG_MODO_DETECCION, CONFIG_DIAS_PURGA, PALETAS
    try:
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM temas_comerciales")
        
        cursor.execute('''
            SELECT nombre, modo, color_base, color_texto, btn_exito, btn_accion, btn_peligro, btn_neutral, 
                   prompt_usar_borde, prompt_usar_bg, prompt_color_borde, prompt_color_bg, prompt_color_hover,
                   btn_exito_hover, btn_accion_hover, btn_peligro_hover, btn_neutral_hover
            FROM temas_comerciales
        ''')
        PALETAS = {}
        for row in cursor.fetchall():
            PALETAS[row[0]] = {
                "mode": row[1], "color_base": row[2], "color_texto": row[3], "btn_exito": row[4],
                "btn_accion": row[5], "btn_peligro": row[6], "btn_neutral": row[7], "prompt_usar_borde": int(row[8]),
                "prompt_usar_bg": int(row[9]), "prompt_color_borde": row[10], "prompt_color_bg": row[11], "prompt_color_hover": row[12],
                "btn_exito_hover": row[13] if row[13] else '#059669',
                "btn_accion_hover": row[14] if row[14] else '#0891B2',
                "btn_peligro_hover": row[15] if row[15] else '#DC2626',
                "btn_neutral_hover": row[16] if row[16] else '#374151'
            }
            
        cursor.execute("SELECT clave, valor FROM configuracion")
        for clave, valor in cursor.fetchall():
            if clave == "tema": TEMA_ACTUAL = valor if valor in PALETAS else "Dark Neon Vault"
            if clave == "modo_deteccion": CONFIG_MODO_DETECCION = valor
            if clave == "dias_purga": CONFIG_DIAS_PURGA = valor
        conn.close()
    except Exception: pass

def guardar_config_db(clave, valor):
    try:
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))
        conn.commit()
        conn.close()
    except Exception: pass

def ejecutar_purga_automatica():
    try:
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        dias = int(CONFIG_DIAS_PURGA)
        cursor.execute("DELETE FROM prompts WHERE eliminado_en IS NOT NULL AND datetime(eliminado_en) <= datetime('now', ?, 'localtime')", (f'-{dias} days',))
        conn.commit()
        conn.close()
    except Exception: pass

def obtener_texto_prompt(prompt_id):
    texto_recuperado = ""
    try:
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        cursor.execute("SELECT contenido FROM prompts WHERE id = ?", (prompt_id,))
        res = cursor.fetchone()
        if res: texto_recuperado = res[0]
        conn.close()
    except Exception: pass
    return texto_recuperado

def actualizar_cache_prompts():
    global PROMPTS_CACHE
    PROMPTS_CACHE = []
    try:
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo FROM prompts WHERE eliminado_en IS NULL ORDER BY id ASC")
        for fila in cursor.fetchall():
            PROMPTS_CACHE.append({"id": fila[0], "etiqueta": fila[1]})
        conn.close()
    except Exception: pass

def guardar_nuevo_prompt(titulo, contenido):
    try:
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO prompts (titulo, contenido) VALUES (?, ?)", (titulo, contenido))
        conn.commit()
        conn.close()
    except Exception: pass

def actualizar_prompt(prompt_id, titulo, contenido):
    try:
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        cursor.execute("UPDATE prompts SET titulo = ?, contenido = ? WHERE id = ?", (titulo, contenido, prompt_id))
        conn.commit()
        conn.close()
    except Exception: pass

def ejecutar_borrado_logico_db(prompt_id):
    try:
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE prompts SET eliminado_en = ? WHERE id = ?", (fecha_actual, prompt_id))
        conn.commit()
        conn.close()
    except Exception: pass

def ejecutar_restauracion_db(prompt_id):
    try:
        conn = sqlite3.connect("prompts.sqlite")
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

def ejecutar_disparo_dinamico(prompt_id, ocu_v=True, f_chat=False):
    def hilo_proceso():
        texto_raw = obtener_texto_prompt(prompt_id)
        if not texto_raw or not texto_raw.strip(): return
        if ocu_v: root.withdraw()
        time.sleep(0.4)
        try:
            ejecutar_inyeccion_inteligente(texto_raw, f_chat)
        except Exception: pass
        finally:
            if ocu_v:
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
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, 400, 450)
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        ctk.CTkLabel(self, text="Título del Prompt:", text_color=t["color_texto"], font=("Arial", 12, "bold")).pack(pady=(15, 2), padx=20, anchor="w")
        self.txt_titulo = ctk.CTkEntry(self, width=360)
        self.txt_titulo.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self, text="Contenido:", text_color=t["color_texto"], font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        self.txt_contenido = ctk.CTkTextbox(self, width=360, height=220)
        self.txt_contenido.pack(pady=5, padx=20, fill="both", expand=True)
        
        btn_g = ctk.CTkButton(self, text="Guardar Cambios", fg_color=t["btn_accion"], hover_color=t["btn_accion_hover"], command=self.procesar_datos)
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
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, 420, 170)
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        lbl_msg = ctk.CTkLabel(self, text=f"¿Estás seguro de enviar a la papelera el prompt?\n\n\"{titulo_prompt}\"", text_color=t["color_texto"], wraplength=380, justify="center")
        lbl_msg.pack(pady=20, padx=20)
        
        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=10)
        
        btn_cancelar = ctk.CTkButton(frame_botones, text="Cancelar", fg_color=t["btn_neutral"], hover_color=t["btn_neutral_hover"], command=self.destroy)
        btn_cancelar.pack(side="left", padx=10)
        btn_cancelar.focus_set()
        
        btn_confirmar = ctk.CTkButton(frame_botones, text="Eliminar", fg_color=t["btn_peligro"], hover_color=t["btn_peligro_hover"], command=self.confirmar)
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
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, 460, 420)
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        ctk.CTkLabel(self, text="Historial de Prompts Eliminados", text_color=t["color_texto"], font=("Arial", 14, "bold")).pack(pady=10)
        
        self.scroll_papelera = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_papelera.pack(fill="both", expand=True, padx=15, pady=10)
        
        frame_ctrl = ctk.CTkFrame(self, fg_color="transparent")
        frame_ctrl.pack(fill="x", side="bottom", pady=15, padx=15)
        
        btn_salir = ctk.CTkButton(frame_ctrl, text="Salir", fg_color=t["btn_neutral"], hover_color=t["btn_neutral_hover"], command=self.destroy)
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
            
            btn_restaurar = ctk.CTkButton(fila, text="↺ Restaurar", width=95, height=28, fg_color=t["btn_exito"], hover_color=t["btn_exito_hover"],
                                           command=lambda id_p=r_id: self.restaurar_registro(id_p))
            btn_restaurar.pack(side="right", padx=5)

    def restaurar_registro(self, prompt_id):
        ejecutar_restauracion_db(prompt_id)
        actualizar_cache_prompts()
        filtrar_prompts_ui()
        self.cargar_eliminados()

# ==========================================
# CONFIGURACIÓN: PURGA REDISEÑADA COMPACTA
# ==========================================
class VentanaConfigurarPurga(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        global CONFIG_DIAS_PURGA
        self.title("Configurar Purga Automática")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        # AJUSTE DE ALTURA ÓPTIMA (140px)
        centrar_ventana(self, 380, 140)       
        self.bind("<Escape>", lambda e: self.destroy())
        
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        frame_input = ctk.CTkFrame(self, fg_color="transparent")
        frame_input.pack(fill="x", pady=(15, 5), padx=20)
        
        ctk.CTkLabel(frame_input, text="Días de retención antes de borrar:", text_color=t["color_texto"], font=("Arial", 12)).pack(side="left", padx=5)
        
        self.entry_dias = ctk.CTkEntry(frame_input, width=80, justify="center")
        self.entry_dias.pack(side="right", padx=5)
        self.entry_dias.insert(0, CONFIG_DIAS_PURGA)
        
        # LÍNEA DE BOTONES: ACCIÓN Y SALIDA
        frame_btns = ctk.CTkFrame(self, fg_color="transparent")
        frame_btns.pack(fill="x", side="bottom", pady=15, padx=25)
        
        btn_salir = ctk.CTkButton(frame_btns, text="Salir", fg_color=t["btn_neutral"], hover_color=t["btn_neutral_hover"], width=100, command=self.destroy)
        btn_salir.pack(side="right", padx=(10, 0))
        
        btn_g = ctk.CTkButton(frame_btns, text="Guardar Plazo", fg_color=t["btn_exito"], hover_color=t["btn_exito_hover"], width=120, command=self.guardar_plazo)
        btn_g.pack(side="right")

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
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, 390, 340)
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
        
        btn_salir = ctk.CTkButton(frame_btns, text="Salir", fg_color=t["btn_neutral"], hover_color=t["btn_neutral_hover"], width=100, command=self.destroy)
        btn_salir.pack(side="right", padx=(10, 0))
        
        btn_aceptar = ctk.CTkButton(frame_btns, text="Aceptar", fg_color=t["btn_accion"], hover_color=t["btn_accion_hover"], width=100, command=self.confirmar_guardado)
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
# CRUD DE TEMAS COMERCIALES AVANZADO v30
# ==========================================
class VentanaCrudTemas(ctk.CTkToplevel):
    def __init__(self, master, callback_recargar_menu, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.callback_recargar_menu = callback_recargar_menu
        self.title("Administrar Temas Avanzado")
        self.transient(master)
        self.grab_set()
        
        centrar_ventana(self, 960, 680)
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.id_tema_seleccionado = None
        self.visualizadores = {}  
        t = PALETAS[TEMA_ACTUAL]
        self.configure(fg_color=t["color_base"])
        
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)
        
        panel_izquierdo = ctk.CTkFrame(self, fg_color="transparent")
        panel_izquierdo.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        frame_form = ctk.CTkScrollableFrame(panel_izquierdo)
        frame_form.pack(fill="both", expand=True, pady=(0, 10))
        
        ctk.CTkLabel(frame_form, text="Paleta Atómica de Componentes", font=("Arial", 13, "bold")).pack(pady=5)
        
        def crear_input_color(parent, label_text, placeholder, clave_ref):
            ctk.CTkLabel(parent, text=label_text, font=("Arial", 10, "bold") if "Color" not in label_text else None).pack(anchor="w", padx=10, pady=(5,0))
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=2)
            
            ent = ctk.CTkEntry(f, placeholder_text=placeholder)
            ent.pack(side="left", fill="x", expand=True)
            ent.bind("<KeyRelease>", lambda e: self.actualizar_muestra_desde_texto(clave_ref))
            
            preview = ctk.CTkLabel(f, text="", width=24, height=24, corner_radius=4, fg_color="#1E293B")
            preview.pack(side="left", padx=5)
            self.visualizadores[clave_ref] = preview
            
            btn = ctk.CTkButton(f, text="🎨", width=32, fg_color=t["btn_neutral"], hover_color=t["btn_neutral_hover"], command=lambda: self.invocar_selector_color(ent, clave_ref))
            btn.pack(side="right")
            return ent

        ctk.CTkLabel(frame_form, text="Nombre del Tema:").pack(anchor="w", padx=10)
        self.ent_nombre = ctk.CTkEntry(frame_form)
        self.ent_nombre.pack(fill="x", padx=10, pady=2)
        
        self.ent_base = crear_input_color(frame_form, "Color Base (Fondo Ventana):", "#0A0E17", "base")
        self.ent_texto = crear_input_color(frame_form, "Color Texto General:", "#E2E8F0", "texto")
        
        # SECCIÓN DINÁMICA: COLORES BASE Y HOVERS DE BOTONES INTERACTIVOS
        self.ent_exito = crear_input_color(frame_form, "Color Éxito (Nuevo, Guardar):", "#10B981", "exito")
        self.ent_exito_hover = crear_input_color(frame_form, "↳ Color Éxito al pasar Mouse:", "#059669", "exito_hover")
        
        self.ent_accion = crear_input_color(frame_form, "Color Acción (Inyectar, Activo):", "#06B6D4", "accion")
        self.ent_accion_hover = crear_input_color(frame_form, "↳ Color Acción al pasar Mouse:", "#0891B2", "accion_hover")
        
        self.ent_peligro = crear_input_color(frame_form, "Color Peligro (Eliminar):", "#EF4444", "peligro")
        self.ent_peligro_hover = crear_input_color(frame_form, "↳ Color Peligro al pasar Mouse:", "#DC2626", "peligro_hover")
        
        self.ent_neutral = crear_input_color(frame_form, "Color Neutral (Salir, Editar):", "#4B5563", "neutral")
        self.ent_neutral_hover = crear_input_color(frame_form, "↳ Color Neutral al pasar Mouse:", "#374151", "neutral_hover")
        
        ctk.CTkLabel(frame_form, text="Diseño Contenedor Listado (Tarjetas)", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(8,2))
        self.chk_borde = ctk.CTkCheckBox(frame_form, text="Habilitar Contorno/Borde")
        self.chk_borde.pack(anchor="w", padx=10, pady=2)
        
        self.chk_bg = ctk.CTkCheckBox(frame_form, text="Habilitar Fondo (Background)")
        self.chk_bg.pack(anchor="w", padx=10, pady=2)
        
        self.ent_p_borde = crear_input_color(frame_form, "Color del Contorno:", "#10B981", "p_borde")
        self.ent_p_bg = crear_input_color(frame_form, "Color del Fondo Tarjeta:", "#111827", "p_bg")
        self.ent_p_hover = crear_input_color(frame_form, "Color Hover (Al pasar el ratón):", "#1F2937", "p_hover")
        
        self.btn_guardar = ctk.CTkButton(frame_form, text="Registrar Tema", fg_color=t["btn_exito"], hover_color=t["btn_exito_hover"], command=self.guardar_tema)
        self.btn_guardar.pack(fill="x", padx=10, pady=10)
        
        btn_l = ctk.CTkButton(frame_form, text="Limpiar / Nuevo", fg_color=t["btn_neutral"], hover_color=t["btn_neutral_hover"], command=self.limpiar_formulario)
        btn_l.pack(fill="x", padx=10, pady=2)
        
        self.btn_eliminar = ctk.CTkButton(frame_form, text="Eliminar Tema", fg_color=t["btn_peligro"], hover_color=t["btn_peligro_hover"], command=self.eliminar_tema)
        self.btn_eliminar.pack(fill="x", padx=10, pady=5)
        self.btn_eliminar.configure(state="disabled")

        frame_barra_inferior = ctk.CTkFrame(panel_izquierdo, fg_color="transparent")
        frame_barra_inferior.pack(fill="x", side="bottom", pady=5)
        
        self.btn_salir = ctk.CTkButton(frame_barra_inferior, text="Salir", fg_color=t["btn_neutral"], hover_color=t["btn_neutral_hover"], command=self.destroy)
        self.btn_salir.pack(side="right", padx=10)
        
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

    def invocar_selector_color(self, entry_widget, clave_ref):
        color_actual = entry_widget.get().strip()
        if not color_actual.startswith("#"): color_actual = None
        color_elegido = colorchooser.askcolor(title="Selecciona un color", initialcolor=color_actual)
        if color_elegido[1]:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, color_elegido[1])
            self.visualizadores[clave_ref].configure(fg_color=color_elegido[1])

    def actualizar_muestra_desde_texto(self, clave_ref):
        try:
            val_txt = ""
            if clave_ref == "base": val_txt = self.ent_base.get()
            elif clave_ref == "texto": val_txt = self.ent_texto.get()
            elif clave_ref == "exito": val_txt = self.ent_exito.get()
            elif clave_ref == "exito_hover": val_txt = self.ent_exito_hover.get()
            elif clave_ref == "accion": val_txt = self.ent_accion.get()
            elif clave_ref == "accion_hover": val_txt = self.ent_accion_hover.get()
            elif clave_ref == "peligro": val_txt = self.ent_peligro.get()
            elif clave_ref == "peligro_hover": val_txt = self.ent_peligro_hover.get()
            elif clave_ref == "neutral": val_txt = self.ent_neutral.get()
            elif clave_ref == "neutral_hover": val_txt = self.ent_neutral_hover.get()
            elif clave_ref == "p_borde": val_txt = self.ent_p_borde.get()
            elif clave_ref == "p_bg": val_txt = self.ent_p_bg.get()
            elif clave_ref == "p_hover": val_txt = self.ent_p_hover.get()
            
            color_valido = normalizar_y_validar_color(val_txt)
            if color_valido:
                self.visualizadores[clave_ref].configure(fg_color=color_valido)
        except Exception: pass

    def refrescar_todos_los_visualizadores(self):
        for clave in self.visualizadores.keys():
            self.actualizar_muestra_desde_texto(clave)

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
            
            # Cargar los hovers dinámicos mapeando las nuevas posiciones de la tupla
            self.ent_exito_hover.delete(0, tk.END); self.ent_exito_hover.insert(0, r[14] if r[14] else '#059669')
            self.ent_accion_hover.delete(0, tk.END); self.ent_accion_hover.insert(0, r[15] if r[15] else '#0891B2')
            self.ent_peligro_hover.delete(0, tk.END); self.ent_peligro_hover.insert(0, r[16] if r[16] else '#DC2626')
            self.ent_neutral_hover.delete(0, tk.END); self.ent_neutral_hover.insert(0, r[17] if r[17] else '#374151')
            
            self.btn_guardar.configure(text="Actualizar Configuración")
            self.btn_eliminar.configure(state="normal")
            self.refrescar_todos_los_visualizadores()

    def limpiar_formulario(self):
        self.id_tema_seleccionado = None
        self.ent_nombre.delete(0, tk.END)
        self.ent_base.delete(0, tk.END)
        self.ent_texto.delete(0, tk.END)
        self.ent_exito.delete(0, tk.END)
        self.ent_exito_hover.delete(0, tk.END)
        self.ent_accion.delete(0, tk.END)
        self.ent_accion_hover.delete(0, tk.END)
        self.ent_peligro.delete(0, tk.END)
        self.ent_peligro_hover.delete(0, tk.END)
        self.ent_neutral.delete(0, tk.END)
        self.ent_neutral_hover.delete(0, tk.END)
        self.chk_borde.select()
        self.chk_bg.select()
        self.ent_p_borde.delete(0, tk.END)
        self.ent_p_bg.delete(0, tk.END)
        self.ent_p_hover.delete(0, tk.END)
        self.btn_guardar.configure(text="Registrar Tema")
        self.btn_eliminar.configure(state="disabled")
        for preview in self.visualizadores.values(): preview.configure(fg_color="#1E293B")

    def guardar_tema(self):
        nombre = self.ent_nombre.get().strip()
        if not nombre:
            messagebox.showerror("Error", "El nombre del tema es obligatorio.")
            return

        inputs = {
            "base": self.ent_base.get(), "texto": self.ent_texto.get(), "exito": self.ent_exito.get(),
            "exito_hover": self.ent_exito_hover.get(), "accion": self.ent_accion.get(), "accion_hover": self.ent_accion_hover.get(),
            "peligro": self.ent_peligro.get(), "peligro_hover": self.ent_peligro_hover.get(), "neutral": self.ent_neutral.get(),
            "neutral_hover": self.ent_neutral_hover.get(), "p_borde": self.ent_p_borde.get(), "p_bg": self.ent_p_bg.get(), "p_hover": self.ent_p_hover.get()
        }

        valores_validados = {}
        for clave, valor in inputs.items():
            validado = normalizar_y_validar_color(valor)
            if not validado:
                messagebox.showerror("Color Inválido", f"El color para '{clave}' no es hexadecimal válido.")
                return
            valores_validados[clave] = validado

        borde_flag = 1 if self.chk_borde.get() else 0
        bg_flag = 1 if self.chk_bg.get() else 0
        
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        
        if self.id_tema_seleccionado:
            cursor.execute('''
                UPDATE temas_comerciales SET nombre=?, color_base=?, color_texto=?, btn_exito=?, btn_accion=?, 
                                             btn_peligro=?, btn_neutral=?, prompt_usar_borde=?, prompt_usar_bg=?, 
                                             prompt_color_borde=?, prompt_color_bg=?, prompt_color_hover=?,
                                             btn_exito_hover=?, btn_accion_hover=?, btn_peligro_hover=?, btn_neutral_hover=? WHERE id=?
            ''', (nombre, valores_validados["base"], valores_validados["texto"], valores_validados["exito"], 
                  valores_validados["text" if "accion" not in valores_validados else "accion"], valores_validados["peligro"], valores_validados["neutral"], 
                  borde_flag, bg_flag, valores_validados["p_borde"], valores_validados["p_bg"], valores_validados["p_hover"],
                  valores_validados["exito_hover"], valores_validados["accion_hover"], valores_validados["peligro_hover"], valores_validados["neutral_hover"], self.id_tema_seleccionado))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO temas_comerciales 
                (nombre, modo, color_base, color_texto, btn_exito, btn_accion, btn_peligro, btn_neutral, prompt_usar_borde, 
                 prompt_usar_bg, prompt_color_borde, prompt_color_bg, prompt_color_hover, btn_exito_hover, btn_accion_hover, btn_peligro_hover, btn_neutral_hover)
                VALUES (?, 'dark', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, valores_validados["base"], valores_validados["texto"], valores_validados["exito"], 
                  valores_validados["accion"], valores_validados["peligro"], valores_validados["neutral"], 
                  borde_flag, bg_flag, valores_validados["p_borde"], valores_validados["p_bg"], valores_validados["p_hover"],
                  valores_validados["exito_hover"], valores_validados["accion_hover"], valores_validados["peligro_hover"], valores_validados["neutral_hover"]))
        
        conn.commit()
        conn.close()
        
        guardar_config_db("tema", nombre)
        cargar_configuracion_global()
        cambiar_tema_aplicacion(nombre)
        
        self.callback_recargar_menu()
        self.actualizar_tabla_ui()
        self.limpiar_formulario()
        filtrar_prompts_ui()

    def eliminar_tema(self):
        if not self.id_tema_seleccionado: return
        nombre_tema = self.ent_nombre.get().strip()
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
# INTERFAZ Y LOGICA COMPLEMENTARIA
# ==========================================
def seleccionar_prompt(id_seleccionado, frame_asociado, frame_contenedor):
    global id_prompt_actual
    id_prompt_actual = id_seleccionado
    t = PALETAS[TEMA_ACTUAL]
    
    for child in frame_contenedor.winfo_children():
        if isinstance(child, ctk.CTkFrame):
            orig_bg = t["prompt_color_bg"] if t["prompt_usar_bg"] else t["color_base"]
            child.configure(fg_color=orig_bg)
            # Retornar el texto de las otras tarjetas a su color normal
            for widget in child.winfo_children():
                if isinstance(widget, ctk.CTkLabel) and widget.cget("text") != "✕" and widget.cget("text") != "✎":
                    widget.configure(text_color=t["color_texto"])
            
    frame_asociado.configure(fg_color="#1E293B")
    
    # DINÁMICA DE SELECCIÓN: Cambiar color del título al seleccionarlo
    for widget in frame_asociado.winfo_children():
        if isinstance(widget, ctk.CTkLabel) and widget.cget("text") != "✕" and widget.cget("text") != "✎":
            widget.configure(text_color=t["prompt_color_borde"])

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
        
        b_width = 2 if t["prompt_usar_borde"] else 0
        b_color = t["prompt_color_borde"] if t["prompt_usar_borde"] else None
        card_bg = t["prompt_color_bg"] if t["prompt_usar_bg"] else t["color_base"]
        card_hover = t.get("prompt_color_hover", "#1F2937")
        
        color_inicial = "#1E293B" if id_prompt_actual == reg_id else card_bg
        color_texto_inicial = t["prompt_color_borde"] if id_prompt_actual == reg_id else t["color_texto"]
        
        card_frame = ctk.CTkFrame(frame_lista_global, fg_color=color_inicial, border_width=b_width, border_color=b_color, corner_radius=8)
        card_frame.pack(fill="x", pady=4, padx=5)
        
        lbl_titulo = ctk.CTkLabel(card_frame, text=reg_titulo, text_color=color_texto_inicial, font=("Arial", 12, "bold"), anchor="w", cursor="hand2")
        lbl_titulo.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        
        # DINÁMICA DE HOVER: Cambiar fondo y color del texto al pasar el ratón
        def al_entrar_mouse(e, frm=card_frame, lbl=lbl_titulo, hover_c=card_hover, r_id=reg_id):
            frm.configure(fg_color=hover_c)
            if id_prompt_actual != r_id:
                lbl.configure(text_color=t["prompt_color_borde"])

        def al_salir_mouse(e, r_id=reg_id, frm=card_frame, lbl=lbl_titulo, def_bg=card_bg):
            if id_prompt_actual == r_id:
                frm.configure(fg_color="#1E293B")
                lbl.configure(text_color=t["prompt_color_borde"])
            else:
                frm.configure(fg_color=def_bg)
                lbl.configure(text_color=t["color_texto"])

        card_frame.bind("<Enter>", al_entrar_mouse)
        card_frame.bind("<Leave>", al_salir_mouse)
        lbl_titulo.bind("<Enter>", al_entrar_mouse)
        lbl_titulo.bind("<Leave>", al_salir_mouse)
        
        # EVENTOS COMBINADOS: UN SOLO CLIC SELECCIONA, DOBLE CLIC INYECTA
        card_frame.bind("<Button-1>", lambda e, r_id=reg_id, f=card_frame: seleccionar_prompt(r_id, f, frame_lista_global))
        lbl_titulo.bind("<Button-1>", lambda e, r_id=reg_id, f=card_frame: seleccionar_prompt(r_id, f, frame_lista_global))
        
        # IMPLEMENTACIÓN DE DOBLE CLIC AUTOMÁTICO EN EL TÍTULO Y TARJETA
        card_frame.bind("<Double-Button-1>", lambda e, r_id=reg_id: ejecutar_disparo_dinamico(r_id, ocu_v=True))
        lbl_titulo.bind("<Double-Button-1>", lambda e, r_id=reg_id: ejecutar_disparo_dinamico(r_id, ocu_v=True))
        
        btn_edit = ctk.CTkButton(card_frame, text="✎", width=32, height=26, fg_color=t["btn_neutral"], hover_color=t["btn_neutral_hover"],
                                 command=lambda r_id=reg_id: abrir_editor_directo(r_id))
        btn_edit.pack(side="left", padx=2)
        
        btn_del = ctk.CTkButton(card_frame, text="✕", width=32, height=26, fg_color=t["btn_peligro"], hover_color=t["btn_peligro_hover"],
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
            btn_nuevo.configure(fg_color=t["btn_exito"], hover_color=t["btn_exito_hover"])
            btn_inyectar.configure(fg_color=t["btn_accion"], hover_color=t["btn_accion_hover"])
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
        ejecutar_disparo_dinamico(id_prompt_actual, ocu_v=True)

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
    root.title("PromptVault Premium v30")
    
    centrar_ventana(root, 460, 560)
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
    
    btn_nuevo = ctk.CTkButton(frame_acciones, text="[+] Nuevo Prompt", fg_color=t["btn_exito"], hover_color=t["btn_exito_hover"], width=140, command=abrir_creador)
    btn_nuevo.pack(side="left")
    
    btn_inyectar = ctk.CTkButton(frame_acciones, text="Inyectar Selección", fg_color=t["btn_accion"], hover_color=t["btn_accion_hover"], command=puente_de_disparo)
    btn_inyectar.pack(side="right", fill="x", expand=True, padx=(10, 0))
    
    keyboard.add_hotkey('ctrl+comma', lambda: alternar_visibilidad_ventana())
    root.bind("<Escape>", ocultar_por_escape)
    
    root.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()