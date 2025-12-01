function initCMRIPrograms() {
    // --- STATE ---
    let currentStep = 0;
    let answers = {
        roof: null,
        children: null,
        tv: null
    };

    // --- DOM ELEMENTS ---
    const sections = document.querySelectorAll('.section');
    const navBtns = document.querySelectorAll('.nav-btn');
    const calcBtn = document.getElementById('calc-btn');
    const probDisplay = document.getElementById('prob-display');

    // --- NAVIGATION ---
    function setStep(stepIndex) {
        currentStep = stepIndex;
        sections.forEach((sec, idx) => sec.classList.toggle('active', idx === stepIndex));
        navBtns.forEach((btn, idx) => btn.classList.toggle('active', idx === stepIndex));
    }

    // --- SELECTION LOGIC ---
    function selectAnswer(category, idPart, points) {
        answers[category] = { points };

        // Deselect all in this category
        const groupBtns = document.querySelectorAll(`[data-category="${category}"]`);
        groupBtns.forEach(btn => btn.classList.remove('selected'));

        // Select clicked
        const clickedBtn = document.querySelector(`[data-category="${category}"][data-id="${idPart}"]`);
        if (clickedBtn) clickedBtn.classList.add('selected');

        checkSurveyComplete();
    }

    function checkSurveyComplete() {
        calcBtn.disabled = !(answers.roof && answers.children && answers.tv);
    }

    // --- CALCULATION ---
    function calculateAndShow() {
        const roofPts = answers.roof.points;
        const childPts = answers.children.points;
        const tvPts = answers.tv.points;
        const total = roofPts + childPts + tvPts;

        // Update score display
        document.getElementById('score-roof').innerText = `+${roofPts} pts`;
        document.getElementById('score-children').innerText = `+${childPts} pts`;
        document.getElementById('score-tv').innerText = `+${tvPts} pts`;
        document.getElementById('score-total-val').innerText = total;

        // Reset table highlights
        document.querySelectorAll('.lookup-table tr').forEach(r => r.classList.remove('highlight-row'));

        let probability;
        if (total < 10) {
            probability = 85;
            document.getElementById('row-very-high').classList.add('highlight-row');
        } else if (total < 20) {
            probability = 60;
            document.getElementById('row-high').classList.add('highlight-row');
        } else if (total < 30) {
            probability = 35;
            document.getElementById('row-mod').classList.add('highlight-row');
        } else {
            probability = 10;
            document.getElementById('row-low').classList.add('highlight-row');
        }

        probDisplay.innerText = `${probability}%`;
        setStep(2);
    }

    // --- RESET ---
    function resetApp() {
        answers = { roof: null, children: null, tv: null };
        document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
        checkSurveyComplete();
        setStep(0);
    }

    // --- EVENT LISTENERS ---
    // Navigation buttons
    navBtns.forEach((btn, idx) => btn.addEventListener('click', () => setStep(idx)));

    document.querySelectorAll('.option-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const category = btn.getAttribute('data-category');
        const idPart = btn.getAttribute('data-id');
        const points = parseInt(btn.getAttribute('data-points'), 10);
        selectAnswer(category, idPart, points);
    });
    });

    // Expose setStep and resetApp globally for navigation buttons
    window.setStep = setStep;
    window.resetApp = resetApp;

    // Calculate button
    calcBtn.addEventListener('click', calculateAndShow);

    // Back/Reset links
    document.querySelectorAll('.back-link[onclick]').forEach(link => {
        if (link.getAttribute('onclick').includes('resetApp')) {
            link.addEventListener('click', resetApp);
            link.removeAttribute('onclick');
        } else if (link.getAttribute('onclick').includes('setStep')) {
            link.addEventListener('click', e => {
                e.preventDefault();
                const targetStep = parseInt(link.getAttribute('data-step'));
                setStep(targetStep);
            });
            link.removeAttribute('onclick');
        }
    });

    // Expose functions globally if needed
    window.setStep = setStep;
    window.resetApp = resetApp;
}
