// Mac Activity Tracker Dashboard JavaScript

const API_BASE = '';

// Chart instances
let appsChart = null;
let websitesChart = null;
let typingChart = null;
let weeklyChart = null;

// Current selected date
let selectedDate = new Date().toISOString().split('T')[0];

// Chart colors
const chartColors = [
    '#58a6ff', '#3fb950', '#d29922', '#f85149', '#a371f7',
    '#79c0ff', '#56d364', '#e3b341', '#ffa198', '#d2a8ff',
    '#39d353', '#db6d28', '#8b949e', '#f0883e', '#bc8cff'
];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeDateSelector();
    loadDashboard();
    loadWeeklyTrends();
    loadRecommendations();

    // Auto-refresh every 60 seconds
    setInterval(() => {
        if (selectedDate === new Date().toISOString().split('T')[0]) {
            loadDashboard();
        }
    }, 60000);
});

function initializeDateSelector() {
    const dateInput = document.getElementById('selected-date');
    const prevBtn = document.getElementById('prev-day');
    const nextBtn = document.getElementById('next-day');
    const todayBtn = document.getElementById('today-btn');

    dateInput.value = selectedDate;

    dateInput.addEventListener('change', (e) => {
        selectedDate = e.target.value;
        loadDashboard();
    });

    prevBtn.addEventListener('click', () => {
        const date = new Date(selectedDate);
        date.setDate(date.getDate() - 1);
        selectedDate = date.toISOString().split('T')[0];
        dateInput.value = selectedDate;
        loadDashboard();
    });

    nextBtn.addEventListener('click', () => {
        const date = new Date(selectedDate);
        date.setDate(date.getDate() + 1);
        selectedDate = date.toISOString().split('T')[0];
        dateInput.value = selectedDate;
        loadDashboard();
    });

    todayBtn.addEventListener('click', () => {
        selectedDate = new Date().toISOString().split('T')[0];
        dateInput.value = selectedDate;
        loadDashboard();
    });
}

async function loadDashboard() {
    document.body.classList.add('loading');

    try {
        const response = await fetch(`${API_BASE}/api/daily/${selectedDate}`);
        const data = await response.json();

        updateProductivityScore(data.productivity);
        updateHighlights(data.overview.highlights);
        updateStats(data.overview);
        updateAppsChart(data.overview.apps);
        updateWebsitesChart(data.overview.websites);
        updateTypingChart(data.overview.typing);

        document.getElementById('status-text').textContent =
            `Last updated: ${new Date().toLocaleTimeString()}`;
    } catch (error) {
        console.error('Error loading dashboard:', error);
        document.getElementById('status-text').textContent =
            'Error loading data. Is the tracker running?';
    }

    document.body.classList.remove('loading');
}

function updateProductivityScore(productivity) {
    const scoreEl = document.getElementById('productivity-score');
    const gradeEl = document.getElementById('productivity-grade');
    const circleEl = document.getElementById('score-circle');
    const productiveEl = document.getElementById('productive-hours');
    const distractionEl = document.getElementById('distraction-hours');
    const totalEl = document.getElementById('total-hours');
    const feedbackEl = document.getElementById('productivity-feedback');

    const score = productivity.score || 0;
    scoreEl.textContent = score;
    gradeEl.textContent = `Grade: ${productivity.grade || '-'}`;

    // Update circle gradient
    const percentage = score;
    let color = '#3fb950'; // green
    if (score < 60) color = '#f85149'; // red
    else if (score < 80) color = '#d29922'; // yellow

    circleEl.style.background = `conic-gradient(${color} ${percentage}%, var(--card-bg) ${percentage}%)`;

    productiveEl.textContent = `${productivity.productive_hours || 0}h`;
    distractionEl.textContent = `${productivity.distraction_hours || 0}h`;
    totalEl.textContent = `${productivity.total_hours || 0}h`;

    // Update feedback
    const feedback = productivity.feedback || [];
    feedbackEl.innerHTML = feedback.map(f => `<p>${f}</p>`).join('');
}

function updateHighlights(highlights) {
    const list = document.getElementById('highlights-list');
    if (!highlights || highlights.length === 0) {
        list.innerHTML = '<li>No activity recorded yet for this day</li>';
        return;
    }
    list.innerHTML = highlights.map(h => `<li>${h}</li>`).join('');
}

function updateStats(overview) {
    document.getElementById('stat-apps').textContent = overview.apps?.app_count || 0;
    document.getElementById('stat-sites').textContent = overview.websites?.domain_count || 0;
    document.getElementById('stat-words').textContent = formatNumber(overview.typing?.total_words || 0);
    document.getElementById('stat-wpm').textContent = overview.typing?.average_wpm || 0;
}

function updateAppsChart(appsData) {
    const ctx = document.getElementById('apps-chart').getContext('2d');
    const apps = appsData?.apps?.slice(0, 10) || [];

    if (apps.length === 0) {
        if (appsChart) appsChart.destroy();
        ctx.font = '14px -apple-system';
        ctx.fillStyle = '#8b949e';
        ctx.textAlign = 'center';
        ctx.fillText('No app data for this day', ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }

    const data = {
        labels: apps.map(a => a.name),
        datasets: [{
            data: apps.map(a => a.seconds / 3600),
            backgroundColor: chartColors.slice(0, apps.length),
            borderWidth: 0
        }]
    };

    if (appsChart) appsChart.destroy();

    appsChart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const hours = context.raw.toFixed(2);
                            const pct = apps[context.dataIndex].percentage;
                            return `${hours}h (${pct}%)`;
                        }
                    }
                }
            }
        }
    });

    // Update legend
    const legendEl = document.getElementById('apps-legend');
    legendEl.innerHTML = apps.slice(0, 6).map((app, i) => `
        <div class="legend-item">
            <span class="legend-color" style="background: ${chartColors[i]}"></span>
            <span>${app.name}: ${app.hours}h</span>
        </div>
    `).join('');
}

