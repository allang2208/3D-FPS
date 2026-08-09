"""Start ComfyUI on the 5080 with the venv python (avoids cmd/SSH encoding issues)."""
import glob
import os
import subprocess
import sys

# Locate ComfyUI root on D:\ (any parent dir, handles Chinese path safely)
candidates = []
for parent in glob.glob(r"D:\*"):
    root = os.path.join(parent, "ComfyUI")
    if os.path.exists(os.path.join(root, "main.py")):
        candidates.append(root)
if not candidates:
    print("ComfyUI not found on D:\\", file=sys.stderr)
    sys.exit(1)
root = candidates[0]
python = os.path.join(root, ".venv", "Scripts", "python.exe")
log = os.path.join("D:", "comfyui_3d.log")

with open(log, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(
        [python, "main.py", "--listen", "0.0.0.0", "--port", "8188", "--enable-cors-header", "*"],
        cwd=root,
        stdout=lf,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
print(f"started pid={proc.pid} root={root}")
