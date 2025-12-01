function initDashboard() {

	// 1️⃣ === SPLINE AREA CHART FOR PRE/POST BANDS (GET DATA FROM API) ===
	fetch("/ppi/prepost-latest")
    .then(res => res.json())
    .then(apiData => {

        const categories = apiData.bands.map(b => b.band);
        const preValues = apiData.bands.map(b => b.pre ?? 0);
        const postValues = apiData.bands.map(b => b.post ?? 0);

        // Dynamically calculate height based on container
        const container = document.querySelector("#spline-area");
        const containerHeight = container.clientHeight || 350; 
        const dynamicHeight = containerHeight * 30; 

        const bandChartOptions = {
            chart: {
                height: dynamicHeight,
                type: "area",
                toolbar: { show: false }
            },
            
            // Retain the line colors
            colors: ["#727cf5", "#6c757d"], 
            dataLabels: { enabled: false },
            stroke: { curve: "smooth", width: 3 },
            series: [
                { name: "Pre Intervention", data: preValues },
                { name: "Post Intervention", data: postValues }
            ],
            
            xaxis: { categories, title: { text: "PPI Scores" }  },
            
            yaxis: { title: { text: "Counts" } },
            fill: {
                type: "gradient",
                gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.2 }
            },
            
            // Standard tooltip settings (colors handled by the CSS above)
            tooltip: {
                shared: true,
                intersect: false,
            }
        };

        new ApexCharts(container, bandChartOptions).render();
    })
    .catch(err => console.error("Error loading prepost-latest:", err));






	// 2️⃣ === TOP SUMMARY FETCH ===
	fetch('/ppi/improvement-stats')
		.then(res => res.json())
		.then(data => {
			document.getElementById("improved").textContent = data.improved;
			document.getElementById("improved_pct").innerHTML =
				`<i class="mdi mdi-arrow-up-bold"></i> ${data.improved_pct}%`;

			document.getElementById("same").textContent = data.same;
			document.getElementById("same_pct").innerHTML =
				`<i class="mdi mdi-equal"></i> ${data.same_pct}%`;

			document.getElementById("worsened").textContent = data.worsened;
			document.getElementById("worsened_pct").innerHTML =
				`<i class="mdi mdi-arrow-down-bold"></i> ${data.worsened_pct}%`;

			document.getElementById("total_clients").textContent = data.total_clients;
		})
		.catch(err => console.error("Error loading summary:", err));



	// 3️⃣ === TIME ANALYTICS CHART ===
	let chart;
	function loadChart(group = 'D') {
		fetch(`/ppi/trend-data?group=${group}`)
			.then(res => res.json())
			.then(data => {
				const options = {
					chart: { type: "area", height: 350, toolbar: { show: false }},
					series: [{ name: "Values", data: data.values }],
					xaxis: { categories: data.labels },
					stroke: { width: 3, curve: "smooth" },
					colors: ["#3AC47D"],
					dataLabels: { enabled: false }
				};

				if (chart) {
					chart.updateOptions({
						series: [{ data: data.values }],
						xaxis: { categories: data.labels }
					});
				} else {
					chart = new ApexCharts(document.querySelector("#analytics"), options);
					chart.render();
				}
			});
	}

	loadChart();
	document.getElementById("timeFilter").addEventListener("change", e => loadChart(e.target.value));



	// 4️⃣ === PHILIPPINE MAP SECTION (UNCHANGED) ===
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
