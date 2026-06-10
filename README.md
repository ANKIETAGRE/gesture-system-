# AntiGravity OS

AntiGravity is an AI-powered touchless desktop operating system that uses Machine Learning and Computer Vision to let you control your computer with custom hand gestures.

## Features

- **Custom Gesture Training:** Use your webcam to record entirely custom hand gestures (e.g. a peace sign, a closed fist, pointing).
- **Rotation-Invariant ML Engine:** The system uses 210 pairwise 3D Euclidean distance features computed from MediaPipe landmarks. This means your gestures are recognized regardless of whether your hand is tilted or rotated.
- **System Integration:** Map your custom gestures to native OS commands seamlessly:
  - Open Browser
  - Open Calculator
  - Lock Screen
  - Close Applications (Alt+F4)
  - Task View (Win+Tab) & Alt+Tab Navigation
  - Virtual Desktop Switching
  - Media Controls (Volume Up/Down, Play/Pause, Next/Prev Track)
  - Open YouTube
- **Local & Private:** Your webcam feed and trained ML models (`gesture_model.pkl`) never leave your computer. 

## Project Structure

- `/backend`: The Python FastAPI server handling the MediaPipe vision engine, the KNN machine learning training logic, and `pyautogui` OS automations.
- `/backend/static`: The vanilla HTML/JS/CSS frontend dashboard that connects to the backend via WebSockets to give you a real-time live feed and training interface.

## Tech Stack

- **Computer Vision:** Google MediaPipe (Python)
- **Machine Learning:** Scikit-Learn (K-Nearest Neighbors)
- **Backend:** FastAPI, Uvicorn, WebSockets
- **OS Automation:** PyAutoGUI
- **Frontend:** HTML5, CSS3, Vanilla JavaScript

## Running Locally

1. Navigate to the `backend` directory.
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn opencv-python mediapipe pyautogui pydantic websockets scikit-learn joblib
   ```
3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```
4. Open your browser and navigate to `http://127.0.0.1:8000/`.

## Usage

1. Open the web interface.
2. Click **Configure Gestures**.
3. Type a name and select the desired OS action.
4. Click **Hold Hand & Record**. Hold your hand steadily in front of the camera for a few seconds.
5. Once recording is complete, click **Train Model**.
6. Switch back to the dashboard, perform your gesture, and watch the OS action trigger!
