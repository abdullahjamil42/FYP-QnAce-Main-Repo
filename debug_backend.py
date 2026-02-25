
import sys
import os
from pathlib import Path

# Add current dir to path
sys.path.insert(0, str(Path(os.getcwd()) / "integrated_system"))

print("Testing imports...")
try:
    import torch
    print(f"Torch version: {torch.__version__}")
    
    import numpy
    print(f"Numpy version: {numpy.__version__}")
    
    from integrated_system.coaching_engine import initialize_coaching_engine
    print("Coaching engine imported")
    
    from integrated_system.api.main import app
    print("FastAPI app imported")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
