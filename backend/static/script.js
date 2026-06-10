document.addEventListener('DOMContentLoaded', () => {
    const connectionStatus = document.getElementById('connection-status');
    const dot = connectionStatus.querySelector('.dot');
    const text = connectionStatus.querySelector('.text');
    
    const handIndicator = document.getElementById('hand-indicator');
    const handText = document.getElementById('hand-text');
    const videoFeed = document.getElementById('video-feed');
    
    const mainView = document.getElementById('main-view');
    const configView = document.getElementById('config-view');
    const btnConfigure = document.getElementById('btn-configure');
    const btnBack = document.getElementById('btn-back');
    const btnRecord = document.getElementById('btn-record');
    const btnTrain = document.getElementById('btn-train');
    const statusMsg = document.getElementById('config-status-msg');
    
    const recordingOverlay = document.getElementById('recording-overlay');
    const recordingProgress = document.getElementById('recording-progress');
    const systemModeBadge = document.getElementById('system-mode-badge');
    const predictionBox = document.getElementById('prediction-box');
    const predictedActionText = document.getElementById('predicted-action-text');

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/status`;
    const apiUrl = `${window.location.protocol}//${window.location.host}/api`;
    
    let ws;
    let systemState = "IDLE";
    
    // View navigation
    btnConfigure.addEventListener('click', () => {
        mainView.classList.add('hidden');
        configView.classList.remove('hidden');
    });

    btnBack.addEventListener('click', () => {
        configView.classList.add('hidden');
        mainView.classList.remove('hidden');
    });

    // Recording and Training
    btnRecord.addEventListener('click', async () => {
        const gestureName = document.getElementById('gesture-name').value;
        const actionName = document.getElementById('action-name').value;
        
        if (!gestureName.trim()) {
            statusMsg.textContent = "Please enter a gesture name.";
            statusMsg.style.color = "var(--danger)";
            return;
        }

        statusMsg.textContent = "Recording starting in 2 seconds. Hold your hand up!";
        statusMsg.style.color = "var(--text-main)";
        
        setTimeout(async () => {
            try {
                const response = await fetch(`${apiUrl}/record_start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gesture_name: gestureName, action_name: actionName })
                });
                const data = await response.json();
                statusMsg.textContent = "Recording...";
            } catch (err) {
                console.error(err);
            }
        }, 2000);
    });

    btnTrain.addEventListener('click', async () => {
        statusMsg.textContent = "Training model...";
        statusMsg.style.color = "var(--text-main)";
        try {
            const response = await fetch(`${apiUrl}/train`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.error) {
                statusMsg.textContent = "Error: " + data.error;
                statusMsg.style.color = "var(--danger)";
            } else {
                statusMsg.textContent = `Model trained successfully! (${data.samples} samples)`;
                statusMsg.style.color = "var(--primary)";
            }
        } catch (err) {
            console.error(err);
            statusMsg.textContent = "Training failed.";
            statusMsg.style.color = "var(--danger)";
        }
    });

    // WebSocket logic
    function connect() {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            dot.className = 'dot connected';
            text.textContent = 'WebSocket Connected';
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Update the image with the base64 frame from python
            if (data.image) {
                videoFeed.src = 'data:image/jpeg;base64,' + data.image;
            }
            
            // Handle hand detection UI
            if (data.hand_detected) {
                if (!handIndicator.classList.contains('active')) {
                    handIndicator.className = 'hand-state-overlay active';
                    handText.textContent = 'Hand Detected!';
                }
            } else {
                if (!handIndicator.classList.contains('inactive')) {
                    handIndicator.className = 'hand-state-overlay inactive';
                    handText.textContent = 'No hand detected';
                }
            }

            // Handle System State
            if (systemState !== data.state) {
                systemState = data.state;
                systemModeBadge.textContent = `Mode: ${systemState}`;
                
                if (systemState === 'RECORDING') {
                    recordingOverlay.classList.remove('hidden');
                } else {
                    recordingOverlay.classList.add('hidden');
                    if (statusMsg.textContent === "Recording...") {
                        statusMsg.textContent = "Recording complete!";
                        statusMsg.style.color = "var(--primary)";
                    }
                }

                if (systemState === 'LIVE') {
                    predictionBox.classList.remove('hidden');
                } else {
                    predictionBox.classList.add('hidden');
                }
            }

            // Update Recording Progress
            if (systemState === 'RECORDING' && data.target_frames > 0) {
                const percent = (data.frames_recorded / data.target_frames) * 100;
                recordingProgress.style.width = `${percent}%`;
            }

            // Handle Live Prediction
            if (systemState === 'LIVE' && data.predicted_gesture) {
                predictedActionText.textContent = data.predicted_gesture;
            } else if (systemState === 'LIVE') {
                predictedActionText.textContent = "None";
            }
        };
        
        ws.onclose = () => {
            dot.className = 'dot disconnected';
            text.textContent = 'WebSocket Disconnected. Reconnecting...';
            handIndicator.className = 'hand-state-overlay inactive';
            handText.textContent = 'Waiting for connection...';
            setTimeout(connect, 2000);
        };
        
        ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            ws.close();
        };
    }
    
    connect();
});
