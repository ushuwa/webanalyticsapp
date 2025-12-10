function initScholarshipDashboard() {

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
			title: { text: 'Client per Area' },
			mapNavigation: { enabled: true },
			colorAxis: {
				min: minPPI,
				max: maxPPI,
				stops: [[0, 'red'], [1, 'green']]
			},
			tooltip: {
				formatter: function() {
					if (this.point.avg_ppi !== undefined) {
						return `<b>${this.point.name}</b><br/>Dependent Count: ${this.point.avg_ppi}`;
					}
					return this.point.name;
				}
			},
			series: [
				{ data: heatmapData, name: 'Clients' },
				{ type: 'mappoint', name: 'Municipalities', data: markerData }
			]
		});
	})();


	// Sample player data
	let clients = [
		{ name: "Alice", score: 88 },
		{ name: "Bob", score: 95 },
		{ name: "Charlie", score: 72 },
		{ name: "Diana", score: 91 },
		{ name: "Alice", score: 88 },
		{ name: "Bob", score: 95 },
		{ name: "Charlie", score: 72 },
		{ name: "Diana", score: 91 },
	];

	let descending = true; // sort direction

	// Render table rows
	function renderTable() {
		const body = document.getElementById("tableBody");
		body.innerHTML = "";

		clients
			.sort((a, b) => descending ? b.score - a.score : a.score - b.score)
			.forEach((clients, index) => {
				body.innerHTML += `
					<tr>
						<td>${index + 1}</td>
						<td>${clients.name}</td>
						<td>${clients.score}</td>
					</tr>
				`;
			});
	}

	function sortByScore() {
		descending = !descending;
		renderTable();
	}

	renderTable();



	function setScore(value) {
		if (value < 0) value = 0;
		if (value > 100) value = 100;

		const needle = document.getElementById("needle");
		const scoreValue = document.getElementById("scoreValue");

		// convert score (0–100) to degrees (-90deg to +90deg)
		let degree = (value / 100) * 180 - 90;

		needle.style.transform = `rotate(${degree}deg)`;
		scoreValue.textContent = value;
	}

	// Example: animate to 50% on load
	setTimeout(() => setScore(50), 500);


}



// function initScholarshipDashboard() {
//   (async () => {
//     const apiData = await fetch('/ppi/heatmap-data').then(res => res.json());

//     // 1. Group municipalities by major island
//     const groups = {
//       luzon: [],
//       visayas: [],
//       mindanao: []
//     };

//     apiData.forEach(d => {
//       const unit = d.unit.toLowerCase();

//       if (
//         unit.includes("luzon") ||
//         unit.includes("ilocos") ||
//         unit.includes("cordillera") ||
//         unit.includes("cagayan") ||
//         unit.includes("central luzon") ||
//         unit.includes("calabarzon") ||
//         unit.includes("mimaropa") ||
//         unit.includes("metro manila")
//       ) groups.luzon.push(d);

//       else if (
//         unit.includes("visayas") ||
//         unit.includes("iloilo") ||
//         unit.includes("cebu") ||
//         unit.includes("leyte") ||
//         unit.includes("negros")
//       ) groups.visayas.push(d);

//       else groups.mindanao.push(d);
//     });

//     // 2. Get min/max for color scaling
//     const allPPI = apiData.map(d => d.avg_ppi);
//     const min = Math.min(...allPPI);
//     const max = Math.max(...allPPI);

//     function getColor(value) {
//       const t = (value - min) / (max - min);
//       const r = Math.round(255 * (1 - t));
//       const g = Math.round(255 * t);
//       return `rgb(${r}, ${g}, 0)`;
//     }

//     // 3. Compute average per island
//     function avg(arr) {
//       if (!arr.length) return min;
//       return arr.reduce((a, b) => a + b.avg_ppi, 0) / arr.length;
//     }

//     const luzonAvg = avg(groups.luzon);
//     const visayasAvg = avg(groups.visayas);
//     const mindanaoAvg = avg(groups.mindanao);

//     // 4. Apply colors to SVG regions
//     document.querySelectorAll("#luzon path").forEach(p => {
//       p.style.fill = "#6c757d";
//     });

//     document.querySelectorAll("#visayas path").forEach(p => {
//       p.style.fill = "#6c757d";
//     });

//     document.querySelectorAll("#mindanao path").forEach(p => {
//       p.style.fill = "#6c757d";
//     });
//   })();
// }
