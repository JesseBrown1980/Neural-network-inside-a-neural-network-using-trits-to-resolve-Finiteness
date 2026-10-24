import subprocess
import sys
import os

def run():
    print("=== Step 1: Compiling asolaria_ternary_fluid_v1.cpp ===")
    cmd_compile = ["g++", "-O3", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-static", "asolaria_ternary_fluid_v1.cpp", "-o", "asolaria_ternary_fluid_v1.exe"]
    res = subprocess.run(cmd_compile)
    if res.returncode != 0:
        print("Compilation failed!")
        sys.exit(1)
    print("Compilation successful.\n")

    print("=== Step 2: Running Simulation & Micro-reversibility Check ===")
    cmd_run = [os.path.join(".", "asolaria_ternary_fluid_v1.exe"), "reproduced_results.csv"]
    res = subprocess.run(cmd_run)
    if res.returncode != 0:
        print("Simulation execution failed!")
        sys.exit(1)
    print("\nSimulation completed.\n")

    print("=== Step 3: Verifying Exact CSV Reproduction ===")
    with open("reproduced_results.csv", "rb") as f1, open("asolaria_ternary_fluid_v1_results.csv", "rb") as f2:
        b1 = f1.read().replace(b"\r\n", b"\n").strip()
        b2 = f2.read().replace(b"\r\n", b"\n").strip()
        if b1 == b2:
            print("[PASS] Byte-for-byte exact match with reference results CSV!")
        else:
            print("[FAIL] Output mismatch with reference CSV!")
            sys.exit(1)

if __name__ == "__main__":
    run()
