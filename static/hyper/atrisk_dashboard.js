function initAtriskDashboard() {

	// 3️⃣ === PHILIPPINE MAP SECTION (UNCHANGED) ===
	(async () => {
		const topology = await fetch(
			'https://code.highcharts.com/mapdata/countries/ph/ph-all.topo.json'
		).then(res => res.json());

		const apiData = await fetch('/ppi/heatmap-data').then(res => res.json());

		const hcKeyMapping = {};
		const geometries = topology.objects.default?.geometries || topology.objects['ph-all'].geometries;
		geometries.forEach(geom => {
			hcKeyMapping[geom.properties.name] = geom.properties['hc-key'];
		});

		const minPPI = Math.min(...apiData.map(d => d.avg_ppi));
		const maxPPI = Math.max(...apiData.map(d => d.avg_ppi));

		const getColor = (value) => {
			const ratio = (value - minPPI) / (maxPPI - minPPI);
			const r = Math.round(255 * (1 - ratio));
			const g = Math.round(255 * ratio);
			return `rgb(${r},${g},0)`;
		};

		const heatmapData = apiData
			.map(item => {
				const key = hcKeyMapping[item.unit];
				if (!key) return null;
				return {
					'hc-key': key,
					value: item.avg_ppi,
					name: item.unit,
					count: item.count,
					color: getColor(item.avg_ppi)
				};
			})
			.filter(Boolean);

		const markerData = apiData.map(item => ({
			name: item.unit,
			lat: item.lat,
			lon: item.lng,
			avg_ppi: item.avg_ppi,
			count: item.count,
			marker: {
				radius: 2 + ((item.avg_ppi - minPPI) / (maxPPI - minPPI)) * 6,
				fillColor: getColor(item.avg_ppi),
				lineColor: '#000',
				lineWidth: 1
			}
		}));

		Highcharts.mapChart('philippinemap', {
			chart: { map: topology },
			title: { text: 'Philippines Average PPI Heatmap' },
			mapNavigation: { enabled: true },
			colorAxis: {
				min: minPPI,
				max: maxPPI,
				stops: [[0, 'red'], [1, 'green']]
			},
			tooltip: {
				formatter: function() {
					if (this.point.avg_ppi !== undefined) {
						return `<b>${this.point.name}</b><br/>Average PPI: ${this.point.avg_ppi}`;
					}
					return this.point.name;
				}
			},
			series: [
				{ data: heatmapData, name: 'Average PPI' },
				{ type: 'mappoint', name: 'Municipalities', data: markerData }
			]
		});
	})();

}



        // Log setup for better debugging of Firestore/Auth, though not strictly needed here
        // console.log("Initializing Score Gauge Script...");

        /**
         * Converts a score percentage into a color (Red/Orange/Green).
         * @param {number} score - The score percentage (0 to 100).
         * @returns {string} The HEX color code.
         */
        function scoreToColor(score) {
            if (score < 40) {
                return '#ef4444'; // Tailwind red-500 (High Risk)
            } else if (score < 70) {
                return '#f97316'; // Tailwind orange-500 (Medium Risk)
            } else {
                return '#10b981'; // Tailwind emerald-500 (Low Risk)
            }
        }

        /**
         * Updates the radial scoring gauge's progress and color.
         * @param {number} score - The score percentage (0 to 100).
         */
        function updateGauge(score) {
            // 1. Get the elements
            const progressCircle = document.getElementById('gauge-progress-circle');
            const scoreText = document.getElementById('score-text');

            if (!progressCircle || !scoreText) {
                console.error("Gauge elements not found.");
                return;
            }

            // 2. Clamp the score between 0 and 100
            const clampedScore = Math.min(100, Math.max(0, score));

            // 3. Define the circumference (2 * PI * 45 ≈ 282.74)
            const circumference = 282.74;

            // 4. Calculate the offset
            // Offset = Circumference - (Score / 100) * Circumference
            const offset = circumference - (clampedScore / 100) * circumference;

            // 5. Calculate Color
            const color = scoreToColor(clampedScore);

            // 6. Apply the new styles
            progressCircle.style.strokeDashoffset = offset;
            progressCircle.style.stroke = color;
            scoreText.style.color = color;

            // 7. Update the displayed text
            scoreText.textContent = `${clampedScore}%`;
        }

        // --- Demo/Initialization ---

        // Wait for the DOM to be fully loaded before running logic
        document.addEventListener('DOMContentLoaded', () => {
            // Start the gauge at 0
            updateGauge(0);

            // --- DEMO: Simulate score updates ---
            const demoScores = [92, 45, 68];
            let currentDemoIndex = 0;

            const scoreDemoLoop = () => {
                const newScore = demoScores[currentDemoIndex % demoScores.length];
                updateGauge(newScore);
                currentDemoIndex++;
            };

            // Run the demo loop every 3 seconds
            setInterval(scoreDemoLoop, 3000);

            // Set the initial score after a short delay
            setTimeout(() => {
                 updateGauge(demoScores[0]);
                 currentDemoIndex = 1;
            }, 500);
        });

  