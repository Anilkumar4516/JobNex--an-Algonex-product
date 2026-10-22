// script.js - JobNex Interactive Frontend Controller
const API_BASE = "http://127.0.0.1:8000";

// DOM Elements
const navButtons = document.querySelectorAll(".nav-btn");
const tabContents = document.querySelectorAll(".tab-content");
const toast = document.getElementById("toast");
const serverStatus = document.getElementById("server-status");

// Sample Data for quick testing
const SAMPLE_RESUME = `Anilkumar - Senior Python & Full Stack Engineer
Skills: Python, FastAPI, MySQL, Redis, Docker, Git, REST APIs, JavaScript, React, CI/CD, Unit Testing.
Experience:
- Engineered asynchronous microservices in FastAPI and MySQL handling 5,000+ daily requests.
- Designed database schemas, optimized composite indexes, and implemented connection pooling.
- Developed automated resume matching algorithms and integrated Google GenAI / Gemini APIs.
- Built responsive UI components using vanilla JS, CSS3, and React.`;

const SAMPLE_JD = `Job Title: Senior Python Backend Engineer
Company: Northwind Labs
Requirements:
- Strong hands-on experience in Python 3.11+, FastAPI or Flask, and asynchronous programming.
- Proficiency in relational databases (MySQL/PostgreSQL), indexing, and query optimization.
- Experience with Docker, cloud infrastructure (AWS/GCP), and CI/CD pipelines.
- Familiarity with AI/LLM integration (Google Gemini, OpenAI, or LangChain).
- Understanding of automated unit testing, Pytest, and RESTful API best practices.`;

