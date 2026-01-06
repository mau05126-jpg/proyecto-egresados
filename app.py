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
            static_folder='static',  # Asegurar que encuentra archivos estáticos
            template_folder='templates')

# Obtener DATABASE_URL de las variables de entorno de Vercel
DATABASE_URL = os.environ.get('DATABASE_URL', '')

print("=" * 60)
print("🚀 SISTEMA DE CONTROL DE EGRESADOS - UMB")
print("📊 Configurando conexión a Neon PostgreSQL")
print(f"✅ DATABASE_URL configurada: {'SÍ' if DATABASE_URL else 'NO'}")
print("=" * 60)

# Formatear correctamente la URL para Neon PostgreSQL
if DATABASE_URL:
    # Asegurar que sea postgresql:// no postgres://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Agregar opciones SSL para Neon
    if 'sslmode' not in DATABASE_URL:
        if '?' in DATABASE_URL:
            DATABASE_URL += '&sslmode=require'
        else:
            DATABASE_URL += '?sslmode=require'
else:
    print("⚠️  ADVERTENCIA: DATABASE_URL no encontrada")
    print("ℹ️  Configurando base de datos en memoria para desarrollo")

# Configuración de la aplicación
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-umb-2026-sistema-egresados')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'connect_args': {
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
    }
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
    """Inicializar la base de datos"""
    try:
        with app.app_context():
            print("🔧 Verificando/Creando tablas en Neon PostgreSQL...")
            
            # Crear tablas si no existen
            db.create_all()
            
            # Verificar si ya hay usuarios
            users_count = User.query.count()
            egresados_count = Egresado.query.count()
            
            print(f"📊 Usuarios en sistema: {users_count}")
            print(f"📊 Egresados registrados: {egresados_count}")
            
            # Crear usuario admin si no existe
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                print("✅ Usuario admin creado: admin / admin123")
            
            # Crear usuario coordinador si no existe
            coordinador_user = User.query.filter_by(username='coordinador').first()
            if not coordinador_user:
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
                print("✅ Usuario coordinador creado: coordinador / coordinadorUMB2026")
            
            db.session.commit()
            print("✅ Base de datos inicializada correctamente en Neon")
            
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {str(e)}")
        print(f"🔧 DATABASE_URL: {DATABASE_URL[:50]}...")

# Llamar a la inicialización
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
        # Obtener todos los egresados
        lista_egresados = Egresado.query.order_by(Egresado.nombre_completo).all()
        
        # Calcular estadísticas
        total_egresados = len(lista_egresados)
        titulados = sum(1 for e in lista_egresados if e.estatus == 'Titulado')
        egresados_count = sum(1 for e in lista_egresados if e.estatus == 'Egresado')
        seguimiento = sum(1 for e in lista_egresados if e.estatus == 'En seguimiento')
        
        print(f"📊 Mostrando dashboard con {total_egresados} egresados")
        
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
            
            print(f"📝 Intentando registrar egresado: {nombre_completo}")
            
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
            
            print(f"✅ Egresado registrado: {nombre_completo} (ID: {nuevo_egresado.id})")
            flash(f'¡Egresado {nombre_completo} registrado exitosamente!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al registrar egresado: {str(e)}")
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
            
            print(f"✅ Egresado actualizado: {egresado.nombre_completo}")
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
            
            print(f"🗑️ Egresado eliminado: {nombre}")
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

# ========== RUTAS DE INICIALIZACIÓN Y DIAGNÓSTICO ==========
@app.route('/init')
def init_db():
    """Inicializar base de datos (para Vercel)"""
    try:
        with app.app_context():
            # Crear tablas
            db.create_all()
            
            # Verificar tablas creadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            # Crear usuarios por defecto
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                print("✅ Usuario admin creado")
                
            if not User.query.filter_by(username='coordinador').first():
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
                print("✅ Usuario coordinador creado")
            
            db.session.commit()
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>✅ Base de datos inicializada</title>
                <style>
                    body {{ font-family: Arial, sans-serif; background: #f5f5f5; }}
                    .container {{ max-width: 800px; margin: 50px auto; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .success {{ color: #28a745; }}
                    .info {{ background: #d1ecf1; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background: #007bff; color: white; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="success">✅ Base de datos inicializada</h1>
                    <p>El sistema ha sido configurado correctamente en Neon PostgreSQL.</p>
                    
                    <h3>📊 Tablas creadas:</h3>
                    <table>
                        <tr><th>Tabla</th><th>Estado</th></tr>
                        {' '.join([f'<tr><td>{table}</td><td>✅ Creada</td></tr>' for table in tables])}
                    </table>
                    
                    <div class="info">
                        <h3>👤 Credenciales de acceso:</h3>
                        <p><strong>Usuario coordinador:</strong> coordinador</p>
                        <p><strong>Contraseña:</strong> coordinadorUMB2026</p>
                        <p><strong>Usuario admin:</strong> admin</p>
                        <p><strong>Contraseña:</strong> admin123</p>
                        <p><strong>Base de datos:</strong> Neon PostgreSQL (Vercel)</p>
                    </div>
                    
                    <a href="/login" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px;">Ir al Login</a>
                    <a href="/test-db" style="display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px;">Probar Conexión</a>
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
                <p><strong>Error:</strong> {str(e)}</p>
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
        with app.app_context():
            # Probar conexión y conteo
            count_egresados = Egresado.query.count()
            count_users = User.query.count()
            
            # Obtener algunos egresados de ejemplo
            egresados = Egresado.query.limit(5).all()
            
            return jsonify({
                'status': 'success',
                'message': '✅ Conexión exitosa a la base de datos',
                'database': 'Neon PostgreSQL',
                'stats': {
                    'total_egresados': count_egresados,
                    'total_usuarios': count_users
                },
                'ejemplos': [
                    {
                        'id': e.id,
                        'matricula': e.matricula,
                        'nombre': e.nombre_completo
                    } for e in egresados
                ] if egresados else []
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database_url': DATABASE_URL[:50] + '...' if DATABASE_URL else 'No configurada'
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
        
        print(f"📤 Exportando {total_egresados} egresados en formato {formato}")
        
        # Preparar datos
        datos = []
        for e in egresados:
            datos.append({
                'Matrícula': e.matricula,
                'Nombre': e.nombre_completo,
                'Carrera': e.carrera,
                'Generación': e.generacion,
                'Estatus': e.estatus,
                'Teléfono': e.telefono,
                'Email': e.email,
                'Fecha Registro': e.fecha_registro.strftime('%d/%m/%Y') if e.fecha_registro else ''
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
            output.write('Matrícula,Nombre Completo,Carrera,Generación,Estatus,Teléfono,Email,Fecha Registro\n'.encode('utf-8'))
            # Escribir datos
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
            
            # Tabla de datos
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
            
            tabla = Table(tabla_datos, colWidths=[80, 150, 280, 80, 70])
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
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
            
            # Resumen
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
                "<font size=8><i>Sistema de Control de Egresados - UMB<br/>"
                "Base de datos: Neon PostgreSQL<br/>"
                "Documento generado automáticamente</i></font>",
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
        print(f"❌ Error al exportar: {str(e)}")
        flash(f'Error al exportar: {str(e)}', 'danger')
        return redirect('/dashboard')

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
    print("3. O Usuario: admin / Contraseña: admin123")
    print("4. Visita http://localhost:5000/test-db para probar conexión")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

# ========== PARA VERCEL ==========
application = app