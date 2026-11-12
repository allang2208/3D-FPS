import ctypes
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import time

base = Path(__file__).resolve().parent
out = base / time.strftime("run-%H%M%S")
out.mkdir()
(base / "latest.txt").write_text(out.name)
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
kernel.CreateMutexW.restype = ctypes.c_void_p
for name in ("ReleaseMutex", "CloseHandle"):
    getattr(kernel, name).argtypes = [ctypes.c_void_p]
kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
mutex = kernel.CreateMutexW(None, 0, r"Local\CodexUeMcp-Port-8000")
if not mutex or kernel.WaitForSingleObject(mutex, 15 * 60 * 1000) not in (0, 128):
    raise RuntimeError("UE capture batch unavailable")
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
endpoint = f"127.0.0.1:{port}"
exe = "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
project = (base.parents[2] / "FPSGAME.uproject").as_posix()
tag = base.name.split("-")[-1] + out.name.split("-")[-1]
procs = []
timeline = []
seed = base.parents[1] / "M249BagIconWire/20261112-151132/run-151624"
seed_tag = "151132151624"
for role in ("host", "guest"):
    user_saves = out / (role + "-profile") / "Saved/SaveGames"
    user_saves.mkdir(parents=True)
    shutil.copyfile(seed / f"{role}.ids", out / f"{role}.ids")
    original = seed / (role + "-profile") / "Saved/SaveGames"
    for part in ("A", "B"):
        prefix = "ColdSteel_BagWireAudit_"
        for suffix in ("sav", "sha1"):
            shutil.copyfile(original / f"{prefix}{seed_tag}_{role}_{part}.{suffix}", user_saves / f"{prefix}{tag}_{role}_{part}.{suffix}")

def event(kind, **detail):
    record = dict(event=kind, time=time.strftime("%H:%M:%S"), **detail)
    timeline.append(record)
    (out / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf8")
    print(record, flush=True)

def start(role, join):
    user = out / (role + "-profile")
    user.mkdir(exist_ok=True)
    level = "/Engine/Maps/Entry?game=/Script/FPSGAME.FPSGAMEGameMode"
    if role == "host":
        level += "?listen"
    else:
        level = endpoint
    args = [exe, project, level, "-game", "-RenderOffscreen", "-windowed", "-ResX=1600", "-ResY=900", "-ForceRes",
            "-unattended", "-nosound", "-nosplash", "-nop4", "-NoLiveCoding", "-Multiprocess",
            "-AssetGatherAll=false", "-NoAssetRegistryCacheWrite", "-SkipStartupMenu", "-NoLoadingScreen",
            "-BagPreseed", "-EnablePlugins=BagCheck", "-PLUGIN=" + (base / "BagCheck/BagCheck.uplugin").as_posix(),
            "-UserDir=" + user.as_posix(), "-abslog=" + (out / f"{role}-{join}.log").as_posix(),
            f"-BagWireDir={out.as_posix()}", f"-BagWireRole={role}", f"-BagWireJoin={join}",
            f"-BagWireURL={endpoint}", f"-ColdSteelProfile=BagWireAudit_{tag}_{role}",
            "-ini:Engine:[/Script/EngineSettings.GameMapsSettings]:GameDefaultMap=/Engine/Maps/Entry",
            "-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False",
            "-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False",
            "-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180",
            "-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=180",
            "-DPCVars=t.MaxFPS=24,fps.body.AsyncPreload=0,Editor.AsyncSkinnedAssetCompilation=0,Editor.AsyncStaticMeshCompilation=0"]
    if role == "host":
        args.extend([f"-port={port}", "-multihome=127.0.0.1"])
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    procs.append((role, join, p))
    event("start", role=role, join=join, pid=p.pid, endpoint=endpoint)
    return p

def wait_for(names, active, timeout=540):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        for p in active:
            if p.poll() is not None:
                raise RuntimeError(f"peer {p.pid} exited {p.returncode} while waiting for {names}")
        for f in out.glob("*.error"):
            raise RuntimeError(f"{f.name}: {f.read_text()}")
        if all((out / name).is_file() and (out / name).stat().st_size for name in names):
            return
        time.sleep(1)
    raise TimeoutError(str(names))

def command(i):
    p = out / "next-phase.tmp"
    p.write_text(str(i))
    p.replace(out / "phase.txt")

def stop(role, join, p):
    (out / f"{role}-{join}.quit").write_text("normal exit")
    if p.wait(timeout=100) != 0:
        raise RuntimeError(f"exit from {role} {join}: {p.returncode}")
    event("exit", role=role, join=join, pid=p.pid)

try:
    command(0)
    host = start("host", 0)
    wait_for(["listen.ready"], [host], 300)
    for join, phases in enumerate(((0, 1), (2, 3), (4,))):
        command(phases[0])
        guest = start("guest", join)
        for phase in phases:
            command(phase)
            wait_for([f"host-{phase}.sample", f"guest-{phase}.sample", f"host-{phase}.shadow"], [host, guest])
            event("sampled", phase=phase, host=host.pid, guest=guest.pid)
        stop("guest", join, guest)
        if join < 2:
            wait_for([f"host-{phases[-1]}.offline"], [host], 210)
            event("confirmed_disconnect", old_guest=guest.pid)
    stop("host", 0, host)
    event("passed")
except Exception as e:
    event("failed", reason=str(e))
    raise
finally:
    for role, join, p in reversed(procs):
        if p.poll() is None:
            (out / f"{role}-{join}.quit").write_text("shutdown")
            try:
                p.wait(timeout=40)
            except subprocess.TimeoutExpired:
                p.terminate()
    kernel.ReleaseMutex(mutex)
    kernel.CloseHandle(mutex)
