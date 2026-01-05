import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-123456-ues-san-jose'

# CONFIGURACIÓN PARA XAMPP MYSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/proyecto_egresados'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("✅ Usando MySQL (Desarrollo local - XAMPP)")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

# Modelos de Base de Datos (versión simplificada - sin columnas de fecha adicionales)
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

# Crear tablas automáticamente al iniciar
def init_database():
    try:
        with app.app_context():
            db.create_all()
            
            # Crear usuario administrador por defecto si no existe
            if not User.query.filter_by(username='coordinador').first():
                coordinador = User(username='coordinador')
                coordinador.set_password('coordinadorUMB2026')
                db.session.add(coordinador)
                db.session.commit()
                print("✅ Usuario coordinador creado: coordinador / coordinadorUMB2026")
            
            print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")

# Inicializar la base de datos
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
    # Obtener todos los egresados para la tabla
    lista_egresados = Egresado.query.order_by(Egresado.nombre_completo).all()
    
    # Estadísticas (usando consultas para eficiencia)
    total_egresados = len(lista_egresados)
    
    # Contar por estatus
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
            
            # Validaciones básicas
            if not matricula or not nombre_completo or not carrera or not generacion or not estatus:
                flash('Todos los campos obligatorios deben ser completados', 'warning')
                return redirect(url_for('formularios'))
            
            if len(matricula) != 8:
                flash('La matrícula debe tener exactamente 8 caracteres', 'warning')
                return redirect(url_for('formularios'))
            
            # Verificar si la matrícula ya existe
            if Egresado.query.filter_by(matricula=matricula).first():
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
            # Actualizar datos
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
            'email': e.email
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
        
        # Validar datos requeridos
        required_fields = ['matricula', 'nombre_completo', 'carrera', 'generacion', 'estatus']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Campo requerido faltante: {field}'
                }), 400
        
        # Verificar matrícula única
        if Egresado.query.filter_by(matricula=data['matricula']).first():
            return jsonify({
                'success': False,
                'error': 'La matrícula ya está registrada'
            }), 400
        
        # Crear nuevo egresado
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
        
        # Actualizar campos permitidos
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

# ========== RUTAS UTILITARIAS ==========

@app.route('/init')
def init_db():
    """Inicializar base de datos (crear tablas y usuario admin)"""
    try:
        with app.app_context():
            db.create_all()
            
            # Crear usuario admin si no existe
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
                    <title>✅ Sistema listo</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                </head>
                <body class="bg-light">
                    <div class="container py-5">
                        <div class="card shadow">
                            <div class="card-body text-center">
                                <h1 class="text-success">✅ Sistema listo</h1>
                                <p class="lead">La base de datos ya está configurada.</p>
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
                        <p>Verifica que XAMPP esté corriendo y MySQL esté activo.</p>
                        <a href="/" class="btn btn-secondary mt-3">Volver al inicio</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''

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


from datetime import datetime

@app.context_processor
def inject_now():
    return {'fecha_actual': datetime.now().strftime('%d/%m/%Y')}


@app.route('/egresado/<int:id>')
def ver_egresado(id):
    egresado = Egresado.query.get_or_404(id)
    return render_template('ver_egresado.html', egresado=egresado)



import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from flask import send_file, make_response, redirect
from datetime import datetime

@app.route('/exportar/<formato>')
def exportar_egresados(formato):
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


@app.context_processor
def inject_now():
    from datetime import datetime
    return {'fecha_actual': datetime.now().strftime('%d/%m/%Y')}






# ========== INICIO DE LA APLICACIÓN ==========

if __name__ == '__main__':
    print("=" * 50)
    print("SISTEMA DE CONTROL DE EGRESADOS - UES SAN JOSÉ DEL RINCÓN")
    print("=" * 50)
    print("Modo: DESARROLLO")
    print("Base de datos: XAMPP MySQL")
    print("=" * 50)
    print("Instrucciones:")
    print("1. Asegúrate de que XAMPP esté corriendo (MySQL y Apache)")
    print("2. Visita http://localhost:5000/init para inicializar BD")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)