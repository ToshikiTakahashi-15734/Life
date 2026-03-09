#!/usr/bin/env python3
"""メインエントリポイント: 収集 → HTML生成 → ブラウザ表示"""

import subprocess
import sys
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"


def main():
    print("Step 1: Collecting trends...")
    subprocess.run([sys.executable, str(SCRIPTS_DIR / "collector.py")], check=True)

    print("\nStep 2: Generating HTML...")
    subprocess.run([sys.executable, str(SCRIPTS_DIR / "generate_html.py")], check=True)

    index_path = BASE_DIR / "public" / "index.html"
    print(f"\nStep 3: Opening browser...")
    webbrowser.open(f"file://{index_path}")
    print(f"\nDone! Open: file://{index_path}")


if __name__ == "__main__":
    main()
