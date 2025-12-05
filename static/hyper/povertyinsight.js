function initPovertyInsights() {

    // --- HARDCODED SEGMENTATION DATA (replace with your own) ---
    const data = {
        city: {
            "Manila": 120,
            "Cebu": 80,
            "Davao": 65,
            "Baguio": 40
        },
        income_level: {
            "Low Income": 150,
            "Lower-Middle": 90,
            "Middle": 55,
            "Upper-Middle": 20,
            "High Income": 5
        }
    };
    // ------------------------------------------------------------

    // Extract city data
    const cityLabels = Object.keys(data.city);
    const cityValues = Object.values(data.city);

    // Extract income data
    const incomeLabels = Object.keys(data.income_level);
    const incomeValues = Object.values(data.income_level);

    /* ---------------------------------------------
        BAR CHART (Cities)
    ---------------------------------------------- */
    const barColors = document.querySelector('.bar-container').dataset.colors.split(',');

    var cityOptions = {
        chart: {
            type: 'bar',
            height: 300
        },
        series: [{
            name: 'Clients',
            data: cityValues
        }],
        xaxis: {
            categories: cityLabels
        },
        colors: ['#aa1f0e'],
    };

    var cityChart = new ApexCharts(document.querySelector(".bar-container"), cityOptions);
    cityChart.render();

    /* ---------------------------------------------
        HORIZONTAL BAR CHART (Income Levels)
    ---------------------------------------------- */
    const incomeColors = document.querySelector('.bar-container-horizontal').dataset.colors.split(',');

    var incomeOptions = {
        chart: {
            type: 'bar',
            height: 300
        },
        series: [{
            name: 'Clients',
            data: incomeValues
        }],
        xaxis: {
            categories: incomeLabels
        },
        plotOptions: {
            bar: {
                horizontal: true
            }
        },
        colors: ['#aa1f0e']
    };

    var incomeChart = new ApexCharts(document.querySelector(".bar-container-horizontal"), incomeOptions);
    incomeChart.render();

    // Fetch API Data
    // fetch('/ppi/segmentation')
    //     .then(response => response.json())
    //     .then(data => {

    //         // Extract city data
    //         const cityLabels = Object.keys(data.city);
    //         const cityValues = Object.values(data.city);

    //         // Extract income data
    //         const incomeLabels = Object.keys(data.income_level);
    //         const incomeValues = Object.values(data.income_level);

    //         /* ---------------------------------------------
    //             BAR CHART (Cities)
    //         ---------------------------------------------- */
    //         const barColors = document.querySelector('.bar-container').dataset.colors.split(',');

    //         var cityOptions = {
    //             chart: {
    //                 type: 'bar',
    //                 height: 300
    //             },
    //             series: [{
    //                 name: 'Clients',
    //                 data: cityValues
    //             }],
    //             xaxis: {
    //                 categories: cityLabels
    //             },
    //             colors: ['#aa1f0e'],
    //         };

    //         var cityChart = new ApexCharts(document.querySelector(".bar-container"), cityOptions);
    //         cityChart.render();


    //         /* ---------------------------------------------
    //             HORIZONTAL BAR CHART (Income Levels)
    //         ---------------------------------------------- */
    //         const incomeColors = document.querySelector('.bar-container-horizontal').dataset.colors.split(',');

    //         var incomeOptions = {
    //             chart: {
    //                 type: 'bar',
    //                 height: 300
    //             },
    //             series: [{
    //                 name: 'Clients',
    //                 data: incomeValues
    //             }],
    //             xaxis: {
    //                 categories: incomeLabels
    //             },
    //             plotOptions: {
    //                 bar: {
    //                     horizontal: true
    //                 }
    //             },
    //             colors: ['#aa1f0e']
    //         };

    //         var incomeChart = new ApexCharts(document.querySelector(".bar-container-horizontal"), incomeOptions);
    //         incomeChart.render();
    //     })
    //     .catch(error => console.error('Error fetching segmentation data:', error));


    // --- HARDCODED COHORT DATA (replace with your own) ---
    const data1 = {
        cohort_by_month: {
            "2024-01": 12,
            "2024-02": 18,
            "2024-03": 22,
            "2024-04": 15,
            "2024-05": 30,
            "2024-06": 25,
            "2024-07": 20,
            "2024-08": 28,
            "2024-09": 35,
            "2024-10": 40,
            "2024-11": 32,
            "2024-12": 45
        },
        cohort_by_year: {
            "2021": 150,
            "2022": 250,
            "2023": 180,
            "2024": 250,
            "2025": 150
        }
    };
    // ------------------------------------------------------------

    /* ------------------------------------------------
        FORMAT MONTHLY COHORT
    -------------------------------------------------- */
    const monthLabels = Object.keys(data1.cohort_by_month);
    const monthValues = Object.values(data1.cohort_by_month);

    // MONTHLY COHORT CHART
    var monthlyOptions = {
        chart: {
            type: 'line',
            height: 350,
            zoom: { enabled: false }
        },
        series: [{
            name: "New Clients",
            data: monthValues
        }],
        xaxis: {
            categories: monthLabels,
            tickAmount: 12,
            labels: { rotate: -45 }
        },
        stroke: {
            width: 3,
            curve: 'smooth'
        },
        markers: {
            size: 3
        },
        colors: ['#aa1f0e'],
        tooltip: {
            y: { formatter: val => `${val} clients` }
        }
    };

    new ApexCharts(document.querySelector("#cohortByMonth"), monthlyOptions).render();

    /* ------------------------------------------------
        FORMAT YEARLY COHORT
    -------------------------------------------------- */
    const yearLabels = Object.keys(data1.cohort_by_year);
    const yearValues = Object.values(data1.cohort_by_year);

    // YEARLY COHORT CHART
    var yearlyOptions = {
        chart: {
            type: 'line',
            height: 350
        },
        series: [{
            name: "New Clients",
            data: yearValues
        }],
        xaxis: {
            categories: yearLabels
        },
        colors: ['#aa1f0e'],
        plotOptions: {
            bar: {
                borderRadius: 4,
                distributed: false
            }
        },
        tooltip: {
            y: { formatter: val => `${val} clients` }
        }
    };

    new ApexCharts(document.querySelector("#cohortByYear"), yearlyOptions).render();

    
    // fetch('/ppi/cohort-analysis') // <-- update based on your endpoint
    //     .then(res => res.json())
    //     .then(data => {

    //         /* ------------------------------------------------
    //             FORMAT MONTHLY COHORT
    //         -------------------------------------------------- */
    //         const monthLabels = Object.keys(data.cohort_by_month);
    //         const monthValues = Object.values(data.cohort_by_month);

    //         // MONTHLY COHORT CHART
    //         var monthlyOptions = {
    //             chart: {
    //                 type: 'line',
    //                 height: 350,
    //                 zoom: { enabled: false }
    //             },
    //             series: [{
    //                 name: "New Clients",
    //                 data: monthValues
    //             }],
    //             xaxis: {
    //                 categories: monthLabels,
    //                 tickAmount: 12,
    //                 labels: { rotate: -45 }
    //             },
    //             stroke: {
    //                 width: 3,
    //                 curve: 'smooth'
    //             },
    //             markers: {
    //                 size: 3
    //             },
    //             colors: ['#aa1f0e'],
    //             tooltip: {
    //                 y: { formatter: val => `${val} clients` }
    //             }
    //         };

    //         new ApexCharts(document.querySelector("#cohortByMonth"), monthlyOptions).render();


    //         /* ------------------------------------------------
    //             FORMAT YEARLY COHORT
    //         -------------------------------------------------- */
    //         const yearLabels = Object.keys(data.cohort_by_year);
    //         const yearValues = Object.values(data.cohort_by_year);

    //         // YEARLY COHORT CHART
    //         var yearlyOptions = {
    //             chart: {
    //                 type: 'line',
    //                 height: 350
    //             },
    //             series: [{
    //                 name: "New Clients",
    //                 data: yearValues
    //             }],
    //             xaxis: {
    //                 categories: yearLabels
    //             },
    //             colors: ['#aa1f0e'],
    //             plotOptions: {
    //                 bar: {
    //                     borderRadius: 4,
    //                     distributed: false
    //                 }
    //             },
    //             tooltip: {
    //                 y: { formatter: val => `${val} clients` }
    //             }
    //         };

    //         new ApexCharts(document.querySelector("#cohortByYear"), yearlyOptions).render();

    //     })
    //     .catch(err => console.error("Cohort API error:", err));
    
    // --- HARDCODED DATA ---
    const data2 = {
        pre_probability_table: [
            { band: "0-20%", count: 10, percentage: 20},
            { band: "21-40%", count: 20, percentage: 40 },
            { band: "41-60%", count: 30, percentage: 60 },
            { band: "61-80%", count: 40, percentage: 80 },
            { band: "81-100%", count: 50, percentage: 100 }
        ],
        post_probability_table: [
            { band: "0-20%", count: 50, percentage: 100 },
            { band: "21-40%", count: 40, percentage: 80 },
            { band: "41-60%", count: 30, percentage: 60 },
            { band: "61-80%", count: 20, percentage: 40 },
            { band: "81-100%", count: 10, percentage: 20 }
        ]
    };
    // ------------------------------------------------

    // Extract labels and values
    const bands = data2.pre_probability_table.map(i => i.band);
    const preCounts = data2.pre_probability_table.map(i => i.count);
    const postCounts = data2.post_probability_table.map(i => i.count);
    const prePercentages = data2.pre_probability_table.map(i => i.percentage);
    const postPercentages = data2.post_probability_table.map(i => i.percentage);

    // ----------------------------------------------------
    // PRE PROBABILITY CHART  (Counts + tooltip percentage)
    // ----------------------------------------------------
    const preOptions = {
        chart: { type: 'bar', height: 300 },
        series: [{ name: 'Clients (Count)', data: preCounts }],
        xaxis: { categories: bands },
        colors: ['#aa1f0e'],
        dataLabels: { enabled: true },
        tooltip: {
            y: { formatter: (val, opts) => `${val} clients (${prePercentages[opts.dataPointIndex]}%)` }
        }
    };

    new ApexCharts(document.querySelector("#preProbabilityChart"), preOptions).render();

    // ----------------------------------------------------
    // POST PROBABILITY CHART  (Counts + tooltip percentage)
    // ----------------------------------------------------
    const postOptions = {
        chart: { type: 'bar', height: 300 },
        series: [{ name: 'Clients (Count)', data: postCounts }],
        xaxis: { categories: bands },
        colors: ['#aa1f0e'],
        dataLabels: { enabled: true },
        tooltip: {
            y: { formatter: (val, opts) => `${val} clients (${postPercentages[opts.dataPointIndex]}%)` }
        }
    };

    new ApexCharts(document.querySelector("#postProbabilityChart"), postOptions).render();

    
    // --------------------------------------------------
    // PRE & POST PROBABILITY SEPARATE CHARTS
    // --------------------------------------------------
    // fetch('/ppi/poverty-probability-tables')
    //     .then(res => res.json())
    //     .then(data => {

    //     // Extract labels
    //     const bands = data.pre_probability_table.map(i => i.band);

    //     // Extract counts
    //     const preCounts = data.pre_probability_table.map(i => i.count);
    //     const postCounts = data.post_probability_table.map(i => i.count);

    //     // Extract percentages
    //     const prePercentages = data.pre_probability_table.map(i => i.percentage);
    //     const postPercentages = data.post_probability_table.map(i => i.percentage);


    //     // ----------------------------------------------------
    //     // PRE PROBABILITY CHART  (Counts + tooltip percentage)
    //     // ----------------------------------------------------
    //     const preOptions = {
    //         chart: {
    //             type: 'bar',
    //             height: 300
    //         },
    //         series: [{
    //             name: 'Clients (Count)',
    //             data: preCounts
    //         }],
    //         xaxis: {
    //             categories: bands
    //         },
    //         colors: ['#aa1f0e'],
    //         dataLabels: {
    //             enabled: true
    //         },
    //         tooltip: {
    //             y: {
    //                 formatter: function(val, opts) {
    //                     const i = opts.dataPointIndex;
    //                     return `${val} clients (${prePercentages[i]}%)`;
    //                 }
    //             }
    //         }
    //     };

    //     new ApexCharts(
    //         document.querySelector("#preProbabilityChart"),
    //         preOptions
    //     ).render();


    //     // ----------------------------------------------------
    //     // POST PROBABILITY CHART  (Counts + tooltip percentage)
    //     // ----------------------------------------------------
    //     const postOptions = {
    //         chart: {
    //             type: 'bar',
    //             height: 300
    //         },
    //         series: [{
    //             name: 'Clients (Count)',
    //             data: postCounts
    //         }],
    //         xaxis: {
    //             categories: bands
    //         },
    //         colors: ['#aa1f0e'],
    //         dataLabels: {
    //             enabled: true
    //         },
    //         tooltip: {
    //             y: {
    //                 formatter: function(val, opts) {
    //                     const i = opts.dataPointIndex;
    //                     return `${val} clients (${postPercentages[i]}%)`;
    //                 }
    //             }
    //         }
    //     };

    //     new ApexCharts(
    //         document.querySelector("#postProbabilityChart"),
    //         postOptions
    //     ).render();

    // })
    // .catch(err => console.error("Error loading probability charts:", err));


    
// fetch('/ppi/poverty-probability-tables')
//     .then(res => res.json())
//     .then(data => {

//         // Format data
//         const bands = data.pre_probability_table.map(i => i.band);
//         const preValues = data.pre_probability_table.map(i => i.percentage);
//         const postValues = data.post_probability_table.map(i => i.percentage);

//         // ---------------- PRE CHART ----------------
//         var preOptions = {
//             chart: {
//                 type: 'bar',
//                 height: 300
//             },
//             series: [{
//                 name: "Pre Probability (%)",
//                 data: preValues
//             }],
//             xaxis: {
//                 categories: bands
//             },
//             colors: ["#aa1f0e"],
//             dataLabels: {
//                 enabled: true,
//                 formatter: val => val + "%"
//             },
//             tooltip: {
//                 y: { formatter: val => val + "%" }
//             }
//         };

//         new ApexCharts(
//             document.querySelector("#preProbabilityChart"),
//             preOptions
//         ).render();

//         // ---------------- POST CHART ----------------
//         var postOptions = {
//             chart: {
//                 type: 'bar',
//                 height: 300
//             },
//             series: [{
//                 name: "Post Probability (%)",
//                 data: postValues
//             }],
//             xaxis: {
//                 categories: bands
//             },
//             colors: ["#0acf97"],
//             dataLabels: {
//                 enabled: true,
//                 formatter: val => val + "%"
//             },
//             tooltip: {
//                 y: { formatter: val => val + "%" }
//             }
//         };

//         new ApexCharts(
//             document.querySelector("#postProbabilityChart"),
//             postOptions
//         ).render();

//     })
//     .catch(err => console.error("Probability API error:", err));

    
}

    
    // fetch('/ppi/poverty-probability-tables')
    //     .then(res => res.json())
    //     .then(data => {

    //         const bands = data.pre_probability_table.map(i => i.band);
            
    //         const preCounts = data.pre_probability_table.map(i => i.count);
    //         const postCounts = data.post_probability_table.map(i => i.count);
            
            
    //         const postChartContainer = document.querySelector('#postProbabilityChart').closest('.card');
    //         if (postChartContainer) {
    //             postChartContainer.style.display = 'none';
                
    //             const preChartTitle = document.querySelector('#preProbabilityChart').closest('.card-body').querySelector('.header-title');
    //             if (preChartTitle) {
    //                 preChartTitle.textContent = "Pre vs Post Probability (Client Count)";
    //             }
    //         }
            
    //         var stackedOptions = {
    //             chart: {
    //                 type: 'bar',
    //                 height: 300,
    //                 stacked: true, 
    //                 stackType: 'normal' 
    //             },
    //             series: [{
    //                 name: "Pre Count",
    //                 data: preCounts
    //             }, {
    //                 name: "Post Count",
    //                 data: postCounts
    //             }],
    //             xaxis: {
    //                 categories: bands
    //             },
    //             yaxis: {
    //                 title: {
    //                     text: "Client Count"
    //                 }
    //             },
    //             colors: ["#aa1f0e", "#e3eaef"], 
    //             plotOptions: {
    //                 bar: {
    //                     horizontal: false
    //                 }
    //             },
    //             dataLabels: {
    //                 enabled: false
    //             },
    //             tooltip: {
    //                 y: { 
    //                     formatter: val => `${val} clients` 
    //                 }
    //             },
    //             legend: {
    //                 position: 'top',
    //                 horizontalAlign: 'center'
    //             }
    //         };

    //         new ApexCharts(
    //             document.querySelector("#preProbabilityChart"),
    //             stackedOptions
    //         ).render();

    //     })
    //     .catch(err => console.error("Probability API error:", err));