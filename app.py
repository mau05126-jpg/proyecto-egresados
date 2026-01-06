import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
           static_folder='static',
           static_url_path='/static')

# ========== CONFIGURACIÓN ROBUSTA PARA VERCEL ==========

logger.info("=" * 60)
logger.info("🚀 INICIANDO SISTEMA DE CONTROL DE EGRESADOS - UMB")
logger.info("📊 CONFIGURACIÓN PARA VERCEL + NEON POSTGRESQL")
logger.info("=" * 60)

# Detectar si estamos en Vercel
IS_VERCEL = 'VERCEL' in os.environ or 'VERCEL_ENV' in os.environ
logger.info(f"🔧 Entorno: {'Vercel' if IS_VERCEL else 'Local'}")

# Obtener DATABASE_URL de variables de entorno de Vercel
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    logger.info("✅ DATABASE_URL encontrada en variables de entorno")
    
    # Para Vercel, siempre usar PostgreSQL, nunca SQLite
    # Asegurar formato correcto
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        logger.info("✅ URL convertida de postgres:// a postgresql://")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    logger.info("📊 Usando: Neon PostgreSQL (Vercel)")
    
else:
    # Solo usar SQLite si estamos en desarrollo local Y no hay DATABASE_URL
    if not IS_VERCEL:
        logger.warning("⚠️  DATABASE_URL no encontrada, usando SQLite para desarrollo local")
        basedir = os.path.abspath(os.path.dirname(__file__))
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "egresados.db")}'
    else:
        # En Vercel sin DATABASE_URL, mostrar error claro
        logger.error("❌ ERROR CRÍTICO: DATABASE_URL no configurada en Vercel")
        logger.error("Por favor, configura DATABASE_URL en Vercel Environment Variables")
        # Crear una aplicación mínima que muestre error
        @app.route('/')
        def error_page():
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>❌ Error de configuración</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <div class="card shadow">
                        <div class="card-body text-center">
                            <h1 class="text-danger">❌ Error de configuración</h1>
                            <p class="lead">DATABASE_URL no configurada en Vercel</p>
                            <div class="alert alert-danger mt-3">
                                <h5>Instrucciones:</h5>
                                <ol class="text-start">
                                    <li>Ve a tu proyecto en Vercel</li>
                                    <li>Sección <strong>Settings → Environment Variables</strong></li>
                                    <li>Agrega:<br>
                                        <code>DATABASE_URL = postgresql://neondb_owner:tu_contraseña@ep-morning-rain-ac7g49y5-pooler.sa-east-1.aws.neon.tech/proyecto_egresados?sslmode=require</code>
                                    </li>
                                    <li>Agrega también:<br>
                                        <code>SECRET_KEY = una-clave-secreta-segura</code>
                                    </li>
                                    <li>Haz redeploy</li>
                                </ol>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            ''', 500

# Configuración común
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-umb-2026-sistema-egresados')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar SQLAlchemy solo si tenemos una URI válida
if 'SQLALCHEMY_DATABASE_URI' in app.config:
    try:
        db = SQLAlchemy(app)
        logger.info("✅ SQLAlchemy inicializado correctamente")
    except Exception as e:
        logger.error(f"❌ Error al inicializar SQLAlchemy: {e}")
        # En Vercel, si falla la conexión, mostrar error
        if IS_VERCEL:
            @app.route('/')
            def db_error():
                return f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>❌ Error de conexión a base de datos</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                </head>
                <body class="bg-light">
                    <div class="container py-5">
                        <div class="card shadow">
                            <div class="card-body text-center">
                                <h1 class="text-danger">❌ Error de conexión a base de datos</h1>
                                <p class="lead">No se pudo conectar a Neon PostgreSQL</p>
                                <div class="alert alert-danger mt-3">
                                    <p>Error: {str(e)}</p>
                                    <p>Verifica que tu DATABASE_URL en Vercel sea correcta y que Neon PostgreSQL esté activo.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                ''', 500

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

# ========== MODELOS ==========

if 'db' in locals():
    class User(UserMixin, db.Model):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password_hash = db.Column(db.String(200))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        def set_password(self, password):
            self.password_hash = generate_password_hash(password)
        
        def check_password(self, password):
            return check_password_hash(self.password_hash, password)

    class Egresado(db.Model):
        __tablename__ = 'egresado'
        id = db.Column(db.Integer, primary_key=True)
        matricula = db.Column(db.String(20), unique=True, nullable=False)
        nombre_completo = db.Column(db.String(200), nullable=False)
        carrera = db.Column(db.String(100))
        generacion = db.Column(db.String(20))
        estatus = db.Column(db.String(50))
        domicilio = db.Column(db.Text)
        genero = db.Column(db.String(20))
        telefono = db.Column(db.String(20))
        email = db.Column(db.String(100))
        fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
        fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

