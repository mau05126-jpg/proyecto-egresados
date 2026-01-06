/**
 * SISTEMA DE CONTROL DE EGRESADOS - UMB
 * JavaScript unificado y corregido
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Script cargado correctamente');
    
    // ========== DASHBOARD - BÚSQUEDA ==========
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('#egresadosTable tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    }
    
    // ========== DASHBOARD - MODAL DE ELIMINACIÓN ==========
    const deleteModal = document.getElementById('confirmDeleteModal');
    if (deleteModal) {
        // Usar el evento de Bootstrap 5 para el modal
        deleteModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget; // Botón que activó el modal
            
            // Obtener datos de los atributos data-*
            const id = button.getAttribute('data-id');
            const matricula = button.getAttribute('data-matricula');
            const nombre = button.getAttribute('data-nombre');
            const carrera = button.getAttribute('data-carrera');
            const generacion = button.getAttribute('data-generacion');
            const estatus = button.getAttribute('data-estatus');
            
            // Actualizar contenido del modal
            document.getElementById('deleteMatricula').textContent = matricula;
            document.getElementById('deleteNombre').textContent = nombre;
            document.getElementById('deleteCarrera').textContent = carrera;
            document.getElementById('deleteGeneracion').textContent = generacion;
            
            // Actualizar badge de estatus
            const estatusBadge = document.getElementById('deleteEstatus');
            estatusBadge.textContent = estatus;
            estatusBadge.className = 'badge ' + 
                (estatus === 'Titulado' ? 'bg-success' : 
                 estatus === 'Egresado' ? 'bg-primary' : 
                 'bg-warning text-dark');
            
            // Actualizar acción del formulario
            document.getElementById('deleteForm').action = '/eliminar/' + id;
        });
        
        // Limpiar modal al cerrar
        deleteModal.addEventListener('hidden.bs.modal', function() {
            document.getElementById('deleteMatricula').textContent = '';
            document.getElementById('deleteNombre').textContent = '';
            document.getElementById('deleteCarrera').textContent = '';
            document.getElementById('deleteGeneracion').textContent = '';
            document.getElementById('deleteEstatus').textContent = '';
            document.getElementById('deleteForm').action = '';
        });
    }
    
    // ========== FORMULARIOS - VALIDACIÓN GENERAL ==========
    
    // Validación para formulario de NUEVO egresado
    const formEgresado = document.getElementById('egresadoForm');
    if (formEgresado) {
        setupFormValidation(formEgresado, 'guardar');
    }
    
    // Validación para formulario de EDITAR egresado
    const formEditar = document.getElementById('editarEgresadoForm');
    if (formEditar) {
        setupFormValidation(formEditar, 'actualizar');
    }
    
    // ========== VALIDACIÓN DE MATRÍCULA EN TIEMPO REAL ==========
    const matriculaInputs = document.querySelectorAll('input[name="matricula"], #matricula');
    matriculaInputs.forEach(input => {
        input.addEventListener('input', function() {
            // Solo números y limitar a 20 caracteres (PostgreSQL permite hasta 20)
            this.value = this.value.replace(/\D/g, '');
            
            if (this.value.length > 20) {
                this.value = this.value.slice(0, 20);
            }
            
            // Validación visual
            validateMatricula(this);
        });
        
        input.addEventListener('blur', function() {
            validateMatricula(this);
        });
    });
    
    // ========== MEJORAS DE UX ==========
    
    // Efecto hover en campos
    const formInputs = document.querySelectorAll('.form-control, .form-select');
    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('input-focused');
        });
    });
    
    // Auto-ocultar alertas después de 5 segundos
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });
    
    // ========== FUNCIONES AUXILIARES ==========
    
    function setupFormValidation(form, actionType) {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    showFieldError(field, 'Este campo es obligatorio');
                    isValid = false;
                    
                    // Enfocar el primer campo inválido
                    if (!isValid) {
                        field.focus();
                    }
                } else {
                    clearFieldError(field);
                }
            });
            
            // Validación específica para matrícula
            const matriculaInput = form.querySelector('#matricula, input[name="matricula"]');
            if (matriculaInput && matriculaInput.value.trim()) {
                const value = matriculaInput.value.trim();
                if (value.length < 8 || value.length > 20) {
                    showFieldError(matriculaInput, 'La matrícula debe tener entre 8 y 20 dígitos');
                    isValid = false;
                    matriculaInput.focus();
                }
            }
            
            if (!isValid) {
                e.preventDefault();
                
                // Mostrar mensaje de error general
                showAlert(form, 'danger', 'Error: Por favor completa todos los campos obligatorios correctamente.');
            } else {
                // Animación de carga en el botón de enviar
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    const originalText = submitBtn.innerHTML;
                    const originalDisabled = submitBtn.disabled;
                    
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> ' + 
                                          (actionType === 'guardar' ? 'Guardando...' : 'Actualizando...');
                    submitBtn.disabled = true;
                    
                    // Si el formulario no se envía (error), restaurar botón después de 3 segundos
                    setTimeout(() => {
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = originalDisabled;
                    }, 3000);
                }
            }
        });
    }
    
    function validateMatricula(field) {
        const value = field.value.trim();
        
        if (value.length === 0) {
            clearFieldError(field);
            return;
        }
        
        if (value.length >= 8 && value.length <= 20) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            clearFieldError(field);
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            showFieldError(field, `La matrícula debe tener entre 8 y 20 dígitos (tienes ${value.length})`);
        }
    }
    
    function showFieldError(field, message) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
        
        // Remover mensaje anterior si existe
        let existingFeedback = field.parentNode.querySelector('.invalid-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        // Crear nuevo mensaje
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        field.parentNode.appendChild(feedback);
    }
    
    function clearFieldError(field) {
        field.classList.remove('is-invalid', 'is-valid');
        
        // Remover mensaje si existe
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }
    
    function showAlert(form, type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
        alertDiv.innerHTML = `
            <i class="bi ${type === 'danger' ? 'bi-exclamation-triangle' : 'bi-info-circle'} me-2"></i>
            <strong>${type === 'danger' ? 'Error:' : 'Información:'}</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        form.parentNode.insertBefore(alertDiv, form.nextSibling);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
});