from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta

app = Flask(__name__)

# In-memory storage: list of dicts
data_store = []
MAX_POINTS = 360  # ~1 hour at 10s intervals

# Alert threshold (for vaccine fridge)
TEMP_THRESHOLD = 8.0  # °C

# Alert event tracking
alert_active = False
alert_start_time = None
alert_events = []  # list of dicts: {'start': iso, 'end': iso, 'max_temp': float}
current_alert_max_temp = -999

@app.route('/data', methods=['POST'])
def receive_data():
    """Endpoint to receive sensor data from ESP32."""
    global alert_active, alert_start_time, current_alert_max_temp

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    content = request.json
    if 'temp' not in content or 'humidity' not in content:
        return jsonify({"error": "Missing temp or humidity"}), 400

    # Add server timestamp
    entry = {
        'timestamp': datetime.now().isoformat(),
        'temp': float(content['temp']),
        'humidity': float(content['humidity'])
    }
    data_store.append(entry)

    # Keep only the last MAX_POINTS entries
    if len(data_store) > MAX_POINTS:
        del data_store[0:len(data_store)-MAX_POINTS]

    # --- Alert logic ---
    temp = entry['temp']
    if temp > TEMP_THRESHOLD:
        if not alert_active:
            # Alert just started
            alert_active = True
            alert_start_time = datetime.now()
            current_alert_max_temp = temp
        else:
            # Alert ongoing, update max temp
            if temp > current_alert_max_temp:
                current_alert_max_temp = temp
    else:
        if alert_active:
            # Alert just ended
            alert_events.append({
                'start': alert_start_time.isoformat(),
                'end': datetime.now().isoformat(),
                'max_temp': current_alert_max_temp
            })
            alert_active = False
            alert_start_time = None
            current_alert_max_temp = -999

    return jsonify({"status": "ok"}), 200

@app.route('/api/alerts')
def get_alerts():
    """Return alert events and current alert status."""
    current = None
    if alert_active and alert_start_time:
        current = {
            'start': alert_start_time.isoformat(),
            'max_temp': current_alert_max_temp
        }
    # Return last 10 alert events (most recent first)
    recent = alert_events[-10:][::-1]
    return jsonify({
        'active': alert_active,
        'current': current,
        'events': recent
    })

@app.route('/')
def dashboard():
    """Serve the dashboard HTML."""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/data')
def get_data():
    """Return data from the last hour as JSON."""
    one_hour_ago = datetime.now() - timedelta(hours=1)
    filtered = [d for d in data_store
                if datetime.fromisoformat(d['timestamp']) >= one_hour_ago]
    return jsonify(filtered)

