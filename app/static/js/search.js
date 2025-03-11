// Get base URL path
const baseUrlPath = window.location.pathname.includes('/programas/') 
    ? '/programas' 
    : '';

document.addEventListener('DOMContentLoaded', function() {
    let planSearchTimeout;
    const programSearchForm = document.getElementById('programSearch');
    const planSearchForm = document.getElementById('planSearch');
    const planResults = document.getElementById('plan-results');
    const programResults = document.getElementById('program-results');

    // Populate career dropdowns
    fetch(`${baseUrlPath}/api/careers`)
        .then(response => response.json())
        .then(careers => {
            const careerSelects = document.querySelectorAll('#nombre-carrera, #plan-carrera');
            careerSelects.forEach(select => {
                careers.forEach(career => {
                    const option = document.createElement('option');
                    option.value = career.carrera;
                    option.textContent = career.nombre || career.carrera;
                    select.appendChild(option);
                });
            });
        });

    // Handle program search
    if (programSearchForm) {
        programSearchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchData = {
                nombre_materia: document.getElementById('nombre-materia').value,
                carrera: document.getElementById('nombre-carrera').value,
                ano: document.getElementById('ano-academico').value
            };

            fetch(`${baseUrlPath}/api/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(searchData)
            })
            .then(response => response.json())
            .then(results => {
                displayProgramResults(results);
            })
            .catch(error => {
                console.error('Error:', error);
                programResults.innerHTML = '<div class="alert alert-danger">Error al buscar programas</div>';
            });
        });
    }

    // Handle plan search
    if (planSearchForm) {
        planSearchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchData = {
                carrera: document.getElementById('plan-carrera').value,
                vigente: document.getElementById('vigente').value
            };

            clearTimeout(planSearchTimeout);
            planSearchTimeout = setTimeout(() => {
                fetch(`${baseUrlPath}/api/search_planes`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(searchData)
                })
                .then(response => response.json())
                .then(results => {
                    displayPlanResults(results);
                })
                .catch(error => {
                    console.error('Error:', error);
                    planResults.innerHTML = '<div class="alert alert-danger">Error al buscar planes</div>';
                });
            }, 300);
        });
    }

    function displayProgramResults(results) {
        if (!results || results.length === 0) {
            programResults.innerHTML = '<div class="text-center text-muted"><em>No se encontraron programas</em></div>';
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-hover">';
        html += '<thead class="table-primary"><tr>';
        html += '<th>Año</th><th>Carrera</th><th>Materia</th><th>Acción</th>';
        html += '</tr></thead><tbody>';

        results.forEach((program, index) => {
            html += '<tr>';
            html += `<td>${program.ano_academico}</td>`;
            html += `<td>${program.codigo_carrera}</td>`;
            html += `<td>${program.nombre_materia}</td>`;
            html += '<td>';
            html += `<a href="${baseUrlPath}/download/programa/old-${index + 1}" class="btn btn-sm btn-outline-primary">`;
            html += '<i class="fas fa-download me-1"></i> Descargar</a>';
            html += '</td>';
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        programResults.innerHTML = html;
    }

    function displayPlanResults(results) {
        if (!results || results.length === 0) {
            planResults.innerHTML = '<div class="text-center text-muted"><em>No se encontraron planes</em></div>';
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-hover">';
        html += '<thead class="table-primary"><tr>';
        html += '<th>Carrera</th><th>Plan</th><th>Estado</th><th>Ordenanzas</th><th>Acción</th>';
        html += '</tr></thead><tbody>';

        results.forEach(plan => {
            html += '<tr>';
            html += `<td>${plan.nombre || plan.carrera}</td>`;
            html += `<td>${plan.plan_version_SIU}</td>`;
            html += `<td>${plan.vigente === 'si' ? 'Vigente' : 'No vigente'}</td>`;
            html += `<td>${plan.ordenanzas_resoluciones}</td>`;
            html += '<td>';
            html += `<a href="${baseUrlPath}/download/plan/${encodeURIComponent(plan.plan_version_SIU)}" class="btn btn-sm btn-outline-primary">`;
            html += '<i class="fas fa-download me-1"></i> Descargar</a>';
            html += '</td>';
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        planResults.innerHTML = html;
    }
});