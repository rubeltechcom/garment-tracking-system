import traceback
import sys
import tkinter as tk
from garment_tracker import MainApp

def run_debug():
    try:
        # Simulate a logged in user
        admin_user = {
            "username": "admin",
            "name": "Administrator",
            "role": "admin"
        }
        print("Starting MainApp with simulated admin login...")
        app = MainApp(admin_user)
        # We don't want to run mainloop() in the background if it works, 
        # we just want to see if __init__ completes.
        print("MainApp initialized successfully.")
        app.destroy()
    except Exception:
        with open("crash_log.txt", "w") as f:
            traceback.print_exc(file=f)
        print("CRASH DETECTED! Check crash_log.txt")
        sys.exit(1)

if __name__ == "__main__":
    run_debug()
