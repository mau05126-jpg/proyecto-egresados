# backup_db_final.py
import os
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def backup_neon_database():
    print("=" * 60)
    print("🔄 SISTEMA DE RESPALDO - BASE DE DATOS")
    print("=" * 60)
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL no encontrada en .env")
        print("Asegúrate de tener un archivo .env con DATABASE_URL")
        return False
    
    # Crear carpeta de backups si no existe
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"✅ Carpeta '{backup_dir}/' creada")
    
    # Nombre del archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'backup_egresados_{timestamp}.sql')
    
    print(f"\n📦 Iniciando respaldo...")
    print(f"📁 Archivo: {backup_file}")
    print(f"🕐 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Intentar primero con pg_dump desde el PATH, luego con la ruta completa
    pg_dump_candidates = [
        'pg_dump',
        r'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe'
    ]
    
    pg_dump_path = None
    for candidate in pg_dump_candidates:
        try:
            # Verificar si el comando existe
            result = subprocess.run([candidate, '--version'], 
                                   capture_output=True, 
                                   text=True, 
                                   timeout=5)
            if result.returncode == 0:
                pg_dump_path = candidate
                print(f"✅ Usando: {candidate}")
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not pg_dump_path:
        print("❌ ERROR: No se pudo encontrar pg_dump en el sistema")
        print("Asegúrate de que PostgreSQL esté instalado y en el PATH")
        return False
    
    try:
        # Usar pg_dump para hacer el backup
        result = subprocess.run(
            [pg_dump_path, DATABASE_URL, '-f', backup_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos máximo
        )
        
        if result.returncode == 0:
            # Verificar tamaño del archivo
            file_size = os.path.getsize(backup_file)
            size_mb = file_size / (1024 * 1024)
            
            print(f"\n✅ ¡RESPALDO COMPLETADO EXITOSAMENTE!")
            print(f"📊 Tamaño: {size_mb:.2f} MB")
            print(f"📍 Ubicación: {os.path.abspath(backup_file)}")
            
            # Listar todos los backups
            listar_backups(backup_dir)
            
            return True
        else:
            print(f"\n❌ ERROR al crear respaldo:")
            print("Código de error:", result.returncode)
            if result.stderr:
                print("Error detallado:", result.stderr[:500])  # Limitar la salida
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ ERROR: Tiempo de espera agotado (>5 minutos)")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR inesperado: {e}")
        return False

def listar_backups(backup_dir='backups'):
    """Listar todos los backups existentes"""
    if not os.path.exists(backup_dir):
        return
    
    backups = [f for f in os.listdir(backup_dir) if f.endswith('.sql')]
    
    if backups:
        print(f"\n📋 BACKUPS DISPONIBLES ({len(backups)}):")
        print("-" * 60)
        
        # Ordenar por fecha (más reciente primero)
        backups.sort(reverse=True)
        
        for i, backup in enumerate(backups[:5], 1):
            filepath = os.path.join(backup_dir, backup)
            size = os.path.getsize(filepath) / (1024 * 1024)
            mtime = os.path.getmtime(filepath)
            date = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')
            
            print(f"{i}. {backup}")
            print(f"   📅 Fecha: {date}")
            print(f"   📊 Tamaño: {size:.2f} MB")
            print()
        
        if len(backups) > 5:
            print(f"   ... y {len(backups) - 5} backups más")

def limpiar_backups_antiguos(backup_dir='backups', dias=30):
    """Eliminar backups más antiguos de X días"""
    if not os.path.exists(backup_dir):
        return
    
    print(f"\n🧹 Limpiando backups antiguos (>{dias} días)...")
    
    now = datetime.now().timestamp()
    eliminados = 0
    
    for backup in os.listdir(backup_dir):
        if not backup.endswith('.sql'):
            continue
        
        filepath = os.path.join(backup_dir, backup)
        file_age = (now - os.path.getmtime(filepath)) / (24 * 3600)
        
        if file_age > dias:
            os.remove(filepath)
            eliminados += 1
            print(f"   ❌ Eliminado: {backup} ({file_age:.0f} días)")
    
    if eliminados == 0:
        print("   ✅ No hay backups antiguos para eliminar")
    else:
        print(f"   ✅ {eliminados} backup(s) eliminado(s)")

if __name__ == '__main__':
    print("\n🎯 SISTEMA DE RESPALDO DE BASE DE DATOS")
    print("Universidad Mexiquense del Bicentenario")
    print("Sistema de Control de Egresados\n")
    
    # Ejecutar backup
    exito = backup_neon_database()
    
    if exito:
        # Opcional: Limpiar backups antiguos (más de 30 días)
        limpiar_backups_antiguos(dias=30)
        
        print("\n" + "=" * 60)
        print("✅ PROCESO COMPLETADO")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ PROCESO FALLIDO")
        print("=" * 60)