import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ========== CONFIGURACIÓN SIMPLE PARA VERCEL ==========
app = Flask(__name__)

# Obtener DATABASE_URL de Vercel
DATABASE_URL = os.environ.get('DATABASE_URL')

print("=" * 50)
print("INICIANDO APLICACIÓN EN VERCEL")
print(f"DATABASE_URL configurada: {DATABASE_URL is not None}")
print("=" * 50)

# Configuración de base de datos
if DATABASE_URL:
    # Asegurar formato correcto
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Fallback para desarrollo
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local.db'
    print("⚠️ ADVERTENCIA: Usando SQLite temporal")

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-temp-umb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ========== MODELOS SIMPLES ==========
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Egresado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(200), nullable=False)
    carrera = db.Column(db.String(100))
    generacion = db.Column(db.String(20))
    estatus = db.Column(db.String(50))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== INICIALIZAR BD ==========
with app.app_context():
    try:
        print("Creando tablas...")
        db.create_all()
        
        # Crear usuario por defecto si no existe
        if not User.query.filter_by(username='coordinador').first():
            user = User(username='coordinador')
            user.set_password('coordinadorUMB2026')
            db.session.add(user)
            db.session.commit()
            print("Usuario creado: coordinador / coordinadorUMB2026")
            
        print("✅ Base de datos lista")
    except Exception as e:
        print(f"❌ Error: {e}")

# ========== RUTAS PRINCIPALES ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'¡Bienvenido {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        egresados = Egresado.query.all()
        total = len(egresados)
        
        return render_template('dashboard.html',
                             total_egresados=total,
                             egresados=egresados)
    except:
        return render_template('dashboard.html',
                             total_egresados=0,
                             egresados=[])

@app.route('/formularios', methods=['GET', 'POST'])
@login_required
def formularios():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            data = {
                'matricula': request.form.get('matricula', '').strip(),
                'nombre_completo': request.form.get('nombre_completo', '').strip(),
                'carrera': request.form.get('carrera', '').strip(),
                'generacion': request.form.get('generacion', '').strip(),
                'estatus': request.form.get('estatus', '').strip(),
                'telefono': request.form.get('telefono', '').strip(),
                'email': request.form.get('email', '').strip()
            }
            
            # Validar
            if not all([data['matricula'], data['nombre_completo'], data['carrera']]):
                flash('Complete los campos obligatorios', 'warning')
                return redirect(url_for('formularios'))
            
            # Verificar matrícula única
            if Egresado.query.filter_by(matricula=data['matricula']).first():
                flash('Matrícula ya registrada', 'danger')
                return redirect(url_for('formularios'))
            
            # Crear nuevo egresado
            nuevo = Egresado(**data)
            db.session.add(nuevo)
            db.session.commit()
            
            flash(f'¡Egresado {data["nombre_completo"]} registrado!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('formularios'))
    
    return render_template('formularios.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('index'))

# ========== RUTAS DE PRUEBA ==========
@app.route('/test')
def test():
    """Ruta simple para probar"""
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>✅ Aplicación funcionando</h1>
        <p>Si ves esto, Flask está funcionando.</p>
        <p><a href="/login">Ir al login</a></p>
    </body>
    </html>
    '''

@app.route('/check-db')
def check_db():
    """Verificar conexión a base de datos"""
    try:
        with app.app_context():
            egresados = Egresado.query.count()
            usuarios = User.query.count()
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head><title>Check DB</title></head>
            <body>
                <h1>✅ Base de datos conectada</h1>
                <p>Egresados: {egresados}</p>
                <p>Usuarios: {usuarios}</p>
                <p><a href="/">Ir al inicio</a></p>
            </body>
            </html>
            '''
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head><title>Error DB</title></head>
        <body>
            <h1>❌ Error de base de datos</h1>
            <p>{str(e)}</p>
            <p><a href="/">Ir al inicio</a></p>
        </body>
        </html>
        '''

# ========== PARA VERCEL ==========
application = app

if __name__ == '__main__':
    app.run(debug=True)