

/* dashboard */


document.addEventListener('DOMContentLoaded', function() {
    // Buscador
    const searchInput = document.getElementById('searchInput');
    const table = document.getElementById('egresadosTable');
    
    if (searchInput && table) {
        searchInput.addEventListener('keyup', function() {
            const filter = this.value.toLowerCase();
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            
            for (let row of rows) {
                const cells = row.getElementsByTagName('td');
                let found = false;
                
                for (let cell of cells) {
                    if (cell.textContent.toLowerCase().includes(filter)) {
                        found = true;
                        break;
                    }
                }
                
                row.style.display = found ? '' : 'none';
            }
        });
    }
    
    // Modal de eliminación
    const deleteButtons = document.querySelectorAll('.delete-btn');
    const deleteForm = document.getElementById('deleteForm');
    const deleteModal = document.getElementById('confirmDeleteModal');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Obtener datos del egresado
            const id = this.getAttribute('data-id');
            const matricula = this.getAttribute('data-matricula');
            const nombre = this.getAttribute('data-nombre');
            const carrera = this.getAttribute('data-carrera');
            const generacion = this.getAttribute('data-generacion');
            const estatus = this.getAttribute('data-estatus');
            
            // Actualizar contenido del modal
            document.getElementById('deleteMatricula').textContent = matricula;
            document.getElementById('deleteNombre').textContent = nombre;
            document.getElementById('deleteCarrera').textContent = carrera;
            document.getElementById('deleteGeneracion').textContent = generacion;
            
            // Estilo para el badge de estatus
            const estatusBadge = document.getElementById('deleteEstatus');
            estatusBadge.textContent = estatus;
            estatusBadge.className = 'badge ';
            
            if (estatus === 'Titulado') {
                estatusBadge.classList.add('bg-success');
            } else if (estatus === 'Egresado') {
                estatusBadge.classList.add('bg-primary');
            } else {
                estatusBadge.classList.add('bg-warning', 'text-dark');
            }
            
            // Actualizar acción del formulario
            deleteForm.action = `/eliminar/${id}`;
        });
    });
    
    // Limpiar modal al cerrar
    if (deleteModal) {
        deleteModal.addEventListener('hidden.bs.modal', function () {
            document.getElementById('deleteMatricula').textContent = '';
            document.getElementById('deleteNombre').textContent = '';
            document.getElementById('deleteCarrera').textContent = '';
            document.getElementById('deleteGeneracion').textContent = '';
            document.getElementById('deleteEstatus').textContent = '';
            deleteForm.action = '';
        });
    }
});



// Editar Egresado - Validación de formulario y mejoras de UX

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('editarEgresadoForm');
    
    // Validación al enviar
    form.addEventListener('submit', function(e) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                showFieldError(field, 'Este campo es obligatorio');
                isValid = false;
                
                if (isValid === false) {
                    field.focus();
                }
            } else {
                clearFieldError(field);
            }
        });
        
        if (!isValid) {
            e.preventDefault();
            
            // Mostrar mensaje de error general
            const errorAlert = document.createElement('div');
            errorAlert.className = 'alert alert-danger alert-dismissible fade show mt-3';
            errorAlert.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Error:</strong> Por favor completa todos los campos obligatorios correctamente.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            // Insertar después del formulario
            form.parentNode.insertBefore(errorAlert, form.nextSibling);
            
            setTimeout(() => {
                if (errorAlert.parentNode) {
                    errorAlert.remove();
                }
            }, 5000);
        } else {
            // Animación de éxito antes de enviar
            const submitBtn = form.querySelector('.btn-primary-lg');
            const originalText = submitBtn.innerHTML;
            
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Actualizando...';
            submitBtn.disabled = true;
            
            // Simular carga (en producción esto ocurriría realmente)
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 1500);
        }
    });
    
    // Funciones de ayuda
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
        field.classList.remove('is-invalid');
        
        // Remover mensaje si existe
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }
    
    // Mejorar experiencia de usuario
    const inputs = form.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            if (!this.disabled) {
                this.parentNode.style.transform = 'scale(1.02)';
            }
        });
        
        input.addEventListener('blur', function() {
            this.parentNode.style.transform = 'scale(1)';
        });
    });
    
    // Asegurar que el texto del botón Cancelar sea negro en hover
    const cancelBtn = document.querySelector('.btn-cancel-lg');
    if (cancelBtn) {
        cancelBtn.addEventListener('mouseenter', function() {
            this.style.color = '#000000';
        });
        
        cancelBtn.addEventListener('mouseleave', function() {
            this.style.color = '';
        });
    }
});



// Formularios

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('egresadoForm');
    const matriculaInput = document.getElementById('matricula');
    
    // Validación de matrícula en tiempo real
    if (matriculaInput) {
        matriculaInput.addEventListener('input', function() {
            // Solo números
            this.value = this.value.replace(/\D/g, '');
            
            // Limitar a 8 dígitos
            if (this.value.length > 8) {
                this.value = this.value.slice(0, 8);
            }
            
            // Validación visual
            validateMatricula(this);
        });
        
        matriculaInput.addEventListener('blur', function() {
            validateMatricula(this);
        });
    }
    
    // Validación al enviar
    form.addEventListener('submit', function(e) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                showFieldError(field, 'Este campo es obligatorio');
                isValid = false;
                
                if (isValid === false) {
                    field.focus();
                }
            } else {
                clearFieldError(field);
            }
        });
        
        // Validación específica para matrícula
        if (matriculaInput && matriculaInput.value.trim()) {
            if (matriculaInput.value.length !== 8) {
                showFieldError(matriculaInput, 'La matrícula debe tener 8 dígitos');
                isValid = false;
                matriculaInput.focus();
            }
        }
        
        if (!isValid) {
            e.preventDefault();
            
            // Mostrar mensaje de error general
            const errorAlert = document.createElement('div');
            errorAlert.className = 'alert alert-danger alert-dismissible fade show mt-3';
            errorAlert.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Error:</strong> Por favor completa todos los campos obligatorios correctamente.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            // Insertar después del formulario
            form.parentNode.insertBefore(errorAlert, form.nextSibling);
            
            setTimeout(() => {
                if (errorAlert.parentNode) {
                    errorAlert.remove();
                }
            }, 5000);
        } else {
            // Animación de éxito antes de enviar
            const submitBtn = form.querySelector('.btn-primary-lg');
            const originalText = submitBtn.innerHTML;
            
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Guardando...';
            submitBtn.disabled = true;
            
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 1500);
        }
    });
    
    // Funciones de ayuda
    function validateMatricula(field) {
        const value = field.value.trim();
        
        if (value.length === 0) {
            clearFieldError(field);
            return;
        }
        
        if (value.length === 8) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            clearFieldError(field);
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            showFieldError(field, `Faltan ${8 - value.length} dígitos`);
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
        field.classList.remove('is-invalid');
        
        // Remover mensaje si existe
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }
    
    // Mejorar experiencia de usuario
    const inputs = form.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentNode.style.transform = 'scale(1.02)';
        });
        
        input.addEventListener('blur', function() {
            this.parentNode.style.transform = 'scale(1)';
        });
    });
    
    const cancelBtn = document.querySelector('.btn-cancel-lg');
    if (cancelBtn) {
        cancelBtn.addEventListener('mouseenter', function() {
            this.style.color = '#000000';
        });
        
        cancelBtn.addEventListener('mouseleave', function() {
            this.style.color = '';
        });
    }
});
