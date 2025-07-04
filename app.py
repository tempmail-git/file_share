import os
import uuid
import time
import threading
import shutil
import zipfile
import io
from flask import Flask, render_template_string, request, jsonify, send_file, make_response

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 * 1024  # 100 GB

# In-memory storage for active transfers
transfers = {}
transfer_lock = threading.Lock()
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# HTML template embedded in the Python code
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeoTransfer | File Sharing</title>
    <style>
        :root {
            --primary: #6366f1;
            --primary-light: #818cf8;
            --secondary: #0ea5e9;
            --accent: #8b5cf6;
            --success: #10b981;
            --error: #ef4444;
            --dark: #1e293b;
            --darker: #0f172a;
            --light: #f1f5f9;
            --card-bg: rgba(255, 255, 255, 0.08);
            --card-border: rgba(255, 255, 255, 0.1);
            --text-primary: #e2e8f0;
            --text-secondary: #94a3b8;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, var(--darker) 0%, var(--dark) 100%);
            min-height: 100vh;
            padding: 20px;
            color: var(--text-primary);
            overflow-x: hidden;
        }
        
        body::before {
            content: "";
            position: fixed;
            top: -50%;
            left: -50%;
            right: -50%;
            bottom: -50%;
            background: radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.1) 0%, transparent 60%);
            z-index: -1;
            animation: rotate 20s linear infinite;
        }
        
        @keyframes rotate {
            100% {
                transform: rotate(360deg);
            }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            padding: 30px 0 20px;
            position: relative;
        }
        
        .logo {
            font-size: 3.5rem;
            margin-bottom: 15px;
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 15px rgba(99, 102, 241, 0.3));
        }
        
        .tagline {
            font-size: 1.2rem;
            max-width: 600px;
            margin: 0 auto 40px;
            color: var(--text-secondary);
            font-weight: 300;
            line-height: 1.6;
        }
        
        .card-container {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 16px;
            border: 1px solid var(--card-border);
            padding: 30px;
            width: 100%;
            max-width: 500px;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            position: relative;
            overflow: hidden;
        }
        
        .card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            opacity: 0.8;
        }
        
        .card:hover {
            transform: translateY(-8px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
        }
        
        .card-header {
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--card-border);
        }
        
        .card-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            box-shadow: 0 4px 10px rgba(99, 102, 241, 0.3);
        }
        
        .card-icon i {
            font-size: 24px;
            color: white;
        }
        
        .card-title {
            font-size: 1.6rem;
            font-weight: 700;
            background: linear-gradient(45deg, var(--text-primary), var(--text-secondary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .drop-area {
            border: 2px dashed var(--card-border);
            border-radius: 12px;
            padding: 40px 20px;
            text-align: center;
            margin-bottom: 25px;
            transition: all 0.3s;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        
        .drop-area::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(99, 102, 241, 0.05);
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .drop-area:hover::before {
            opacity: 1;
        }
        
        .drop-area.active {
            border-color: var(--primary);
            background-color: rgba(99, 102, 241, 0.08);
        }
        
        .drop-area i {
            font-size: 3.5rem;
            margin-bottom: 15px;
            display: block;
            color: var(--primary-light);
            opacity: 0.8;
        }
        
        .drop-area p {
            margin: 5px 0;
            color: var(--text-secondary);
        }
        
        .file-input {
            display: none;
        }
        
        .btn {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border: none;
            padding: 14px 30px;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-block;
            text-align: center;
            width: 100%;
            max-width: 240px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .btn::before {
            content: "";
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: 0.5s;
        }
        
        .btn:hover::before {
            left: 100%;
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
        }
        
        .btn:disabled {
            background: var(--card-border);
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .btn:disabled:hover::before {
            left: -100%;
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, var(--accent), #a78bfa);
        }
        
        .btn-secondary:hover {
            box-shadow: 0 8px 20px rgba(139, 92, 246, 0.4);
        }
        
        .btn-accent {
            background: linear-gradient(135deg, var(--success), #34d399);
        }
        
        .btn-accent:hover {
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
        }
        
        .progress-container {
            margin: 25px 0;
        }
        
        .progress-bar {
            height: 10px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
            overflow: hidden;
            position: relative;
        }
        
        .progress {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            width: 0%;
            transition: width 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            position: relative;
        }
        
        .progress::after {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            background-size: 200% 100%;
            animation: shimmer 2s infinite;
        }
        
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        
        .file-info {
            display: flex;
            justify-content: space-between;
            margin-top: 12px;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        
        .id-container {
            margin: 25px 0;
            display: none;
            text-align: center;
        }
        
        .transfer-id {
            font-size: 1.5rem;
            font-weight: bold;
            padding: 16px 30px;
            background: rgba(99, 102, 241, 0.1);
            border-radius: 12px;
            display: inline-block;
            margin: 20px 0;
            color: var(--text-primary);
            border: 1px dashed var(--primary-light);
            cursor: pointer;
            position: relative;
            transition: all 0.3s;
            font-family: 'Fira Code', monospace;
            letter-spacing: 1px;
            backdrop-filter: blur(5px);
        }
        
        .transfer-id:hover {
            background: rgba(99, 102, 241, 0.2);
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(99, 102, 241, 0.2);
        }
        
        .id-tooltip {
            position: absolute;
            top: -35px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            backdrop-filter: blur(5px);
        }
        
        .transfer-id:hover .id-tooltip {
            opacity: 1;
        }
        
        .file-list {
            margin-top: 20px;
            max-height: 240px;
            overflow-y: auto;
            display: none;
            border-radius: 12px;
            background: rgba(0, 0, 0, 0.1);
            padding: 15px;
        }
        
        /* Scrollbar styling */
        .file-list::-webkit-scrollbar {
            width: 8px;
        }
        
        .file-list::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }
        
        .file-list::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 4px;
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid var(--card-border);
            align-items: center;
        }
        
        .file-item:last-child {
            border-bottom: none;
        }
        
        .file-name {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
            font-size: 0.95rem;
        }
        
        .file-size {
            margin-left: 15px;
            color: var(--text-secondary);
            font-size: 0.9rem;
            min-width: 70px;
            text-align: right;
        }
        
        .file-progress {
            width: 100%;
            margin-top: 8px;
        }
        
        .status {
            padding: 16px;
            border-radius: 12px;
            margin: 25px 0;
            text-align: center;
            display: none;
            backdrop-filter: blur(5px);
        }
        
        .status.success {
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        
        .status.error {
            background: rgba(239, 68, 68, 0.1);
            color: var(--error);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .instructions {
            margin-top: 40px;
            text-align: center;
            color: var(--text-secondary);
            font-size: 1rem;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .instructions h3 {
            font-size: 1.4rem;
            margin-bottom: 20px;
            color: var(--text-primary);
            font-weight: 600;
        }
        
        .steps {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }
        
        .step-card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            border: 1px solid var(--card-border);
            transition: transform 0.3s;
        }
        
        .step-card:hover {
            transform: translateY(-5px);
        }
        
        .step-number {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 15px;
            color: white;
            font-weight: bold;
            font-size: 1.2rem;
        }
        
        .step-card h4 {
            margin-bottom: 12px;
            font-size: 1.1rem;
            color: var(--text-primary);
        }
        
        .step-card p {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.5;
        }
        
        .file-limit {
            text-align: center;
            margin-top: 15px;
            color: var(--text-secondary);
            font-size: 0.95rem;
        }
        
        footer {
            text-align: center;
            margin-top: 60px;
            padding: 30px;
            color: var(--text-secondary);
            font-size: 0.95rem;
            border-top: 1px solid var(--card-border);
        }
        
        .link-input {
            width: 100%;
            padding: 14px 20px;
            border-radius: 12px;
            background: rgba(0, 0, 0, 0.1);
            border: 1px solid var(--card-border);
            color: var(--text-primary);
            font-size: 1rem;
            transition: all 0.3s;
            outline: none;
        }
        
        .link-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.3);
        }
        
        .link-input::placeholder {
            color: var(--text-secondary);
        }
        
        @media (max-width: 768px) {
            .card-container {
                flex-direction: column;
                align-items: center;
            }
            
            .card {
                max-width: 100%;
            }
            
            .steps {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">NeoTransfer</div>
            <p class="tagline">Peer-to-peer file sharing with end-to-end encryption. No server storage, no waiting.</p>
        </header>
        
        <div class="card-container">
            <!-- Sender Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">
                        <i class="fas fa-cloud-upload-alt"></i>
                    </div>
                    <h2 class="card-title">Send Files</h2>
                </div>
                
                <div class="drop-area" id="dropArea">
                    <i class="fas fa-cloud-upload-alt"></i>
                    <p>Drag & drop your files here</p>
                    <p>or</p>
                    <button class="btn" id="browseBtn">Browse Files</button>
                </div>
                <input type="file" id="fileInput" class="file-input" multiple>
                
                <div class="file-list" id="fileList"></div>
                
                <div class="progress-container" id="progressContainer" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress" id="totalProgressBar"></div>
                    </div>
                    <div class="file-info">
                        <span id="totalFiles">0 files</span>
                        <span id="totalSize">0 bytes</span>
                    </div>
                </div>
                
                <button class="btn" id="sendBtn" disabled>Generate Transfer ID</button>
                
                <div class="id-container" id="idContainer">
                    <p>Share this transfer ID with the recipient:</p>
                    <div class="transfer-id" id="transferId">
                        <span id="idText">Loading...</span>
                        <div class="id-tooltip">Click to copy</div>
                    </div>
                    <p class="instructions">The recipient should enter this ID in the "Receive Files" section</p>
                </div>
                
                <p class="file-limit">Supports multiple files and large transfers up to 100GB</p>
            </div>
            
            <!-- Receiver Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">
                        <i class="fas fa-cloud-download-alt"></i>
                    </div>
                    <h2 class="card-title">Receive Files</h2>
                </div>
                
                <input type="text" id="peerId" class="link-input" placeholder="Enter transfer ID">
                <button class="btn btn-secondary" id="receiveBtn" style="margin-top: 20px;">Connect</button>
                
                <div class="file-list" id="receiveFileList"></div>
                
                <div class="progress-container" id="receiveProgress" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress" id="receiveBar"></div>
                    </div>
                    <div class="file-info">
                        <span id="receiveStatusText">Preparing download...</span>
                    </div>
                </div>
                
                <div class="status" id="receiveStatus"></div>
                
                <a class="btn btn-accent" id="downloadBtn" style="display: none; margin-top: 20px;">Download All Files</a>
            </div>
        </div>
        
        <div class="instructions">
            <h3>How It Works</h3>
            <div class="steps">
                <div class="step-card">
                    <div class="step-number">1</div>
                    <h4>Select Files</h4>
                    <p>Choose files you want to send by dragging or browsing</p>
                </div>
                <div class="step-card">
                    <div class="step-number">2</div>
                    <h4>Generate ID</h4>
                    <p>Create a unique transfer ID to share with the recipient</p>
                </div>
                <div class="step-card">
                    <div class="step-number">3</div>
                    <h4>Share ID</h4>
                    <p>Send the transfer ID to your recipient through any channel</p>
                </div>
                <div class="step-card">
                    <div class="step-number">4</div>
                    <h4>Receive Files</h4>
                    <p>Recipient enters the ID to download files directly</p>
                </div>
            </div>
        </div>
        
        <footer>
            <p>NeoTransfer | Secure peer-to-peer file sharing | Built with Python Flask</p>
            <p>Files are transferred directly between browsers - no server storage</p>
        </footer>
    </div>

    <script>
        // DOM Elements
        const dropArea = document.getElementById('dropArea');
        const fileInput = document.getElementById('fileInput');
        const browseBtn = document.getElementById('browseBtn');
        const sendBtn = document.getElementById('sendBtn');
        const progressContainer = document.getElementById('progressContainer');
        const totalProgressBar = document.getElementById('totalProgressBar');
        const totalFiles = document.getElementById('totalFiles');
        const totalSize = document.getElementById('totalSize');
        const fileList = document.getElementById('fileList');
        const idContainer = document.getElementById('idContainer');
        const transferId = document.getElementById('transferId');
        const idText = document.getElementById('idText');
        
        const peerIdInput = document.getElementById('peerId');
        const receiveBtn = document.getElementById('receiveBtn');
        const receiveFileList = document.getElementById('receiveFileList');
        const receiveProgress = document.getElementById('receiveProgress');
        const receiveBar = document.getElementById('receiveBar');
        const receiveStatusText = document.getElementById('receiveStatusText');
        const receiveStatus = document.getElementById('receiveStatus');
        const downloadBtn = document.getElementById('downloadBtn');
        
        // Variables
        let selectedFiles = [];
        let transferIdValue = null;
        const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks
        
        // Event Listeners
        browseBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileSelect);
        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropArea.classList.add('active');
        });
        dropArea.addEventListener('dragleave', () => {
            dropArea.classList.remove('active');
        });
        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dropArea.classList.remove('active');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                handleFileSelect();
            }
        });
        
        sendBtn.addEventListener('click', generateTransferId);
        transferId.addEventListener('click', copyTransferId);
        receiveBtn.addEventListener('click', connectToPeer);
        
        // Handle file selection
        function handleFileSelect() {
            if (fileInput.files.length === 0) return;
            
            selectedFiles = Array.from(fileInput.files);
            updateFileList(selectedFiles);
            sendBtn.disabled = false;
        }
        
        // Update file list display
        function updateFileList(files) {
            fileList.innerHTML = '';
            fileList.style.display = 'block';
            progressContainer.style.display = 'block';
            
            let totalSizeBytes = 0;
            
            files.forEach((file, index) => {
                totalSizeBytes += file.size;
                
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                    <div class="file-progress">
                        <div class="progress-bar">
                            <div class="progress" id="fileProgress-${index}" style="width: 0%"></div>
                        </div>
                    </div>
                `;
                fileList.appendChild(fileItem);
            });
            
            totalFiles.textContent = `${files.length} file${files.length > 1 ? 's' : ''}`;
            totalSize.textContent = formatFileSize(totalSizeBytes);
            totalProgressBar.style.width = '0%';
        }
        
        // Format file size
        function formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' bytes';
            else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
            else if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
            else return (bytes / 1073741824).toFixed(1) + ' GB';
        }
        
        // Generate transfer ID
        function generateTransferId() {
            if (selectedFiles.length === 0) return;
            
            // Show progress
            totalProgressBar.style.width = '10%';
            
            // Create a new transfer on the server
            fetch('/create_transfer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_count: selectedFiles.length,
                    total_size: selectedFiles.reduce((sum, file) => sum + file.size, 0)
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    transferIdValue = data.transfer_id;
                    // Upload files in chunks
                    uploadFiles(transferIdValue);
                } else {
                    showStatus('Error: ' + data.error, 'error');
                    totalProgressBar.style.width = '0%';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showStatus('Error creating transfer', 'error');
                totalProgressBar.style.width = '0%';
            });
        }
        
        // Upload files in chunks
        function uploadFiles(transferId) {
            let uploadedCount = 0;
            const totalCount = selectedFiles.length;
            
            selectedFiles.forEach((file, fileIndex) => {
                const fileId = uuidv4();
                const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
                let chunkIndex = 0;
                
                function uploadNextChunk() {
                    if (chunkIndex >= totalChunks) {
                        // File upload complete
                        uploadedCount++;
                        updateTotalProgress(uploadedCount, totalCount);
                        
                        if (uploadedCount === totalCount) {
                            // All files uploaded
                            idContainer.style.display = 'block';
                            idText.textContent = transferId;
                            sendBtn.disabled = true;
                            showStatus('All files uploaded! Share the transfer ID.', 'success');
                            
                            // Animate ID container
                            idContainer.style.opacity = '0';
                            idContainer.style.transform = 'translateY(20px)';
                            setTimeout(() => {
                                idContainer.style.transition = 'all 0.5s ease';
                                idContainer.style.opacity = '1';
                                idContainer.style.transform = 'translateY(0)';
                            }, 100);
                        }
                        return;
                    }
                    
                    const start = chunkIndex * CHUNK_SIZE;
                    const end = Math.min(file.size, start + CHUNK_SIZE);
                    const chunk = file.slice(start, end);
                    
                    const formData = new FormData();
                    formData.append('transfer_id', transferId);
                    formData.append('file_id', fileId);
                    formData.append('file_index', fileIndex.toString());
                    formData.append('chunk_index', chunkIndex.toString());
                    formData.append('total_chunks', totalChunks.toString());
                    formData.append('chunk', chunk);
                    formData.append('file_name', file.name);
                    formData.append('file_size', file.size.toString());
                    
                    fetch('/upload_chunk', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Update progress for this file
                            const progress = ((chunkIndex + 1) / totalChunks) * 100;
                            document.getElementById(`fileProgress-${fileIndex}`).style.width = `${progress}%`;
                            
                            chunkIndex++;
                            uploadNextChunk();
                        } else {
                            showStatus(`Error uploading ${file.name}: ${data.error}`, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showStatus(`Error uploading ${file.name}`, 'error');
                    });
                }
                
                // Start uploading chunks for this file
                uploadNextChunk();
            });
        }
        
        // Update total progress
        function updateTotalProgress(uploadedCount, totalCount) {
            const progress = (uploadedCount / totalCount) * 100;
            totalProgressBar.style.width = `${progress}%`;
        }
        
        // Simple UUID generator for file chunks
        function uuidv4() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }
        
        // Copy transfer ID to clipboard
        function copyTransferId() {
            const textArea = document.createElement('textarea');
            textArea.value = transferIdValue;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            // Show visual feedback
            const originalText = idText.textContent;
            idText.textContent = 'Copied to clipboard!';
            idText.style.color = '#10b981';
            
            setTimeout(() => {
                idText.textContent = originalText;
                idText.style.color = '';
            }, 2000);
        }
        
        // Connect to peer
        function connectToPeer() {
            const transferId = peerIdInput.value.trim();
            if (!transferId) return;
            
            receiveBtn.disabled = true;
            receiveStatus.textContent = 'Connecting to peer...';
            receiveStatus.className = 'status';
            receiveStatus.style.display = 'block';
            
            // Animate status appearance
            receiveStatus.style.opacity = '0';
            receiveStatus.style.transform = 'translateY(10px)';
            setTimeout(() => {
                receiveStatus.style.transition = 'all 0.3s ease';
                receiveStatus.style.opacity = '1';
                receiveStatus.style.transform = 'translateY(0)';
            }, 100);
            
            // Check if transfer exists
            fetch(`/transfer/${transferId}`)
            .then(response => response.json())
            .then(data => {
                if (data.exists) {
                    receiveStatus.textContent = 'Transfer found! Preparing download...';
                    
                    // Get file list
                    fetch(`/transfer/${transferId}/files`)
                    .then(response => response.json())
                    .then(fileData => {
                        if (fileData.success) {
                            displayReceiveFiles(fileData.files);
                            receiveStatus.textContent = `Ready to download ${fileData.files.length} files`;
                            receiveStatus.className = 'status success';
                            
                            // Show download button
                            downloadBtn.href = `/download_all/${transferId}`;
                            downloadBtn.textContent = `Download All Files (${formatFileSize(fileData.total_size)})`;
                            downloadBtn.style.display = 'inline-block';
                            
                            // Animate download button appearance
                            downloadBtn.style.opacity = '0';
                            downloadBtn.style.transform = 'translateY(10px)';
                            setTimeout(() => {
                                downloadBtn.style.transition = 'all 0.4s ease';
                                downloadBtn.style.opacity = '1';
                                downloadBtn.style.transform = 'translateY(0)';
                            }, 100);
                        } else {
                            receiveStatus.textContent = 'Error: ' + fileData.error;
                            receiveStatus.className = 'status error';
                        }
                    });
                } else {
                    receiveStatus.textContent = 'Transfer not found. Please check the ID.';
                    receiveStatus.className = 'status error';
                    receiveBtn.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                receiveStatus.textContent = 'Error connecting to server';
                receiveStatus.className = 'status error';
                receiveBtn.disabled = false;
            });
        }
        
        // Display files for receiving
        function displayReceiveFiles(files) {
            receiveFileList.innerHTML = '';
            receiveFileList.style.display = 'block';
            
            // Animate file list appearance
            receiveFileList.style.opacity = '0';
            receiveFileList.style.transform = 'translateY(10px)';
            setTimeout(() => {
                receiveFileList.style.transition = 'all 0.4s ease';
                receiveFileList.style.opacity = '1';
                receiveFileList.style.transform = 'translateY(0)';
            }, 100);
            
            files.forEach(file => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <div class="file-name">${file.filename}</div>
                    <div class="file-size">${formatFileSize(file.filesize)}</div>
                `;
                receiveFileList.appendChild(fileItem);
            });
        }
        
        // Show status message
        function showStatus(message, type) {
            // In a real implementation, this would show a status message
            console.log(`${type}: ${message}`);
        }
        
        // Initialize
        function init() {
            // Check if we have a transfer ID in the URL
            const pathParts = window.location.pathname.split('/');
            if (pathParts.length > 2 && pathParts[1] === 'receive') {
                peerIdInput.value = pathParts[2];
            }
        }
        
        // Start the app
        init();
    </script>
</body>
</html>   """

# Flask Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/create_transfer', methods=['POST'])
def create_transfer():
    data = request.json
    transfer_id = str(uuid.uuid4())
    
    with transfer_lock:
        transfers[transfer_id] = {
            'files': [],
            'total_size': data['total_size'],
            'file_count': data['file_count'],
            'created_at': time.time(),
            'downloaded': False,
            'chunks': {}
        }
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_transfer, args=(transfer_id,))
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    return jsonify({
        'success': True,
        'transfer_id': transfer_id
    })

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    transfer_id = request.form.get('transfer_id')
    file_id = request.form.get('file_id')
    file_index = int(request.form.get('file_index'))
    chunk_index = int(request.form.get('chunk_index'))
    total_chunks = int(request.form.get('total_chunks'))
    file_name = request.form.get('file_name')
    file_size = int(request.form.get('file_size'))
    chunk = request.files['chunk']
    
    with transfer_lock:
        if transfer_id not in transfers:
            return jsonify({'success': False, 'error': 'Invalid transfer ID'}), 400
        
        transfer = transfers[transfer_id]
        
        # Create directory for chunks if it doesn't exist
        chunk_dir = os.path.join(UPLOAD_FOLDER, transfer_id, file_id)
        os.makedirs(chunk_dir, exist_ok=True)
        
        # Save chunk
        chunk_path = os.path.join(chunk_dir, f'chunk_{chunk_index}')
        chunk.save(chunk_path)
        
        # Track chunks
        if file_id not in transfer['chunks']:
            transfer['chunks'][file_id] = {
                'file_name': file_name,
                'file_size': file_size,
                'total_chunks': total_chunks,
                'received_chunks': 0,
                'file_index': file_index
            }
        
        transfer['chunks'][file_id]['received_chunks'] += 1
        
        # Check if all chunks received
        if transfer['chunks'][file_id]['received_chunks'] == total_chunks:
            # Combine chunks into a single file
            output_path = os.path.join(UPLOAD_FOLDER, transfer_id, f'file_{file_index}_{file_name}')
            with open(output_path, 'wb') as outfile:
                for i in range(total_chunks):
                    chunk_path = os.path.join(chunk_dir, f'chunk_{i}')
                    with open(chunk_path, 'rb') as infile:
                        shutil.copyfileobj(infile, outfile)
            
            # Add to files list
            transfer['files'].append({
                'filename': file_name,
                'filepath': output_path,
                'filesize': file_size,
                'file_index': file_index
            })
            
            # Remove chunks
            shutil.rmtree(chunk_dir)
            del transfer['chunks'][file_id]
    
    return jsonify({'success': True})

@app.route('/transfer/<transfer_id>')
def check_transfer(transfer_id):
    with transfer_lock:
        exists = transfer_id in transfers and not transfers[transfer_id]['downloaded']
    return jsonify({'exists': exists})

@app.route('/transfer/<transfer_id>/files')
def transfer_files(transfer_id):
    with transfer_lock:
        if transfer_id in transfers:
            transfer = transfers[transfer_id]
            return jsonify({
                'success': True,
                'files': [{
                    'filename': f['filename'],
                    'filesize': f['filesize']
                } for f in transfer['files']],
                'total_size': transfer['total_size']
            })
    return jsonify({'success': False, 'error': 'Transfer not found'}), 404

@app.route('/download_all/<transfer_id>')
def download_all(transfer_id):
    with transfer_lock:
        if transfer_id not in transfers:
            return "Transfer not found", 404
            
        transfer = transfers[transfer_id]
        
        if transfer['downloaded']:
            return "Files already downloaded", 410  # Gone
        
        # Create in-memory zip file
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in transfer['files']:
                # Only add files that actually exist
                if os.path.exists(file['filepath']):
                    zf.write(file['filepath'], arcname=file['filename'])
                else:
                    print(f"File not found: {file['filepath']}")
        
        # Prepare response
        memory_file.seek(0)
        response = make_response(memory_file.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename="transfer_{transfer_id}.zip"'
        
        # Mark as downloaded
        transfer['downloaded'] = True
        
        return response

def cleanup_transfer(transfer_id):
    """Clean up the transfer after 1 hour"""
    time.sleep(3600)  # Wait for 1 hour
    
    with transfer_lock:
        if transfer_id in transfers:
            # Delete all files
            transfer_dir = os.path.join(UPLOAD_FOLDER, transfer_id)
            if os.path.exists(transfer_dir):
                shutil.rmtree(transfer_dir)
            
            # Remove the transfer record
            del transfers[transfer_id]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
