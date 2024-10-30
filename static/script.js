const sendBtn = document.querySelector('#send-btn');
const promptInput = document.querySelector('#prompt-input');
const responseText = document.querySelector('#response-text');
const fileUpload = document.querySelector('#file-upload');
const dropZone = document.querySelector('#drop-zone');
const errorMessage = document.querySelector('#error-message');
const tableHead = document.querySelector('#table-head');
const tableBody = document.querySelector('#table-body');
let parsedData = null;

// Enable send button when input is provided
promptInput.addEventListener('input', function (event) {
    sendBtn.disabled = event.target.value ? false : true;
});

// Handle file upload and parsing with d3-dsv
fileUpload.addEventListener('change', handleFileUpload);
dropZone.addEventListener('dragover', (event) => event.preventDefault());
dropZone.addEventListener('drop', handleFileDrop);

// Handle drag-and-drop file upload
function handleFileDrop(event) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
        processFile(file);
    }
}

// Handle click-to-upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        processFile(file);
    }
}

// Process CSV file
function processFile(file) {
    if (file.type !== 'text/csv') {
        errorMessage.style.display = 'block';
        return;
    }
    errorMessage.style.display = 'none';

    const reader = new FileReader();
    reader.onload = (event) => {
        const data = d3.csvParse(event.target.result, d3.autoType);
        parsedData = data;
        displayDataPreview(data);
    };
    reader.readAsText(file);
}

// Display data preview
function displayDataPreview(data) {
    const headers = Object.keys(data[0]);
    tableHead.innerHTML = `<tr>${headers.map((header) => `<th>${header}</th>`).join('')}</tr>`;

    const previewRows = data.slice(0, 5).map((row) => {
        const values = headers.map((header) => `<td>${row[header]}</td>`).join('');
        return `<tr>${values}</tr>`;
    }).join('');
    tableBody.innerHTML = previewRows;
}

// Send message to backend
sendBtn.addEventListener('click', sendMessage);
promptInput.addEventListener('keyup', function (event) {
    if (event.keyCode === 13) {
        sendBtn.click();
    }
});

function sendMessage() {
    const prompt = promptInput.value;
    if (!prompt || !parsedData) {
        responseText.textContent = 'Please upload a CSV file and ask a question.';
        return;
    }

    promptInput.value = '';
    sendBtn.disabled = true;
    responseText.textContent = 'Waiting for response...';

    // Send request to backend
    fetch('/query', {
        method: 'POST',
        body: JSON.stringify({ prompt, data: parsedData }),
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            responseText.textContent = data.description;
            renderVegaChart(data.vegaSpec);
        })
        .catch(error => {
            responseText.textContent = 'Error: ' + error.message;
        })
        .finally(() => {
            sendBtn.disabled = false;
        });
}

// Render Vega-Lite chart
function renderVegaChart(spec) {
    vegaEmbed('#vega-chart', spec)
        .catch(error => console.error('Error rendering Vega chart:', error));
}
