#!/usr/bin/env python3
"""
Sandbox Setup Verification Script

This script verifies that your Blaxel sandbox environment is properly configured
for Manim rendering without installation timeouts.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_success(text):
    """Print success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print error message."""
    print(f"❌ {text}")


def print_warning(text):
    """Print warning message."""
    print(f"⚠ {text}")


def print_info(text):
    """Print info message."""
    print(f"ℹ {text}")


def check_env_file():
    """Check if .env file exists."""
    env_path = Path(".env")
    if not env_path.exists():
        print_error(".env file not found")
        print_info("Create a .env file with MANIM_SANDBOX_IMAGE and BLAXEL_API_KEY")
        return False
    print_success(".env file found")
    return True


def check_environment_variables():
    """Check required environment variables."""
    load_dotenv()

    all_good = True

    # Check MANIM_SANDBOX_IMAGE
    manim_image = os.getenv("MANIM_SANDBOX_IMAGE")
    if not manim_image:
        print_error("MANIM_SANDBOX_IMAGE not set in .env")
        print_info("Run ./deploy_sandbox.sh to deploy a custom sandbox")
        all_good = False
    elif manim_image == "blaxel/py-app:latest":
        print_warning("Using default sandbox image (will cause installation attempts)")
        print_info("Deploy custom sandbox with: ./deploy_sandbox.sh")
        all_good = False
    else:
        print_success(f"Custom sandbox image configured: {manim_image}")

    # Check MANIM_SANDBOX_NAME
    sandbox_name = os.getenv("MANIM_SANDBOX_NAME")
    if not sandbox_name:
        print_warning("MANIM_SANDBOX_NAME not set in .env")
        print_info("Using default: 'manim-sandbox'")
    else:
        print_success(f"Persistent sandbox name configured: {sandbox_name}")

    # Check BLAXEL_API_KEY
    api_key = os.getenv("BLAXEL_API_KEY")
    if not api_key:
        print_error("BLAXEL_API_KEY not set in .env")
        print_info("Get your API key from https://blaxel.ai")
        all_good = False
    elif api_key.startswith("bl_"):
        print_success(f"Blaxel API key configured: {api_key[:8]}...")
    else:
        print_warning(
            "BLAXEL_API_KEY doesn't look like a valid key (should start with 'bl_')"
        )
        all_good = False

    # Check BLAXEL_SANDBOX_URL (optional but recommended)
    sandbox_url = os.getenv("BLAXEL_SANDBOX_URL")
    if sandbox_url:
        print_success(f"Sandbox URL configured: {sandbox_url}")
    else:
        print_info("BLAXEL_SANDBOX_URL not set (will use default)")

    return all_good


def check_dependencies():
    """Check if required Python packages are installed."""
    required_packages = [
        "blaxel",
        "mcp",
        "httpx",
        "dotenv",
        "gradio",
    ]

    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} installed")
        except ImportError:
            print_error(f"{package} not installed")
            all_installed = False

    if not all_installed:
        print_info("Install dependencies with: pip install -r requirements.txt")
        print_info("Or with uv: uv sync")

    return all_installed


def check_sandbox_script():
    """Check if deployment script exists."""
    script_path = Path("deploy_sandbox.sh")
    if not script_path.exists():
        print_error("deploy_sandbox.sh not found")
        return False

    if not os.access(script_path, os.X_OK):
        print_warning("deploy_sandbox.sh is not executable")
        print_info("Run: chmod +x deploy_sandbox.sh")
        return False

    print_success("deploy_sandbox.sh found and executable")
    return True


def test_blaxel_import():
    """Test if Blaxel SDK can be imported and basic functionality works."""
    try:
        from blaxel.core.sandbox import SandboxInstance

        print_success("Blaxel SDK can be imported")
        return True
    except ImportError as e:
        print_error(f"Cannot import Blaxel SDK: {e}")
        print_info("Install with: pip install blaxel")
        return False


def main():
    """Run all verification checks."""
    print_header("Manim Sandbox Setup Verification")

    print_info("This script checks if your environment is configured correctly")
    print_info("for rendering with the custom Blaxel sandbox (no timeouts).")

    print_header("Step 1: Environment Files")
    env_file_ok = check_env_file()

    print_header("Step 2: Environment Variables")
    env_vars_ok = check_environment_variables()

    print_header("Step 3: Python Dependencies")
    deps_ok = check_dependencies()

    print_header("Step 4: Blaxel SDK")
    blaxel_ok = test_blaxel_import()

    print_header("Step 5: Deployment Script")
    script_ok = check_sandbox_script()

    # Final summary
    print_header("Summary")

    if env_file_ok and env_vars_ok and deps_ok and blaxel_ok and script_ok:
        print_success("All checks passed! Your setup is ready.")
        print_info("\nYou can now run:")
        print_info("  python3 app.py          # Gradio UI")
        print_info("  python3 main.py         # CLI mode")
        print_info("\nThe renderer will use your custom sandbox and skip installation.")
        return 0
    else:
        print_error("Some checks failed. Please fix the issues above.")
        print_info("\nQuick fix checklist:")
        if not env_file_ok:
            print_info("  1. Create .env file in project root")
        if not env_vars_ok:
            print_info("  2. Run ./deploy_sandbox.sh to create custom sandbox")
            print_info("  3. Add BLAXEL_API_KEY to .env")
        if not deps_ok:
            print_info("  4. Install dependencies: pip install -r requirements.txt")
        if not blaxel_ok:
            print_info("  5. Install Blaxel SDK: pip install blaxel")
        return 1


if __name__ == "__main__":
    sys.exit(main())
