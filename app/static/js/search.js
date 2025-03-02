document.addEventListener('DOMContentLoaded', function() {
    // Program search functionality
    const programSearchForm = document.getElementById('programSearch');
    const programResultsDiv = document.getElementById('program-results');
    const carreraSelect = document.getElementById('nombre-carrera');
    const anoAcademicoSelect = document.getElementById('ano-academico');
    
    // Load search options when page loads
    if (carreraSelect && anoAcademicoSelect) {
        fetch('/api/search_options')
            .then(response => response.json())
            .then(data => {
                // Populate career options
                data.careers.forEach(career => {
                    const option = document.createElement('option');
                    option.value = career.code;
                    option.textContent = `${career.name} (${career.code})`;
                    carreraSelect.appendChild(option);
                });
                
                // Populate academic year options
                data.academic_years.forEach(year => {
                    const option = document.createElement('option');
                    option.value = year;
                    option.textContent = year;
                    anoAcademicoSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading search options:', error);
                carreraSelect.innerHTML = '<option value="">Error cargando carreras</option>';
                anoAcademicoSelect.innerHTML = '<option value="">Error cargando años</option>';
            });
    }
    
    if (programSearchForm) {
        programSearchForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const nombreMateria = document.getElementById('nombre-materia').value.trim();
            const nombreCarrera = carreraSelect.value;
            const anoAcademico = anoAcademicoSelect.value;
            
            // Show loading state
            programResultsDiv.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Buscando programas...</p>
                </div>
            `;
            
            // Build API URL with search parameters
            let apiUrl = '/api/search_programs?';
            if (nombreMateria) apiUrl += `nombre_materia=${encodeURIComponent(nombreMateria)}&`;
            if (nombreCarrera) apiUrl += `nombre_carrera=${encodeURIComponent(nombreCarrera)}&`;
            if (anoAcademico) apiUrl += `ano_academico=${encodeURIComponent(anoAcademico)}&`;
            
            // Make API request
            fetch(apiUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Error en la respuesta del servidor');
                    }
                    return response.json();
                })
                .then(programs => {
                    if (programs.length === 0) {
                        programResultsDiv.innerHTML = `
                            <div class="alert alert-info">
                                No se encontraron programas con los criterios especificados.
                            </div>
                        `;
                    } else {
                        // Create table with results
                        let tableHtml = `
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead class="table-light">
                                        <tr>
                                            <th>Año Académico</th>
                                            <th>Materia</th>
                                            <th>Año de Cursada</th>
                                            <th>Acción</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                        `;
                        
                        // Add each program to the table
                        programs.forEach(program => {
                            const nombreMateria = program.nombre_materia || 'Sin nombre';
                            const anoAcademico = program.ano_academico || '-';
                            const anoPlan = program.ano_plan || '-';
                            const programId = program.id_programa;
                            
                            tableHtml += `
                                <tr>
                                    <td>${anoAcademico}</td>
                                    <td>${nombreMateria}</td>
                                    <td>${anoPlan}</td>
                                    <td>
                                        <a href="/download/programa/${programId}" class="btn btn-sm btn-primary" target="_blank">
                                            <i class="fas fa-download me-1"></i> Descargar
                                        </a>
                                    </td>
                                </tr>
                            `;
                        });
                        
                        tableHtml += `
                                    </tbody>
                                </table>
                            </div>
                        `;
                        
                        programResultsDiv.innerHTML = tableHtml;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    programResultsDiv.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            Error al buscar programas. Por favor, intente nuevamente.
                        </div>
                    `;
                });
        });
    }
    
    // Plan de Estudio search functionality
    const planSearchForm = document.getElementById('planSearch');
    const planResultsDiv = document.getElementById('plan-results');
    const planCarreraSelect = document.getElementById('plan-carrera');
    const vigenteSelect = document.getElementById('vigente');
    
    // Load planes options when page loads
    if (planCarreraSelect && vigenteSelect) {
        fetch('/api/planes_options')
            .then(response => response.json())
            .then(data => {
                // Populate career options
                data.careers.forEach(career => {
                    const option = document.createElement('option');
                    option.value = career.code;
                    option.textContent = `${career.name} (${career.code})`;
                    planCarreraSelect.appendChild(option);
                });
                
                // Populate vigencia options
                data.vigencia_states.forEach(state => {
                    const option = document.createElement('option');
                    option.value = state;
                    option.textContent = state === 'si' ? 'Vigente' : 'No vigente';
                    vigenteSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading planes options:', error);
                planCarreraSelect.innerHTML = '<option value="">Error cargando carreras</option>';
                vigenteSelect.innerHTML = '<option value="">Error cargando estados</option>';
            });
    }
    
    if (planSearchForm) {
        planSearchForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const carrera = planCarreraSelect.value;
            const vigente = vigenteSelect.value;
            
            // Show loading state
            planResultsDiv.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Buscando planes de estudio...</p>
                </div>
            `;
            
            // Build API URL with search parameters
            let apiUrl = '/api/search_planes?';
            if (carrera) apiUrl += `carrera=${encodeURIComponent(carrera)}&`;
            if (vigente) apiUrl += `vigente=${encodeURIComponent(vigente)}`;
            
            // Make API request
            fetch(apiUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Error en la respuesta del servidor');
                    }
                    return response.json();
                })
                .then(planes => {
                    if (planes.length === 0) {
                        planResultsDiv.innerHTML = `
                            <div class="alert alert-info">
                                No se encontraron planes de estudio con los criterios especificados.
                            </div>
                        `;
                    } else {
                        // Create cards with results
                        let cardsHtml = '<div class="row row-cols-1 row-cols-md-2 g-4">';
                        
                        // Add each plan to the cards
                        planes.forEach(plan => {
                            const nombre = plan.nombre || 'Sin nombre';
                            const anioVigencia = plan.anio_entrada_vigencia || '-';
                            const vigenteText = plan.vigente === 'si' ? 
                                '<span class="badge bg-success">Vigente</span>' : 
                                '<span class="badge bg-secondary">No vigente</span>';
                            const ordenanzas = plan.ordenanzas_resoluciones || '-';
                            const planId = plan.plan_version_SIU;
                            const hasUrl = !!plan.url_planEstudio;
                            
                            cardsHtml += `
                                <div class="col">
                                    <div class="card h-100">
                                        <div class="card-body">
                                            <h5 class="card-title">${nombre}</h5>
                                            <p class="card-text">
                                                <strong>Ordenanzas:</strong> ${ordenanzas}<br>
                                                <strong>Estado:</strong> ${vigenteText}
                                            </p>
                                        </div>
                                        <div class="card-footer bg-transparent border-0">
                                            ${hasUrl ? `
                                                <a href="/download/plan/${planId}" class="btn btn-primary w-100" target="_blank">
                                                    <i class="fas fa-file-pdf me-1"></i> Descargar Plan
                                                </a>
                                            ` : `
                                                <button class="btn btn-secondary w-100" disabled>
                                                    <i class="fas fa-exclamation-circle me-1"></i> Plan no disponible
                                                </button>
                                            `}
                                        </div>
                                    </div>
                                </div>
                            `;
                        });
                        
                        cardsHtml += '</div>';
                        planResultsDiv.innerHTML = cardsHtml;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    planResultsDiv.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            Error al buscar planes de estudio. Por favor, intente nuevamente.
                        </div>
                    `;
                });
        });
    }
});