// ---------------- Navigation Tabs ----------------
function switchTab(tabId) {
    navButtons.forEach(btn => {
        btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    tabContents.forEach(content => {
        if (content.id === tabId) {
            content.classList.add("active");
            content.hidden = false;
        } else {
            content.classList.remove("active");
            content.hidden = true;
        }
    });

    if (tabId === "tab-workbench") {
        loadWorkbenchData();
    } else if (tabId === "tab-applications") {
        loadApplicationsData();
    } else if (tabId === "tab-jobs") {
        const grid = document.getElementById("jobs-grid");
        if (grid.children.length === 0) {
            triggerJobSearch();
        }
    }
}

navButtons.forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// ---------------- Toast Notifications ----------------
let toastTimeout;
function showToast(message, type = "info") {
    clearTimeout(toastTimeout);
    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    toast.hidden = false;
    toastTimeout = setTimeout(() => {
        toast.hidden = true;
    }, 4000);
}

// ---------------- Health Check ----------------
async function checkBackendHealth() {
    try {
        const res = await fetch(`${API_BASE}/`);
        if (res.ok) {
            serverStatus.innerHTML = `<span class="status-dot"></span><span class="status-text">Backend Connected</span>`;
        } else {
            serverStatus.innerHTML = `<span class="status-dot" style="background:#ef4444;box-shadow:0 0 8px #ef4444;"></span><span class="status-text">Backend Error</span>`;
        }
    } catch {
        serverStatus.innerHTML = `<span class="status-dot" style="background:#f59e0b;box-shadow:0 0 8px #f59e0b;"></span><span class="status-text">Offline / Connecting</span>`;
    }
}

// ---------------- Tab 1: Resume Analyzer ----------------
const analyzeForm = document.getElementById("analyze-form");
const resumeInput = document.getElementById("resume_text");
const jdInput = document.getElementById("jd_text");
const resumeCount = document.getElementById("resume-count");
const jdCount = document.getElementById("jd-count");
const analyzeBtn = document.getElementById("analyze-button");
const emptyResults = document.getElementById("empty-results");
const activeResults = document.getElementById("active-results");
const scoreNumber = document.getElementById("score-number");
const scoreCircle = document.getElementById("score-circle");
const matchedTags = document.getElementById("matched-skills-tags");
const missingTags = document.getElementById("missing-skills-tags");
const matchedCount = document.getElementById("matched-count");
const missingCount = document.getElementById("missing-count");
const suggestionsList = document.getElementById("suggestions-list");
const saveBadge = document.getElementById("analysis-save-badge");
const btnLoadSample = document.getElementById("btn-load-sample");
const btnGoWorkbench = document.getElementById("btn-go-workbench");
const btnPrepInterview = document.getElementById("btn-prep-interview");

function updateCounts() {
    resumeCount.textContent = `${resumeInput.value.length} chars`;
    jdCount.textContent = `${jdInput.value.length} chars`;
}
resumeInput.addEventListener("input", updateCounts);
jdInput.addEventListener("input", updateCounts);

btnLoadSample.addEventListener("click", () => {
    resumeInput.value = SAMPLE_RESUME;
    jdInput.value = SAMPLE_JD;
    updateCounts();
    showToast("Sample Python Engineer resume and JD loaded!", "success");
});

// Auto-Scrape Job URL using GenAI
const btnAutoScrapeGenai = document.getElementById("btn-auto-scrape-genai");
const autoScrapeUrlInput = document.getElementById("auto-scrape-url");

if (btnAutoScrapeGenai && autoScrapeUrlInput) {
    btnAutoScrapeGenai.addEventListener("click", async () => {
        const url = autoScrapeUrlInput.value.trim();
        if (!url) {
            showToast("Please enter a valid job URL to scrape", "error");
            return;
        }

        btnAutoScrapeGenai.disabled = true;
        btnAutoScrapeGenai.textContent = "Scraping with GenAI...";

        try {
            const res = await fetch(`${API_BASE}/api/jobs/scrape`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Scrape failed");

            const skillsStr = (data.required_skills && data.required_skills.length > 0)
                ? `\nKey Required Skills: ${data.required_skills.join(", ")}`
                : "";
            const emailStr = data.apply_email ? `\nRecruiter Contact: ${data.apply_email}` : "";
            const locationStr = data.location ? `\nLocation: ${data.location}` : "";

            jdInput.value = `Job Title: ${data.job_title || 'Role'}\nCompany: ${data.company || 'Hiring Company'}${locationStr}${emailStr}${skillsStr}\n\nJob Description:\n${data.job_description || ''}`;
            updateCounts();

            showToast(`GenAI successfully scraped: "${data.job_title}" at "${data.company}"!`, "success");
        } catch (err) {
            showToast(`Auto-scrape note: ${err.message}`, "error");
        } finally {
            btnAutoScrapeGenai.disabled = false;
            btnAutoScrapeGenai.textContent = "⚡ Scrape with GenAI";
        }
    });
}

if (btnGoWorkbench) btnGoWorkbench.addEventListener("click", () => switchTab("tab-workbench"));
if (btnPrepInterview) btnPrepInterview.addEventListener("click", () => {
    document.getElementById("prep-role").value = "Senior Python Backend Engineer";
    document.getElementById("prep-jd").value = jdInput.value || SAMPLE_JD;
    switchTab("tab-interview");
    generateInterviewPrep();
});

analyzeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const resumeText = resumeInput.value.trim();
    const jdText = jdInput.value.trim();

    if (!resumeText || !jdText) {
        showToast("Please provide both resume and job description.", "error");
        return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.querySelector(".btn-text").textContent = "Analyzing & Saving to Workbench...";

    try {
        const response = await fetch(`${API_BASE}/api/analyse`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resume_text: resumeText, jd_text: jdText })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Analysis request failed");
        }

        renderAnalysisResults(data);
        showToast(`Analysis complete! Saved to MySQL Workbench (ID: #${data.Analysis_Id})`, "success");
    } catch (err) {
        showToast(`Analysis failed: ${err.message}`, "error");
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.querySelector(".btn-text").textContent = "⚡ Analyze Resume & Save";
    }
});

function renderAnalysisResults(data) {
    emptyResults.hidden = true;
    activeResults.hidden = false;

    const score = Math.round(data.matched_score || data.match_score || 0);
    scoreNumber.textContent = `${score}%`;

    if (score >= 70) {
        scoreCircle.style.borderColor = "var(--success)";
        scoreCircle.style.boxShadow = "0 0 15px rgba(16, 185, 129, 0.4)";
    } else if (score >= 40) {
        scoreCircle.style.borderColor = "var(--warning)";
        scoreCircle.style.boxShadow = "0 0 15px rgba(245, 158, 11, 0.4)";
    } else {
        scoreCircle.style.borderColor = "var(--danger)";
        scoreCircle.style.boxShadow = "0 0 15px rgba(239, 68, 68, 0.4)";
    }

    saveBadge.textContent = `Saved to MySQL Workbench #${data.Analysis_Id || "Done"}`;

    const matched = data.matched_skills || [];
    matchedCount.textContent = matched.length;
    matchedTags.innerHTML = matched.length > 0 
        ? matched.map(s => `<span class="skill-tag matched">${escapeHtml(s)}</span>`).join("")
        : `<span class="text-muted">No exact skill matches detected</span>`;

    const missing = data.missing_skills || [];
    missingCount.textContent = missing.length;
    missingTags.innerHTML = missing.length > 0
        ? missing.map(s => `<span class="skill-tag missing">${escapeHtml(s)}</span>`).join("")
        : `<span class="text-muted">None! All JD skills covered.</span>`;

    const suggestions = data.suggestions || [];
    suggestionsList.innerHTML = suggestions.length > 0
        ? suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join("")
        : `<li>Resume is closely aligned with the job description.</li>`;
}

