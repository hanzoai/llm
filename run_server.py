#!/usr/bin/env python3
# Simple script to run the LLM proxy server

import os
import sys
import subprocess

def main():
    # Activate the virtual environment if it exists
    venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")
    if os.path.exists(venv_path):
        activate_script = os.path.join(venv_path, "bin", "activate")
        if os.path.exists(activate_script):
            print(f"Activating virtual environment: {venv_path}")
            # Use the activated environment's Python to run the module
            python_path = os.path.join(venv_path, "bin", "python")
            cmd = [
                python_path, 
                "-m", 
                "llm.proxy.proxy_server", 
                "--host", 
                "0.0.0.0", 
                "--port", 
                "4000"
            ]
            
            if len(sys.argv) > 1 and sys.argv[1] == "--config":
                cmd.extend(["--config", sys.argv[2]])
                
            print(f"Running command: {' '.join(cmd)}")
            subprocess.run(cmd)
            return
    
    # If we get here, we couldn't activate the venv
    print("Error: Virtual environment not found. Please create one with: python3 -m venv .venv")
    sys.exit(1)

if __name__ == "__main__":
    main()
