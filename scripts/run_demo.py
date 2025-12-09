"""
Script to run the Streamlit Demo.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    os.chdir(project_root)
    os.system("streamlit run streamlit_app/app.py --server.port 8501")