// ---------------- Tab 2: MySQL Workbench Viewer ----------------
const workbenchTbody = document.getElementById("workbench-tbody");
const btnRefreshWorkbench = document.getElementById("btn-refresh-workbench");

btnRefreshWorkbench.addEventListener("click", loadWorkbenchData);

async function loadWorkbenchData() {
    workbenchTbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Fetching records from MySQL...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/api/analyses`);
        const data = await res.json();
        const records = data.analyses || [];

        if (records.length === 0) {
            workbenchTbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No analyses saved in MySQL workbench yet. Run an analysis in Tab 1!</td></tr>`;
            return;
        }

        workbenchTbody.innerHTML = records.map(r => {
            const score = Math.round(r.matched_score || 0);
            const scoreClass = score >= 70 ? "score-high" : (score >= 40 ? "score-med" : "score-low");
            const dateStr = r.created_At ? r.created_At.replace("T", " ").substring(0, 19) : "Recently";
            const matchedCount = (r.matched_skills || []).length;
            const missingCount = (r.missing_skills || []).length;
            const preview = (r.jd_preview || r.resume_preview || "Analysis record").substring(0, 45) + "...";

            return `
                <tr>
                    <td><strong>#${r.Analysis_id}</strong></td>
                    <td class="text-muted">${escapeHtml(dateStr)}</td>
                    <td><span class="score-badge ${scoreClass}">${score}%</span></td>
                    <td><span class="skill-tag matched">${matchedCount} skills</span></td>
                    <td><span class="skill-tag missing">${missingCount} missing</span></td>
                    <td><small class="text-muted">${escapeHtml(preview)}</small></td>
                    <td>
                        <button class="btn-secondary btn-sm" onclick="viewAnalysisDetail(${r.Analysis_id})">View</button>
                        <button class="btn-secondary btn-sm" style="color:#ef4444;" onclick="deleteAnalysisRecord(${r.Analysis_id})">Delete</button>
                    </td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        workbenchTbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Failed to load MySQL records: ${escapeHtml(err.message)}</td></tr>`;
    }
}

window.viewAnalysisDetail = async function(id) {
    try {
        const res = await fetch(`${API_BASE}/api/analyses/${id}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Record not found");

        const modalBody = document.getElementById("modal-body");
        document.getElementById("modal-title").textContent = `Analysis #${data.Analysis_id} Detail`;

        modalBody.innerHTML = `
            <div style="margin-bottom:1rem;">
                <strong>Date:</strong> ${escapeHtml(data.created_At || "")} &nbsp;|&nbsp;
                <strong>Match Score:</strong> <span class="score-badge score-high">${Math.round(data.matched_score)}%</span>
            </div>
            <h4>Matched Skills:</h4>
            <div class="badges-container" style="margin-bottom:1rem;">
                ${(data.matched_skills || []).map(s => `<span class="skill-tag matched">${escapeHtml(s)}</span>`).join("")}
            </div>
            <h4>Missing Skills:</h4>
            <div class="badges-container" style="margin-bottom:1rem;">
                ${(data.missing_skills || []).map(s => `<span class="skill-tag missing">${escapeHtml(s)}</span>`).join("")}
            </div>
            <h4>Suggestions:</h4>
            <ul class="suggestions-list" style="margin-bottom:1rem;">
                ${(data.suggestions || []).map(s => `<li>${escapeHtml(s)}</li>`).join("")}
            </ul>
            <h4>Resume Content Excerpt:</h4>
            <pre style="background:rgba(0,0,0,0.3);padding:0.75rem;border-radius:6px;max-height:140px;overflow:auto;margin-bottom:1rem;font-size:0.8rem;">${escapeHtml(data.resume_text || "")}</pre>
            <h4>Job Description Excerpt:</h4>
            <pre style="background:rgba(0,0,0,0.3);padding:0.75rem;border-radius:6px;max-height:140px;overflow:auto;font-size:0.8rem;">${escapeHtml(data.jd_text || "")}</pre>
        `;
        document.getElementById("detail-modal").hidden = false;
    } catch (err) {
        showToast(err.message, "error");
    }
};

window.deleteAnalysisRecord = async function(id) {
    if (!confirm(`Are you sure you want to delete analysis #${id} from MySQL?`)) return;
    try {
        const res = await fetch(`${API_BASE}/api/analyses/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast(`Analysis #${id} deleted from MySQL Workbench`, "success");
            loadWorkbenchData();
        } else {
            throw new Error("Delete failed");
        }
    } catch (err) {
        showToast(err.message, "error");
    }
};

// ---------------- Tab 3: Live Job Search ----------------
const jobSearchForm = document.getElementById("job-search-form");
const jobKeywordInput = document.getElementById("job-keyword");
const jobRegionSelect = document.getElementById("job-region");
const jobsGrid = document.getElementById("jobs-grid");
const jobsCountText = document.getElementById("jobs-count-text");

jobSearchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    triggerJobSearch();
});

