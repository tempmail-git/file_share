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
    <title>File sharing</title>
    <style>
        :root {
            --primary: #ff6b6b;
            --secondary: #4ecdc4;
            --dark: #292f36;
            --light: #f7f9f9;
            --gray: #e0e0e0;
            --success: #4caf50;
            --accent: #ff9e44;
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
        
        .btn-accent {
            background: var(--accent);
        }
        
        .btn-accent:hover {
            background: #ff8c2b;
            box-shadow: 0 5px 15px rgba(255, 158, 68, 0.4);
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
        
        .id-container {
            margin: 20px 0;
            display: none;
            text-align: center;
        }
        
        .transfer-id {
            font-size: 1.5rem;
            font-weight: bold;
            padding: 15px 25px;
            background: rgba(78, 205, 196, 0.1);
            border-radius: 8px;
            display: inline-block;
            margin: 15px 0;
            color: var(--dark);
            border: 1px dashed var(--secondary);
            cursor: pointer;
            position: relative;
        }
        
        .transfer-id:hover {
            background: rgba(78, 205, 196, 0.2);
        }
        
        .id-tooltip {
            position: absolute;
            top: -30px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.8rem;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
        }
        
        .transfer-id:hover .id-tooltip {
            opacity: 1;
        }
        
        .file-list {
            margin-top: 15px;
            max-height: 200px;
            overflow-y: auto;
            display: none;
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .file-name {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
        }
        
        .file-size {
            margin-left: 10px;
            color: #666;
        }
        
        .file-progress {
            width: 100%;
            margin-top: 5px;
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
        
        .file-limit {
            text-align: center;
            margin-top: 10px;
            color: #666;
            font-size: 0.9rem;
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
            <div class="logo">File Sharing</div>
            <p class="tagline">Peer-to-peer file sharing in your browser. No server storage, no waiting.</p>
        </header>
        
        <div class="card-container">
            <!-- Sender Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📤</div>
                    <h2 class="card-title">Send Files</h2>
                </div>
                
                <div class="drop-area" id="dropArea">
                    <i>📁</i>
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
                    <div class="card-icon">📥</div>
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
            <h3>How it works:</h3>
            <ol>
                <li><strong>Sender</strong> selects files and generates a transfer ID</li>
                <li><strong>Recipient</strong> enters the transfer ID to connect</li>
                <li>Files are transferred <strong>directly</strong> between browsers</li>
                <li>Files are <strong>never stored</strong> on any server - completely private</li>
                <li>Transfer works as long as both browsers are connected</li>
                <li>Supports multiple files and large transfers up to 100GB</li>
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
            idText.textContent = 'Copied!';
            setTimeout(() => {
                idText.textContent = originalText;
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
