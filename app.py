from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-123456'  # Cambia esto en producción

# Configuración de base de datos
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/egresados.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos de base de datos
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
    matricula = db.Column(db.String(8), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(100), nullable=False)
    carrera = db.Column(db.String(100), nullable=False)
    generacion = db.Column(db.String(9), nullable=False)
    estatus = db.Column(db.String(20), nullable=False)
    domicilio = db.Column(db.String(200))
    genero = db.Column(db.String(10))
    telefono = db.Column(db.String(15))
    email = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rutas principales
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('¡Login exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    egresados = Egresado.query.all()
    return render_template('dashboard.html', egresados=egresados)

@app.route('/formularios')
@login_required
def formularios():
    return render_template('formularios.html')

# API para CRUD
@app.route('/api/egresados', methods=['GET'])
@login_required
def get_egresados():
    egresados = Egresado.query.all()
    return jsonify([{
        'id': e.id,
        'matricula': e.matricula,
        'nombre': e.nombre_completo,
        'carrera': e.carrera,
        'generacion': e.generacion,
        'estatus': e.estatus
    } for e in egresados])

@app.route('/api/egresados', methods=['POST'])
@login_required
def create_egresado():
    data = request.json
    nuevo = Egresado(**data)
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({'message': 'Egresado creado exitosamente'})

# Ruta para inicializar base de datos
@app.route('/init')
def init_db():
    with app.app_context():
        db.create_all()
        
        # Crear usuario admin si no existe
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            return 'Base de datos inicializada. Usuario: admin, Contraseña: admin123'
    
    return 'Base de datos ya existe'

if __name__ == '__main__':
    app.run(debug=True)