# ========== INICIALIZACIÓN ==========

def init_database():
    """Inicializar tablas y usuario por defecto"""
    try:
        with app.app_context():
            if 'db' not in locals():
                logger.error("❌ No se puede inicializar: db no definido")
                return False
                
            db.create_all()
            logger.info("✅ Tablas de base de datos verificadas/creadas")
            
            # Crear usuario coordinador por defecto si no existe
            if not User.query.filter_by(username='coordinador').first():
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
                logger.info("✅ Usuario coordinador creado")
            
            # Crear usuario admin si no existe
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                logger.info("✅ Usuario admin creado")
            
            db.session.commit()
            logger.info("✅ Base de datos inicializada correctamente")
            return True
    except Exception as e:
        logger.error(f"❌ Error al inicializar base de datos: {e}")
        return False

# ========== RUTAS PRINCIPALES ==========

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'db' not in locals():
        flash('Error de configuración de base de datos', 'danger')
        return render_template('login.html')
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash(f'¡Bienvenido {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if 'db' not in locals():
        flash('Error de conexión a la base de datos', 'danger')
        return render_template('dashboard.html', 
                             total_egresados=0,
                             titulados=0,
                             egresados_count=0,
                             seguimiento=0,
                             egresados=[])
    
    try:
        lista_egresados = Egresado.query.order_by(Egresado.nombre_completo).all()
        
        total_egresados = len(lista_egresados)
        titulados = sum(1 for e in lista_egresados if e.estatus == 'Titulado')
        egresados_count = sum(1 for e in lista_egresados if e.estatus == 'Egresado')
        seguimiento = sum(1 for e in lista_egresados if e.estatus == 'En seguimiento')
        
        return render_template('dashboard.html', 
                             total_egresados=total_egresados,
                             titulados=titulados,
                             egresados_count=egresados_count,
                             seguimiento=seguimiento,
                             egresados=lista_egresados)
    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html', 
                             total_egresados=0,
                             titulados=0,
                             egresados_count=0,
                             seguimiento=0,
                             egresados=[])

@app.route('/formularios', methods=['GET', 'POST'])
@login_required
def formularios():
    if 'db' not in locals():
        flash('Error de conexión a la base de datos', 'danger')
        return render_template('formularios.html')
    
    if request.method == 'POST':
        try:
            matricula = request.form.get('matricula', '').strip()
            nombre_completo = request.form.get('nombre_completo', '').strip()
            carrera = request.form.get('carrera', '').strip()
            generacion = request.form.get('generacion', '').strip()
            estatus = request.form.get('estatus', '').strip()
            domicilio = request.form.get('domicilio', '').strip()
            genero = request.form.get('genero', '').strip()
            telefono = request.form.get('telefono', '').strip()
            email = request.form.get('email', '').strip()
            
            if not all([matricula, nombre_completo, carrera, generacion, estatus]):
                flash('Todos los campos obligatorios deben ser completados', 'warning')
                return redirect(url_for('formularios'))
            
            if len(matricula) < 8 or len(matricula) > 20:
                flash('La matrícula debe tener entre 8 y 20 caracteres', 'warning')
                return redirect(url_for('formularios'))
            
            if Egresado.query.filter_by(matricula=matricula).first():
                flash('La matrícula ya está registrada', 'danger')
                return redirect(url_for('formularios'))
            
            nuevo_egresado = Egresado(
                matricula=matricula,
                nombre_completo=nombre_completo,
                carrera=carrera,
                generacion=generacion,
                estatus=estatus,
                domicilio=domicilio if domicilio else None,
                genero=genero if genero else None,
                telefono=telefono if telefono else None,
                email=email if email else None
            )
            
            db.session.add(nuevo_egresado)
            db.session.commit()
            
            flash(f'¡Egresado {nombre_completo} registrado exitosamente!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar egresado: {str(e)}', 'danger')
            return redirect(url_for('formularios'))
    
    return render_template('formularios.html')