# Enhanced Dashboard HTML with current values, alerts, and time ranges
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Cold Room Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #f0f4f8;
            --card-bg: #ffffff;
            --text-primary: #2c3e50;
            --text-secondary: #7f8c8d;
            --accent-temp: #e74c3c;
            --accent-hum: #3498db;
            --alert-color: #e74c3c;
            --ok-color: #27ae60;
            --border-radius: 12px;
            --shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            padding: 20px;
            min-height: 100vh;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .header p {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }

        .alert-banner {
            display: none;
            background-color: var(--alert-color);
            color: white;
            padding: 15px;
            text-align: center;
            font-size: 1.5rem;
            font-weight: bold;
            border-radius: var(--border-radius);
            margin-bottom: 25px;
            box-shadow: var(--shadow);
            animation: pulse 1.5s infinite;
        }
        .alert-banner .alert-time {
            font-size: 1rem;
            font-weight: normal;
            margin-top: 5px;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.8; }
            100% { opacity: 1; }
        }

        .current-values {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            margin-bottom: 30px;
        }
        .value-card {
            background: var(--card-bg);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            padding: 20px 30px;
            text-align: center;
            min-width: 200px;
            flex: 1;
            max-width: 300px;
        }
        .value-card .label {
            font-size: 1rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .value-card .number {
            font-size: 3rem;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 8px;
        }
        .value-card.temp .number { color: var(--accent-temp); }
        .value-card.hum .number { color: var(--accent-hum); }
        .value-card .unit {
            font-size: 1.2rem;
            color: var(--text-secondary);
        }
        .value-card .timestamp {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 10px;
        }

        .alert-history {
            background: var(--card-bg);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            padding: 20px;
            margin-bottom: 25px;
        }
        .alert-history h2 {
            text-align: center;
            margin-bottom: 15px;
        }
        .alert-history table {
            width: 100%;
            border-collapse: collapse;
        }
        .alert-history th, .alert-history td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            text-align: center;
        }
        .alert-history th {
            background-color: #f8f9fa;
        }

        .charts-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
        }
        .chart-box {
            flex: 1;
            min-width: 400px;
            background: var(--card-bg);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            padding: 20px;
        }
        .chart-box h2 {
            text-align: center;
            margin-bottom: 15px;
            font-weight: 600;
        }

        @media (max-width: 768px) {
            .current-values { flex-direction: column; align-items: center; }
            .chart-box { min-width: 90%; }
            .header h1 { font-size: 2rem; }
            .alert-history table { font-size: 0.9rem; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>❄️ Cold Room Monitor</h1>
        <p>Real-time temperature & humidity monitoring for vaccine fridge</p>
    </div>

    <div id="alertBanner" class="alert-banner">
        ⚠️ TEMPERATURE ALERT: Above 8°C!
        <div class="alert-time" id="alertTime"></div>
    </div>

    <div class="current-values">
        <div class="value-card temp">
            <div class="label">Temperature</div>
            <div class="number"><span id="currentTemp">--</span><span class="unit">°C</span></div>
            <div class="timestamp" id="lastUpdate">Last update: --</div>
        </div>
        <div class="value-card hum">
            <div class="label">Humidity</div>
            <div class="number"><span id="currentHum">--</span><span class="unit">%</span></div>
            <div class="timestamp">Relative Humidity</div>
        </div>
    </div>

    <div class="alert-history" id="alertHistory">
        <h2>Recent Alerts</h2>
        <table>
            <thead>
                <tr>
                    <th>Start Time</th>
                    <th>End Time</th>
                    <th>Max Temp (°C)</th>
                </tr>
            </thead>
            <tbody id="alertTableBody">
                <tr><td colspan="3">No alerts recorded</td></tr>
            </tbody>
        </table>
    </div>

    <div class="charts-container">
        <div class="chart-box">
            <h2>Temperature (°C)</h2>
            <canvas id="tempChart"></canvas>
        </div>
        <div class="chart-box">
            <h2>Humidity (%)</h2>
            <canvas id="humChart"></canvas>
        </div>
    </div>

    <script>
        let tempChart, humChart;
        const TEMP_THRESHOLD = 8.0; // same as server

        function initCharts() {
            const tempCtx = document.getElementById('tempChart').getContext('2d');
            const humCtx = document.getElementById('humChart').getContext('2d');

            tempChart = new Chart(tempCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Temperature (°C)',
                        data: [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { beginAtZero: false } },
                    plugins: { legend: { display: false } }
                }
            });

            humChart = new Chart(humCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Humidity (%)',
                        data: [],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { beginAtZero: true } },
                    plugins: { legend: { display: false } }
                }
            });
        }

        function formatTime(isoString) {
            const d = new Date(isoString);
            return d.toLocaleTimeString();
        }

        function updateDashboard(data) {
            if (data.length === 0) return;

            const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
            const temps = data.map(d => d.temp);
            const hums = data.map(d => d.humidity);

            tempChart.data.labels = labels;
            tempChart.data.datasets[0].data = temps;
            tempChart.update();

            humChart.data.labels = labels;
            humChart.data.datasets[0].data = hums;
            humChart.update();

            const latest = data[data.length - 1];
            document.getElementById('currentTemp').textContent = latest.temp.toFixed(1);
            document.getElementById('currentHum').textContent = latest.humidity.toFixed(1);
            document.getElementById('lastUpdate').textContent = 
                'Last update: ' + new Date(latest.timestamp).toLocaleTimeString();

            const alertBanner = document.getElementById('alertBanner');
            if (latest.temp > TEMP_THRESHOLD) {
                alertBanner.style.display = 'block';
                // Will be filled by fetchAlerts()
            } else {
                alertBanner.style.display = 'none';
            }
        }

        function updateAlerts(alertData) {
            const banner = document.getElementById('alertBanner');
            const alertTime = document.getElementById('alertTime');
            const tableBody = document.getElementById('alertTableBody');

            if (alertData.active && alertData.current) {
                banner.style.display = 'block';
                alertTime.textContent = 'Alert started at ' + formatTime(alertData.current.start) + 
                                       ' (Max temp: ' + alertData.current.max_temp.toFixed(1) + '°C)';
            } else {
                banner.style.display = 'none';
                alertTime.textContent = '';
            }

            // Populate alert history table
            if (alertData.events && alertData.events.length > 0) {
                let rows = '';
                alertData.events.forEach(evt => {
                    rows += `<tr>
                        <td>${formatTime(evt.start)}</td>
                        <td>${formatTime(evt.end)}</td>
                        <td>${evt.max_temp.toFixed(1)}</td>
                    </tr>`;
                });
                tableBody.innerHTML = rows;
            } else {
                tableBody.innerHTML = '<tr><td colspan="3">No alerts recorded</td></tr>';
            }
        }

        function fetchData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(err => console.error('Error fetching data:', err));
        }

        function fetchAlerts() {
            fetch('/api/alerts')
                .then(response => response.json())
                .then(data => updateAlerts(data))
                .catch(err => console.error('Error fetching alerts:', err));
        }

        // Initial load
        initCharts();
        fetchData();
        fetchAlerts();
        // Refresh every 10 seconds
        setInterval(fetchData, 10000);
        setInterval(fetchAlerts, 10000);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)