async function triggerJobSearch() {
    const keyword = jobKeywordInput.value.trim() || "Python";
    const region = jobRegionSelect.value || "global";

    jobsGrid.innerHTML = `<div class="card" style="grid-column:1/-1;text-align:center;padding:2rem;">Searching live job postings...</div>`;
    jobsCountText.textContent = `Searching for "${keyword}" in ${region.toUpperCase()}...`;

    try {
        const res = await fetch(`${API_BASE}/api/jobs/search?keyword=${encodeURIComponent(keyword)}&region=${encodeURIComponent(region)}&limit=10`);
        const data = await res.json();
        const jobs = data.jobs || [];

        jobsCountText.textContent = `Found ${jobs.length} jobs via ${data.source ? data.source.toUpperCase() : 'JobNex Engine'}.`;

        if (jobs.length === 0) {
            jobsGrid.innerHTML = `<div class="card" style="grid-column:1/-1;text-align:center;padding:2rem;">No jobs found for this search. Try searching for "Python", "Northwind Labs", or "Brightpath Systems".</div>`;
            return;
        }

        jobsGrid.innerHTML = jobs.map((job, idx) => {
            const isFeatured = job.company.includes("Northwind") || job.company.includes("Brightpath");
            return `
                <div class="job-card">
                    <div>
                        <div class="job-card-header">
                            <span class="job-company">${escapeHtml(job.company)}</span>
                            ${isFeatured ? '<span class="badge-sub">Featured Role</span>' : ''}
                        </div>
                        <h4 class="job-title">${escapeHtml(job.title)}</h4>
                        <div class="job-meta-row">
                            <span class="job-badge">📍 ${escapeHtml(job.location || 'Remote')}</span>
                            ${job.job_type ? `<span class="job-badge">⏱️ ${escapeHtml(job.job_type)}</span>` : ''}
                            <span class="job-badge">🌐 ${escapeHtml(job.source || 'remotive')}</span>
                        </div>
                        <p class="job-snippet" style="margin-top:0.75rem;">${escapeHtml(job.description || '')}</p>
                    </div>

                    <div class="job-actions-row">
                        <button class="btn-primary btn-sm flex-1" onclick="useJobInAnalyzer(${idx})">Analyze Match</button>
                        <button class="btn-secondary btn-sm" onclick="queueJobForApply(${idx})">Queue Apply</button>
                        ${job.url ? `<a href="${escapeHtml(job.url)}" target="_blank" class="btn-secondary btn-sm" rel="noopener">Link ↗</a>` : ''}
                    </div>
                </div>
            `;
        }).join("");

        window.currentJobsList = jobs;
    } catch (err) {
        jobsGrid.innerHTML = `<div class="card" style="grid-column:1/-1;text-align:center;padding:2rem;color:#ef4444;">Search failed: ${escapeHtml(err.message)}</div>`;
    }
}

window.useJobInAnalyzer = function(idx) {
    const job = window.currentJobsList[idx];
    if (!job) return;

    if (!resumeInput.value.trim()) {
        resumeInput.value = SAMPLE_RESUME;
    }
    jdInput.value = `Job Title: ${job.title}\nCompany: ${job.company}\nLocation: ${job.location}\n\nDescription:\n${job.description}`;
    updateCounts();
    switchTab("tab-analyzer");
    analyzeForm.dispatchEvent(new Event("submit"));
};

