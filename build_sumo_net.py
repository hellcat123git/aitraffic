"""
build_sumo_net.py — One-time network builder for the AI-Traffic SUMO scenario.

Run this script once before launching any simulation. It calls netconvert
to generate intersection.net.xml from the node and edge XML source files.

Usage (from project root):
    python build_sumo_net.py
"""

import subprocess
import sys
import os


SUMO_DIR = os.path.join(os.path.dirname(__file__), "sumo")
NET_FILE = os.path.join(SUMO_DIR, "intersection.net.xml")
NOD_FILE = os.path.join(SUMO_DIR, "intersection.nod.xml")
EDG_FILE = os.path.join(SUMO_DIR, "intersection.edg.xml")


def check_netconvert():
    """Verify netconvert is on PATH or in SUMO_HOME/bin."""
    sumo_home = os.environ.get("SUMO_HOME", "")
    candidates = ["netconvert"]
    if sumo_home:
        candidates.insert(0, os.path.join(sumo_home, "bin", "netconvert"))
        candidates.insert(0, os.path.join(sumo_home, "bin", "netconvert.exe"))

    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    return None


def build_network():
    print("=" * 60)
    print("  AI-Traffic — SUMO Network Builder")
    print("=" * 60)

    netconvert = check_netconvert()
    if not netconvert:
        print("\n❌ ERROR: 'netconvert' not found.")
        print("   Please install SUMO and set SUMO_HOME, or run:")
        print("   pip install eclipse-sumo")
        sys.exit(1)

    print(f"✅ netconvert found: {netconvert}")

    # Create output directory for simulation results
    os.makedirs(os.path.join(SUMO_DIR, "..", "sumo", "output"), exist_ok=True)

    cmd = [
        netconvert,
        "--node-files", NOD_FILE,
        "--edge-files", EDG_FILE,
        "--output-file", NET_FILE,
        "--no-turnarounds",
        "--tls.default-type", "static",
        "--junctions.join",
        "--verbose",
    ]

    print(f"\n🔧 Running netconvert...")
    print(f"   {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0 and os.path.isfile(NET_FILE):
        size_kb = os.path.getsize(NET_FILE) / 1024
        print(f"\n✅ Network built successfully: {NET_FILE} ({size_kb:.1f} KB)")
        print("\n📋 Next steps:")
        print("   1. Run AI-driven mode:  python main_app.py --mode sumo")
        print("   2. Run baseline mode:   python main_app.py --mode sumo --baseline")
        print("   3. Full stack:          python run_smart_city.py --mode sumo")
    else:
        print(f"\n❌ netconvert failed (exit code {result.returncode}).")
        print("   Check the output above for XML validation errors.")
        sys.exit(1)


if __name__ == "__main__":
    build_network()
