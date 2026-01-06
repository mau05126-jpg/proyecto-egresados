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

# ========== CONFIGURACIÓN VERCEL + NEON ==========
app = Flask(__name__,
            static_folder='static',
            template_folder='templates',
            static_url_path='/static')

# Obtener DATABASE_URL de las variables de entorno de Vercel
DATABASE_URL = os.environ.get('DATABASE_URL', '')

print("=" * 60)
print("🚀 SISTEMA DE CONTROL DE EGRESADOS - UMB")
print("📊 Inicializando sistema...")
print("=" * 60)

# Formatear correctamente la URL para Neon PostgreSQL
if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    if 'sslmode' not in DATABASE_URL:
        if '?' in DATABASE_URL:
            DATABASE_URL += '&sslmode=require'
        else:
            DATABASE_URL += '?sslmode=require'
    print(f"✅ Base de datos: Neon PostgreSQL configurada")
else:
    print("⚠️  ADVERTENCIA: DATABASE_URL no encontrada")
    DATABASE_URL = 'sqlite:///temporal.db'
    print(f"⚠️  Usando base de datos temporal: SQLite")

# Configuración de la aplicación
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-umb-2026-sistema-egresados')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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

# ========== INICIALIZACIÓN DE BASE DE DATOS ==========
def init_database():
    """Inicializar la base de datos al arrancar"""
    try:
        with app.app_context():
            print("🔧 Verificando/Creando tablas...")
            
            # Crear todas las tablas
            db.create_all()
            
            # Contar registros existentes
            users_count = User.query.count()
            egresados_count = Egresado.query.count()
            
            print(f"👤 Usuarios en sistema: {users_count}")
            print(f"📊 Egresados registrados: {egresados_count}")
            
            # Crear usuarios por defecto si no existen
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                print("✅ Usuario admin creado: admin / admin123")
            
            coordinador_user = User.query.filter_by(username='coordinador').first()
            if not coordinador_user:
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
                print("✅ Usuario coordinador creado: coordinador / coordinadorUMB2026")
            
            # Crear usuario rector si no existe
            rector_user = User.query.filter_by(username='rector').first()
            if not rector_user:
                rector = User(username='rector')
                rector.set_password('rectorUMB2026')
                db.session.add(rector)
                print("✅ Usuario rector creado: rector / rectorUMB2026")
            
            db.session.commit()
            print("✅ Base de datos inicializada correctamente")
            
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {str(e)}")