# ... (mantén las otras rutas como editar, eliminar, logout igual) ...

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_egresado(id):
    if 'db' not in locals():
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('dashboard'))
    
    egresado = Egresado.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            egresado.nombre_completo = request.form.get('nombre_completo', '').strip()
            egresado.carrera = request.form.get('carrera', '').strip()
            egresado.generacion = request.form.get('generacion', '').strip()
            egresado.estatus = request.form.get('estatus', '').strip()
            egresado.domicilio = request.form.get('domicilio', '').strip()
            egresado.genero = request.form.get('genero', '').strip()
            egresado.telefono = request.form.get('telefono', '').strip()
            egresado.email = request.form.get('email', '').strip()
            
            db.session.commit()
            flash(f'¡Información de {egresado.nombre_completo} actualizada exitosamente!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar información: {str(e)}', 'danger')
    
    return render_template('editar.html', egresado=egresado)

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_egresado(id):
    if 'db' not in locals():
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            egresado = Egresado.query.get_or_404(id)
            nombre = egresado.nombre_completo
            
            db.session.delete(egresado)
            db.session.commit()
            
            flash(f'¡Egresado {nombre} eliminado exitosamente!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar egresado: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('¡Sesión cerrada exitosamente!', 'info')
    return redirect(url_for('index'))

# ========== RUTAS UTILITARIAS ==========

@app.route('/init')
def init_db():
    """Inicializar base de datos (crear tablas y usuarios por defecto)"""
    if 'db' not in locals():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>❌ Error de inicialización</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow">
                    <div class="card-body text-center">
                        <h1 class="text-danger">❌ Error de inicialización</h1>
                        <p class="lead">Base de datos no configurada.</p>
                        <p>Verifica que DATABASE_URL esté configurada en Vercel Environment Variables.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        ''', 500
    
    try:
        if init_database():
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>✅ Base de datos inicializada</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <div class="card shadow">
                        <div class="card-body text-center">
                            <h1 class="text-success">✅ Base de datos inicializada</h1>
                            <p class="lead">El sistema ha sido configurado correctamente.</p>
                            
                            <div class="alert alert-info mt-4">
                                <h5>Credenciales de acceso:</h5>
                                <p><strong>Usuario:</strong> admin</p>
                                <p><strong>Contraseña:</strong> admin123</p>
                                <p><strong>Usuario:</strong> coordinador</p>
                                <p><strong>Contraseña:</strong> coordinadorUMB2026</p>
                            </div>
                            
                            <a href="/login" class="btn btn-primary btn-lg mt-3">Ir al Login</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''
        else:
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>❌ Error de inicialización</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <div class="card shadow">
                        <div class="card-body text-center">
                            <h1 class="text-danger">❌ Error de inicialización</h1>
                            <p class="lead">No se pudo inicializar la base de datos.</p>
                            <a href="/" class="btn btn-secondary mt-3">Volver al inicio</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''
                
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>❌ Error de inicialización</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow">
                    <div class="card-body text-center">
                        <h1 class="text-danger">❌ Error de inicialización</h1>
                        <p class="lead">Error: {str(e)}</p>
                        <a href="/" class="btn btn-secondary mt-3">Volver al inicio</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''

@app.route('/test-db')
def test_db():
    """Ruta para probar la conexión a la base de datos"""
    if 'db' not in locals():
        return jsonify({
            'status': 'error',
            'error': 'Base de datos no configurada',
            'vercel_env': IS_VERCEL,
            'database_url_set': bool(os.environ.get('DATABASE_URL'))
        }), 500
    
    try:
        count_egresados = Egresado.query.count()
        count_users = User.query.count()
        
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if 'postgresql' in db_uri:
            db_type = 'Neon PostgreSQL'
        elif 'sqlite' in db_uri:
            db_type = 'SQLite local'
        else:
            db_type = 'Desconocido'
        
        return jsonify({
            'status': 'success',
            'message': f'✅ Conexión exitosa a {db_type}',
            'database': db_type,
            'vercel': IS_VERCEL,
            'stats': {
                'egresados': count_egresados,
                'usuarios': count_users
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'vercel': IS_VERCEL,
            'database_url': app.config.get('SQLALCHEMY_DATABASE_URI', 'No configurada'),
            'timestamp': datetime.now().isoformat()
        }), 500

# ========== MANEJO DE ERRORES ==========

@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_servidor(error):
    return render_template('500.html'), 500

@app.errorhandler(401)
def no_autorizado(error):
    flash('Debes iniciar sesión para acceder a esta página', 'warning')
    return redirect(url_for('login'))

# ========== CONTEXT PROCESSOR ==========

@app.context_processor
def inject_now():
    return {
        'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
        'anio_actual': datetime.now().year
    }

# ========== EJECUCIÓN ==========

# Vercel necesita "application" en lugar de "app"
application = app

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SISTEMA DE CONTROL DE EGRESADOS - UMB")
    logger.info("Modo: DESARROLLO LOCAL")
    logger.info("=" * 60)
    
    # Solo inicializar base de datos si tenemos db
    if 'db' in locals():
        try:
            init_database()
        except Exception as e:
            logger.error(f"Error durante inicialización: {e}")
    
    app.run(debug=False, host='0.0.0.0', port=5000)