window.queueJobForApply = async function(idx) {
    const job = window.currentJobsList[idx];
    if (!job) return;

    const resumeText = resumeInput.value.trim() || SAMPLE_RESUME;

    try {
        const res = await fetch(`${API_BASE}/api/applications`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                resume_text: resumeText,
                job_title: job.title,
                company: job.company,
                job_description: job.description,
                job_url: job.url || null
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Queueing failed");

        showToast(`Queued application for ${job.title} at ${job.company}! (Score: ${Math.round(data.match_score)}%)`, "success");
    } catch (err) {
        showToast(err.message, "error");
    }
};

// ---------------- Tab 4: Interview Prep with Answer Tips ----------------
const interviewForm = document.getElementById("interview-prep-form");
const prepRoleInput = document.getElementById("prep-role");
const prepJdInput = document.getElementById("prep-jd");
const prepEmpty = document.getElementById("prep-empty");
const prepContainer = document.getElementById("prep-container");
const btnGeneratePrep = document.getElementById("btn-generate-prep");

interviewForm.addEventListener("submit", (e) => {
    e.preventDefault();
    generateInterviewPrep();
});

async function generateInterviewPrep() {
    const role = prepRoleInput.value.trim() || "Python Software Engineer";
    const jd = prepJdInput.value.trim();

    btnGeneratePrep.disabled = true;
    btnGeneratePrep.innerHTML = `<span>⏳ Raising Questions & Answer Tips...</span>`;

    try {
        const res = await fetch(`${API_BASE}/api/interview/prep`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                job_title: role,
                job_description: jd,
                resume_text: resumeInput.value.trim() || ""
            })
        });

        const data = await res.json();
        const questions = data.questions || [];

        prepEmpty.hidden = true;
        prepContainer.hidden = false;

        prepContainer.innerHTML = questions.map((q, idx) => {
            const tips = q.answer_tips || {};
            const keyPoints = tips.key_points || [];
            const star = tips.star_framework || {};
            const pitfall = tips.pitfalls_to_avoid || "Avoid generic answers without specific metrics.";
            const samplePhrase = tips.sample_answer_points || "";

            return `
                <div class="prep-item ${idx === 0 ? 'open' : ''}" id="prep-item-${q.id}">
                    <div class="prep-question-header" onclick="togglePrepItem(${q.id})">
                        <div>
                            <div class="prep-category-tag">${escapeHtml(q.category || 'Interview Question')}</div>
                            <div class="prep-question-text">Q${q.id}: ${escapeHtml(q.question)}</div>
                        </div>
                        <span class="prep-arrow">▶</span>
                    </div>

                    <div class="prep-answer-body">
                        <div class="answer-tip-box">
                            <h5>💡 Key Talking Points (What Interviewers Expect):</h5>
                            <ul class="suggestions-list">
                                ${keyPoints.map(kp => `<li>${escapeHtml(kp)}</li>`).join("")}
                            </ul>
                        </div>

                        ${star.situation ? `
                            <div class="star-grid">
                                <div class="star-cell"><strong>S - Situation:</strong><br>${escapeHtml(star.situation)}</div>
                                <div class="star-cell"><strong>T - Task:</strong><br>${escapeHtml(star.task)}</div>
                                <div class="star-cell"><strong>A - Action:</strong><br>${escapeHtml(star.action)}</div>
                                <div class="star-cell"><strong>R - Result:</strong><br>${escapeHtml(star.result)}</div>
                            </div>
                        ` : ''}

                        ${samplePhrase ? `
                            <div style="margin-bottom:0.75rem;">
                                <strong>Sample Answer Phrasing:</strong>
                                <p style="font-style:italic;color:var(--text-secondary);margin-top:0.25rem;">"${escapeHtml(samplePhrase)}"</p>
                            </div>
                        ` : ''}

                        <div class="pitfall-box">
                            ⚠️ <strong>Pitfall to Avoid:</strong> ${escapeHtml(pitfall)}
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        showToast(`Generated ${questions.length} interview questions with complete Answer Tips!`, "success");
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        btnGeneratePrep.disabled = false;
        btnGeneratePrep.innerHTML = `<span>🎯 Generate Questions & Answer Tips</span>`;
    }
}

window.togglePrepItem = function(id) {
    const item = document.getElementById(`prep-item-${id}`);
    if (item) {
        item.classList.toggle("open");
    }
};

// ---------------- Tab 5: Referrals & HR Email Generator ----------------
const btnScrapeHr = document.getElementById("btn-scrape-hr");
const scrapeUrlInput = document.getElementById("scrape-url");
const scrapeResultBox = document.getElementById("scrape-result");
const referralGenForm = document.getElementById("referral-gen-form");
const previewSubject = document.getElementById("preview-subject");
const previewBody = document.getElementById("preview-body");
const btnCopyEmail = document.getElementById("btn-copy-email");
const btnSendEmailNow = document.getElementById("btn-send-email-now");
const sendTargetEmail = document.getElementById("send-target-email");

btnScrapeHr.addEventListener("click", async () => {
    const url = scrapeUrlInput.value.trim();
    if (!url) {
        showToast("Please enter a valid URL to scrape HR contacts", "error");
        return;
    }

    btnScrapeHr.disabled = true;
    btnScrapeHr.textContent = "Scraping...";
    scrapeResultBox.hidden = false;
    scrapeResultBox.innerHTML = `Searching webpage for HR & recruiter contacts...`;

    try {
        const res = await fetch(`${API_BASE}/api/hr/scrape`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });
        const data = await res.json();

        if (data.hr_email) {
            scrapeResultBox.innerHTML = `
                ✅ <strong>Found Recruiter / HR Contact:</strong> <code style="color:var(--cyan);">${escapeHtml(data.hr_email)}</code><br>
                ${data.recruiter_hint ? `<span>Contact Name: <strong>${escapeHtml(data.recruiter_hint)}</strong></span><br>` : ''}
                <button type="button" class="btn-secondary btn-sm" style="margin-top:0.4rem;" onclick="useScrapedEmail('${escapeHtml(data.hr_email)}')">Use this Recruiter Email</button>
            `;
            sendTargetEmail.value = data.hr_email;
            showToast(`Found HR contact: ${data.hr_email}`, "success");
        } else {
            scrapeResultBox.innerHTML = `ℹ️ No direct email found on this page. You can still generate the Google or Employee referral letter below!`;
        }
    } catch (err) {
        scrapeResultBox.innerHTML = `⚠️ Scraper note: ${escapeHtml(err.message)}`;
    } finally {
        btnScrapeHr.disabled = false;
        btnScrapeHr.textContent = "Scrape HR Contact";
    }
});

window.useScrapedEmail = function(email) {
    sendTargetEmail.value = email;
    showToast(`Recipient email set to: ${email}`, "info");
};

referralGenForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const company = document.getElementById("ref-company").value.trim();
    const title = document.getElementById("ref-title").value.trim();
    const referrer = document.getElementById("ref-referrer").value.trim();
    const access = document.getElementById("ref-access").value;
    const jobId = document.getElementById("ref-job-id").value.trim();
    const skills = document.getElementById("ref-skills").value.split(",").map(s => s.trim()).filter(Boolean);

    try {
        const res = await fetch(`${API_BASE}/api/referrals/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                applicant_name: "Anilkumar",
                job_title: title,
                target_company: company,
                referrer_name: referrer,
                job_id_or_url: jobId,
                access_type: access,
                top_skills: skills
            })
        });

        const data = await res.json();
        previewSubject.textContent = data.subject || "Employee Referral Request";
        previewBody.value = data.body || "";
        showToast("Referral outreach email generated!", "success");
    } catch (err) {
        showToast(err.message, "error");
    }
});

