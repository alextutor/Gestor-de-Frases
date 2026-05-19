import customtkinter as ctk
import sqlite3
import re
import time
import keyboard
import pygetwindow as gw
import ctypes
from tkinter import messagebox

# --- CONFIGURACIÓN DE ESTILO (de v1) ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    pantalla_ancho = ventana.winfo_screenwidth()
    pantalla_alto = ventana.winfo_screenheight()
    x = (pantalla_ancho // 2) - (ancho // 2)
    y = (pantalla_alto // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

# --- MOTOR DE ENFOQUE BAJO NIVEL (de v4) ---
def forzar_foco_ventana(lista_objetivos):
    """Busca y obliga a la ventana a estar al frente."""
    try:
        todas_las_ventanas = gw.getAllTitles()
        for titulo_ventana in todas_las_ventanas:
            for objetivo in lista_objetivos:
                if objetivo.lower() in titulo_ventana.lower():
                    win = gw.getWindowsWithTitle(titulo_ventana)[0]
                    if win.isMinimized:
                        win.restore()
                    # Uso de API de Windows para foco real
                    hwnd = win._hWnd
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    return True
    except Exception as e:
        print(f"Error de enfoque: {e}")
    return False

# --- VENTANA: GESTIONAR VARIABLES / EDITAR (de v1) ---
class VentanaVariables(ctk.CTkToplevel):
    def __init__(self, parent, datos_prompt, callback_actualizar):
        super().__init__(parent)
        self.id_p, self.titulo, self.contenido = datos_prompt
        self.callback_actualizar = callback_actualizar
        
        ancho, alto = 480, 620
        self.title(f"Gestionar: {self.titulo}")
        centrar_ventana(self, ancho, alto)
        
        self.attributes("-topmost", True)
        self.transient(parent)  
        self.grab_set()         
        self.focus_force()      
        
        self.entradas_dinamicas = {}
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.tab_copiar = self.tabview.add("Rellenar y Enviar")
        self.tab_editar = self.tabview.add("Editar / Eliminar")

        self.setup_tab_copiar()
        self.setup_tab_editar()

    def setup_tab_copiar(self):
        ctk.CTkLabel(self.tab_copiar, text=self.titulo, font=("Segoe UI", 18, "bold")).pack(pady=10)
        frame = ctk.CTkScrollableFrame(self.tab_copiar, fg_color="transparent")
        frame.pack(pady=10, padx=10, fill="both", expand=True)

        variables = re.findall(r"\{\{(.*?)\}\}", self.contenido)
        for var in variables:
            ctk.CTkLabel(frame, text=f"{var.upper()}", font=("Segoe UI", 11, "bold"), text_color="#3b8ed0").pack(pady=(10, 0), anchor="w", padx=15)
            entry = ctk.CTkEntry(frame, placeholder_text=f"Ingresar {var}...", height=35, corner_radius=10)
            entry.pack(pady=(2, 10), fill="x", padx=10)
            self.entradas_dinamicas[var] = entry

        # Botón actualizado para ENVIAR directamente (como en v4)
        ctk.CTkButton(self.tab_copiar, text="ENVIAR A LA APP", height=45, corner_radius=10,
                      font=("Segoe UI", 13, "bold"), command=self.procesar_y_enviar).pack(pady=20, padx=20, fill="x")

    def setup_tab_editar(self):
        ctk.CTkLabel(self.tab_editar, text="Título:", font=("Segoe UI", 12)).pack(pady=(10,0), padx=20, anchor="w")
        self.edit_titulo = ctk.CTkEntry(self.tab_editar, corner_radius=10)
        self.edit_titulo.insert(0, self.titulo)
        self.edit_titulo.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(self.tab_editar, text="Contenido:", font=("Segoe UI", 12)).pack(pady=(10,0), padx=20, anchor="w")
        self.edit_contenido = ctk.CTkTextbox(self.tab_editar, corner_radius=10, border_width=1)
        self.edit_contenido.insert("1.0", self.contenido)
        self.edit_contenido.pack(fill="both", padx=20, pady=10, expand=True)

        ctk.CTkButton(self.tab_editar, text="GUARDAR CAMBIOS", fg_color="#1f6aa5", height=35, command=self.actualizar_db).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.tab_editar, text="ELIMINAR", fg_color="#a33333", height=35, command=self.eliminar_db).pack(pady=10, padx=20, fill="x")

    def procesar_y_enviar(self):
        resultado = self.contenido
        for var, entry in self.entradas_dinamicas.items():
            resultado = resultado.replace(f"{{{{{var}}}}}", entry.get())
        # Llamamos al método de escritura del padre (v4 logic)[cite: 5]
        self.master.auto_escribir(resultado)
        self.destroy()

    def actualizar_db(self):
        conn = sqlite3.connect('prompts.sqlite')
        conn.cursor().execute("UPDATE prompts SET titulo = ?, contenido = ? WHERE id = ?", 
                             (self.edit_titulo.get(), self.edit_contenido.get("1.0", "end-1c"), self.id_p))
        conn.commit()
        conn.close()
        self.callback_actualizar()
        self.destroy()

    def eliminar_db(self):
        if messagebox.askyesno("Confirmar", "¿Eliminar este prompt?"):
            conn = sqlite3.connect('prompts.sqlite')
            conn.cursor().execute("DELETE FROM prompts WHERE id = ?", (self.id_p,))
            conn.commit()
            conn.close()
            self.callback_actualizar()
            self.destroy()

# --- VENTANA: CREAR NUEVO PROMPT (de v1) ---
class VentanaNuevoPrompt(ctk.CTkToplevel):
    def __init__(self, parent, callback_actualizar):
        super().__init__(parent)
        ancho, alto = 500, 600
        self.title("Nuevo Prompt")
        centrar_ventana(self, ancho, alto)
        self.attributes("-topmost", True)
        self.transient(parent) 
        self.grab_set()
        self.focus_force()
        self.callback_actualizar = callback_actualizar

        ctk.CTkLabel(self, text="NUEVO PROMPT", font=("Segoe UI", 20, "bold")).pack(pady=20)
        
        self.entry_titulo = ctk.CTkEntry(self, placeholder_text="Título...", height=40, corner_radius=10)
        self.entry_titulo.pack(fill="x", padx=30, pady=10)
        
        self.txt_contenido = ctk.CTkTextbox(self, height=300, corner_radius=10, border_width=1)
        self.txt_contenido.pack(fill="both", padx=30, pady=10)

        # --- CONTENEDOR DE BOTONES ---
        self.frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botones.pack(pady=20, padx=30, fill="x")

        # Botón CANCELAR
        self.btn_cancelar = ctk.CTkButton(
            self.frame_botones, 
            text="CANCELAR", 
            fg_color="#6c757d", 
            hover_color="#5a6268", 
            command=self.destroy
        )
        self.btn_cancelar.pack(side="left", padx=(0, 10), expand=True, fill="x")

        # Botón GUARDAR
        self.btn_guardar = ctk.CTkButton(
            self.frame_botones, 
            text="GUARDAR", 
            fg_color="#28a745", 
            hover_color="#218838", 
            command=self.guardar_db
        )
        self.btn_guardar.pack(side="left", padx=(10, 0), expand=True, fill="x")
        

    def guardar_db(self):
        t, c = self.entry_titulo.get(), self.txt_contenido.get("1.0", "end-1c")
        if t and c:
            conn = sqlite3.connect('prompts.sqlite')
            conn.cursor().execute("INSERT INTO prompts (titulo, contenido) VALUES (?, ?)", (t, c))
            conn.commit()
            conn.close()
            self.callback_actualizar()
            self.destroy()

# --- CLASE PRINCIPAL ---
class PromptVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ancho, alto = 480, 600
        self.title("PromptVault Universal v6")
        centrar_ventana(self, ancho, alto)
        self.attributes("-topmost", True)
        self.configure(fg_color="#121212")

        # Lista de objetivos de v4[cite: 5]
        self.apps_compatibles = [
            "Google Gemini", "Claude", "ChatGPT", "Notepad", 
            "Bloc de notas", "Word", "Discord", "WhatsApp" , "z.ai" 
        ]

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filtrar_prompts)

        ctk.CTkLabel(self, text="PROMPT VAULT", font=("Segoe UI", 24, "bold")).pack(pady=(25, 20))
        self.entry_search = ctk.CTkEntry(self, placeholder_text="🔍 Buscar...", textvariable=self.search_var, height=40, corner_radius=20)
        self.entry_search.pack(pady=10, padx=30, fill="x")

        self.scroll_lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_lista.pack(pady=10, padx=20, fill="both", expand=True)

        self.btn_add = ctk.CTkButton(self, text="+", width=56, height=56, corner_radius=28,
                                     font=("Segoe UI", 28), command=lambda: VentanaNuevoPrompt(self, self.cargar_prompts_desde_db))
        self.btn_add.place(relx=0.88, rely=0.9, anchor="center")

        self.cargar_prompts_desde_db()

        # Registrar el atajo global Alt + .
        keyboard.add_hotkey('alt+.', self.alternar_ventana)

    def alternar_ventana(self):
        """Muestra la ventana si está oculta/minimizada, o la oculta si está visible."""
        if self.state() == "iconic" or not self.winfo_viewable():
            self.deiconify()
            self.attributes("-topmost", True)
            self.focus_force()
        else:
            self.iconify()

            
    def cargar_prompts_desde_db(self):
        # --- NUEVO BLOQUE DE SEGURIDAD ---
        conn = sqlite3.connect('prompts.sqlite')
        cursor = conn.cursor()
        # Esto crea la tabla si el archivo es nuevo o está vacío
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        # ---------------------------------
        
        self.actualizar_ui_lista("SELECT id, titulo, contenido FROM prompts ORDER BY titulo ASC")

    def filtrar_prompts(self, *args):
        self.actualizar_ui_lista(f"SELECT id, titulo, contenido FROM prompts WHERE titulo LIKE '%{self.search_var.get()}%' ORDER BY titulo ASC")

    def actualizar_ui_lista(self, query):
        for w in self.scroll_lista.winfo_children(): w.destroy()
        conn = sqlite3.connect('prompts.sqlite')
        cursor = conn.cursor()
        cursor.execute(query)
        for row in cursor.fetchall():
            f = ctk.CTkFrame(self.scroll_lista, fg_color="#1e1e1e", corner_radius=12)
            f.pack(fill="x", pady=4, padx=5)
            
            btn_titulo = ctk.CTkButton(f, text=row[1], height=40, corner_radius=10,
                               fg_color="transparent", hover_color="#2a2a2a", 
                               anchor="w", font=("Segoe UI", 12),
                               command=lambda c=row[2]: self.auto_escribir(c))
            btn_titulo.pack(side="left", fill="x", expand=True, padx=(10, 0))
            
            btn_editar = ctk.CTkButton(f, text="✎", width=30, height=30, corner_radius=8,
                               fg_color="transparent", hover_color="#333333",
                               font=("Segoe UI", 14),
                               command=lambda r=row: VentanaVariables(self, r, self.cargar_prompts_desde_db))
            btn_editar.pack(side="right", padx=(0, 10))
        conn.close()

    def auto_escribir(self, texto):
        """MOTOR EXACTO DE v4: Enfocar y escribir sin usar mouse[cite: 5]."""
        # 1. Minimizar gestor
        self.iconify()
        time.sleep(0.5)

        # 2. Buscar ventana y forzar foco (Lógica de v4)[cite: 5]
        if forzar_foco_ventana(self.apps_compatibles):
            time.sleep(0.6) # Pausa necesaria para que el sistema asuma el foco[cite: 5]
            try:
                # 3. Limpiar estados previos y escribir (Lógica de v4)[cite: 5]
                keyboard.release('ctrl')
                keyboard.release('shift')
                keyboard.write(texto, delay=0.01) # Escritura de bajo nivel[cite: 5]
            except Exception as e:
                print(f"Error al escribir: {e}")
        else:
            # Si no hay ninguna app abierta, escribe donde esté el foco actual
            keyboard.write(texto, delay=0.01)

if __name__ == "__main__":
    app = PromptVaultApp()
    app.mainloop()