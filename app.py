import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy import text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# ========== CONFIGURACIÓN VERCEL + NEON ==========

# IMPORTANTE: Para Vercel, usar solo os.environ
DATABASE_URL = os.environ.get('DATABASE_URL')

# FIX CRÍTICO: Si no hay DATABASE_URL, no salir - usar valor por defecto
if not DATABASE_URL:
    print("⚠️  ADVERTENCIA: DATABASE_URL no encontrada en variables de entorno")
    # En producción, usar una URL por defecto
    if os.environ.get('VERCEL') or os.environ.get('FLASK_ENV') == 'production':
        DATABASE_URL = 'sqlite:////tmp/temp.db'
        print("✅ Usando SQLite temporal para Vercel")
    else:
        # En desarrollo local
        print("❌ ERROR: DATABASE_URL no encontrada")
        print("Configura las variables de entorno en Vercel Dashboard:")
        print("1. DATABASE_URL = tu_url_de_neon")
        print("2. SECRET_KEY = tu_clave_secreta")
        # No salir para que al menos cargue la página
        DATABASE_URL = 'sqlite:////tmp/temp.db'

# FIX CRÍTICO: Asegurar formato correcto para PostgreSQL
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# FIX CRÍTICO: Asegurar sslmode=require para Neon
if 'postgresql://' in DATABASE_URL and 'sslmode=' not in DATABASE_URL:
    if '?' in DATABASE_URL:
        DATABASE_URL += '&sslmode=require'
    else:
        DATABASE_URL += '?sslmode=require'

print("=" * 60)
print("🚀 SISTEMA DE CONTROL DE EGRESADOS - UMB")
print(f"📊 Base de datos: {'Neon PostgreSQL' if 'neon' in DATABASE_URL.lower() else 'SQLite temporal'}")
print(f"🔗 URL: {DATABASE_URL[:50]}..." if len(DATABASE_URL) > 50 else f"🔗 URL: {DATABASE_URL}")
print("=" * 60)

# Configuración de la aplicación
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-umb-2026-sistema-egresados')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# FIX CRÍTICO: Configuración simplificada para evitar errores de conexión
# Eliminamos los parámetros keepalives que causan problemas
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# Inicializar extensiones
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

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
    return User.query.get(int(user_id))

# ========== INICIALIZACIÓN CON FIX PARA VERCEL ==========

def init_database():
    """Inicializar la base de datos con manejo de errores mejorado"""
    try:
        with app.app_context():
            print("🔧 Creando tablas si no existen...")
            db.create_all()
            
            # Crear usuario coordinador por defecto si no existe
            if not User.query.filter_by(username='coordinador').first():
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
                db.session.commit()
                print("✅ Usuario coordinador creado: coordinador / coordinadorUMB2026")
            
            # Crear usuario admin por defecto si no existe
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ Usuario admin creado: admin / admin123")
            
            print("✅ Base de datos inicializada correctamente")
            return True
            
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {str(e)}")
        # Intentar rollback si hay error
        try:
            db.session.rollback()
        except:
            pass
        return False

# Inicializar base de datos al arrancar
print("🔄 Inicializando base de datos...")
init_database()

# ========== RUTAS PRINCIPALES ==========

@app.route('/')
def index():
    """Página de inicio del sistema"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        try:
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=True)
                flash(f'¡Bienvenido {user.username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Usuario o contraseña incorrectos', 'danger')
        except Exception as e:
            flash(f'Error al iniciar sesión: {str(e)}', 'danger')
    
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
            
            if not matricula or not nombre_completo or not carrera or not generacion or not estatus:
                flash('Todos los campos obligatorios deben ser completados', 'warning')
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

@app.route('/init')
def init_db():
    """Inicializar base de datos (para Vercel)"""
    try:
        db.create_all()
        
        # Crear usuario coordinador por defecto si no existe
        if not User.query.filter_by(username='coordinador').first():
            coordinador = User(username='coordinador')
            coordinador.set_password('coordinadorUMB2026')
            db.session.add(coordinador)
        
        # Crear usuario admin por defecto si no existe
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
        
        db.session.commit()
        
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>✅ Base de datos inicializada</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f5f5; }
                .container { max-width: 600px; margin: 50px auto; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .success { color: #28a745; }
                .info { background: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">✅ Base de datos inicializada</h1>
                <p>El sistema ha sido configurado correctamente.</p>
                
                <div class="info">
                    <h3>Credenciales de acceso:</h3>
                    <p><strong>Usuario:</strong> coordinador</p>
                    <p><strong>Contraseña:</strong> coordinadorUMB2026</p>
                    <p><strong>Usuario:</strong> admin</p>
                    <p><strong>Contraseña:</strong> admin123</p>
                    <p class="text-muted mt-2">Base de datos: Neon PostgreSQL (Vercel)</p>
                </div>
                
                <a href="/login" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">Ir al Login</a>
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
            <style>
                body {{ font-family: Arial, sans-serif; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 50px auto; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .error {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="error">❌ Error de inicialización</h1>
                <p>Error: {str(e)}</p>
                <p>Verifica que la variable de entorno DATABASE_URL esté configurada correctamente en Vercel.</p>
                <a href="/" style="display: inline-block; padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px;">Volver al inicio</a>
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
        
        return jsonify({
            'status': 'success',
            'message': '✅ Conexión exitosa a la base de datos',
            'database': 'Neon PostgreSQL' if 'neon' in DATABASE_URL.lower() else 'SQLite temporal',
            'stats': {
                'egresados': count_egresados,
                'usuarios': count_users
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database_url': DATABASE_URL[:50] + '...' if DATABASE_URL else 'No configurada'
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
    return {'fecha_actual': datetime.now().strftime('%d/%m/%Y')}

# ========== PARA VERCEL ==========

# Vercel necesita "application" en lugar de "app" en serverless
if __name__ == "__main__":
    print("=" * 60)
    print("SISTEMA DE CONTROL DE EGRESADOS - UES SAN JOSÉ DEL RINCÓN")
    print("=" * 60)
    print("Modo: DESARROLLO LOCAL")
    print("Base de datos: Neon PostgreSQL (Vercel)")
    print("=" * 60)
    print("Instrucciones:")
    print("1. Visita http://localhost:5000/init para inicializar BD")
    print("2. Usuario: coordinador / Contraseña: coordinadorUMB2026")
    print("3. O Usuario: admin / Contraseña: admin123")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

# Vercel usa "application" en modo serverless
application = app