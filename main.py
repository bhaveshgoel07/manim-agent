#!/usr/bin/env python3
"""
NeuroAnim - Modular STEM Animation Generator

Entry point for the NeuroAnim system. This script provides a command-line
interface for generating educational STEM animations.
"""

import asyncio
import sys

from orchestrator import main as orchestrator_main


def main():
    """Main entry point."""
    try:
        asyncio.run(orchestrator_main())
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
