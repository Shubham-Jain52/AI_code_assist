const API_URL = ""; // Relative path

document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const clearBtn = document.getElementById('clearBtn');
    const codeInput = document.getElementById('codeInput');
    const spinner = analyzeBtn.querySelector('.loader-spinner');
    const btnText = analyzeBtn.querySelector('.btn-text');

    // Results elements
    const emptyState = document.getElementById('emptyState');
    const resultsContent = document.getElementById('resultsContent');
    const riskScoreEl = document.getElementById('riskScore');
    const qualityScoreEl = document.getElementById('qualityScore');
    const riskBar = document.getElementById('riskBar');
    const qualityBar = document.getElementById('qualityBar');
    const flagsList = document.getElementById('flagsList');
    const statusBadge = document.getElementById('statusBadge');

    analyzeBtn.addEventListener('click', async () => {
        const code = codeInput.value.trim();
        if (!code) return;

        // UI Loading State
        setLoading(true);
        resetResults();

        try {
            // 1. Submit Review
            const response = await fetch(`${API_URL}/review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ diff: code, language: 'python' })
            });

            if (!response.ok) throw new Error('Submission failed');

            const data = await response.json();
            const submissionId = data.submission_id;

            // 2. Poll for Status
            await pollStatus(submissionId);

        } catch (error) {
            console.error(error);
            alert("Analysis failed. Please check backend connection.");
            setLoading(false);
        }
    });

    clearBtn.addEventListener('click', () => {
        codeInput.value = '';
        resetResults();
        emptyState.classList.remove('hidden');
        resultsContent.classList.add('hidden');
    });

    async function pollStatus(id) {
        let attempts = 0;
        const maxAttempts = 20;

        const interval = setInterval(async () => {
            attempts++;
            try {
                const res = await fetch(`${API_URL}/status/${id}`);
                const data = await res.json();

                if (data.status === 'completed') {
                    clearInterval(interval);
                    showResults(data);
                    setLoading(false);
                } else if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    alert("Analysis timed out.");
                    setLoading(false);
                }
            } catch (e) {
                console.error(e);
            }
        }, 1000);
    }

    function setLoading(isLoading) {
        analyzeBtn.disabled = isLoading;
        if (isLoading) {
            spinner.classList.remove('hidden');
            btnText.textContent = 'Analyzing...';
            statusBadge.classList.remove('hidden');
            statusBadge.textContent = 'Processing...';
            statusBadge.style.background = 'rgba(245, 158, 11, 0.2)';
            statusBadge.style.color = '#f59e0b';
        } else {
            spinner.classList.add('hidden');
            btnText.textContent = 'Analyze Code';
            statusBadge.textContent = 'Completed';
            statusBadge.style.background = 'rgba(34, 197, 94, 0.2)';
            statusBadge.style.color = '#22c55e';
        }
    }

    function resetResults() {
        flagsList.innerHTML = '';
        riskScoreEl.textContent = '0';
        qualityScoreEl.textContent = '0';
        riskBar.style.width = '0%';
        qualityBar.style.width = '0%';
    }

    function showResults(data) {
        emptyState.classList.add('hidden');
        resultsContent.classList.remove('hidden');

        // Animate Scores
        animateValue(riskScoreEl, 0, data.risk_score, 1000);
        animateValue(qualityScoreEl, 0, data.quality_score, 1000);

        setTimeout(() => {
            riskBar.style.width = `${data.risk_score}%`;
            qualityBar.style.width = `${data.quality_score}%`;
        }, 100);

        // Color Logic
        const riskBox = riskScoreEl.closest('.metric-box');
        riskBox.classList.remove('danger', 'success');
        if (data.risk_score > 50) riskBox.classList.add('danger');
        else if (data.risk_score < 20) riskBox.classList.add('success');

        // Flags
        data.flags.forEach(flag => {
            const li = document.createElement('li');
            li.className = 'issue-item';

            if (flag.includes('Security')) li.classList.add('security');
            else li.classList.add('quality');

            li.textContent = flag;
            flagsList.appendChild(li);
        });

        if (data.flags.length === 0) {
            const li = document.createElement('li');
            li.className = 'issue-item';
            li.style.borderLeftColor = '#22c55e';
            li.textContent = "✨ Clean code! No issues detected.";
            flagsList.appendChild(li);
        }
    }

    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }
});
