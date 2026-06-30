import tkinter as tk
import customtkinter as ctk
import sqlite3
from datetime import datetime

# Configuración inicial de la interfaz
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PromptVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PromptVault - Asistente de Inyección de Frases v23")
        self.geometry("700x500")
        
        # Inicializar Base de Datos y realizar migración si es necesario
        self.inicializar_db()
        
        # Caché de memoria para búsqueda reactiva
        self.cache_prompts = []
        
        # Contenedor de la interfaz principal
        self.init_ui()
        
        # Cargar datos por primera vez
        self.cargar_cache_y_refrescar()

    def inicializar_db(self):
        self.conn = sqlite3.connect("prompts.sqlite")
        self.cursor = self.conn.cursor()
        
        # Crear tabla si no existe
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL,
                eliminado_en TEXT DEFAULT NULL
            )
        ''')
        
        # Migración: Verificar si la columna 'eliminado_en' ya existe
        self.cursor.execute("PRAGMA table_info(prompts)")
        columnas = [col[1] for col in self.cursor.fetchall()]
        if "eliminado_en" not in columnas:
            self.cursor.execute("ALTER TABLE prompts ADD COLUMN eliminado_en TEXT DEFAULT NULL")
            self.conn.commit()
            
        # Creación del índice parcial optimizado para registros activos
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prompts_activos 
            ON prompts(id) WHERE eliminado_en IS NULL
        ''')
        self.conn.commit()

    def init_ui(self):
        # Barra superior de búsqueda
        self.frame_top = ctk.CTkFrame(self, height=50)
        self.frame_top.pack(fill="x", padx=10, pady=5)
        
        self.lbl_buscar = ctk.CTkLabel(self.frame_top, text="Buscar:")
        self.lbl_buscar.pack(side="left", padx=5)
        
        self.entry_buscar = ctk.CTkEntry(self.frame_top, placeholder_text="Escribe para filtrar en tiempo real...")
        self.entry_buscar.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_buscar.bind("<KeyRelease>", self.filtrar_prompts)
        
        # Lista de prompts (Scrollable Frame)
        self.frame_lista = ctk.CTkScrollableFrame(self, label_text="Lista de Prompts Activos")
        self.frame_lista.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Guardar referencias de los widgets dinámicos mapeados por ID de prompt
        self.widgets_prompts = {}

    def cargar_cache_y_refrescar(self):
        # Leer únicamente los registros donde eliminado_en es NULL
        self.cursor.execute("SELECT id, titulo, contenido FROM prompts WHERE eliminado_en IS NULL")
        self.cache_prompts = [{"id": r[0], "titulo": r[1], "contenido": r[2]} for r in self.cursor.fetchall()]
        self.renderizar_lista(self.cache_prompts)

    def renderizar_lista(self, lista_datos):
        # Limpiar widgets previos
        for widget in self.frame_lista.winfo_children():
            widget.destroy()
        self.widgets_prompts.clear()
        
        for item in lista_datos:
            item_id = item["id"]
            
            # Contenedor por cada fila de prompt
            row_frame = ctk.CTkFrame(self.frame_lista)
            row_frame.pack(fill="x", pady=2, padx=5)
            
            lbl_title = ctk.CTkLabel(row_frame, text=item["titulo"], font=("Arial", 12, "bold"), anchor="w")
            lbl_title.pack(side="left", fill="x", expand=True, padx=10)
            
            # Botón de eliminación con estilo de alerta / cruz [✕]
            btn_eliminar = ctk.CTkButton(
                row_frame, 
                text="[✕] Eliminar", 
                width=80, 
                fg_color="#D32F2F", 
                hover_color="#B71C1C",
                command=lambda id_p=item_id, tit=item["titulo"]: self.abrir_modal_confirmacion(id_p, tit)
            )
            btn_eliminar.pack(side="right", padx=5, pady=2)
            
            # Guardamos la referencia del contenedor de la fila para poder destruirlo directamente
            self.widgets_prompts[item_id] = row_frame

    def filtrar_prompts(self, event):
        termino = self.entry_buscar.get().lower()
        if not termino:
            self.renderizar_lista(self.cache_prompts)
            return
            
        # Filtrado reactivo directo sobre la caché en memoria
        filtrados = [p for p in self.cache_prompts if termino in p["titulo"].lower() or termino in p["contenido"].lower()]
        self.renderizar_lista(filtrados)

    def abrir_modal_confirmacion(self, prompt_id, titulo_prompt):
        # Ventana modal CustomTkinter (Sub-ventana de confirmación)
        modal = ctk.CTkToplevel(self)
        modal.title("Confirmar Eliminación Segura")
        modal.geometry("420x180")
        modal.resizable(False, False)
        
        # Bloquear foco en la sub-ventana modal
        modal.grab_set()
        modal.transient(self)
        
        # Centrar relativo a la ventana principal
        x = self.winfo_x() + (self.winfo_width() // 2) - 210
        y = self.winfo_y() + (self.winfo_height() // 2) - 90
        modal.geometry(f"+{x}+{y}")
        
        # Mensajes e interfaz interna de la modal
        lbl_msg = ctk.CTkLabel(
            modal, 
            text=f"¿Estás seguro de que deseas enviar a la papelera el prompt?\n\n\"{titulo_prompt}\"",
            wraplength=380, 
            justify="center",
            font=("Arial", 11)
        )
        lbl_msg.pack(pady=20, padx=20)
        
        frame_botones = ctk.CTkFrame(modal, fg_color="transparent")
        frame_botones.pack(pady=10)
        
        # Botón de Cancelar con foco por defecto para mayor seguridad
        btn_cancelar = ctk.CTkButton(
            frame_botones, 
            text="Cancelar", 
            fg_color="#555555", 
            hover_color="#444444",
            command=modal.destroy
        )
        btn_cancelar.pack(side="left", padx=10)
        btn_cancelar.focus_set()
        
        # Botón de Confirmar Eliminación (Borrado Lógico)
        btn_confirmar = ctk.CTkButton(
            frame_botones, 
            text="Eliminar (Borrado Lógico)", 
            fg_color="#D32F2F", 
            hover_color="#B71C1C",
            command=lambda: self.ejecutar_borrado_logico(prompt_id, modal)
        )
        btn_confirmar.pack(side="left", padx=10)

    def ejecutar_borrado_logico(self, prompt_id, modal_window):
        try:
            # 1. Actualización en Base de Datos (Marcado Lógico con timestamp ISO)
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("UPDATE prompts SET eliminado_en = ? WHERE id = ?", (fecha_actual, prompt_id))
            self.conn.commit()
            
            # 2. Sincronización inmediata de la caché de memoria
            self.cache_prompts = [p for p in self.cache_prompts if p["id"] != prompt_id]
            
            # 3. Remoción del elemento de la UI sin necesidad de refrescar todo el frame desde disco
            if prompt_id in self.widgets_prompts:
                self.widgets_prompts[prompt_id].destroy()
                del self.widgets_prompts[prompt_id]
                
            # Cerrar modal de confirmación de forma segura
            modal_window.destroy()
            
        except sqlite3.Error as e:
            print(f"Error en persistencia SQLite: {e}")
            modal_window.destroy()

    def on_closing(self):
        if hasattr(self, 'conn'):
            self.conn.close()
        self.destroy()

if __name__ == "__main__":
    app = PromptVaultApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
