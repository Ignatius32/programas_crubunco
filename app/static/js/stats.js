document.addEventListener('DOMContentLoaded', function() {
    const baseUrlPath = window.location.pathname.includes('/programas/') 
        ? '/programas' 
        : '';

    const carreraSelect = document.getElementById('stats-carrera');
    const refreshBtn = document.getElementById('stats-refresh');
    const tableBody = document.querySelector('#stats-table tbody');
    const loading = document.getElementById('stats-loading');
    const summary = document.getElementById('stats-summary');
    const totalSpan = document.getElementById('stats-total');

    function setLoading(isLoading) {
        loading.classList.toggle('d-none', !isLoading);
    }

    let chart;

    function ensureChart(ctx, labels, totalData, histData, apiData) {
        if (chart) {
            chart.data.labels = labels;
            chart.data.datasets[0].data = totalData;
            chart.data.datasets[1].data = histData;
            chart.data.datasets[2].data = apiData;
            chart.update();
            return chart;
        }

        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Total',
                        data: totalData,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13,110,253,0.1)',
                        tension: 0.2,
                        borderWidth: 2,
                        pointRadius: 3
                    },
                    {
                        label: 'Histórico',
                        data: histData,
                        borderColor: '#6c757d',
                        backgroundColor: 'rgba(108,117,125,0.1)',
                        hidden: true,
                        tension: 0.2,
                        borderWidth: 2,
                        pointRadius: 3
                    },
                    {
                        label: 'API',
                        data: apiData,
                        borderColor: '#20c997',
                        backgroundColor: 'rgba(32,201,151,0.1)',
                        hidden: true,
                        tension: 0.2,
                        borderWidth: 2,
                        pointRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Año' }
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Cantidad' },
                        ticks: { precision: 0 }
                    }
                }
            }
        });
        return chart;
    }

    function renderStats(data) {
        tableBody.innerHTML = '';

        // Sort counts by year desc (they come sorted from server, but ensure)
        const counts = [...data.counts].sort((a, b) => (b.year || '').localeCompare(a.year || ''));
        counts.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.year}</td>
                <td class="text-end"><strong>${item.total}</strong></td>
                <td class="text-end">${item.hist}</td>
                <td class="text-end">${item.api}</td>
            `;
            tableBody.appendChild(tr);
        });

        totalSpan.textContent = data.total_programs || 0;
        summary.classList.toggle('d-none', false);

        // Render chart with ascending chronological order for better reading
        const ascending = [...counts].sort((a, b) => (a.year || '').localeCompare(b.year || ''));
        const labels = ascending.map(i => i.year);
        const totalData = ascending.map(i => i.total);
        const histData = ascending.map(i => i.hist);
        const apiData = ascending.map(i => i.api);

        const ctx = document.getElementById('stats-chart').getContext('2d');
        ensureChart(ctx, labels, totalData, histData, apiData);
    }

    function fetchStats() {
        setLoading(true);
        summary.classList.add('d-none');

        const params = new URLSearchParams();
        if (carreraSelect.value) {
            params.set('carrera', carreraSelect.value);
        }

        fetch(`${baseUrlPath}/api/stats/programs_per_year?${params.toString()}`)
            .then(resp => {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            })
            .then(data => {
                renderStats(data);
            })
            .catch(err => {
                console.error('Stats error:', err);
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-danger">
                            Error al cargar estadísticas
                        </td>
                    </tr>
                `;
            })
            .finally(() => setLoading(false));
    }

    // Initial load
    fetchStats();

    // Events
    refreshBtn.addEventListener('click', fetchStats);
    carreraSelect.addEventListener('change', fetchStats);

    // Initialize Bootstrap tooltips on this page
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
