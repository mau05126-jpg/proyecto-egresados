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

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========

print("=" * 60)
print("🚀 SISTEMA DE CONTROL DE EGRESADOS - UMB")
print("=" * 60)

# Configuración para local y Vercel
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    print("✅ DATABASE_URL encontrada (Vercel/Neon PostgreSQL)")
    # Corregir si viene como postgres://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    print("⚠️  Usando SQLite local para desarrollo")
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "egresados.db")}'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-umb-2026-sistema-egresados')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    return db.session.get(User, int(user_id))

# ========== INICIALIZACIÓN ==========

def init_database():
    try:
        with app.app_context():
            db.create_all()
            
            # Crear usuario coordinador por defecto si no existe
            if not User.query.filter_by(username='coordinador').first():
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
                db.session.commit()
                print("✅ Usuario coordinador creado")
            
            # Crear usuario admin si no existe
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ Usuario admin creado")
            
            print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")

init_database()

# ========== RUTAS PRINCIPALES ==========

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
            
            if not matricula or not nombre_completo or not carrera or not generacion or not estatus:
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
            flash(f'¡Información de {egresado.nombre_completo} actualizada exitosamente!', 'success')
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

# ========== API REST ==========

@app.route('/api/egresados', methods=['GET'])
@login_required
def api_get_egresados():
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

# ========== RUTAS UTILITARIAS ==========

@app.route('/init')
def init_db():
    try:
        init_database()
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
    try:
        count_egresados = Egresado.query.count()
        count_users = User.query.count()
        
        db_type = 'Neon PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite local'
        
        return jsonify({
            'status': 'success',
            'message': f'✅ Conexión exitosa a {db_type}',
            'database': db_type,
            'stats': {
                'egresados': count_egresados,
                'usuarios': count_users
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# ========== EXPORTACIÓN ==========

@app.route('/exportar/<formato>')
@login_required
def exportar_egresados(formato):
    try:
        egresados = Egresado.query.all()
        
        if not egresados:
            flash('No hay egresados para exportar', 'warning')
            return redirect(url_for('dashboard'))
        
        total_egresados = len(egresados)
        titulados = len([e for e in egresados if e.estatus == 'Titulado'])
        egresados_count = len([e for e in egresados if e.estatus == 'Egresado'])
        seguimiento = len([e for e in egresados if e.estatus == 'En seguimiento'])
        
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
            df = pd.DataFrame(datos)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Egresados')
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
            df = pd.DataFrame(datos)
            output = BytesIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            return send_file(
                output,
                download_name=f'egresados_umb_{datetime.now().strftime("%Y%m%d")}.csv',
                as_attachment=True,
                mimetype='text/csv'
            )
        
        elif formato == 'pdf':
            buffer = BytesIO()
            
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                                    rightMargin=30, leftMargin=30,
                                    topMargin=30, bottomMargin=30)
            elements = []
            
            styles = getSampleStyleSheet()
            
            title = Paragraph(
                f"<para align=center><b>REPORTE DE EGRESADOS - UMB</b><br/>"
                f"<font size=12>Universidad Mexiquense del Bicentenario</font><br/>"
                f"<font size=10>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</font></para>", 
                styles["Heading1"]
            )
            elements.append(title)
            
            elements.append(Paragraph("<br/>", styles["Normal"]))
            
            tabla_datos = [['MATRÍCULA', 'NOMBRE COMPLETO', 'CARRERA', 'GENERACIÓN', 'ESTATUS']]
            
            for e in egresados:
                nombre = e.nombre_completo[:35] + '...' if len(e.nombre_completo) > 35 else e.nombre_completo
                carrera = e.carrera[:30] + '...' if len(e.carrera) > 30 else e.carrera
                tabla_datos.append([
                    e.matricula,
                    nombre,
                    carrera,
                    e.generacion,
                    e.estatus
                ])
            
            tabla = Table(tabla_datos, colWidths=[80, 150, 150, 80, 80])
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
            ]))
            
            elements.append(tabla)
            
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
            
            elements.append(Paragraph("<br/><br/>", styles["Normal"]))
            footer = Paragraph(
                "<font size=8><i>Sistema de Control de Egresados - UMB<br/>"
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
        
        flash('Formato de exportación no válido', 'danger')
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
    return {'fecha_actual': datetime.now().strftime('%d/%m/%Y')}

# ========== EJECUCIÓN ==========

application = app

if __name__ == "__main__":
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