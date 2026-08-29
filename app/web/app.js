/**
 * RFQ AI System - Frontend Logic (Consolidated)
 */

// --- DOM Elements ---
const chat = document.getElementById("chat");
const questionInput = document.getElementById("question");
const sendBtn = document.getElementById("sendBtn");
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileNameDisplay = document.getElementById("fileName");
const progressBar = document.getElementById("progress");
const documentsContainer = document.getElementById("documents");

/* =========================================
   FILE MANAGEMENT (PHASE 3: BUNDLE UPLOAD)
   ========================================= */
if (dropZone && fileInput) {

    dropZone.addEventListener("click", () => fileInput.click());

}
fileInput.style.display = "none"; 

fileInput.addEventListener("change", async () => {
    const files = fileInput.files;
    if (files.length === 0) return;
    await handleFiles(files);
});

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", async (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length > 0) await handleFiles(files);
});
async function handleFiles(files) {

    fileNameDisplay.textContent = `Analyzing bundle of ${files.length} file(s)...`;
    progressBar.style.width = "50%";

    try {

        const responseData = await uploadBundle(files);

        fileNameDisplay.textContent = "Analysis complete!";
        progressBar.style.width = "100%";

        const aiDiv = createMessageElement("ai system");

        aiDiv.innerHTML = `
        <b>📂 RFQ Bundle Uploaded</b><br>
        ${[...files].map(f => "• " + f.name).join("<br>")}
        `;

        if (responseData && responseData.engineering_analysis) {
            displayConflictReport(responseData.engineering_analysis);
        }

    } catch (error) {

        console.error("Bundle upload failed:", error);
        alert("Failed to process the RFQ bundle.");
        progressBar.style.width = "0%";

    }

    setTimeout(() => {
        fileNameDisplay.textContent = "";
        progressBar.style.width = "0%";
    }, 3000);

    loadDocuments();
}

function uploadBundle(files) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append("project_name", "RFQ Analysis " + new Date().toLocaleTimeString());
        
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload/bundle");

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(xhr.statusText));
            }
        };

        xhr.onerror = () => reject(new Error("Network Error"));
        xhr.send(formData);
    });
}

/* =========================================
   PHASE 4: REQUIREMENT MATRIX UI & EXPORT
   ========================================= */

function displayConflictReport(analysis) {
    const aiDiv = createMessageElement("ai system-alert");
    
    let html = `<h3>⚠️ Engineering Conflict Report</h3>`;
    html += `<p>Cross-referenced ${analysis.total_entities_checked} items.</p>`;

    if (analysis.conflicts_found > 0) {
        html += `<p style="color: #ff4d4d;">❌ Found ${analysis.conflicts_found} conflict(s).</p>`;
        html += `<button id="downloadCsvBtn" class="action-btn">📥 Download CSV Report</button>`;
        
        html += `<div class="table-wrapper">
                    <table>
                        <thead>
                            <tr><th>Entity</th><th>Source Quantities</th></tr>
                        </thead>
                        <tbody>`;
        
        if(analysis.conflict_details) {
            analysis.conflict_details.forEach(item => {
                let qtyStr = Object.entries(item.quantities)
                                   .map(([src, qty]) => `<b>${src}:</b> ${qty}`)
                                   .join('<br>');
                html += `<tr><td>${item.entity}</td><td>${qtyStr}</td></tr>`;
            });
        }
        html += `</tbody></table></div>`;
    } else {
        html += `<p style="color: #28a745;">✅ No major conflicts detected between documents.</p>`;
    }

    aiDiv.innerHTML = html; 
    chat.scrollTop = chat.scrollHeight;

    const downloadBtn = document.getElementById("downloadCsvBtn");
    if (downloadBtn) {
        downloadBtn.onclick = () => downloadCSV(analysis);
    }
}

async function downloadCSV(analysisData) {
    try {
        const response = await fetch("/export/conflicts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(analysisData)
        });
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "RFQ_Conflict_Report.csv";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        alert("Failed to download the report.");
    }
}

/* =========================================
   CHAT FUNCTIONALITY
   ========================================= */

function createMessageElement(type) {
    const div = document.createElement("div");
    div.className = `message ${type}`;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div;
}

async function askAI() {
    const question = questionInput.value.trim();
    if (!question) return;

    // 1. Lock UI
    questionInput.disabled = true;
    sendBtn.disabled = true;

    // 2. Display user message
    createMessageElement("user").textContent = question;
    questionInput.value = "";
    
    const aiDiv = createMessageElement("ai thinking");
    aiDiv.textContent = "Thinking...";

    try {
        const response = await fetch("/query/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });

        if (!response.ok) throw new Error("Server error");
        // Inside your askAI() function's try block:
        const data = await response.json();
        aiDiv.classList.remove("thinking");

        // Format the answer with sources
        
        aiDiv.innerHTML = `
            ${data.answer}
            ${data.sources && data.sources.length > 0 
                ? `<div class="sources" style="margin-top:10px; font-size:0.8em; color:gray;">
                    <strong>Sources:</strong> ${data.sources.join(", ")}
                </div>` 
                : ""
            }
        `;

    } catch (error) {
        console.error("Chat Error:", error);
        aiDiv.classList.remove("thinking");
        aiDiv.classList.add("error");
        aiDiv.textContent = "⚠️ Error: Could not connect to service.";
    } finally {
        // 3. Unlock UI (Crucial)
        questionInput.disabled = false;
        sendBtn.disabled = false;
        questionInput.focus();
        chat.scrollTop = chat.scrollHeight;
    }
}

/* =========================================
   DOCUMENT MANAGEMENT
   ========================================= */

async function loadDocuments() {
    try {
        const response = await fetch("/documents");
        const data = await response.json();
        documentsContainer.innerHTML = "";

        if (!data.documents || data.documents.length === 0) {
            documentsContainer.innerHTML = "<p class='empty-state'>No documents uploaded yet.</p>";
            return;
        }

        data.documents.forEach(doc => {
            const div = document.createElement("div");
            div.className = "document-item";
            div.innerHTML = `<span class="doc-name">${doc}</span>`;
            
            const delBtn = document.createElement("button");
            delBtn.className = "delete-btn";
            delBtn.innerHTML = "🗑️";
            delBtn.onclick = () => deleteDocument(doc);

            div.appendChild(delBtn);
            documentsContainer.appendChild(div);
        });
    } catch (error) {
        documentsContainer.innerHTML = "<p class='error-state'>Error loading documents.</p>";
    }
}

async function deleteDocument(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;
    try {
        await fetch(`/delete/${filename}`, { method: "DELETE" });
        loadDocuments();
    } catch (error) {
        alert("Error deleting document.");
    }
}

// Final Event Listeners
sendBtn.onclick = askAI;
questionInput.onkeydown = (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        askAI();
    }
};

// Initial Load
loadDocuments();