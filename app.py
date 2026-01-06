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
from dotenv import load_dotenv

# ========== CONFIGURACIÓN PARA VERCEL ==========

# En Vercel, las variables de entorno vienen de os.environ, no de .env
app = Flask(__name__)

# Asegurar que DATABASE_URL esté correctamente formateada
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# DEBUG: Verificar si las variables están cargadas
print("=" * 60)
print("🚀 INICIANDO APLICACIÓN EN VERCEL")
print(f"✅ DATABASE_URL configurada: {'SÍ' if DATABASE_URL else 'NO'}")
print(f"✅ SECRET_KEY configurada: {'SÍ' if os.environ.get('SECRET_KEY') else 'NO'}")
print("=" * 60)

# Corregir formato de DATABASE_URL si es necesario
if DATABASE_URL:
    # Asegurar que sea postgresql:// no postgres://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Asegurar que tenga sslmode=require
    if 'sslmode' not in DATABASE_URL:
        if '?' in DATABASE_URL:
            DATABASE_URL += '&sslmode=require'
        else:
            DATABASE_URL += '?sslmode=require'
else:
    # Si no hay DATABASE_URL en Vercel, usar SQLite temporal
    print("⚠️  ADVERTENCIA: DATABASE_URL no encontrada, usando SQLite temporal")
    DATABASE_URL = 'sqlite:////tmp/temp.db'

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
    """Inicializar la base de datos al arrancar la aplicación"""
    try:
        with app.app_context():
            print("🔧 Creando tablas en la base de datos...")
            db.create_all()
            
            # Crear usuario admin por defecto si no existe
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
            
            # Crear usuario coordinador por defecto si no existe
            coordinador_user = User.query.filter_by(username='coordinador').first()
            if not coordinador_user:
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
            
            db.session.commit()
            print("✅ Base de datos inicializada correctamente")
            
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {str(e)}")
        # No hacemos exit(1) para que la aplicación pueda continuar

# Llamar a la inicialización al importar
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
            
            # Validar campos obligatorios
            if not all([matricula, nombre_completo, carrera, generacion, estatus]):
                flash('Todos los campos obligatorios deben ser completados', 'warning')
                return redirect(url_for('formularios'))
            
            # Validar matrícula única
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

# ========== API REST PARA CRUD (AGREGADO) ==========

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

@app.route('/init')
def init_db():
    """Inicializar base de datos (para Vercel)"""
    try:
        with app.app_context():
            db.create_all()
            
            # Crear usuarios por defecto si no existen
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                
            if not User.query.filter_by(username='coordinador').first():
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
            
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
                    <p>El sistema ha sido configurado correctamente en Neon PostgreSQL.</p>
                    
                    <div class="info">
                        <h3>Credenciales de acceso:</h3>
                        <p><strong>Usuario:</strong> coordinador</p>
                        <p><strong>Contraseña:</strong> coordinadorUMB2026</p>
                        <p><strong>Usuario:</strong> admin</p>
                        <p><strong>Contraseña:</strong> admin123</p>
                        <p>Base de datos: Neon PostgreSQL (Vercel)</p>
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
            'database': 'Neon PostgreSQL' if 'neon' in DATABASE_URL else 'SQLite temporal',
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

# ========== EXPORTACIÓN DE DATOS MEJORADA ==========

@app.route('/exportar/<formato>')
@login_required
def exportar_egresados(formato):
    """Exportar egresados a Excel, CSV o PDF - VERSIÓN MEJORADA"""
    try:
        # Obtener todos los egresados
        egresados = Egresado.query.all()
        
        # Calcular estadísticas
        total_egresados = len(egresados)
        titulados = len([e for e in egresados if e.estatus == 'Titulado'])
        egresados_count = len([e for e in egresados if e.estatus == 'Egresado'])
        seguimiento = len([e for e in egresados if e.estatus == 'En seguimiento'])
        
        # Preparar datos - solo con campos que tienes
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
            # Escribir encabezados
            output.write('Matrícula,Nombre Completo,Carrera,Generación,Estatus\n'.encode('utf-8'))
            # Escribir datos
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
            # Exportar a PDF en orientación horizontal para más espacio
            buffer = BytesIO()
            
            # Crear documento PDF en orientación horizontal
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                                    rightMargin=30, leftMargin=30,
                                    topMargin=30, bottomMargin=30)
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            
            # Título
            title = Paragraph(
                f"<para align=center><b>REPORTE DE EGRESADOS</b><br/>"
                f"<font size=12>Universidad Mexiquense del Bicentenario</font><br/>"
                f"<font size=10>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</font></para>", 
                styles["Heading1"]
            )
            elements.append(title)
            
            # Espacio
            elements.append(Paragraph("<br/>", styles["Normal"]))
            
            # Preparar datos para la tabla - mostrar más texto
            tabla_datos = [['MATRÍCULA', 'NOMBRE COMPLETO', 'CARRERA', 'GENERACIÓN', 'ESTATUS']]
            
            for e in egresados:
                # Mostrar el nombre completo (hasta 40 caracteres) y la carrera completa (sin truncar mucho)
                nombre = e.nombre_completo[:40] + '...' if len(e.nombre_completo) > 40 else e.nombre_completo
                carrera = e.carrera[:60] + '...' if len(e.carrera) > 60 else e.carrera
                tabla_datos.append([
                    e.matricula,
                    nombre,
                    carrera,
                    e.generacion,
                    e.estatus
                ])
            
            # Crear tabla con anchos ajustados (orientación horizontal da más espacio)
            # Anchos: Matrícula, Nombre, Carrera, Generación, Estatus
            tabla = Table(tabla_datos, colWidths=[80, 150, 280, 80, 70])
            tabla.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),  # Verde UMB
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
                # Filas alternadas
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
                # Alineación
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Matrícula centrada
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Generación centrada
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Estatus centrado
                # Ajuste de texto para la carrera
                ('WORDWRAP', (2, 1), (2, -1), True),
            ]))
            
            elements.append(tabla)
            
            # Estadísticas
            elements.append(Paragraph("<br/><br/>", styles["Normal"]))
            
            # Crear tabla de resumen
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
            
            # Generar PDF
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

# ========== RUTA ADICIONAL PARA VER EGRESADO ==========

@app.route('/egresado/<int:id>')
def ver_egresado(id):
    """Ver información detallada de un egresado"""
    try:
        egresado = Egresado.query.get_or_404(id)
        return render_template('ver_egresado.html', egresado=egresado)
    except Exception as e:
        flash(f'Error al cargar información del egresado: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

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

# ========== EJECUTAR APLICACIÓN ==========

if __name__ == '__main__':
    print("=" * 60)
    print("SISTEMA DE CONTROL DE EGRESADOS - UMB")
    print("Modo: DESARROLLO LOCAL")
    print("=" * 60)
    print("Instrucciones:")
    print("1. Visita http://localhost:5000/init para inicializar BD")
    print("2. Usuario: coordinador / Contraseña: coordinadorUMB2026")
    print("3. O Usuario: admin / Contraseña: admin123")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

# ========== PARA VERCEL ==========
# Vercel necesita esta variable para funcionar correctamente
application = app