function initDashboard() {

	// --- HARDCODED DATA (edit these values as needed) ---
	const data = {
		improved: 100,
		improved_pct: 100,
		same: 100,
		same_pct: 100,
		worsened: 100,
		worsened_pct: 100,
		total_clients: 100
	};
	// -----------------------------------------------------

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

	//work with api
	// 1️⃣ === TOP SUMMARY FETCH ===
	// fetch('/ppi/improvement-stats')
	// 	.then(res => res.json())
	// 	.then(data => {
	// 		document.getElementById("improved").textContent = data.improved;
	// 		document.getElementById("improved_pct").innerHTML =
	// 			`<i class="mdi mdi-arrow-up-bold"></i> ${data.improved_pct}%`;

	// 		document.getElementById("same").textContent = data.same;
	// 		document.getElementById("same_pct").innerHTML =
	// 			`<i class="mdi mdi-equal"></i> ${data.same_pct}%`;

	// 		document.getElementById("worsened").textContent = data.worsened;
	// 		document.getElementById("worsened_pct").innerHTML =
	// 			`<i class="mdi mdi-arrow-down-bold"></i> ${data.worsened_pct}%`;

	// 		document.getElementById("total_clients").textContent = data.total_clients;
	// 	})
	// 	.catch(err => console.error("Error loading summary:", err));


	// --- HARDCODED DATA (replace with your own if needed) ---
	const apiData = {
		bands: [
			{ band: "0-10",  pre: 12, post: 20 },
			{ band: "11-20", pre: 18, post: 25 },
			{ band: "21-30", pre: 10, post: 17 },
			{ band: "31-40", pre: 8,  post: 14 },
			{ band: "41-50", pre: 5,  post: 9 }
		]
	};
	// ---------------------------------------------------------

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
		colors: ["#aa1f0e", "#6c757d"],
		dataLabels: { enabled: false },
		stroke: { curve: "smooth", width: 3 },

		series: [
			{ name: "Pre Intervention", data: preValues },
			{ name: "Post Intervention", data: postValues }
		],

		xaxis: { categories, title: { text: "PPI Scores" } },
		yaxis: { title: { text: "Counts" } },

		fill: {
			type: "gradient",
			gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.2 }
		},

		tooltip: {
			shared: true,
			intersect: false
		}
	};

	// Render chart
	new ApexCharts(container, bandChartOptions).render();

	//working with api
	// 2️⃣ === SPLINE AREA CHART FOR PRE/POST BANDS (GET DATA FROM API) ===
	// fetch("/ppi/prepost-latest")
    // .then(res => res.json())
    // .then(apiData => {

    //     const categories = apiData.bands.map(b => b.band);
    //     const preValues = apiData.bands.map(b => b.pre ?? 0);
    //     const postValues = apiData.bands.map(b => b.post ?? 0);

    //     // Dynamically calculate height based on container
    //     const container = document.querySelector("#spline-area");
    //     const containerHeight = container.clientHeight || 350; 
    //     const dynamicHeight = containerHeight * 30; 

    //     const bandChartOptions = {
    //         chart: {
    //             height: dynamicHeight,
    //             type: "area",
    //             toolbar: { show: false }
    //         },
            
    //         // Retain the line colors
    //         colors: ["#aa1f0e", "#6c757d"], 
    //         dataLabels: { enabled: false },
    //         stroke: { curve: "smooth", width: 3 },
    //         series: [
    //             { name: "Pre Intervention", data: preValues },
    //             { name: "Post Intervention", data: postValues }
    //         ],
            
    //         xaxis: { categories, title: { text: "PPI Scores" }  },
            
    //         yaxis: { title: { text: "Counts" } },
    //         fill: {
    //             type: "gradient",
    //             gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.2 }
    //         },
            
    //         // Standard tooltip settings (colors handled by the CSS above)
    //         tooltip: {
    //             shared: true,
    //             intersect: false,
    //         }
    //     };

    //     new ApexCharts(container, bandChartOptions).render();
    // })
    // .catch(err => console.error("Error loading prepost-latest:", err));



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




	let chart;

	// === HARDCODED SAMPLE DATA FROM YOUR API ===
	const trendData = {
		D: {
			forecast_next_3: [-2.01, -2.27, -2.53],
			group: "D",
			labels: [
				"2024-09-27","2024-09-30","2024-10-01","2024-10-03","2024-10-11","2024-10-15","2024-10-16",
				"2024-10-17","2024-10-18","2024-10-21","2024-10-22","2024-10-28","2024-10-29","2024-10-30",
				"2024-11-04","2024-11-05","2024-11-06","2024-11-07","2024-11-08","2024-11-11","2024-11-12",
				"2024-11-13","2024-11-14","2024-11-15","2024-11-18","2024-11-19","2024-11-20","2024-11-21",
				"2024-11-22","2024-11-25","2024-11-26","2024-11-27","2024-11-28","2024-11-29","2024-12-02",
				"2024-12-03","2024-12-04","2024-12-05","2024-12-06","2024-12-09","2025-01-07","2025-01-08",
				/* trimmed for clarity — KEEP ALL VALUES BELOW */
				...[
					"2024-12-10","2024-12-11","2024-12-12","2024-12-13","2024-12-16","2024-12-17","2024-12-18",
					"2024-12-19","2025-01-06","2025-01-07","2025-01-08","2025-01-10","2025-01-13","2025-01-14",
					"2025-01-15","2025-01-16","2025-01-17","2025-01-20","2025-01-21","2025-01-22",
					"2025-01-23","2025-01-24","2025-01-27","2025-01-28","2025-01-30","2025-01-31","2025-02-03",
					"2025-02-04","2025-02-05","2025-02-06","2025-02-07","2025-02-10","2025-02-11","2025-02-12",
					"2025-02-13","2025-02-14","2025-02-17","2025-02-18","2025-02-19","2025-02-20","2025-02-21",
					"2025-02-24","2025-02-25","2025-02-26","2025-02-27","2025-02-28","2025-03-03","2025-03-04",
					"2025-03-05","2025-03-06","2025-03-07","2025-03-10","2025-03-11","2025-03-12","2025-03-13",
					"2025-03-14","2025-03-17","2025-03-18","2025-03-19","2025-03-20","2025-03-21","2025-03-24",
					"2025-03-25","2025-03-26","2025-03-27","2025-03-28","2025-03-31","2025-04-02","2025-04-03",
					"2025-04-04","2025-04-07","2025-04-08","2025-04-10","2025-04-11","2025-04-14","2025-04-15",
					"2025-04-16","2025-04-21","2025-04-22","2025-04-23","2025-04-24","2025-04-25","2025-04-28",
					"2025-04-29","2025-04-30","2025-05-02","2025-05-05","2025-05-06","2025-05-07","2025-05-08",
					"2025-05-09","2025-05-13","2025-05-14","2025-05-15","2025-05-16","2025-05-19","2025-05-20",
					"2025-05-21","2025-05-22","2025-05-23","2025-05-26","2025-05-27","2025-05-28","2025-05-29",
					"2025-05-30","2025-06-02","2025-06-03","2025-06-04","2025-06-05","2025-06-09","2025-06-10",
					"2025-06-11","2025-06-13","2025-06-16","2025-06-17","2025-06-18","2025-06-19","2025-06-20",
					"2025-06-23","2025-06-24","2025-06-25","2025-06-26","2025-06-27","2025-06-30","2025-07-01",
					"2025-07-02","2025-07-03","2025-07-04","2025-07-07","2025-07-08","2025-07-09","2025-07-10",
					"2025-07-11","2025-07-14","2025-07-15","2025-07-16","2025-07-17","2025-07-18","2025-07-21",
					"2025-07-22","2025-07-24","2025-07-25","2025-07-28","2025-07-29","2025-07-30","2025-07-31",
					"2025-08-01","2025-08-04","2025-08-05","2025-08-06","2025-08-07","2025-08-08","2025-08-11",
					"2025-08-12","2025-08-13","2025-08-14","2025-08-15","2025-08-18","2025-08-19","2025-08-20",
					"2025-08-22","2025-08-26","2025-08-27","2025-08-28","2025-08-29","2025-09-01","2025-09-02",
					"2025-09-03","2025-09-04","2025-09-05","2025-09-08","2025-09-09","2025-09-10","2025-09-11",
					"2025-09-12","2025-09-15","2025-09-16","2025-09-17","2025-09-18","2025-09-19","2025-09-22",
					"2025-09-23","2025-09-24","2025-09-25","2025-09-26","2025-09-29","2025-09-30","2025-10-01",
					"2025-10-02","2025-10-03","2025-10-06","2025-10-07","2025-10-08","2025-10-09","2025-10-10",
					"2025-10-13","2025-10-14","2025-10-15","2025-10-16","2025-10-17","2025-10-20","2025-10-21",
					"2025-10-22","2025-10-23","2025-10-24","2025-10-27","2025-10-28","2025-10-29","2025-10-30"
				]
			],
			trend_slope: -0.2626,
			values: [
				0,0,0,0,0,38,37,16,0,73,39,74,32,76,47,67,70,100,100,59,70,52,61,0,70,75,31,87,100,65,
				41,50,44,68,54,48,54,51,56,52,40,39,43,56,50,38,39,39,42,0,0,54,81,69,82,70,55,83,43,
				79,72,100,66,44,66,88,60,22,45,82,6,63,46,44,76,16,73,39,91,52,42,87,57,36,62,24,51,25,
				57,78,19,69,73,59,52,52,91,17,70,54,30,35,41,81,67,0,42,57,48,6,27,30,35,0,52,100,47,
				23,13,72,25,0,37,41,4,23,34,6,34,15,43,0,24,16,0,17,34,3,28,33,15,24,16,18,62,5,8,9,51,
				26,46,50,23,46,33,22,49,46,43,62,40,78,0,47,68,68,55,58,55,64,56,5,0,0,0,0,0,0,0,0,0,0,
				0,2,0,0,6,0,0,0,0,0,0,0,0,0,0,2,5,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
				0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
			]
		},
		// --- GROUP W (weekly dataset you provided) ---
		W: {
			forecast_next_3: [2.5, 1.53, 0.55],
			group: "W",
			labels: [
				"2024-09-23/2024-09-29","2024-09-30/2024-10-06","2024-10-07/2024-10-13","2024-10-14/2024-10-20",
				"2024-10-21/2024-10-27","2024-10-28/2024-11-03","2024-11-04/2024-11-10","2024-11-11/2024-11-17",
				"2024-11-18/2024-11-24","2024-11-25/2024-12-01","2024-12-02/2024-12-08","2024-12-09/2024-12-15",
				"2024-12-16/2024-12-22","2025-01-06/2025-01-12","2025-01-13/2025-01-19","2025-01-20/2025-01-26",
				"2025-01-27/2025-02-02","2025-02-03/2025-02-09","2025-02-10/2025-02-16","2025-02-17/2025-02-23",
				"2025-02-24/2025-03-02","2025-03-03/2025-03-09","2025-03-10/2025-03-16","2025-03-17/2025-03-23",
				"2025-03-24/2025-03-30","2025-03-31/2025-04-06","2025-04-07/2025-04-13","2025-04-14/2025-04-20",
				"2025-04-21/2025-04-27","2025-04-28/2025-05-04","2025-05-05/2025-05-11","2025-05-12/2025-05-18",
				"2025-05-19/2025-05-25","2025-05-26/2025-06-01","2025-06-02/2025-06-08","2025-06-09/2025-06-15",
				"2025-06-16/2025-06-22","2025-06-23/2025-06-29","2025-06-30/2025-07-06","2025-07-07/2025-07-13",
				"2025-07-14/2025-07-20","2025-07-21/2025-07-27","2025-07-28/2025-08-03","2025-08-04/2025-08-10",
				"2025-08-11/2025-08-17","2025-08-18/2025-08-24","2025-08-25/2025-08-31","2025-09-01/2025-09-07",
				"2025-09-08/2025-09-14","2025-09-15/2025-09-21","2025-09-22/2025-09-28","2025-09-29/2025-10-05",
				"2025-10-06/2025-10-12","2025-10-13/2025-10-19","2025-10-20/2025-10-26","2025-10-27/2025-11-02"
			],
			trend_slope: -0.9742,
			values: [
				0,0,0,23,55,66,72,58,71,51,53,46,43,19,72,72,65,49,51,58,56,47,64,59,41,44,26,56,38,32,
				24,10,21,20,11,39,43,46,57,37,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
			]
		},
		M: {
			forecast_next_3: [4.11, 0.53, -3.04],
			group: "M",

			labels: [
				"2024-09",
				"2024-10",
				"2024-11",
				"2024-12",
				"2025-01",
				"2025-02",
				"2025-03",
				"2025-04",
				"2025-05",
				"2025-06",
				"2025-07",
				"2025-08",
				"2025-09",
				"2025-10"
			],

			trend_slope: -3.5758,

			values: [
				0,
				50,
				61,
				47,
				66,
				54,
				52,
				37,
				19,
				39,
				8,
				0,
				0,
				0
			]
		},
		Q: {
			forecast_next_3: [5.33, 0.19, -4.95],
			group: "Q",

			labels: [
				"2024Q3",
				"2024Q4",
				"2025Q1",
				"2025Q2",
				"2025Q3",
				"2025Q4"
			],

			trend_slope: -5.1429,

			values: [
				0,
				52,
				56,
				32,
				0,
				0
			]
		},
		Y: {
			forecast_next_3: [-24.0, -62.0, -100.0],
			group: "Y",

			labels: [
				"2024",
				"2025"
			],

			trend_slope: -38.0,

			values: [
				52,
				14
			]
		}



	};
	// === END OF HARDCODED DATA ===


	// === CHART LOADER ===
	function loadChart(group = "D") {
		const data = trendData[group];

		const options = {
			chart: { type: "area", height: 350, toolbar: { show: false }},
			series: [{ name: "Values", data: data.values }],
			xaxis: { categories: data.labels },
			stroke: { width: 3, curve: "smooth" },
			colors: ["#aa1f0e"],
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
	}

	// Initial load
	loadChart();

	// Filter dropdown
	document.getElementById("timeFilter").addEventListener("change", e => {
		loadChart(e.target.value);
	});

	//work with api
	// 4️⃣ === TIME ANALYTICS CHART ===
	// let chart;
	// function loadChart(group = 'D') {
	// 	fetch(`/ppi/trend-data?group=${group}`)
	// 		.then(res => res.json())
	// 		.then(data => {
	// 			const options = {
	// 				chart: { type: "area", height: 350, toolbar: { show: false }},
	// 				series: [{ name: "Values", data: data.values }],
	// 				xaxis: { categories: data.labels },
	// 				stroke: { width: 3, curve: "smooth" },
	// 				colors: ["#aa1f0e"],
	// 				dataLabels: { enabled: false }
	// 			};

	// 			if (chart) {
	// 				chart.updateOptions({
	// 					series: [{ data: data.values }],
	// 					xaxis: { categories: data.labels }
	// 				});
	// 			} else {
	// 				chart = new ApexCharts(document.querySelector("#analytics"), options);
	// 				chart.render();
	// 			}
	// 		});
	// }

	// loadChart();
	// document.getElementById("timeFilter").addEventListener("change", e => loadChart(e.target.value));






}