btnCopyEmail.addEventListener("click", () => {
    const fullText = `Subject: ${previewSubject.textContent}\n\n${previewBody.value}`;
    navigator.clipboard.writeText(fullText).then(() => {
        showToast("Referral email copied to clipboard!", "success");
    });
});

btnSendEmailNow.addEventListener("click", async () => {
    const toEmail = sendTargetEmail.value.trim();
    if (!toEmail) {
        showToast("Please provide recipient email address", "error");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/referrals/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                to_email: toEmail,
                subject: previewSubject.textContent,
                body: previewBody.value
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Send failed");
        showToast(`Email sent successfully to ${toEmail}!`, "success");
    } catch (err) {
        showToast(`Send failed: ${err.message}`, "error");
    }
});

// ---------------- Tab 6: Auto-Apply Queue ----------------
const appsTbody = document.getElementById("apps-tbody");
const btnRefreshApps = document.getElementById("btn-refresh-apps");

btnRefreshApps.addEventListener("click", loadApplicationsData);

async function loadApplicationsData() {
    appsTbody.innerHTML = `<tr><td colspan="8" class="text-center py-4">Fetching queued applications...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/api/applications`);
        const data = await res.json();
        const apps = data.applications || [];

        if (apps.length === 0) {
            appsTbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">No applications in queue. Search jobs in Tab 3 and click "Queue Apply"!</td></tr>`;
            return;
        }

        appsTbody.innerHTML = apps.map(app => {
            const score = Math.round(app.match_score || 0);
            const statusBadge = app.status === "sent" 
                ? '<span class="skill-tag matched">Sent</span>' 
                : (app.status === "queued" ? '<span class="skill-tag missing">Queued</span>' : '<span class="job-badge">Manual</span>');

            return `
                <tr>
                    <td><strong>#${app.application_id}</strong></td>
                    <td><strong>${escapeHtml(app.company)}</strong></td>
                    <td>${escapeHtml(app.job_title)}</td>
                    <td><span class="score-badge score-high">${score}%</span></td>
                    <td><code>${escapeHtml(app.apply_email || 'No email (link apply)')}</code></td>
                    <td>${statusBadge}</td>
                    <td class="text-muted">${escapeHtml((app.created_at || '').substring(0, 10))}</td>
                    <td>
                        ${app.status === "queued" ? `<button class="btn-primary btn-sm" onclick="approveApplication(${app.application_id})">Approve & Send</button>` : '<span class="text-muted">Completed</span>'}
                    </td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        appsTbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-danger">${escapeHtml(err.message)}</td></tr>`;
    }
}

