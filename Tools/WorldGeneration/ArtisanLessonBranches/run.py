"""Build and execute the isolated native test without changing the primary project binaries."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

base = Path(__file__).resolve().parent
project = base.parents[2]
engine = Path("E:/Program Files (x86)/UE_5.8/Engine")
tools = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64")
intermediate = project / "Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME"
parser = argparse.ArgumentParser()
parser.add_argument("round")
args = parser.parse_args()
run = project / "Saved/ArtisanLessonBranches" / args.round
if not args.round.isalnum():
    raise ValueError("round must be alphanumeric")
run.mkdir(parents=True, exist_ok=False)
host = run / "Host"
bin_dir = host / "Binaries/Win64"
bin_dir.mkdir(parents=True)
shutil.copy2(project / "FPSGAME.uproject", host)
shutil.copy2(project / "Binaries/Win64/UnrealEditor.modules", bin_dir)
shutil.copytree(project / "Config", host / "Config")
for name in ["Content", "Plugins", "Shaders"]:
    subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(host / name), str(project / name)], check=True)
def write_rsp(name, lines):
    dst = run / name
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dst
def sha(file):
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
objects = {}
manifest = {}
# Freeze current source for the focused lessons and the two workstation implementations.
names = ["WoodworkingAuditCommandlet", "BlacksmithApprenticeship", "CarpenterApprenticeship",
         "ApprenticeMaterials", "ForgingSystem", "WoodworkingSystem", "WoodworkingJob", "ColdSteelProfileRuntime"]
for name in names:
    orig = (intermediate / (name + ".cpp.obj.rsp")).read_text(encoding="utf-8-sig").splitlines()
    src = base / "LessonFixture.cpp" if name == names[0] else Path(orig[0].strip('"'))
    obj = run / (name + ".obj")
    lines = ['"' + src.as_posix() + '"'] + [s for s in orig[1:] if not s.startswith(("/Fo", "/experimental:log", "/sourceDependencies"))]
    lines.append('/Fo"' + obj.as_posix() + '"')
    rsp = write_rsp(name + ".rsp", lines)
    subprocess.run([tools / "cl.exe", "@" + str(rsp)], cwd=engine / "Source", check=True)
    objects[name] = obj
    manifest[str(src)] = sha(src)
lines = []
for line in (intermediate / "UnrealEditor-FPSGAME.dll.rsp").read_text(encoding="utf-8-sig").splitlines():
    if line.startswith(("/DEBUG", "/PDB", "/NATVIS")):
        continue
    if line.startswith("/OUT:"):
        line = '/OUT:"' + (bin_dir / "UnrealEditor-FPSGAME.dll").as_posix() + '"'
    for name, obj in objects.items():
        if line.endswith("/" + name + '.cpp.obj"'):
            line = '"' + obj.as_posix() + '"'
            break
    lines.append(line)
link = write_rsp("link.rsp", lines)
subprocess.run([tools / "link.exe", "@" + str(link)], cwd=engine / "Source", check=True)
manifest["frozen_test_dll_sha256"] = sha(bin_dir / "UnrealEditor-FPSGAME.dll")
(run / "inputs.json").write_text(json.dumps(manifest, indent=2))
command = [engine / "Binaries/Win64/UnrealEditor-Cmd.exe", host / "FPSGAME.uproject", "-run=WoodworkingAudit",
           "-LessonBranchAudit", "-ColdSteelProfile=LessonBranchAudit", "-nullrhi", "-nosound",
           "-unattended", "-nosplash", "-nop4", "-Multiprocess", "-NoAssetRegistryCacheWrite",
           "-AssetGatherAll=false", "-NoShaderCompile", "-abslog=" + str(run / "engine.log"),
           "-Report=" + str(run / "report.txt"), "-UserDir=" + str(run / "User"),
           "-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False",
           "-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False"]
result = subprocess.run([str(v) for v in command], creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL)
(run / "exit-code.txt").write_text(str(result.returncode))
if (run / "report.txt").is_file():
    print((run / "report.txt").read_text(encoding="utf-8-sig"))
raise SystemExit(result.returncode)
