document.addEventListener('DOMContentLoaded', () => {
    const runBenchmarkBtn = document.getElementById('runBenchmarkBtn');
    const benchmarkTableBody = document.getElementById('benchmarkTableBody');

    let latencyChart = null;
    let throughputChart = null;

    function initCharts(labels, aesLatencies, bfLatencies, aesThroughputs, bfThroughputs) {
        const ctxLat = document.getElementById('latencyChart').getContext('2d');
        const ctxThr = document.getElementById('throughputChart').getContext('2d');

        if (latencyChart) latencyChart.destroy();
        if (throughputChart) throughputChart.destroy();

        // 1. Latency Chart (Lower is better)
        latencyChart = new Chart(ctxLat, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'AES-128-CBC (ms)',
                        data: aesLatencies,
                        backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        borderColor: '#3b82f6',
                        borderWidth: 1
                    },
                    {
                        label: 'Blowfish-CBC (ms)',
                        data: bfLatencies,
                        backgroundColor: 'rgba(245, 158, 11, 0.7)',
                        borderColor: '#f59e0b',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Latency (ms) [Lower is Better]', color: '#94a3b8' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        title: { display: true, text: 'Payload Size', color: '#94a3b8' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#f8fafc' } }
                }
            }
        });

        // 2. Throughput Chart (Higher is better)
        throughputChart = new Chart(ctxThr, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'AES-128-CBC Throughput (KB/s)',
                        data: aesThroughputs,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Blowfish-CBC Throughput (KB/s)',
                        data: bfThroughputs,
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        fill: true,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Throughput (KB/s) [Higher is Better]', color: '#94a3b8' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        title: { display: true, text: 'Payload Size', color: '#94a3b8' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#f8fafc' } }
                }
            }
        });
    }

    async function runBenchmark() {
        runBenchmarkBtn.disabled = true;
        runBenchmarkBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Benchmark...';
        benchmarkTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Executing cipher benchmark tests...</td></tr>';

        try {
            const res = await fetch('/api/benchmark/run');
            const data = await res.json();

            if (!data.success) {
                alert("Benchmark failed: " + data.error);
                return;
            }

            const items = data.benchmark_data;
            const labels = items.map(i => `${i.size_kb} KB`);
            const aesLatencies = items.map(i => i.aes_time_ms);
            const bfLatencies = items.map(i => i.blowfish_time_ms);
            const aesThroughputs = items.map(i => i.aes_throughput_kb_s);
            const bfThroughputs = items.map(i => i.blowfish_throughput_kb_s);

            // Render table rows
            benchmarkTableBody.innerHTML = items.map(i => {
                const winner = i.aes_throughput_kb_s >= i.blowfish_throughput_kb_s ?
                    '<span class="badge badge-success"><i class="fa-solid fa-trophy"></i> AES-128</span>' :
                    '<span class="badge badge-warning"><i class="fa-solid fa-trophy"></i> Blowfish</span>';

                return `
                    <tr>
                        <td><strong>${i.size_kb} KB</strong></td>
                        <td>${i.aes_time_ms} ms</td>
                        <td>${i.blowfish_time_ms} ms</td>
                        <td><span class="text-success">${i.aes_throughput_kb_s.toLocaleString()} KB/s</span></td>
                        <td><span class="text-warning">${i.blowfish_throughput_kb_s.toLocaleString()} KB/s</span></td>
                        <td>${winner}</td>
                    </tr>
                `;
            }).join('');

            // Draw Charts
            initCharts(labels, aesLatencies, bfLatencies, aesThroughputs, bfThroughputs);

        } catch (err) {
            alert("Benchmark request failed: " + err.message);
        } finally {
            runBenchmarkBtn.disabled = false;
            runBenchmarkBtn.innerHTML = '<i class="fa-solid fa-play"></i> Re-Run Benchmark Suite';
        }
    }

    runBenchmarkBtn.addEventListener('click', runBenchmark);

    // Auto-run benchmark on first page load
    runBenchmark();
});

