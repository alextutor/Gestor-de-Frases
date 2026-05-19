# Importamos la librería sqlite3, que ya viene incluida en Python.
# No necesitas instalar nada extra para bases de datos locales.
import sqlite3

def crear_base_de_datos():
    try:
        # 1. Conexión: Se crea el archivo 'prompts.sqlite'. 
        # Si ya existe, simplemente se conecta a él.
        conexion = sqlite3.connect('prompts.sqlite')
        
        # 2. El Cursor: Es el objeto que nos permite ejecutar comandos SQL.
        cursor = conexion.cursor()
        
        # 3. La Sentencia SQL: Creamos la tabla 'prompts' con 3 columnas.
        # id: Autoincremental para no repetir registros.
        # titulo: Nombre del prompt (ej. "Saludo Email").
        # contenido: El texto del prompt con las {{variables}}.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL
            )
        ''')
        
        # 4. Datos de prueba: Insertamos un registro inicial para ver que funcione.
        # Usamos el formato {{variable}} que planeamos usar luego.
        cursor.execute('''
            INSERT INTO prompts (titulo, contenido) 
            VALUES (?, ?)
        ''', ("Bienvenida Cliente", "Hola {{nombre}}, bienvenido a nuestra plataforma de {{servicio}}."))
        
        # 5. Guardar cambios: En SQLite es obligatorio hacer 'commit' para salvar.
        conexion.commit()
        print("¡Base de datos y tabla creadas con éxito!")
        
    except sqlite3.Error as e:
        # Si algo sale mal (permisos, carpeta protegida, etc.), nos avisará aquí.
        print(f"Error al crear la base de datos: {e}")
        
    finally:
        # 6. Cierre: Siempre cerramos la conexión para no bloquear el archivo.
        if conexion:
            conexion.close()

# Ejecutamos la función
if __name__ == "__main__":
    crear_base_de_datos()