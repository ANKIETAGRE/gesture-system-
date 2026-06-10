from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import cv2
import asyncio
import base64
import time
import os
import math

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import numpy as np

# We'll import these inside the train endpoint to avoid crash if installation is slow
# from sklearn.neighbors import KNeighborsClassifier
# import joblib

app = FastAPI(title="AntiGravity Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1
)
detector = vision.HandLandmarker.create_from_options(options)

# --- State Management ---
SYSTEM_STATE = "IDLE"  # IDLE, RECORDING, LIVE
X_data = []
y_data = []
gesture_to_action = {}

current_gesture = ""
current_action = ""
frames_recorded = 0
TARGET_FRAMES = 60 # 60 frames per gesture sample
cooldown_until = 0
RELOAD_MODEL_FLAG = False

def extract_features(hand_landmarks):
    features = []
    # Normalize by the distance between wrist (0) and middle finger mcp (9) for scale invariance
    wrist = hand_landmarks[0]
    mcp = hand_landmarks[9]
    scale = math.sqrt((mcp.x - wrist.x)**2 + (mcp.y - wrist.y)**2 + (mcp.z - wrist.z)**2)
    if scale == 0:
        scale = 1

    # Use pairwise distances between all 21 points for rotation & translation invariance
    for i in range(21):
        for j in range(i + 1, 21):
            lm1 = hand_landmarks[i]
            lm2 = hand_landmarks[j]
            dist = math.sqrt((lm1.x - lm2.x)**2 + (lm1.y - lm2.y)**2 + (lm1.z - lm2.z)**2)
            features.append(dist / scale)
            
    return features

def execute_action(action_name):
    print(f"Executing: {action_name}")
    import pyautogui
    
    if action_name == "Open Browser":
        os.system("start chrome")
    elif action_name == "Lock Screen":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    elif action_name == "Calculator":
        os.system("calc")
    elif action_name == "Close Application":
        pyautogui.hotkey('alt', 'f4')
    elif action_name == "Alt Tab":
        pyautogui.hotkey('alt', 'tab')
    elif action_name == "Task View":
        pyautogui.hotkey('win', 'tab')
    elif action_name == "Virtual Desktop Left":
        pyautogui.hotkey('ctrl', 'win', 'left')
    elif action_name == "Virtual Desktop Right":
        pyautogui.hotkey('ctrl', 'win', 'right')
    elif action_name == "Volume Up":
        pyautogui.press('volumeup')
    elif action_name == "Volume Down":
        pyautogui.press('volumedown')
    elif action_name == "Play/Pause":
        pyautogui.press('playpause')
    elif action_name == "Next Track":
        pyautogui.press('nexttrack')
    elif action_name == "Previous Track":
        pyautogui.press('prevtrack')
    elif action_name == "Open YouTube":
        os.system("start chrome https://www.youtube.com")

class RecordRequest(BaseModel):
    gesture_name: str
    action_name: str

@app.post("/api/record_start")
def record_start(req: RecordRequest):
    global SYSTEM_STATE, current_gesture, current_action, frames_recorded
    current_gesture = req.gesture_name
    current_action = req.action_name
    gesture_to_action[current_gesture] = current_action
    frames_recorded = 0
    SYSTEM_STATE = "RECORDING"
    return {"status": "recording started", "target_frames": TARGET_FRAMES}

@app.post("/api/train")
def train_model():
    global SYSTEM_STATE, RELOAD_MODEL_FLAG
    if len(X_data) < 3:
        return {"error": f"Not enough training data recorded. Expected at least 3, got {len(X_data)}"}
    
    from sklearn.neighbors import KNeighborsClassifier
    import joblib

    n_neighbors = min(3, len(X_data))
    knn = KNeighborsClassifier(n_neighbors=n_neighbors)
    knn.fit(X_data, y_data)
    
    # Save the model
    joblib.dump((knn, gesture_to_action), "gesture_model.pkl")
    RELOAD_MODEL_FLAG = True
    SYSTEM_STATE = "LIVE"
    return {"status": "trained", "samples": len(X_data)}

class StateRequest(BaseModel):
    state: str

@app.post("/api/set_state")
def set_state(req: StateRequest):
    global SYSTEM_STATE
    SYSTEM_STATE = req.state
    return {"status": SYSTEM_STATE}

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.websocket("/ws/status")
async def status_endpoint(websocket: WebSocket):
    global SYSTEM_STATE, frames_recorded, cooldown_until, RELOAD_MODEL_FLAG
    await websocket.accept()
    cap = cv2.VideoCapture(0)
    await asyncio.sleep(1)
    
    # Try to load existing model
    model = None
    try:
        import joblib
        if os.path.exists("gesture_model.pkl"):
            model, _ = joblib.load("gesture_model.pkl")
    except Exception as e:
        print("Could not load model:", e)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.1)
                continue
                
            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp_ms = int(time.time() * 1000)
            
            results = detector.detect_for_video(mp_image, timestamp_ms)
            hand_detected = len(results.hand_landmarks) > 0
            
            predicted_gesture = None

            if hand_detected:
                landmarks = results.hand_landmarks[0]
                # Draw hand manually
                for landmark in landmarks:
                    x = int(landmark.x * frame.shape[1])
                    y = int(landmark.y * frame.shape[0])
                    cv2.circle(frame, (x, y), 5, (74, 222, 128), -1)
                
                features = extract_features(landmarks)
                
                if SYSTEM_STATE == "RECORDING":
                    # Add to dataset
                    X_data.append(features)
                    y_data.append(current_gesture)
                    frames_recorded += 1
                    
                    if frames_recorded >= TARGET_FRAMES:
                        SYSTEM_STATE = "IDLE"
                
                elif SYSTEM_STATE == "LIVE" and model is not None:
                    # Predict
                    if time.time() > cooldown_until:
                        import numpy as np
                        try:
                            prediction = model.predict(np.array([features]))[0]
                            predicted_gesture = prediction
                            
                            # Execute action
                            action = gesture_to_action.get(predicted_gesture)
                            if action:
                                execute_action(action)
                                cooldown_until = time.time() + 3.0 # 3 second cooldown between actions
                        except Exception as e:
                            print(f"Prediction error: {e}")

            # Encode frame
            _, buffer = cv2.imencode('.jpg', frame)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            
            # Load model if it wasn't loaded but state changed to LIVE
            if SYSTEM_STATE == "LIVE" and (model is None or RELOAD_MODEL_FLAG):
                try:
                    import joblib
                    model, _ = joblib.load("gesture_model.pkl")
                    RELOAD_MODEL_FLAG = False
                except:
                    pass

            await websocket.send_json({
                "state": SYSTEM_STATE,
                "hand_detected": hand_detected,
                "image": frame_b64,
                "predicted_gesture": predicted_gesture,
                "frames_recorded": frames_recorded,
                "target_frames": TARGET_FRAMES
            })
            
            await asyncio.sleep(0.06)
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        cap.release()
