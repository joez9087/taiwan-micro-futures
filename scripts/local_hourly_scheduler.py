import os
import sys
import time
from datetime import datetime

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.cloud_hourly_alert import dispatch_hourly_alert

def run_local_scheduler(interval_minutes=60):
    print("=" * 70)
    print("   微台指每小時自動推播守護進程 (Taiwan Futures Hourly Alert Daemon)")
    print("=" * 70)
    print(f"[*] 守護進程已啟動，每 {interval_minutes} 分鐘將自動發送最新行情與信號至您的 iPhone Bark...")
    
    # Run once immediately on start
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 執行首次即時推播...")
    try:
        dispatch_hourly_alert()
    except Exception as e:
        print(f"Error: {e}")
        
    while True:
        time.sleep(interval_minutes * 60)
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 執行定時推播...")
        try:
            dispatch_hourly_alert()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    run_local_scheduler(interval_minutes=interval)
