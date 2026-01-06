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

# ========== CONFIGURACIÓN FLASK CON ARCHIVOS ESTÁTICOS ==========
app = Flask(__name__, 
           static_folder='static',
           static_url_path='/static')

# ========== VERIFICACIÓN DE ARCHIVOS ESTÁTICOS ==========
logger.info("=" * 60)
logger.info("🔍 SISTEMA DE CONTROL DE EGRESADOS - UMB")
logger.info("📊 VERIFICANDO ESTRUCTURA DE ARCHIVOS")
logger.info("=" * 60)

# Verificar carpeta static
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, 'static')

if os.path.exists(static_dir):
    logger.info(f"✅ Carpeta 'static/' encontrada en: {static_dir}")
    
    # Listar archivos en static
    css_files = []
    js_files = []
    image_files = []
    
    for root, dirs, files in os.walk(static_dir):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, static_dir)
            
            if file.endswith('.css'):
                css_files.append(relative_path)
            elif file.endswith('.js'):
                js_files.append(relative_path)
            elif file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico')):
                image_files.append(relative_path)
    
    logger.info(f"📁 Archivos CSS encontrados: {len(css_files)}")
    for css in css_files:
        logger.info(f"   - {css}")
    
    logger.info(f"📁 Archivos JS encontrados: {len(js_files)}")
    for js in js_files:
        logger.info(f"   - {js}")
    
    logger.info(f"📁 Imágenes encontradas: {len(image_files)}")
    for img in image_files[:5]:  # Mostrar solo las primeras 5
        logger.info(f"   - {img}")
    
    if len(image_files) > 5:
        logger.info(f"   ... y {len(image_files) - 5} más")
        
else:
    logger.error("❌ Carpeta 'static/' NO encontrada")

logger.info("=" * 60)

# ========== CONFIGURACIÓN BASE DE DATOS ==========

# Detectar si estamos en Vercel
IS_VERCEL = 'VERCEL' in os.environ or 'VERCEL_ENV' in os.environ
logger.info(f"🔧 Entorno: {'Vercel' if IS_VERCEL else 'Local'}")

# Obtener DATABASE_URL de variables de entorno
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    logger.info("✅ DATABASE_URL encontrada en variables de entorno")
    
    # Limpiar y formatear URL
    DATABASE_URL = DATABASE_URL.strip()
    
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        logger.info("✅ URL convertida de postgres:// a postgresql://")
    
    # Eliminar espacios en la URL (problema común con Neon)
    if ' ' in DATABASE_URL:
        logger.warning("⚠️  URL contiene espacios, corrigiendo...")
        DATABASE_URL = DATABASE_URL.replace(' ', '')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    logger.info("📊 Usando: Neon PostgreSQL (Vercel)")
    
