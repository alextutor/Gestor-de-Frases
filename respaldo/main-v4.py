import customtkinter as ctk
import sqlite3
import re
import time
import keyboard
import pygetwindow as gw
import ctypes
from tkinter import messagebox

# --- CONFIGURACIÓN DE BAJO NIVEL (Windows API) ---
def forzar_foco_ventana(titulo_parcial):
    """Usa la API de Windows para traer la ventana al frente de verdad."""
    try:
        ventanas = [w for w in gw.getAllTitles() if titulo_parcial in w]
        if ventanas:
            win = gw.getWindowsWithTitle(ventanas[0])[0]
            # Si está minimizada, la restauramos
            if win.isMinimized:
                win.restore()
            
            # Forzamos la ventana al frente usando el Shell de Windows
            hwnd = win._hWnd
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return True
    except Exception as e:
        print(f"Error de API Windows: {e}")
    return False

# --- CLASE PRINCIPAL ---
class PromptVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PromptVault Pro v4.0")
        self.geometry("480x600")
        self.attributes("-topmost", True)
        self.configure(fg_color="#121212")

        # Cargar interfaz básica
        ctk.CTkLabel(self, text="PROMPT VAULT", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        self.scroll_lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_lista.pack(pady=10, padx=20, fill="both", expand=True)

        self.cargar_prompts()

    def cargar_prompts(self):
        conn = sqlite3.connect('prompts.sqlite')
        cursor = conn.cursor()
        cursor.execute("SELECT titulo, contenido FROM prompts")
        for row in cursor.fetchall():
            btn = ctk.CTkButton(self.scroll_lista, text=row[0], 
                               command=lambda c=row[1]: self.auto_escribir_avanzado(c))
            btn.pack(fill="x", pady=5)
        conn.close()

    def auto_escribir_avanzado(self, texto):
        """Técnica inspirada en Rust (PhraseVault) para inyectar texto."""
        # 1. Minimizar gestor para liberar el escritorio
        self.iconify()
        time.sleep(0.5)

        # 2. Buscar y forzar el foco en Google Gemini (Título de tu imagen)
        if forzar_foco_ventana("Google Gemini"):
            time.sleep(0.6) # Tiempo para que el WebView reaccione
            
            try:
                # 3. Limpiar cualquier estado previo (presionar Esc)
                keyboard.send('esc')
                time.sleep(0.1)
                
                # 4. ESCRIBIR letra por letra con un delay 'orgánico'
                # Esto engaña al WebView de Gemini
                keyboard.write(texto, delay=0.01)
                
            except Exception as e:
                print(f"Error al inyectar: {e}")
        else:
            messagebox.showwarning("Error", "No encontré la ventana 'Google Gemini' abierta.")
            self.deiconify()

if __name__ == "__main__":
    app = PromptVaultApp()
    app.mainloop()