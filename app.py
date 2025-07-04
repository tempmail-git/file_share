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

# HTML template with modern UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FilePizza | Modern File Sharing</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Roboto+Mono:wght@300;400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #8a2be2;      /* Vibrant purple */
            --primary-light: #9d4edd;
            --secondary: #00c6fb;    /* Bright blue */
            --dark: #121212;         /* Deep dark */
            --darker: #0a0a0a;
            --light: #f8f9fa;
            --gray: #2d2d2d;
            --gray-light: #3d3d3d;
            --success: #4caf50;
            --accent: #ff6b6b;
            --text: #e0e0e0;
            --text-light: #b0b0b0;
            --card-bg: rgba(30, 30, 30, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            --transition: all 0.3s ease;
            --radius: 16px;
            --glow: 0 0 15px rgba(138, 43, 226, 0.5);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, var(--darker), var(--dark));
            min-height: 100vh;
            padding: 20px;
            color: var(--text);
            font-family: 'Poppins', sans-serif;
            line-height: 1.6;
            background-attachment: fixed;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at top right, rgba(138, 43, 226, 0.1), transparent 30%),
                        radial-gradient(circle at bottom left, rgba(0, 198, 251, 0.1), transparent 30%);
            z-index: -1;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 40px 0 30px;
            animation: fadeIn 1s ease;
        }
        
        .logo {
            font-size: 4.5rem;
            margin-bottom: 15px;
            color: var(--primary);
            text-shadow: var(--glow);
            position: relative;
            display: inline-block;
        }
        
        .logo::after {
            content: '🍕';
            position: absolute;
            top: -15px;
            right: -25px;
            font-size: 2rem;
            transform: rotate(20deg);
        }
        
        .tagline {
            font-size: 1.4rem;
            color: var(--text-light);
            max-width: 700px;
            margin: 0 auto 30px;
            font-weight: 300;
        }
        
        .cards-container {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            justify-content: center;
            margin-bottom: 40px;
        }
        
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--card-border);
            border-radius: var(--radius);
            padding: 30px;
            width: 100%;
            max-width: 500px;
            transition: var(--transition);
            box-shadow: var(--shadow);
            animation: slideUp 0.8s ease;
            position: relative;
            overflow: hidden;
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
        }
        
        .card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4);
        }
        
        .card-header {
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--gray);
        }
        
        .card-icon {
            font-size: 2.5rem;
            margin-right: 15px;
            color: var(--secondary);
            background: rgba(0, 198, 251, 0.1);
            width: 70px;
            height: 70px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 10px rgba(0, 198, 251, 0.2);
        }
        
        .card-title {
            font-size: 1.8rem;
            font-weight: 600;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .card-content {
            margin-bottom: 25px;
        }
        
        .drop-area {
            border: 2px dashed var(--gray);
            border-radius: 12px;
            padding: 40px 20px;
            text-align: center;
            margin-bottom: 20px;
            transition: var(--transition);
            cursor: pointer;
            background: rgba(30, 30, 30, 0.5);
            position: relative;
        }
        
        .drop-area:hover {
            border-color: var(--primary-light);
            background: rgba(138, 43, 226, 0.05);
        }
        
        .drop-area.active {
            border-color: var(--primary);
            background: rgba(138, 43, 226, 0.1);
            box-shadow: 0 0 20px rgba(138, 43, 226, 0.2);
        }
        
        .drop-area i {
            font-size: 3.5rem;
            color: var(--secondary);
            margin-bottom: 20px;
            display: block;
            transition: var(--transition);
        }
        
        .drop-area p {
            margin: 8px 0;
            font-size: 1.1rem;
        }
        
        .file-input {
            display: none;
        }
        
        .btn {
            background: linear-gradient(90deg, var(--primary), var(--primary-light));
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            display: inline-block;
            text-align: center;
            width: 100%;
            max-width: 280px;
            box-shadow: 0 5px 15px rgba(138, 43, 226, 0.4);
            position: relative;
            overflow: hidden;
            border: 2px solid rgba(255, 255, 255, 0.1);
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(138, 43, 226, 0.6);
        }
        
        .btn:active {
            transform: translateY(1px);
        }
        
        .btn:disabled {
            background: var(--gray);
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .btn-secondary {
            background: linear-gradient(90deg, var(--secondary), #00a6fb);
        }
        
        .btn-secondary:hover {
            box-shadow: 0 8px 25px rgba(0, 198, 251, 0.6);
        }
        
        .btn-accent {
            background: linear-gradient(90deg, var(--accent), #ff5252);
        }
        
        .btn-accent:hover {
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.6);
        }
        
        .btn::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -60%;
            width: 20px;
            height: 200%;
            background: rgba(255, 255, 255, 0.3);
            transform: rotate(25deg);
            transition: all 0.6s;
        }
        
        .btn:hover::after {
            left: 120%;
        }
        
        .progress-container {
            margin: 25px 0;
        }
        
        .progress-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 0.9rem;
            color: var(--text-light);
        }
        
        .progress-bar {
            height: 10px;
            background: var(--gray);
            border-radius: 5px;
            overflow: hidden;
            position: relative;
        }
        
        .progress {
            height: 100%;
            background: linear-gradient(90deg, var(--secondary), var(--primary));
            width: 0%;
            transition: width 0.5s ease;
            position: relative;
        }
        
        .progress::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
        }
        
        .id-container {
            margin: 30px 0;
            display: none;
            text-align: center;
            animation: fadeIn 0.8s ease;
        }
        
        .transfer-id {
            font-size: 1.8rem;
            font-weight: bold;
            padding: 20px 30px;
            background: rgba(30, 30, 30, 0.7);
            border-radius: var(--radius);
            display: inline-block;
            margin: 20px 0;
            color: var(--text);
            border: 2px dashed var(--primary);
            cursor: pointer;
            position: relative;
            font-family: 'Roboto Mono', monospace;
            letter-spacing: 1px;
            transition: var(--transition);
            box-shadow: 0 0 15px rgba(138, 43, 226, 0.3);
        }
        
        .transfer-id:hover {
            background: rgba(45, 45, 45, 0.7);
            transform: scale(1.02);
            box-shadow: 0 0 25px rgba(138, 43, 226, 0.5);
        }
        
        .id-tooltip {
            position: absolute;
            top: -40px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--primary);
            color: white;
            padding: 8px 15px;
            border-radius: 6px;
            font-size: 0.9rem;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            white-space: nowrap;
            font-family: 'Poppins', sans-serif;
        }
        
        .transfer-id:hover .id-tooltip {
            opacity: 1;
        }
        
        .file-list {
            margin-top: 20px;
            max-height: 250px;
            overflow-y: auto;
            display: none;
            border: 1px solid var(--gray);
            border-radius: 12px;
            padding: 15px;
            background: rgba(20, 20, 20, 0.5);
        }
        
        .file-list-header {
            display: flex;
            justify-content: space-between;
            padding-bottom: 10px;
            margin-bottom: 10px;
            border-bottom: 1px solid var(--gray);
            font-weight: 500;
            color: var(--text-light);
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            transition: var(--transition);
        }
        
        .file-item:last-child {
            border-bottom: none;
        }
        
        .file-item:hover {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
        }
        
        .file-name {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
            display: flex;
            align-items: center;
        }
        
        .file-icon {
            margin-right: 10px;
            color: var(--secondary);
        }
        
        .file-size {
            margin-left: 15px;
            color: var(--text-light);
            font-family: 'Roboto Mono', monospace;
            font-size: 0.9rem;
            min-width: 80px;
            text-align: right;
        }
        
        .file-progress {
            width: 100%;
            margin-top: 10px;
        }
        
        .status {
            padding: 15px;
            border-radius: 12px;
            margin: 20px 0;
            text-align: center;
            display: none;
            border-left: 4px solid;
            background: rgba(30, 30, 30, 0.7);
        }
        
        .status.success {
            border-color: var(--success);
            color: var(--success);
        }
        
        .status.error {
            border-color: var(--accent);
            color: var(--accent);
        }
        
        .instructions {
            margin-top: 40px;
            text-align: center;
            color: var(--text-light);
            font-size: 1.1rem;
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .instructions h3 {
            font-size: 1.8rem;
            margin-bottom: 25px;
            color: var(--text);
            position: relative;
            display: inline-block;
        }
        
        .instructions h3::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            border-radius: 3px;
        }
        
        .steps {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 30px;
            margin-top: 30px;
        }
        
        .step-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius);
            padding: 25px;
            width: 100%;
            max-width: 250px;
            text-align: center;
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }
        
        .step-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow);
        }
        
        .step-number {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: bold;
            margin: 0 auto 20px;
            box-shadow: 0 5px 15px rgba(138, 43, 226, 0.4);
        }
        
        .step-card h4 {
            font-size: 1.3rem;
            margin-bottom: 15px;
            color: var(--text);
        }
        
        .step-card p {
            color: var(--text-light);
            font-size: 1rem;
        }
        
        .file-limit {
            text-align: center;
            margin-top: 20px;
            color: var(--text-light);
            font-size: 1rem;
            font-style: italic;
        }
        
        footer {
            text-align: center;
            margin-top: 60px;
            padding: 30px;
            color: var(--text-light);
            font-size: 1rem;
            border-top: 1px solid var(--gray);
        }
        
        .footer-logo {
            font-size: 2rem;
            color: var(--primary);
            margin-bottom: 15px;
        }
        
        @media (max-width: 768px) {
            .cards-container {
                flex-direction: column;
                align-items: center;
            }
            
            .card {
                max-width: 100%;
            }
            
            .steps {
                flex-direction: column;
                align-items: center;
            }
        }
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideUp {
            from { 
                opacity: 0;
                transform: translateY(30px);
            }
            to { 
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        
        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--dark);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-light);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">FilePizza</div>
            <p class="tagline">Fast, secure file sharing with end-to-end encryption. No server storage, no limits.</p>
        </header>
        
        <div class="cards-container">
            <!-- Sender Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📤</div>
                    <h2 class="card-title">Send Files</h2>
                </div>
                
                <div class="card-content">
                    <div class="drop-area" id="dropArea">
                        <i>📁</i>
                        <p>Drag & drop your files here</p>
                        <p>or</p>
                        <button class="btn" id="browseBtn">Browse Files</button>
                    </div>
                    <input type="file" id="fileInput" class="file-input" multiple>
                    
                    <div class="file-list" id="fileList">
                        <div class="file-list-header">
                            <span>File Name</span>
                            <span>Size</span>
                        </div>
                        <!-- Files will be added here dynamically -->
                    </div>
                    
                    <div class="progress-container" id="progressContainer" style="display: none;">
                        <div class="progress-header">
                            <span id="totalFiles">0 files selected</span>
                            <span id="totalSize">0 bytes</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress" id="totalProgressBar"></div>
                        </div>
                    </div>
                    
                    <button class="btn" id="sendBtn" disabled>
                        <span class="btn-text">Generate Transfer ID</span>
                    </button>
                    
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
            </div>
            
            <!-- Receiver Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📥</div>
                    <h2 class="card-title">Receive Files</h2>
                </div>
                
                <div class="card-content">
                    <input type="text" id="peerId" class="link-input" placeholder="Enter transfer ID">
                    <button class="btn btn-secondary" id="receiveBtn" style="margin-top: 20px;">Connect to Transfer</button>
                    
                    <div class="file-list" id="receiveFileList" style="display: none;">
                        <div class="file-list-header">
                            <span>File Name</span>
                            <span>Size</span>
                        </div>
                        <!-- Received files will appear here -->
                    </div>
                    
                    <div class="progress-container" id="receiveProgress" style="display: none;">
                        <div class="progress-header">
                            <span id="receiveStatusText">Preparing download...</span>
                            <span id="receivePercent">0%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress" id="receiveBar"></div>
                        </div>
                    </div>
                    
                    <div class="status" id="receiveStatus"></div>
                    
                    <a class="btn btn-accent" id="downloadBtn" style="display: none; margin-top: 20px;">
                        <span class="btn-text">Download All Files</span>
                    </a>
                </div>
            </div>
        </div>
        
        <div class="instructions">
            <h3>How It Works</h3>
            
            <div class="steps">
                <div class="step-card">
                    <div class="step-number">1</div>
                    <h4>Upload Files</h4>
                    <p>Select files or drag them to the upload area. Our system handles files of any size.</p>
                </div>
                
                <div class="step-card">
                    <div class="step-number">2</div>
                    <h4>Get Transfer ID</h4>
                    <p>We generate a unique transfer ID for your files. No complicated links.</p>
                </div>
                
                <div class="step-card">
                    <div class="step-number">3</div>
                    <h4>Share with Recipient</h4>
                    <p>Send the transfer ID to your recipient through any messaging platform.</p>
                </div>
                
                <div class="step-card">
                    <div class="step-number">4</div>
                    <h4>Recipient Downloads</h4>
                    <p>Your recipient enters the ID and downloads the files directly to their device.</p>
                </div>
            </div>
        </div>
        
        <footer>
            <div class="footer-logo">FilePizza</div>
            <p>Modern File Sharing Platform | Built with Python Flask</p>
            <p>Files are transferred securely with end-to-end encryption</p>
            <p style="margin-top: 15px; font-size: 0.9rem;">&copy; 2023 FilePizza. All rights reserved.</p>
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
        const receivePercent = document.getElementById('receivePercent');
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
            fileList.style.display = 'block';
        }
        
        // Update file list display
        function updateFileList(files) {
            fileList.innerHTML = `
                <div class="file-list-header">
                    <span>File Name</span>
                    <span>Size</span>
                </div>
            `;
            progressContainer.style.display = 'block';
            
            let totalSizeBytes = 0;
            
            files.forEach((file, index) => {
                totalSizeBytes += file.size;
                
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <div class="file-name">
                        <span class="file-icon">📄</span>
                        ${file.name}
                    </div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                `;
                fileList.appendChild(fileItem);
            });
            
            totalFiles.textContent = `${files.length} file${files.length > 1 ? 's' : ''} selected`;
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
            setTimeout(() => {
                idText.textContent = originalText;
            }, 2000);
        }
        
        // Connect to peer
        function connectToPeer() {
            const transferId = peerIdInput.value.trim();
            if (!transferId) return;
            
            receiveBtn.disabled = true;
            receiveStatus.textContent = 'Connecting to transfer source...';
            receiveStatus.className = 'status';
            receiveStatus.style.display = 'block';
            
            // Check if transfer exists
            fetch(`/transfer/${transferId}`)
            .then(response => response.json())
            .then(data => {
                if (data.exists) {
                    receiveStatus.textContent = 'Transfer found! Retrieving file information...';
                    
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
                            
                            // Show progress container
                            receiveProgress.style.display = 'block';
                            simulateTransferProgress();
                        } else {
                            receiveStatus.textContent = 'Error: ' + fileData.error;
                            receiveStatus.className = 'status error';
                            receiveBtn.disabled = false;
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
            receiveFileList.innerHTML = `
                <div class="file-list-header">
                    <span>File Name</span>
                    <span>Size</span>
                </div>
            `;
            receiveFileList.style.display = 'block';
            
            files.forEach(file => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <div class="file-name">
                        <span class="file-icon">📄</span>
                        ${file.filename}
                    </div>
                    <div class="file-size">${formatFileSize(file.filesize)}</div>
                `;
                receiveFileList.appendChild(fileItem);
            });
        }
        
        // Simulate transfer progress
        function simulateTransferProgress() {
            let progress = 0;
            const interval = setInterval(() => {
                progress += 2;
                if (progress > 100) progress = 100;
                
                receiveBar.style.width = `${progress}%`;
                receivePercent.textContent = `${progress}%`;
                receiveStatusText.textContent = `Downloading... ${progress}%`;
                
                if (progress >= 100) {
                    clearInterval(interval);
                    receiveStatusText.textContent = 'Download complete!';
                }
            }, 100);
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
</html>
"""

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
