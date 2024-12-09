document.addEventListener('DOMContentLoaded', function() {
    const activityForm = document.getElementById('activityForm');
    const dateSelector = document.getElementById('dateSelector');
    const locationSelector = document.getElementById('locationSelector');
    const locationInput = document.getElementById('location');
    let selectedDate = dateSelector.value;

    // Inicializar valores
    if (localStorage.getItem('selectedLocation')) {
        locationSelector.value = localStorage.getItem('selectedLocation');
    }
    locationInput.value = locationSelector.value;

    // Convertir horas a formato 12h en la tabla
    const timeCells = document.querySelectorAll('.time-cell');
    timeCells.forEach(cell => {
        const time24 = cell.textContent.trim();
        if (time24) {
            cell.textContent = format12Hour(time24);
        }
    });

    // Manejador del selector de ubicación
    locationSelector.addEventListener('change', function(e) {
        localStorage.setItem('selectedLocation', e.target.value);
        locationInput.value = e.target.value;
        showToast('Ubicación actualizada', 'success');
    });

    // Manejador del selector de fecha
    dateSelector.addEventListener('change', function(e) {
        selectedDate = e.target.value;
        window.location.href = `/?date=${selectedDate}`;
    });

    // Manejador del envío del formulario
    activityForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            date: selectedDate,
            start_time: document.getElementById('start_time').value,
            end_time: document.getElementById('end_time').value,
            description: document.getElementById('description').value,
            location: locationSelector.value
        };

        if (!validateForm(formData)) return;

        try {
            const response = await fetch('/add_activity', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                showToast('Actividad registrada exitosamente', 'success');
                clearForm();
                setTimeout(() => window.location.reload(), 1000);
            } else {
                const errorData = await response.json();
                showToast(errorData.error || 'Error al guardar la actividad', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error al guardar la actividad', 'error');
        }
    });
});

function validateForm(formData) {
    if (!formData.start_time || !formData.end_time || !formData.description) {
        showToast('Por favor, complete todos los campos', 'error');
        return false;
    }

    if (formData.start_time >= formData.end_time) {
        showToast('La hora de fin debe ser mayor que la hora de inicio', 'error');
        return false;
    }

    return true;
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'block';

    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

function clearForm() {
    document.getElementById('start_time').value = '';
    document.getElementById('end_time').value = '';
    document.getElementById('description').value = '';
}

async function deleteActivity(button) {
    if (!await showConfirmDialog(
        'Eliminar Actividad',
        '¿Estás seguro de que deseas eliminar esta actividad?'
    )) {
        return;
    }

    const row = button.closest('tr');
    const id = row.dataset.id;

    try {
        const response = await fetch(`/delete_activity/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('Actividad eliminada exitosamente', 'success');
            row.remove();
            if (document.querySelectorAll('#activitiesTable tbody tr').length === 0) {
                setTimeout(() => location.reload(), 1000);
            }
        } else {
            const errorData = await response.json();
            showToast(errorData.error || 'Error al eliminar la actividad', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error al eliminar la actividad', 'error');
    }
}

async function editActivity(button) {
    const row = button.closest('tr');
    const id = row.dataset.id;
    const cells = row.cells;

    // Convertir hora de 12h a 24h para edición
    const startTime24 = format24Hour(cells[0].textContent.trim());
    const endTime24 = format24Hour(cells[1].textContent.trim());

    const formData = {
        start_time: prompt('Hora de inicio (HH:MM):', startTime24),
        end_time: prompt('Hora de fin (HH:MM):', endTime24),
        description: prompt('Descripción:', cells[2].textContent.trim()),
        location: cells[3].textContent.trim()
    };

    if (!formData.start_time || !formData.end_time || !formData.description) {
        showToast('Todos los campos son requeridos', 'error');
        return;
    }

    const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
    if (!timeRegex.test(formData.start_time) || !timeRegex.test(formData.end_time)) {
        showToast('Formato de hora inválido (HH:MM)', 'error');
        return;
    }

    if (formData.start_time >= formData.end_time) {
        showToast('La hora de fin debe ser mayor que la hora de inicio', 'error');
        return;
    }

    try {
        const response = await fetch(`/edit_activity/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            cells[0].textContent = format12Hour(formData.start_time);
            cells[1].textContent = format12Hour(formData.end_time);
            cells[2].textContent = formData.description;
            showToast('Actividad actualizada exitosamente', 'success');
        } else {
            const errorData = await response.json();
            showToast(errorData.error || 'Error al editar la actividad', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error al editar la actividad', 'error');
    }
}

async function clearDatabase() {
    if (!await showConfirmDialog(
        'Limpiar Base de Datos',
        '¿Estás seguro de que deseas eliminar todas las actividades? Esta acción no se puede deshacer.'
    )) {
        return;
    }

    try {
        const response = await fetch('/clear_database', {
            method: 'POST'
        });

        if (response.ok) {
            showToast('Base de datos limpiada correctamente', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            const errorData = await response.json();
            showToast(errorData.error || 'Error al limpiar la base de datos', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error al limpiar la base de datos', 'error');
    }
}

function showConfirmDialog(title, message) {
    return new Promise((resolve) => {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        dialog.innerHTML = `
            <div class="confirm-dialog-content">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="confirm-dialog-buttons">
                    <button class="btn-secondary">Cancelar</button>
                    <button class="btn-danger">Eliminar</button>
                </div>
            </div>
        `;
        
        const overlay = document.createElement('div');
        overlay.className = 'confirm-dialog-overlay';
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        const cancelButton = dialog.querySelector('.btn-secondary');
        const confirmButton = dialog.querySelector('.btn-danger');
        
        cancelButton.onclick = () => {
            overlay.remove();
            resolve(false);
        };
        
        confirmButton.onclick = () => {
            overlay.remove();
            resolve(true);
        };
    });
}

function format12Hour(time24) {
    if (!time24) return '';
    try {
        const [hours24, minutes] = time24.split(':');
        const hours = parseInt(hours24);
        const period = hours >= 12 ? 'PM' : 'AM';
        const hours12 = hours % 12 || 12;
        return `${hours12.toString().padStart(2, '0')}:${minutes} ${period}`;
    } catch (error) {
        return time24;
    }
}

function format24Hour(time12) {
    if (!time12) return '';
    try {
        const [time, period] = time12.split(' ');
        let [hours, minutes] = time.split(':');
        hours = parseInt(hours);
        
        if (period === 'PM' && hours !== 12) {
            hours += 12;
        } else if (period === 'AM' && hours === 12) {
            hours = 0;
        }
        
        return `${hours.toString().padStart(2, '0')}:${minutes}`;
    } catch (error) {
        return time12;
    }
}
