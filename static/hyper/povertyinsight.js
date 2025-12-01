function initPovertyInsights() {

    // Fetch API Data
    fetch('/ppi/segmentation')
        .then(response => response.json())
        .then(data => {

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
                colors: ['#727cf5'],
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
                colors: incomeColors
            };

            var incomeChart = new ApexCharts(document.querySelector(".bar-container-horizontal"), incomeOptions);
            incomeChart.render();
        })
        .catch(error => console.error('Error fetching segmentation data:', error));


    
    
    fetch('/ppi/cohort-analysis') // <-- update based on your endpoint
        .then(res => res.json())
        .then(data => {

            /* ------------------------------------------------
                FORMAT MONTHLY COHORT
            -------------------------------------------------- */
            const monthLabels = Object.keys(data.cohort_by_month);
            const monthValues = Object.values(data.cohort_by_month);

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
                colors: ['#727cf5'],
                tooltip: {
                    y: { formatter: val => `${val} clients` }
                }
            };

            new ApexCharts(document.querySelector("#cohortByMonth"), monthlyOptions).render();


            /* ------------------------------------------------
                FORMAT YEARLY COHORT
            -------------------------------------------------- */
            const yearLabels = Object.keys(data.cohort_by_year);
            const yearValues = Object.values(data.cohort_by_year);

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
                colors: ['#727cf5'],
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

        })
        .catch(err => console.error("Cohort API error:", err));
}

    