# Inicializar la base de datos
with app.app_context():
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
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash(f'¡Bienvenido {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Panel de control principal"""
    try:
        # Obtener todos los egresados ordenados
        lista_egresados = Egresado.query.order_by(Egresado.nombre_completo).all()
        
        # Calcular estadísticas
        total_egresados = len(lista_egresados)
        titulados = sum(1 for e in lista_egresados if e.estatus and 'titulado' in e.estatus.lower())
        egresados_count = sum(1 for e in lista_egresados if e.estatus and 'egresado' in e.estatus.lower())
        seguimiento = sum(1 for e in lista_egresados if e.estatus and 'seguimiento' in e.estatus.lower())
        
        print(f"📊 Dashboard: Mostrando {total_egresados} egresados")
        
        return render_template('dashboard.html', 
                             total_egresados=total_egresados,
                             titulados=titulados,
                             egresados_count=egresados_count,
                             seguimiento=seguimiento,
                             egresados=lista_egresados)
    except Exception as e:
        print(f"❌ Error en dashboard: {str(e)}")
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
            # Obtener datos del formulario
            matricula = request.form.get('matricula', '').strip()
            nombre_completo = request.form.get('nombre_completo', '').strip()
            carrera = request.form.get('carrera', '').strip()
            generacion = request.form.get('generacion', '').strip()
            estatus = request.form.get('estatus', '').strip()
            domicilio = request.form.get('domicilio', '').strip()
            genero = request.form.get('genero', '').strip()
            telefono = request.form.get('telefono', '').strip()
            email = request.form.get('email', '').strip()
            
            print(f"📝 Intentando registrar: {matricula} - {nombre_completo}")
            
            # Validar campos obligatorios
            if not all([matricula, nombre_completo, carrera, generacion, estatus]):
                flash('Todos los campos obligatorios deben ser completados', 'warning')
                return redirect(url_for('formularios'))
            
            # Validar matrícula única
            existing = Egresado.query.filter_by(matricula=matricula).first()
            if existing:
                flash('La matrícula ya está registrada', 'danger')
                return redirect(url_for('formularios'))
            
            # Crear nuevo egresado
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
            
            # Guardar en base de datos
            db.session.add(nuevo_egresado)
            db.session.commit()
            
            print(f"✅ Registrado exitosamente: ID {nuevo_egresado.id}")
            flash(f'¡Egresado {nombre_completo} registrado exitosamente!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al registrar: {str(e)}")
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
            print(f"✏️ Editando egresado ID: {id}")
            
            # Actualizar campos
            egresado.nombre_completo = request.form.get('nombre_completo', '').strip()
            egresado.carrera = request.form.get('carrera', '').strip()
            egresado.generacion = request.form.get('generacion', '').strip()
            egresado.estatus = request.form.get('estatus', '').strip()
            egresado.domicilio = request.form.get('domicilio', '').strip()
            egresado.genero = request.form.get('genero', '').strip()
            egresado.telefono = request.form.get('telefono', '').strip()
            egresado.email = request.form.get('email', '').strip()
            
            db.session.commit()
            
            print(f"✅ Actualizado: {egresado.nombre_completo}")
            flash(f'¡Información de {egresado.nombre_completo} actualizada exitosamente!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al actualizar: {str(e)}")
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
            
            print(f"🗑️ Eliminado: {nombre}")
            flash(f'¡Egresado {nombre} eliminado exitosamente!', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al eliminar: {str(e)}")
            flash(f'Error al eliminar egresado: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    """Cerrar sesión del usuario"""
    logout_user()
    flash('¡Sesión cerrada exitosamente!', 'info')
    return redirect(url_for('index'))

# ========== RUTAS DE INICIALIZACIÓN ==========
@app.route('/init')
def init_db():
    """Inicializar base de datos - RUTA ESPECIAL PARA VERCEL"""
    try:
        with app.app_context():
            # Crear todas las tablas
            db.create_all()
            
            # Crear usuarios por defecto
            usuarios_creados = []
            
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                usuarios_creados.append('admin:admin123')
            
            if not User.query.filter_by(username='coordinador').first():
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
                usuarios_creados.append('coordinador:coordinadorUMB2026')
            
            if not User.query.filter_by(username='rector').first():
                rector = User(username='rector')
                rector.set_password('rectorUMB2026')
                db.session.add(rector)
                usuarios_creados.append('rector:rectorUMB2026')
            
            db.session.commit()
            
            # Verificar tablas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tablas = inspector.get_table_names()
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>✅ Sistema Inicializado</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>
                    body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
                    .card {{ border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
                    .success-icon {{ color: #28a745; font-size: 4rem; }}
                </style>
            </head>
            <body class="d-flex align-items-center">
                <div class="container">
                    <div class="row justify-content-center">
                        <div class="col-md-8 col-lg-6">
                            <div class="card p-4">
                                <div class="text-center mb-4">
                                    <div class="success-icon">
                                        <i class="bi bi-check-circle-fill"></i>
                                    </div>
                                    <h1 class="text-success">✅ Sistema Inicializado</h1>
                                </div>
                                
                                <div class="alert alert-success">
                                    <h5>Base de datos configurada exitosamente</h5>
                                    <p><strong>URL:</strong> {DATABASE_URL[:50]}...</p>
                                    <p><strong>Tablas creadas:</strong> {', '.join(tablas)}</p>
                                </div>
                                
                                <div class="alert alert-info">
                                    <h5>👤 Usuarios disponibles:</h5>
                                    <ul class="mb-0">
                                        {' '.join([f'<li><strong>{u.split(":")[0]}</strong> / {u.split(":")[1]}</li>' for u in usuarios_creados])}
                                    </ul>
                                </div>
                                
                                <div class="d-grid gap-2">
                                    <a href="/login" class="btn btn-success btn-lg">
                                        <i class="bi bi-box-arrow-in-right"></i> Ir al Login
                                    </a>
                                    <a href="/test-db" class="btn btn-outline-primary">
                                        <i class="bi bi-database-check"></i> Probar Conexión
                                    </a>
                                    <a href="/dashboard" class="btn btn-outline-secondary">
                                        <i class="bi bi-speedometer2"></i> Ir al Dashboard
                                    </a>
                                </div>
                                
                                <div class="mt-4 text-center text-muted">
                                    <small>Sistema de Control de Egresados - UMB © {datetime.now().year}</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Bootstrap Icons -->
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
            </body>
            </html>
            '''
                
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>❌ Error de Inicialización</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light d-flex align-items-center">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card shadow">
                            <div class="card-body text-center">
                                <h1 class="text-danger">❌ Error de Inicialización</h1>
                                <div class="alert alert-danger mt-3">
                                    <p><strong>Error:</strong> {str(e)}</p>
                                </div>
                                <a href="/" class="btn btn-secondary mt-3">Volver al inicio</a>
                            </div>
                        </div>
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
        with app.app_context():
            # Probar conexión y conteo
            count_egresados = Egresado.query.count()
            count_users = User.query.count()
            
            # Obtener algunos egresados de ejemplo
            egresados = Egresado.query.limit(5).all()
            
            return jsonify({
                'status': 'success',
                'message': '✅ Conexión exitosa a la base de datos',
                'database': 'Neon PostgreSQL' if 'neon' in DATABASE_URL or 'postgresql' in DATABASE_URL else 'SQLite',
                'stats': {
                    'total_egresados': count_egresados,
                    'total_usuarios': count_users
                },
                'ejemplos': [
                    {
                        'id': e.id,
                        'matricula': e.matricula,
                        'nombre': e.nombre_completo,
                        'carrera': e.carrera,
                        'estatus': e.estatus
                    } for e in egresados
                ] if egresados else []
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database_url': DATABASE_URL[:100] + '...' if DATABASE_URL else 'No configurada'
        }), 500

# ========== EXPORTACIÓN DE DATOS ==========
@app.route('/exportar/<formato>')
@login_required
def exportar_egresados(formato):
    """Exportar egresados a Excel, CSV o PDF"""
    try:
        # Obtener todos los egresados
        egresados = Egresado.query.all()
        
        if formato == 'excel':
            # Exportar a Excel
            datos = []
            for e in egresados:
                datos.append({
                    'Matrícula': e.matricula,
                    'Nombre Completo': e.nombre_completo,
                    'Carrera': e.carrera,
                    'Generación': e.generacion,
                    'Estatus': e.estatus,
                    'Teléfono': e.telefono,
                    'Email': e.email,
                    'Fecha Registro': e.fecha_registro.strftime('%d/%m/%Y') if e.fecha_registro else ''
                })
            
            df = pd.DataFrame(datos)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Egresados')
            
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
            output.write('Matrícula,Nombre Completo,Carrera,Generación,Estatus,Teléfono,Email,Fecha Registro\n'.encode('utf-8'))
            
            for e in egresados:
                linea = f'"{e.matricula}","{e.nombre_completo}","{e.carrera}","{e.generacion}","{e.estatus}","{e.telefono}","{e.email}","{e.fecha_registro.strftime("%d/%m/%Y") if e.fecha_registro else ""}"\n'
                output.write(linea.encode('utf-8'))
            
            output.seek(0)
            return send_file(
                output,
                download_name=f'egresados_umb_{datetime.now().strftime("%Y%m%d")}.csv',
                as_attachment=True,
                mimetype='text/csv'
            )
        
        elif formato == 'pdf':
            # Exportar a PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            elements = []
            styles = getSampleStyleSheet()
            
            # Título
            title = Paragraph(f"<para align=center><b>REPORTE DE EGRESADOS UMB</b><br/>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</para>", styles["Heading1"])
            elements.append(title)
            elements.append(Paragraph("<br/>", styles["Normal"]))
            
            # Tabla de datos
            tabla_datos = [['Matrícula', 'Nombre', 'Carrera', 'Generación', 'Estatus']]
            for e in egresados:
                tabla_datos.append([e.matricula, e.nombre_completo[:30], e.carrera[:25], e.generacion, e.estatus])
            
            tabla = Table(tabla_datos, colWidths=[70, 140, 120, 60, 70])
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#A9D979')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            
            elements.append(tabla)
            doc.build(elements)
            buffer.seek(0)
            
            return send_file(
                buffer,
                download_name=f'Reporte_Egresados_UMB_{datetime.now().strftime("%Y%m%d")}.pdf',
                as_attachment=True,
                mimetype='application/pdf'
            )
        
        flash('Formato no válido', 'warning')
        return redirect('/dashboard')
        
    except Exception as e:
        print(f"❌ Error al exportar: {str(e)}")
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

# ========== RUTA PARA VER EGRESADO ==========
@app.route('/egresado/<int:id>')
def ver_egresado(id):
    """Ver información detallada de un egresado"""
    try:
        egresado = Egresado.query.get_or_404(id)
        return render_template('ver_egresado.html', egresado=egresado)
    except Exception as e:
        flash(f'Error al cargar información del egresado: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

# ========== CONTEXT PROCESSOR ==========
@app.context_processor
def inject_now():
    return {
        'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
        'anio_actual': datetime.now().strftime('%Y')
    }

# ========== EJECUTAR LOCALMENTE ==========
if __name__ == '__main__':
    print("=" * 60)
    print("SISTEMA DE CONTROL DE EGRESADOS - UMB")
    print("Modo: DESARROLLO LOCAL")
    print("=" * 60)
    print("Instrucciones:")
    print("1. Visita http://localhost:5000/init para inicializar BD")
    print("2. Usuario: coordinador / Contraseña: coordinadorUMB2026")
    print("3. Visita http://localhost:5000/test-db para probar conexión")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

# ========== PARA VERCEL ==========
application = app