import requests
import time
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
# Replace with your specific Channel ID and Read API Key (Not the Write key!)
CHANNEL_ID = "2594968"
READ_API_KEY = "8FFZZKPLYHLOMMB8"
POLL_INTERVAL = 20  # Seconds (match or exceed Arduino upload rate)

# API Endpoint
THINGSPEAK_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"

# --- AI / ANALYTICS MODEL ---
class HeartRateAnalyzer:
    def __init__(self, window_size=10):
        self.history = []
        self.window_size = window_size

    def detect_anomaly(self, current_bpm):
        """
        Uses a statistical Z-score approach to detect anomalies.
        If the current heart rate is significantly different from the 
        recent average, it flags an alert.
        """
        if current_bpm is None or current_bpm == 0:
            return "NO_DATA"

        # Basic Thresholding (Rule-based AI)
        if current_bpm > 100:
            return "CRITICAL: Tachycardia Detected (High HR)"
        if current_bpm < 50:
            return "WARNING: Bradycardia Detected (Low HR)"

        # Statistical Anomaly Detection (Pattern-based AI)
        # We need enough history to calculate a meaningful average
        if len(self.history) < 5:
            self.history.append(current_bpm)
            return "CALIBRATING: Gathering baseline data..."

        # Calculate Mean and Standard Deviation of recent history
        avg_bpm = np.mean(self.history)
        std_bpm = np.std(self.history)

        # Update history (Keep rolling window)
        self.history.append(current_bpm)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        # Calculate Z-Score
        # (Current - Average) / Deviation
        # If Z-score > 2, it's 2 standard deviations away from normal (Anomaly)
        if std_bpm > 0: # Avoid division by zero
            z_score = (current_bpm - avg_bpm) / std_bpm
            if abs(z_score) > 2.0:
                return f"ANOMALY: Irregular spike detected! (Z-Score: {z_score:.2f})"
        
        return "NORMAL: Heart rate is stable."

# --- MAIN LOOP ---
def start_monitoring():
    print(f"--- Starting AI Heart Rate Monitor Backend ---")
    print(f"Listening to ThingSpeak Channel: {CHANNEL_ID}")
    
    analyzer = HeartRateAnalyzer()
    last_entry_id = None

    while True:
        try:
            # 1. Fetch latest data (get last 1 result)
            params = {'api_key': READ_API_KEY, 'results': 1}
            response = requests.get(THINGSPEAK_URL, params=params)
            data = response.json()

            if 'feeds' in data and len(data['feeds']) > 0:
                latest_feed = data['feeds'][0]
                entry_id = latest_feed['entry_id']
                timestamp = latest_feed['created_at']
                
                # Check field1 (assuming BPM is sent to field1)
                bpm_str = latest_feed.get('field1')

                # Only process if this is a new data point
                if entry_id != last_entry_id and bpm_str:
                    try:
                        bpm = float(bpm_str)
                        
                        # 2. Run AI Analysis
                        status = analyzer.detect_anomaly(bpm)
                        
                        # 3. Output Result
                        timestamp_clean = timestamp.replace('T', ' ').replace('Z', '')
                        print(f"[{timestamp_clean}] BPM: {bpm} | Status: {status}")
                        
                        last_entry_id = entry_id
                        
                    except ValueError:
                        print("Error: Invalid data format received.")
                else:
                    # No new data yet
                    pass 

            else:
                print("Waiting for data stream...")

        except Exception as e:
            print(f"Network Error: {e}")

        # Wait before next poll to respect API limits
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    start_monitoring()