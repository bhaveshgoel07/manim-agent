#!/usr/bin/env python3
"""
Basic import tests to verify the NeuroAnim setup.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        import utils
        print("✅ utils module imported successfully")

        from utils.hf_wrapper import HFInferenceWrapper, ModelConfig
        print("✅ HFInferenceWrapper and ModelConfig imported successfully")

        import mcp_servers
        print("✅ mcp_servers module imported successfully")

        from mcp_servers import renderer, creative
        print("✅ renderer and creative modules imported successfully")

        from orchestrator import NeuroAnimOrchestrator
        print("✅ NeuroAnimOrchestrator imported successfully")

        print("\n🎉 All imports successful! NeuroAnim is properly set up.")
        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


if __name__ == "__main__":
    test_imports()