import os
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

# ========== CONFIGURACIÓN PARA VERCEL ==========
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

# IMPORTANTE: En Vercel, las variables vienen de os.environ
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Debug para verificar
print("=" * 50)
print("INICIANDO APLICACIÓN EN VERCEL")
print(f"DATABASE_URL configurada: {'SI' if DATABASE_URL else 'NO'}")
print("=" * 50)

# Configuración de la base de datos
if DATABASE_URL:
    # Corregir formato si es necesario
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Asegurar SSL para Neon
    if 'sslmode' not in DATABASE_URL:
        if '?' in DATABASE_URL:
            DATABASE_URL += '&sslmode=require'
        else:
            DATABASE_URL += '?sslmode=require'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Fallback para desarrollo
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local.db'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-temp-umb-2026')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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
    __tablename__ = 'egresados'
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

# ========== INICIALIZAR BASE DE DATOS ==========
with app.app_context():
    try:
        print("Inicializando base de datos...")
        db.create_all()
        
        # Crear usuario por defecto si no existe
        if not User.query.filter_by(username='coordinador').first():
            user = User(username='coordinador')
            user.set_password('coordinadorUMB2026')
            db.session.add(user)
            db.session.commit()
            print("Usuario coordinador creado")
    except Exception as e:
        print(f"Error al inicializar: {e}")

# ========== RUTAS BÁSICAS ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
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

@app.route('/formularios', methods=['GET', 'POST'])
@login_required
def formularios():
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
            flash(f'¡Información actualizada exitosamente!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar información: {str(e)}', 'danger')
    
    return render_template('editar.html', egresado=egresado)

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_egresado(id):
    if request.method == 'POST':
        try:
            egresado = Egresado.query.get_or_404(id)
            nombre = egresado.nombre_completo
            
            db.session.delete(egresado)
            db.session.commit()
            
            flash(f'¡Egresado eliminado exitosamente!', 'success')
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

# ========== RUTAS DE DIAGNÓSTICO ==========
@app.route('/init')
def init_db():
    """Inicializar base de datos"""
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(username='coordinador').first():
            user = User(username='coordinador')
            user.set_password('coordinadorUMB2026')
            db.session.add(user)
            db.session.commit()
        
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Base de datos inicializada</title>
            <style>
                body { font-family: Arial; background: #f0f0f0; }
                .container { max-width: 600px; margin: 50px auto; padding: 20px; background: white; border-radius: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="color: green;">✅ Base de datos inicializada</h1>
                <p>El sistema está listo para usar.</p>
                <p>Usuario: coordinador</p>
                <p>Contraseña: coordinadorUMB2026</p>
                <a href="/login">Ir al login</a>
            </div>
        </body>
        </html>
        '''

@app.route('/test-db')
def test_db():
    """Probar conexión a la base de datos"""
    try:
        count_egresados = Egresado.query.count()
        count_users = User.query.count()
        
        return jsonify({
            'status': 'success',
            'database': 'Neon PostgreSQL',
            'egresados': count_egresados,
            'usuarios': count_users
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
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
application = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)