"""Open the herbalist's actual conversation in an isolated NullRHI hills game."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time


root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--engine", type=Path, default=Path("E:/Program Files (x86)/UE_5.8"))
parser.add_argument("--module", type=Path, default=root / "Binaries/Win64/UnrealEditor-FPSGAME.dll")
parser.add_argument("--output-root", type=Path, default=root / "Saved/HerbalistConversation")
args = parser.parse_args()

run = args.output_root.resolve() / time.strftime("%Y%m%d-%H%M%S")
project = run / "HerbalistConversationHost"
binary = project / "Binaries/Win64"
binary.mkdir(parents=True, exist_ok=False)
shutil.copy2(root / "FPSGAME.uproject", project)
shutil.copytree(root / "Config", project / "Config")
shutil.copy2(args.module, binary / "UnrealEditor-FPSGAME.dll")
shutil.copy2(root / "Binaries/Win64/UnrealEditor.modules", binary)
for folder in ("Content", "Plugins", "Shaders"):
    subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(project / folder), str(root / folder)],
                   check=True, stdout=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)

log = run / "game.log"
result = run / "result.json"
cmd = [str(args.engine / "Engine/Binaries/Win64/UnrealEditor-Cmd.exe"), str(project / "FPSGAME.uproject"),
       "/Game/GameMaps/L_TemperateHills_Initial", "-game", "-nullrhi", "-RenderOffscreen", "-nosound",
       "-unattended", "-nosplash", "-Multiprocess", "-NoAssetRegistryCacheWrite", "-AssetGatherAll=false",
       "-SkipStartupMenu", "-ClearwaterNoMenu", "-HillsNewWorld", "-HillsSeed=1518277816",
       "-ColdSteelProfile=HerbalistConversation", "-UserDir=" + str(run / "User"), "-abslog=" + str(log),
       "-LocalDataCachePath=D:/FPS3D/DerivedDataCache", "-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen",
       "-HerbalistDialogueResult=" + str(result), "-ExecCmds=t.MaxFPS 30,fps.Test.HerbalistConversation",
       "-ini:Game:[TemperateHills.NightRaid]:Enabled=False",
       "-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False",
       "-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False"]
print("Herbalist conversation run", run, flush=True)
process = subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW, timeout=1100)
if not result.exists():
    raise SystemExit(f"No conversation result, game exit {process.returncode}. See {log}")
summary = json.loads(result.read_text(encoding="utf-8-sig"))
print(json.dumps(summary, ensure_ascii=False, indent=2))
if process.returncode or not summary["passed"]:
    raise SystemExit(1)