window.approveApplication = async function(id) {
    try {
        const res = await fetch(`${API_BASE}/api/applications/${id}/approve`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Approval failed");
        showToast(`Application #${id} approved and sent!`, "success");
        loadApplicationsData();
    } catch (err) {
        showToast(err.message, "error");
    }
};

// ---------------- Tab 7: AI Career Chatbot ----------------
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");
const promptPills = document.querySelectorAll(".prompt-pill");

promptPills.forEach(pill => {
    pill.addEventListener("click", () => {
        chatInput.value = pill.dataset.prompt;
        chatForm.dispatchEvent(new Event("submit"));
    });
});

chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    chatInput.value = "";

    // Append User Message
    const userDiv = document.createElement("div");
    userDiv.className = "message user-msg";
    userDiv.innerHTML = `
        <div class="msg-avatar">👤</div>
        <div class="msg-bubble">${escapeHtml(query)}</div>
    `;
    chatMessages.appendChild(userDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Append Loading Assistant Message
    const assistantDiv = document.createElement("div");
    assistantDiv.className = "message assistant-msg";
    assistantDiv.innerHTML = `
        <div class="msg-avatar">⚡</div>
        <div class="msg-bubble">Thinking...</div>
    `;
    chatMessages.appendChild(assistantDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: query })
        });
        const data = await res.json();

        // Convert basic markdown formatting to HTML
        let replyHtml = escapeHtml(data.reply || "I am here to help.")
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');

        const sourceTag = data.source === "gemini" 
            ? '<div style="margin-top:0.4rem;font-size:0.7rem;color:var(--cyan);">✨ Powered by Gemini AI</div>'
            : '<div style="margin-top:0.4rem;font-size:0.7rem;color:var(--text-muted);">⚡ Powered by JobNex Assistant</div>';

        assistantDiv.querySelector(".msg-bubble").innerHTML = replyHtml + sourceTag;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch {
        assistantDiv.querySelector(".msg-bubble").innerHTML = `Sorry, I encountered a temporary connection issue. Please verify backend is running on port 8000.`;
    }
});

// ---------------- Modal Close ----------------
document.getElementById("btn-modal-close").addEventListener("click", () => {
    document.getElementById("detail-modal").hidden = true;
});
document.getElementById("detail-modal").addEventListener("click", (e) => {
    if (e.target.id === "detail-modal") {
        document.getElementById("detail-modal").hidden = true;
    }
});

// ---------------- Utility: Escape HTML ----------------
function escapeHtml(text) {
    if (!text) return "";
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}

// ---------------- Initial Boot ----------------
document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    // Default referral email sample
    referralGenForm.dispatchEvent(new Event("submit"));
});