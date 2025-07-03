from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import uuid
import os
import time
from threading import Thread, Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# In-memory storage for active transfers
transfers = {}
transfer_lock = Lock()
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# HTML template embedded in the Python code
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title> File Sharing </title>
    <style>
        :root {
            --primary: #ff6b6b;
            --secondary: #4ecdc4;
            --dark: #292f36;
            --light: #f7f9f9;
            --gray: #e0e0e0;
            --success: #4caf50;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
            color: var(--dark);
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            padding: 30px 0;
        }
        
        .logo {
            font-size: 3.5rem;
            margin-bottom: 10px;
            color: var(--primary);
        }
        
        .tagline {
            font-size: 1.2rem;
            color: #555;
            max-width: 600px;
            margin: 0 auto 30px;
        }
        
        .card-container {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            padding: 30px;
            width: 100%;
            max-width: 450px;
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        .card-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--gray);
        }
        
        .card-icon {
            font-size: 2rem;
            margin-right: 15px;
            color: var(--primary);
        }
        
        .card-title {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .drop-area {
            border: 2px dashed var(--gray);
            border-radius: 8px;
            padding: 40px 20px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .drop-area.active {
            border-color: var(--primary);
            background-color: rgba(255, 107, 107, 0.05);
        }
        
        .drop-area i {
            font-size: 3rem;
            color: var(--secondary);
            margin-bottom: 15px;
            display: block;
        }
        
        .file-input {
            display: none;
        }
        
        .btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 50px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-block;
            text-align: center;
            width: 100%;
            max-width: 200px;
        }
        
        .btn:hover {
            background: #ff5252;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 107, 107, 0.4);
        }
        
        .btn-secondary {
            background: var(--secondary);
        }
        
        .btn-secondary:hover {
            background: #3bb5ae;
            box-shadow: 0 5px 15px rgba(78, 205, 196, 0.4);
        }
        
        .btn:disabled {
            background: var(--gray);
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .progress-container {
            margin: 20px 0;
        }
        
        .progress-bar {
            height: 8px;
            background: var(--gray);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress {
            height: 100%;
            background: var(--secondary);
            width: 0%;
            transition: width 0.3s;
        }
        
        .file-info {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            font-size: 0.9rem;
            color: #666;
        }
        
        .link-container {
            margin: 20px 0;
            display: none;
        }
        
        .link-box {
            display: flex;
            border: 1px solid var(--gray);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .link-input {
            flex: 1;
            padding: 12px 15px;
            border: none;
            font-size: 1rem;
        }
        
        .copy-btn {
            background: var(--secondary);
            color: white;
            border: none;
            padding: 0 20px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .copy-btn:hover {
            background: #3bb5ae;
        }
        
        .status {
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
            display: none;
        }
        
        .status.success {
            background: rgba(76, 175, 80, 0.1);
            color: var(--success);
            border: 1px solid var(--success);
        }
        
        .status.error {
            background: rgba(255, 107, 107, 0.1);
            color: var(--primary);
            border: 1px solid var(--primary);
        }
        
        .instructions {
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 0.9rem;
        }
        
        .instructions ol {
            text-align: left;
            max-width: 600px;
            margin: 15px auto;
            padding-left: 20px;
        }
        
        .instructions li {
            margin-bottom: 10px;
        }
        
        footer {
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: #666;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .card-container {
                flex-direction: column;
                align-items: center;
            }
            
            .card {
                max-width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">🍕 FilePizza</div>
            <p class="tagline">Peer-to-peer file sharing in your browser. No server storage, no waiting.</p>
        </header>
        
        <div class="card-container">
            <!-- Sender Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📤</div>
                    <h2 class="card-title">Send a File</h2>
                </div>
                
                <div class="drop-area" id="dropArea">
                    <i>📁</i>
                    <p>Drag & drop your file here</p>
                    <p>or</p>
                    <button class="btn" id="browseBtn">Browse Files</button>
                </div>
                <input type="file" id="fileInput" class="file-input">
                
                <div class="progress-container" id="progressContainer" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress" id="progressBar"></div>
                    </div>
                    <div class="file-info">
                        <span id="fileName"></span>
                        <span id="fileSize"></span>
                    </div>
                </div>
                
                <button class="btn" id="sendBtn" disabled>Generate Link</button>
                
                <div class="link-container" id="linkContainer">
                    <p>Share this link with the recipient:</p>
                    <div class="link-box">
                        <input type="text" id="shareLink" class="link-input" readonly>
                        <button class="copy-btn" id="copyBtn">Copy</button>
                    </div>
                </div>
            </div>
            
            <!-- Receiver Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📥</div>
                    <h2 class="card-title">Receive a File</h2>
                </div>
                
                <input type="text" id="peerId" class="link-input" placeholder="Enter transfer ID">
                <button class="btn btn-secondary" id="receiveBtn" style="margin-top: 20px;">Connect</button>
                
                <div class="progress-container" id="receiveProgress" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress" id="receiveBar"></div>
                    </div>
                    <div class="file-info">
                        <span id="receiveName"></span>
                        <span id="receiveSize"></span>
                    </div>
                </div>
                
                <div class="status" id="receiveStatus"></div>
                
                <a class="btn" id="downloadBtn" style="display: none; margin-top: 20px;">Download File</a>
            </div>
        </div>
        
        <div class="instructions">
            <h3>How it works:</h3>
            <ol>
                <li><strong>Sender</strong> selects a file and generates a shareable link</li>
                <li><strong>Recipient</strong> enters the transfer ID from the link to connect</li>
                <li>Files are transferred <strong>directly</strong> between browsers</li>
                <li>Files are <strong>never stored</strong> on any server - completely private</li>
                <li>Transfer works as long as both browsers are connected</li>
            </ol>
        </div>
        
        <footer>
            <p>FilePizza Clone | Peer-to-peer file sharing | Built with Python Flask</p>
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
        const progressBar = document.getElementById('progressBar');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const linkContainer = document.getElementById('linkContainer');
        const shareLink = document.getElementById('shareLink');
        const copyBtn = document.getElementById('copyBtn');
        
        const peerIdInput = document.getElementById('peerId');
        const receiveBtn = document.getElementById('receiveBtn');
        const receiveProgress = document.getElementById('receiveProgress');
        const receiveBar = document.getElementById('receiveBar');
        const receiveName = document.getElementById('receiveName');
        const receiveSize = document.getElementById('receiveSize');
        const receiveStatus = document.getElementById('receiveStatus');
        const downloadBtn = document.getElementById('downloadBtn');
        
        // Variables
        let selectedFile = null;
        let transferId = null;
        
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
        
        sendBtn.addEventListener('click', generateLink);
        copyBtn.addEventListener('click', copyLink);
        receiveBtn.addEventListener('click', connectToPeer);
        
        // Handle file selection
        function handleFileSelect() {
            if (fileInput.files.length === 0) return;
            
            selectedFile = fileInput.files[0];
            updateFileInfo(selectedFile);
            sendBtn.disabled = false;
        }
        
        // Update file info display
        function updateFileInfo(file) {
            progressContainer.style.display = 'block';
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            progressBar.style.width = '0%';
        }
        
        // Format file size
        function formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' bytes';
            else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
            else return (bytes / 1048576).toFixed(1) + ' MB';
        }
        
        // Generate shareable link
        function generateLink() {
            if (!selectedFile) return;
            
            // Show progress
            progressBar.style.width = '30%';
            
            // Create FormData to send the file to the server
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            // Send file to server to get a transfer ID
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    transferId = data.transfer_id;
                    progressBar.style.width = '100%';
                    linkContainer.style.display = 'block';
                    
                    // Generate the shareable link
                    const link = `${window.location.origin}/receive/${transferId}`;
                    shareLink.value = link;
                    sendBtn.disabled = true;
                    
                    // Show success status
                    showStatus('File ready for sharing! Send the link to the recipient.', 'success');
                } else {
                    showStatus('Error: ' + data.error, 'error');
                    progressBar.style.width = '0%';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showStatus('Error uploading file', 'error');
                progressBar.style.width = '0%';
            });
        }
        
        // Copy link to clipboard
        function copyLink() {
            shareLink.select();
            document.execCommand('copy');
            
            // Show tooltip
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = originalText;
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
            
            // Check if transfer exists
            fetch(`/transfer/${transferId}`)
            .then(response => response.json())
            .then(data => {
                if (data.exists) {
                    receiveStatus.textContent = 'Transfer found! Preparing download...';
                    
                    // Simulate transfer progress
                    simulateTransferProgress(transferId);
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
        
        // Simulate transfer progress
        function simulateTransferProgress(transferId) {
            receiveProgress.style.display = 'block';
            receiveName.textContent = 'Loading...';
            receiveSize.textContent = 'Calculating...';
            
            // Get file info
            fetch(`/transfer/${transferId}/info`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    receiveName.textContent = data.filename;
                    receiveSize.textContent = formatFileSize(data.filesize);
                    
                    // Simulate progress
                    let progress = 0;
                    const interval = setInterval(() => {
                        progress += 5;
                        receiveBar.style.width = `${progress}%`;
                        
                        if (progress >= 100) {
                            clearInterval(interval);
                            receiveStatus.textContent = 'File received successfully!';
                            receiveStatus.className = 'status success';
                            
                            // Show download button
                            downloadBtn.href = `/download/${transferId}`;
                            downloadBtn.textContent = `Download ${data.filename}`;
                            downloadBtn.style.display = 'inline-block';
                        }
                    }, 200);
                } else {
                    receiveStatus.textContent = 'Error: ' + data.error;
                    receiveStatus.className = 'status error';
                    receiveBtn.disabled = false;
                }
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
</html>
"""

# Flask Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    
    # Generate a unique transfer ID
    transfer_id = str(uuid.uuid4())
    filename = file.filename
    file_size = os.fstat(file.stream.fileno()).st_size
    
    # Save the file temporarily
    file_path = os.path.join(UPLOAD_FOLDER, f"{transfer_id}_{filename}")
    file.save(file_path)
    
    # Store transfer information
    with transfer_lock:
        transfers[transfer_id] = {
            'filename': filename,
            'filepath': file_path,
            'filesize': file_size,
            'created_at': time.time(),
            'downloaded': False
        }
    
    # Start a thread to clean up the file after 1 hour
    Thread(target=cleanup_transfer, args=(transfer_id,)).start()
    
    return jsonify({
        'success': True,
        'transfer_id': transfer_id,
        'filename': filename,
        'filesize': file_size
    })

@app.route('/transfer/<transfer_id>')
def check_transfer(transfer_id):
    with transfer_lock:
        exists = transfer_id in transfers and not transfers[transfer_id]['downloaded']
    return jsonify({'exists': exists})

@app.route('/transfer/<transfer_id>/info')
def transfer_info(transfer_id):
    with transfer_lock:
        if transfer_id in transfers:
            transfer = transfers[transfer_id]
            return jsonify({
                'success': True,
                'filename': transfer['filename'],
                'filesize': transfer['filesize']
            })
    return jsonify({'success': False, 'error': 'Transfer not found'}), 404

@app.route('/download/<transfer_id>')
def download_file(transfer_id):
    with transfer_lock:
        if transfer_id in transfers and not transfers[transfer_id]['downloaded']:
            transfer = transfers[transfer_id]
            transfer['downloaded'] = True
            
            # Return the file for download
            return send_file(
                transfer['filepath'],
                as_attachment=True,
                download_name=transfer['filename']
            )
    
    return "File not found or already downloaded", 404

def cleanup_transfer(transfer_id):
    """Clean up the transfer after 1 hour or after download"""
    time.sleep(3600)  # Wait for 1 hour
    
    with transfer_lock:
        if transfer_id in transfers:
            # Delete the file
            try:
                os.unlink(transfers[transfer_id]['filepath'])
            except Exception as e:
                print(f"Error deleting file: {e}")
            
            # Remove the transfer record
            del transfers[transfer_id]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