else:
    # Desarrollo local: usar SQLite en carpeta database/
    if not IS_VERCEL:
        logger.warning("⚠️  DATABASE_URL no encontrada, usando SQLite para desarrollo local")
        
        # Crear carpeta database si no existe
        database_dir = os.path.join(current_dir, 'database')
        if not os.path.exists(database_dir):
            os.makedirs(database_dir)
            logger.info(f"✅ Carpeta 'database/' creada en: {database_dir}")
        
        db_path = os.path.join(database_dir, 'egresados.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        logger.info(f"📊 Usando: SQLite local en {db_path}")
    else:
        # En Vercel sin DATABASE_URL, usar SQLite en memoria temporal
        logger.error("❌ ERROR: DATABASE_URL no configurada en Vercel")
        logger.info("⚠️  Usando SQLite en memoria (temporal)")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

# Configuración común
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-umb-2026-sistema-egresados')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ========== INICIALIZAR SQLALCHEMY ==========
try:
    db = SQLAlchemy(app)
    logger.info("✅ SQLAlchemy inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error al inicializar SQLAlchemy: {e}")
    # Si hay error, mostrar página de error
    @app.route('/')
    def db_error():
        return f'''
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
                        <h1 class="text-danger">❌ Error de configuración de base de datos</h1>
                        <p class="lead">No se pudo conectar a la base de datos</p>
                        <div class="alert alert-danger mt-3">
                            <p>Error: {str(e)}</p>
                            <p>Verifica que tu DATABASE_URL en Vercel sea correcta.</p>
                            <p>URL configurada: {app.config.get('SQLALCHEMY_DATABASE_URI', 'No configurada')}</p>
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
    """Página de inicio"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
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
    """Panel de control principal"""
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
    """Formulario para agregar/modificar egresados"""
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

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_egresado(id):
    """Editar información de un egresado existente"""
    try:
        egresado = Egresado.query.get_or_404(id)
    except Exception as e:
        flash(f'Error al cargar egresado: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    
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
    """Eliminar un egresado del sistema"""
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
    """Cerrar sesión del usuario"""
    logout_user()
    flash('¡Sesión cerrada exitosamente!', 'info')
    return redirect(url_for('index'))

# ========== API REST PARA CRUD ==========

@app.route('/api/egresados', methods=['GET'])
@login_required
def api_get_egresados():
    """API: Obtener todos los egresados (JSON)"""
    try:
        egresados = Egresado.query.all()
        resultado = [{
            'id': e.id,
            'matricula': e.matricula,
            'nombre': e.nombre_completo,
            'carrera': e.carrera,
            'generacion': e.generacion,
            'estatus': e.estatus,
            'domicilio': e.domicilio,
            'genero': e.genero,
            'telefono': e.telefono,
            'email': e.email,
            'fecha_registro': e.fecha_registro.isoformat() if e.fecha_registro else None
        } for e in egresados]
        
        return jsonify({
            'success': True,
            'count': len(resultado),
            'data': resultado
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/egresados', methods=['POST'])
@login_required
def api_create_egresado():
    """API: Crear nuevo egresado"""
    try:
        data = request.get_json()
        
        required_fields = ['matricula', 'nombre_completo', 'carrera', 'generacion', 'estatus']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Campo requerido faltante: {field}'
                }), 400
        
        if Egresado.query.filter_by(matricula=data['matricula']).first():
            return jsonify({
                'success': False,
                'error': 'La matrícula ya está registrada'
            }), 400
        
        nuevo = Egresado(
            matricula=data['matricula'],
            nombre_completo=data['nombre_completo'],
            carrera=data['carrera'],
            generacion=data['generacion'],
            estatus=data['estatus'],
            domicilio=data.get('domicilio'),
            genero=data.get('genero'),
            telefono=data.get('telefono'),
            email=data.get('email')
        )
        
        db.session.add(nuevo)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Egresado creado exitosamente',
            'id': nuevo.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/egresados/<int:id>', methods=['PUT'])
@login_required
def api_update_egresado(id):
    """API: Actualizar egresado existente"""
    try:
        egresado = Egresado.query.get_or_404(id)
        data = request.get_json()
        
        campos_permitidos = ['nombre_completo', 'carrera', 'generacion', 'estatus', 
                            'domicilio', 'genero', 'telefono', 'email']
        
        for campo in campos_permitidos:
            if campo in data:
                setattr(egresado, campo, data[campo])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Egresado actualizado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/egresados/<int:id>', methods=['DELETE'])
@login_required
def api_delete_egresado(id):
    """API: Eliminar egresado"""
    try:
        egresado = Egresado.query.get_or_404(id)
        
        db.session.delete(egresado)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Egresado eliminado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== RUTAS DE DIAGNÓSTICO ==========

@app.route('/debug-static')
def debug_static():
    """Ruta para diagnosticar problemas con archivos estáticos (JSON)"""
    import os
    
    info = {
        'status': 'ok',
        'current_directory': current_dir,
        'static_directory': static_dir,
        'static_exists': os.path.exists(static_dir),
        'files': {
            'css': [],
            'js': [],
            'images': []
        },
        'urls': {
            'css': '/static/css/style.css',
            'js': '/static/js/script.js',
            'test_image': '/static/images/umb.png'
        }
    }
    
    if info['static_exists']:
        for root, dirs, files in os.walk(static_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, static_dir)
                file_size = os.path.getsize(file_path)
                
                file_info = {
                    'path': relative_path,
                    'size_bytes': file_size,
                    'size_kb': round(file_size / 1024, 2),
                    'full_path': file_path
                }
                
                if file.endswith('.css'):
                    info['files']['css'].append(file_info)
                elif file.endswith('.js'):
                    info['files']['js'].append(file_info)
                elif file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico')):
                    info['files']['images'].append(file_info)
    
    return jsonify(info)

@app.route('/verificar-archivos')
def verificar_archivos():
    """Ruta HTML para verificar si los archivos estáticos se cargan"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔍 Verificar Archivos Estáticos - UMB</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <style>
            .file-status { transition: all 0.3s ease; }
            .file-status:hover { transform: scale(1.02); }
        </style>
    </head>
    <body class="bg-light">
        <div class="container py-5">
            <div class="card shadow">
                <div class="card-header bg-primary text-white">
                    <h1 class="h3 mb-0">
                        <i class="bi bi-search me-2"></i>Verificación de Archivos Estáticos
                    </h1>
                </div>
                <div class="card-body">
                    <p class="lead">Esta página verifica si los archivos CSS, JavaScript e imágenes se cargan correctamente en Vercel.</p>
                    
                    <div class="row mt-4">
                        <div class="col-md-4">
                            <div class="card file-status" id="css-card">
                                <div class="card-body text-center">
                                    <i class="bi bi-filetype-css display-4 text-primary"></i>
                                    <h5 class="mt-3">Archivo CSS</h5>
                                    <p><code>/static/css/style.css</code></p>
                                    <div id="css-status" class="badge bg-secondary">No verificado</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="col-md-4">
                            <div class="card file-status" id="js-card">
                                <div class="card-body text-center">
                                    <i class="bi bi-filetype-js display-4 text-warning"></i>
                                    <h5 class="mt-3">Archivo JavaScript</h5>
                                    <p><code>/static/js/script.js</code></p>
                                    <div id="js-status" class="badge bg-secondary">No verificado</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="col-md-4">
                            <div class="card file-status" id="image-card">
                                <div class="card-body text-center">
                                    <i class="bi bi-image display-4 text-success"></i>
                                    <h5 class="mt-3">Imagen UMB</h5>
                                    <p><code>/static/images/umb.png</code></p>
                                    <div id="image-status" class="badge bg-secondary">No verificado</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mt-5">
                        <h4>Acciones</h4>
                        <div class="d-flex gap-2 mt-3">
                            <button onclick="verificarTodos()" class="btn btn-primary">
                                <i class="bi bi-check-circle me-2"></i>Verificar todos los archivos
                            </button>
                            <a href="/dashboard" class="btn btn-success">
                                <i class="bi bi-speedometer2 me-2"></i>Probar Dashboard
                            </a>
                            <a href="/debug-static" target="_blank" class="btn btn-info">
                                <i class="bi bi-code-slash me-2"></i>Ver datos técnicos (JSON)
                            </a>
                        </div>
                    </div>
                    
                    <div id="resultados" class="mt-4"></div>
                </div>
            </div>
        </div>
        
        <script>
        function verificarArchivo(url, elementoId, cardId) {
            return fetch(url)
                .then(response => {
                    const elemento = document.getElementById(elementoId);
                    const card = document.getElementById(cardId);
                    
                    if (response.ok) {
                        elemento.className = 'badge bg-success';
                        elemento.textContent = '✅ Cargado';
                        card.classList.add('border-success');
                        return { success: true, url: url };
                    } else {
                        elemento.className = 'badge bg-danger';
                        elemento.textContent = '❌ Error ' + response.status;
                        card.classList.add('border-danger');
                        return { success: false, url: url, status: response.status };
                    }
                })
                .catch(error => {
                    const elemento = document.getElementById(elementoId);
                    const card = document.getElementById(cardId);
                    elemento.className = 'badge bg-danger';
                    elemento.textContent = '❌ Error de red';
                    card.classList.add('border-danger');
                    return { success: false, url: url, error: error.message };
                });
        }
        
        function verificarTodos() {
            const resultadosDiv = document.getElementById('resultados');
            resultadosDiv.innerHTML = '<div class="alert alert-info">Verificando archivos...</div>';
            
            const archivos = [
                {url: '/static/css/style.css', elemento: 'css-status', card: 'css-card'},
                {url: '/static/js/script.js', elemento: 'js-status', card: 'js-card'},
                {url: '/static/images/umb.png', elemento: 'image-status', card: 'image-card'}
            ];
            
            Promise.all(archivos.map(archivo => 
                verificarArchivo(archivo.url, archivo.elemento, archivo.card)
            )).then(resultados => {
                const exitosos = resultados.filter(r => r.success).length;
                const total = resultados.length;
                
                if (exitosos === total) {
                    resultadosDiv.innerHTML = `
                        <div class="alert alert-success">
                            <h5><i class="bi bi-check-circle-fill me-2"></i>¡Todos los archivos se cargan correctamente!</h5>
                            <p>${exitosos} de ${total} archivos verificados exitosamente.</p>
                            <p>Ahora puedes probar el <a href="/dashboard" class="alert-link">Dashboard</a>.</p>
                        </div>
                    `;
                } else {
                    const errores = resultados.filter(r => !r.success);
                    resultadosDiv.innerHTML = `
                        <div class="alert alert-warning">
                            <h5><i class="bi bi-exclamation-triangle-fill me-2"></i>Algunos archivos tienen problemas</h5>
                            <p>${exitosos} de ${total} archivos verificados exitosamente.</p>
                            <p>Archivos con problemas:</p>
                            <ul>
                                ${errores.map(e => `<li><code>${e.url}</code> - ${e.status || e.error}</li>`).join('')}
                            </ul>
                            <p>Verifica que los archivos existan en GitHub y que Vercel haya hecho deploy correctamente.</p>
                        </div>
                    `;
                }
            });
        }
        
        // Verificar automáticamente al cargar la página
        window.onload = verificarTodos;
        </script>
    </body>
    </html>
    '''

# ========== RUTAS UTILITARIAS ==========

@app.route('/init')
def init_db():
    """Inicializar base de datos (crear tablas y usuario admin)"""
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

# ========== EXPORTACIÓN DE DATOS ==========

@app.route('/exportar/<formato>')
@login_required
def exportar_egresados(formato):
    """Exportar egresados a Excel, CSV o PDF"""
    try:
        # Obtener todos los egresados
        egresados = Egresado.query.all()
        
        # Calcular estadísticas
        total_egresados = len(egresados)
        titulados = len([e for e in egresados if e.estatus == 'Titulado'])
        egresados_count = len([e for e in egresados if e.estatus == 'Egresado'])
        seguimiento = len([e for e in egresados if e.estatus == 'En seguimiento'])
        
        # Preparar datos
        datos = []
        for e in egresados:
            datos.append({
                'Matrícula': e.matricula,
                'Nombre': e.nombre_completo,
                'Carrera': e.carrera,
                'Generación': e.generacion,
                'Estatus': e.estatus
            })
        
        if formato == 'excel':
            # Exportar a Excel
            df = pd.DataFrame(datos)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Egresados')
                # Agregar hoja de resumen
                resumen = {
                    'Categoría': ['Total Egresados', 'Titulados', 'Egresados', 'En Seguimiento'],
                    'Cantidad': [total_egresados, titulados, egresados_count, seguimiento]
                }
                pd.DataFrame(resumen).to_excel(writer, index=False, sheet_name='Resumen')
            
            output.seek(0)
            return send_file(
                output,
                download_name=f'egresados_umb_{datetime.now().strftime("%Y%m%d")}.xlsx',
                as_attachment=True,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        elif formato == 'csv':
            # Exportar a CSV
            output = BytesIO()
            output.write('Matrícula,Nombre Completo,Carrera,Generación,Estatus\n'.encode('utf-8'))
            for e in egresados:
                linea = f'"{e.matricula}","{e.nombre_completo}","{e.carrera}","{e.generacion}","{e.estatus}"\n'
                output.write(linea.encode('utf-8'))
            output.seek(0)
            return send_file(
                output,
                download_name=f'egresados_umb_{datetime.now().strftime("%Y%m%d")}.csv',
                as_attachment=True,
                mimetype='text/csv'
            )
        
        elif formato == 'pdf':
            # Exportar a PDF en orientación horizontal
            buffer = BytesIO()
            
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                                    rightMargin=30, leftMargin=30,
                                    topMargin=30, bottomMargin=30)
            elements = []
            
            styles = getSampleStyleSheet()
            
            # Título
            title = Paragraph(
                f"<para align=center><b>REPORTE DE EGRESADOS</b><br/>"
                f"<font size=12>Universidad Mexiquense del Bicentenario</font><br/>"
                f"<font size=10>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</font></para>", 
                styles["Heading1"]
            )
            elements.append(title)
            
            elements.append(Paragraph("<br/>", styles["Normal"]))
            
            # Preparar datos para la tabla
            tabla_datos = [['MATRÍCULA', 'NOMBRE COMPLETO', 'CARRERA', 'GENERACIÓN', 'ESTATUS']]
            
            for e in egresados:
                nombre = e.nombre_completo[:40] + '...' if len(e.nombre_completo) > 40 else e.nombre_completo
                carrera = e.carrera[:60] + '...' if len(e.carrera) > 60 else e.carrera
                tabla_datos.append([
                    e.matricula,
                    nombre,
                    carrera,
                    e.generacion,
                    e.estatus
                ])
            
            # Crear tabla
            tabla = Table(tabla_datos, colWidths=[80, 150, 280, 80, 70])
            tabla.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                # Contenido
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),
                ('WORDWRAP', (2, 1), (2, -1), True),
            ]))
            
            elements.append(tabla)
            
            # Estadísticas
            elements.append(Paragraph("<br/><br/>", styles["Normal"]))
            
            resumen_datos = [
                ['ESTADÍSTICAS', 'CANTIDAD', 'PORCENTAJE'],
                ['Total Egresados', str(total_egresados), '100%'],
                ['Titulados', str(titulados), f"{(titulados/total_egresados*100):.1f}%" if total_egresados > 0 else '0%'],
                ['Egresados', str(egresados_count), f"{(egresados_count/total_egresados*100):.1f}%" if total_egresados > 0 else '0%'],
                ['En Seguimiento', str(seguimiento), f"{(seguimiento/total_egresados*100):.1f}%" if total_egresados > 0 else '0%']
            ]
            
            tabla_resumen = Table(resumen_datos, colWidths=[120, 80, 80])
            tabla_resumen.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565C0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E3F2FD')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            elements.append(Paragraph("<b>RESUMEN ESTADÍSTICO</b>", styles["Normal"]))
            elements.append(tabla_resumen)
            
            # Pie de página
            elements.append(Paragraph("<br/><br/>", styles["Normal"]))
            footer = Paragraph(
                "<font size=8><i>Sistema de Control de Egresados - UMB Campus San José del Rincón<br/>"
                "Base de datos: Neon PostgreSQL (Vercel)<br/>"
                "Este documento fue generado automáticamente por el sistema</i></font>",
                styles["Normal"]
            )
            elements.append(footer)
            
            doc.build(elements)
            buffer.seek(0)
            
            return send_file(
                buffer,
                download_name=f'Reporte_Egresados_UMB_{datetime.now().strftime("%Y%m%d")}.pdf',
                as_attachment=True,
                mimetype='application/pdf'
            )
        
        return redirect('/dashboard')
    
    except Exception as e:
        flash(f'Error al exportar: {str(e)}', 'danger')
        return redirect('/dashboard')

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

# ========== INICIALIZAR BASE DE DATOS AL INICIAR ==========
with app.app_context():
    try:
        init_database()
        logger.info("✅ Aplicación inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error durante inicialización: {e}")

# ========== EJECUCIÓN ==========

# Vercel necesita "application" en lugar de "app"
application = app

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SISTEMA DE CONTROL DE EGRESADOS - UMB")
    logger.info("Modo: DESARROLLO LOCAL")
    logger.info("=" * 60)
    
    # Inicializar base de datos
    try:
        init_database()
    except Exception as e:
        logger.error(f"Error durante inicialización: {e}")
    
    # IMPORTANTE: SIN letra 'y' extra al final
    app.run(debug=False, host='0.0.0.0', port=5000)