function updateWebsitesChart(websitesData) {
    const ctx = document.getElementById('websites-chart').getContext('2d');
    const domains = websitesData?.domains?.slice(0, 10) || [];

    if (domains.length === 0) {
        if (websitesChart) websitesChart.destroy();
        ctx.font = '14px -apple-system';
        ctx.fillStyle = '#8b949e';
        ctx.textAlign = 'center';
        ctx.fillText('No website data for this day', ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }

    const data = {
        labels: domains.map(d => d.domain),
        datasets: [{
            data: domains.map(d => d.seconds / 3600),
            backgroundColor: chartColors.slice(0, domains.length),
            borderWidth: 0
        }]
    };

    if (websitesChart) websitesChart.destroy();

    websitesChart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const hours = context.raw.toFixed(2);
                            const pct = domains[context.dataIndex].percentage;
                            return `${hours}h (${pct}%)`;
                        }
                    }
                }
            }
        }
    });

    // Update legend
    const legendEl = document.getElementById('websites-legend');
    legendEl.innerHTML = domains.slice(0, 6).map((domain, i) => `
        <div class="legend-item">
            <span class="legend-color" style="background: ${chartColors[i]}"></span>
            <span>${domain.domain}: ${domain.hours}h</span>
        </div>
    `).join('');
}

function updateTypingChart(typingData) {
    const ctx = document.getElementById('typing-chart').getContext('2d');
    const hourlyData = typingData?.hourly_breakdown || {};

    // Create data for all 24 hours
    const hours = Array.from({ length: 24 }, (_, i) => i);
    const words = hours.map(h => hourlyData[h]?.words || 0);
    const keystrokes = hours.map(h => hourlyData[h]?.keystrokes || 0);

    const data = {
        labels: hours.map(h => `${h}:00`),
        datasets: [
            {
                label: 'Words',
                data: words,
                backgroundColor: '#58a6ff',
                borderColor: '#58a6ff',
                borderWidth: 2,
                tension: 0.3,
                fill: true,
                type: 'line'
            },
            {
                label: 'Keystrokes',
                data: keystrokes,
                backgroundColor: 'rgba(163, 113, 247, 0.5)',
                borderColor: '#a371f7',
                borderWidth: 1,
                type: 'bar'
            }
        ]
    };

    if (typingChart) typingChart.destroy();

    typingChart = new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#8b949e' }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#8b949e' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#e6edf3' }
                }
            }
        }
    });
}

async function loadWeeklyTrends() {
    try {
        const response = await fetch(`${API_BASE}/api/weekly`);
        const data = await response.json();

        updateWeeklyChart(data);
        updateWeeklyInsights(data);
    } catch (error) {
        console.error('Error loading weekly trends:', error);
    }
}

function updateWeeklyChart(weeklyData) {
    const ctx = document.getElementById('weekly-chart').getContext('2d');
    const days = weeklyData?.days || [];

    const labels = days.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    });

    const data = {
        labels: labels,
        datasets: [
            {
                label: 'Active Hours',
                data: days.map(d => d.apps?.total_hours || 0),
                backgroundColor: '#58a6ff',
                borderColor: '#58a6ff',
                borderWidth: 2,
                type: 'line',
                yAxisID: 'y'
            },
            {
                label: 'Words Typed (hundreds)',
                data: days.map(d => (d.typing?.total_words || 0) / 100),
                backgroundColor: 'rgba(63, 185, 80, 0.5)',
                borderColor: '#3fb950',
                borderWidth: 1,
                type: 'bar',
                yAxisID: 'y1'
            }
        ]
    };

    if (weeklyChart) weeklyChart.destroy();

    weeklyChart = new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#8b949e' }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#8b949e' },
                    title: {
                        display: true,
                        text: 'Hours',
                        color: '#8b949e'
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#8b949e' },
                    title: {
                        display: true,
                        text: 'Words (hundreds)',
                        color: '#8b949e'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#e6edf3' }
                }
            }
        }
    });
}

function updateWeeklyInsights(weeklyData) {
    const insightsEl = document.getElementById('weekly-insights');
    const insights = weeklyData?.insights || [];
    const totals = weeklyData?.totals || {};

    let html = `
        <p><strong>Weekly Summary:</strong> ${totals.total_hours?.toFixed(1) || 0} total hours,
        ${formatNumber(totals.total_words || 0)} words typed</p>
    `;

    if (insights.length > 0) {
        html += insights.map(i => `<p>${i}</p>`).join('');
    }

    if (weeklyData?.most_productive_day) {
        const date = new Date(weeklyData.most_productive_day);
        html += `<p>Most productive day: ${date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</p>`;
    }

    insightsEl.innerHTML = html;
}

async function loadRecommendations() {
    try {
        const response = await fetch(`${API_BASE}/api/recommendations`);
        const data = await response.json();

        const listEl = document.getElementById('recommendations-list');
        const recommendations = data?.recommendations || [];

        if (recommendations.length === 0) {
            listEl.innerHTML = '<p class="no-data">Keep tracking to get personalized recommendations!</p>';
            return;
        }

        listEl.innerHTML = recommendations.map(rec => `
            <div class="recommendation ${rec.type}">
                <span class="priority">${rec.priority} priority</span>
                <h3>${rec.title}</h3>
                <p>${rec.description}</p>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading recommendations:', error);
    }
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString();
}
