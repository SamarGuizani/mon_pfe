// ============================================
// SIM Box Fraud Detection - Dashboard JS
// ============================================

let currentPage = 1;

// Charger les stats au demarrage
document.addEventListener("DOMContentLoaded", () => {
    loadStats();
    loadTopSuspects();
    loadDistribution();
    loadSuspects(1);
});

// ============================================
// 1. STATISTIQUES GLOBALES
// ============================================
async function loadStats() {
    const res = await fetch("/api/stats");
    const data = await res.json();

    document.getElementById("total-msisdn").textContent = formatNumber(data.total_msisdn);
    document.getElementById("total-suspects").textContent = formatNumber(data.total_suspects);
    document.getElementById("taux-fraude").textContent = data.taux_fraude + "%";
    document.getElementById("avg-locations").textContent = Math.round(data.avg_locations);
}

// ============================================
// 2. TOP 10 SUSPECTS (Bar Chart)
// ============================================
async function loadTopSuspects() {
    const res = await fetch("/api/top_suspects");
    const data = await res.json();

    new Chart(document.getElementById("chart-top-suspects"), {
        type: "bar",
        data: {
            labels: data.map(d => d.msisdn),
            datasets: [{
                label: "Nombre d'appels",
                data: data.map(d => d.appels),
                backgroundColor: "rgba(0, 212, 255, 0.7)",
                borderColor: "#00d4ff",
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: "#7a8fa6" },
                    grid: { color: "#1e2d3d" }
                },
                x: {
                    ticks: { color: "#7a8fa6", font: { size: 11 } },
                    grid: { display: false }
                }
            }
        }
    });
}

// ============================================
// 3. DISTRIBUTION DES APPELS (Doughnut)
// ============================================
async function loadDistribution() {
    const res = await fetch("/api/distribution");
    const data = await res.json();

    const colors = [
        "#00d4ff", "#0099cc", "#006699",
        "#ffa502", "#ff6348", "#ff4757"
    ];

    new Chart(document.getElementById("chart-distribution"), {
        type: "doughnut",
        data: {
            labels: data.map(d => d.tranche + " appels"),
            datasets: [{
                data: data.map(d => d.count),
                backgroundColor: colors,
                borderColor: "#1a2332",
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "right",
                    labels: { color: "#e0e6ed", font: { size: 12 } }
                }
            }
        }
    });
}

// ============================================
// 4. TABLE DES SUSPECTS (avec pagination)
// ============================================
async function loadSuspects(page) {
    currentPage = page;
    const search = document.getElementById("search-input").value;
    const res = await fetch(`/api/suspects?page=${page}&per_page=15&search=${search}`);
    const data = await res.json();

    const tbody = document.getElementById("suspects-body");
    tbody.innerHTML = "";

    data.suspects.forEach(s => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${s.msisdn}</strong></td>
            <td class="${s.nombre_appels > 1000 ? 'high-danger' : s.nombre_appels > 200 ? 'medium-danger' : ''}">${formatNumber(s.nombre_appels)}</td>
            <td>${formatNumber(s.duree_totale)}</td>
            <td class="${s.ratio_courts > 70 ? 'high-danger' : s.ratio_courts > 40 ? 'medium-danger' : ''}">${s.ratio_courts}%</td>
            <td class="${s.nb_imei > 2 ? 'high-danger' : ''}">${s.nb_imei}</td>
            <td>${s.nb_cellules}</td>
            <td class="${s.appels_jour > 50 ? 'high-danger' : s.appels_jour > 20 ? 'medium-danger' : ''}">${s.appels_jour}</td>
            <td>${s.date_detection.substring(0, 10)}</td>
        `;
        tbody.appendChild(tr);
    });

    // Pagination
    renderPagination(data.page, data.pages);
}

function renderPagination(current, total) {
    const div = document.getElementById("pagination");
    div.innerHTML = "";

    // Previous
    if (current > 1) {
        const btn = document.createElement("button");
        btn.textContent = "Precedent";
        btn.onclick = () => loadSuspects(current - 1);
        div.appendChild(btn);
    }

    // Page numbers
    let start = Math.max(1, current - 2);
    let end = Math.min(total, current + 2);

    for (let i = start; i <= end; i++) {
        const btn = document.createElement("button");
        btn.textContent = i;
        btn.className = i === current ? "active" : "";
        btn.onclick = () => loadSuspects(i);
        div.appendChild(btn);
    }

    // Next
    if (current < total) {
        const btn = document.createElement("button");
        btn.textContent = "Suivant";
        btn.onclick = () => loadSuspects(current + 1);
        div.appendChild(btn);
    }
}

// ============================================
// SEARCH
// ============================================
let searchTimeout;
function searchSuspects() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadSuspects(1), 400);
}

// ============================================
// UTILS
// ============================================
function formatNumber(n) {
    return new Intl.NumberFormat("fr-FR").format(n);
}
