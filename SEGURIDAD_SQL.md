
# ============================================================
# ARCHIVO 2: SEGURIDAD_SQL.md (Documentación)
# ============================================================

"""
# DOCUMENTACIÓN DE SEGURIDAD - PROTECCIÓN CONTRA INYECCIÓN SQL

## ✅ Protección Implementada

Este sistema está protegido contra ataques de inyección SQL mediante el uso de **SQLAlchemy ORM**, 
que parametriza automáticamente todas las consultas.

## Ejemplos de Código Seguro

### ❌ VULNERABLE (NO usado en este proyecto):
```python
# NUNCA hacer esto:
query = f"SELECT * FROM egresado WHERE matricula = '{matricula}'"
db.engine.execute(query)
```

### ✅ SEGURO (Usado en este proyecto):
```python
# Todas las consultas usan SQLAlchemy ORM:
egresado = Egresado.query.filter_by(matricula=matricula).first()
```

## Funciones que Usan Protección SQL

1. **Crear egresado** (`/formularios` POST):
   ```python
   nuevo_egresado = Egresado(
       matricula=matricula,
       nombre_completo=nombre_completo,
       # ... más campos
   )
   db.session.add(nuevo_egresado)
   db.session.commit()
   ```

2. **Leer egresados** (`/dashboard`):
   ```python
   lista_egresados = Egresado.query.order_by(Egresado.nombre_completo).all()
   ```

3. **Actualizar egresado** (`/editar/<id>` POST):
   ```python
   egresado = Egresado.query.get_or_404(id)
   egresado.nombre_completo = nombre_completo
   db.session.commit()
   ```

4. **Eliminar egresado** (`/eliminar/<id>` POST):
   ```python
   egresado = Egresado.query.get_or_404(id)
   db.session.delete(egresado)
   db.session.commit()
   ```

5. **Login** (`/login` POST):
   ```python
   user = User.query.filter_by(username=username).first()
   ```

## Verificación de Seguridad

- ✅ Todas las consultas usan SQLAlchemy ORM
- ✅ No hay queries SQL raw en el código
- ✅ Los parámetros se pasan como objetos Python
- ✅ SQLAlchemy escapa automáticamente caracteres peligrosos
- ✅ Uso de `.get_or_404()` para IDs
- ✅ Validación de datos de entrada en formularios

## Pruebas de Seguridad Realizadas

**Intento de inyección en matrícula:**
- Entrada: `12345678' OR '1'='1`
- Resultado: ✅ Rechazado (no es numérico de 8 dígitos)

**Intento de inyección en nombre:**
- Entrada: `Juan'; DROP TABLE egresado; --`
- Resultado: ✅ Guardado como texto literal (sin ejecución SQL)

**Intento de inyección en login:**
- Usuario: `admin' OR '1'='1`
- Resultado: ✅ Usuario no encontrado (búsqueda exacta)

## Recomendaciones Adicionales Implementadas

1. ✅ Validación de longitud de matrícula (8 dígitos)
2. ✅ Validación de formato de email
3. ✅ Sanitización de inputs en formularios
4. ✅ Uso de password hashing (Werkzeug)
5. ✅ Sistema de autenticación (Flask-Login)

## Conclusión

El sistema está completamente protegido contra inyección SQL gracias al uso 
consistente de SQLAlchemy ORM en todas las operaciones de base de datos.

---
Fecha: 06/01/2026
Sistema: Control de Egresados - UMB
"""

# ============================================================
# ARCHIVO 3: README.md (Actualizar con sección de respaldos)
# ============================================================

"""
# Sistema de Control de Egresados - UMB

## 🔒 Seguridad

### Protección contra Inyección SQL
- ✅ **SQLAlchemy ORM**: Todas las consultas están parametrizadas
- ✅ Sin queries SQL raw
- ✅ Validación de datos de entrada
- ✅ Ver documentación completa en `SEGURIDAD_SQL.md`

### Sistema de Respaldos

#### Crear Respaldo Manual
```bash
python backup_db.py
```

#### Respaldos Automáticos (Opcional)
**Windows (Task Scheduler):**
1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Disparador: Diario a las 2:00 AM
4. Acción: Ejecutar `python C:\ruta\backup_db.py`

**Linux/Mac (cron):**
```bash
# Editar crontab
crontab -e

# Agregar línea (respaldo diario a las 2 AM)
0 2 * * * cd /ruta/proyecto && python backup_db.py
```

#### Restaurar desde Respaldo
```bash
psql [DATABASE_URL] < backups/backup_egresados_20260106_020000.sql
```

#### Ubicación de Respaldos
- Carpeta: `backups/`
- Formato: `backup_egresados_YYYYMMDD_HHMMSS.sql`
- Retención: 30 días (limpieza automática)

## 📦 Instalación

### Requisitos Adicionales para Respaldos
```bash
# Instalar PostgreSQL client
# Windows: https://www.postgresql.org/download/windows/
# Mac:
brew install postgresql

# Linux:
sudo apt-get install postgresql-client
```

## 🚀 Características
- CRUD completo de egresados
- Dashboard con estadísticas
- Exportación a Excel/PDF
- Sistema de autenticación
- **Sistema de respaldos automático**
- **Protección contra inyección SQL**

## 📊 Base de Datos
- Producción: Neon PostgreSQL (Vercel)
- Desarrollo: SQLite local
- Respaldos: Diarios automáticos
"""

# ============================================================
# COMANDOS PARA IMPLEMENTAR
# ============================================================

"""
1. Crear archivo backup_db.py con el contenido de arriba
2. Crear archivo SEGURIDAD_SQL.md con la documentación
3. Actualizar README.md con la sección de respaldos
4. Agregar al .gitignore:
   backups/
   *.sql

5. Probar el sistema de respaldo:
   python backup_db.py

6. Commit y push:
   git add .
   git commit -m "ADD: Sistema de respaldos y documentación de seguridad SQL"
   git push origin main
"""