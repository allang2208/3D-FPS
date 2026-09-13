"""Fetch the BSD-licensed Blast 5.0.6 core/stress sources at a pinned revision and build Win64.

No samples, tools, PhysX runtime, or tests are downloaded or executed.
"""
import concurrent.futures
import hashlib
import json
import pathlib
import subprocess
import urllib.request

REVISION = "4f2103c3a9052906296defb12166753450ef787c"
PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Source/ThirdParty/Blast"
SDK = ROOT / "SDK"


def fetch(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FPSGAME-Build"}), timeout=60) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise


def main():
    manifest = ROOT / "upstream.json"
    if not manifest.exists():
        directory = json.loads(fetch(f"https://api.github.com/repos/NVIDIA-Omniverse/PhysX/contents/blast?ref={REVISION}"))
        paths = ["LICENSE.md", "blast/VERSION.md"]
        for folder in ("include", "source", "PACKAGE-LICENSES"):
            sha = next(item["sha"] for item in directory if item["name"] == folder)
            tree = json.loads(fetch(f"https://api.github.com/repos/NVIDIA-Omniverse/PhysX/git/trees/{sha}?recursive=1"))
            for item in tree["tree"]:
                if item["type"] != "blob":
                    continue
                path = item["path"]
                wanted = folder == "PACKAGE-LICENSES"
                wanted |= folder == "include" and path.startswith(("lowlevel/", "globals/", "shared/", "extensions/stress/"))
                wanted |= folder == "source" and path.startswith(("sdk/lowlevel/", "sdk/globals/", "sdk/common/", "sdk/extensions/stress/", "shared/NsFoundation/", "shared/stress_solver/"))
                if wanted:
                    paths.append(f"blast/{folder}/{path}")

        def download(path):
            local = SDK / (path[6:] if path.startswith("blast/") else path)
            data = fetch(f"https://raw.githubusercontent.com/NVIDIA-Omniverse/PhysX/{REVISION}/{path}")
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(data)
            return {"path": path, "sha256": hashlib.sha256(data).hexdigest()}

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            files = list(pool.map(download, paths))
        manifest.write_text(json.dumps({"repository": "https://github.com/NVIDIA-Omniverse/PhysX", "revision": REVISION, "version": "5.0.6", "files": files}, indent=2), encoding="utf-8")
        print(f"Downloaded {len(files)} upstream files", flush=True)

    vswhere = pathlib.Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")
    install = subprocess.check_output([str(vswhere), "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"], text=True).strip()
    vcvars = pathlib.Path(install) / "VC/Auxiliary/Build/vcvars64.bat"
    out = PROJECT / "Intermediate/BlastWin64"
    out.mkdir(parents=True, exist_ok=True)
    library = ROOT / "Lib/Win64"
    library.mkdir(parents=True, exist_ok=True)
    include = ["include/lowlevel", "include/globals", "include/shared/NvFoundation", "include/extensions/stress", "source/sdk/common", "source/sdk/lowlevel", "source/sdk/globals", "source/shared/NsFoundation/include", "source/shared/stress_solver"]
    # Use Blast's six degree-of-freedom stress kernel through our own material
    # adapter. The public extension has family-wide material thresholds.
    sources = [SDK / "source/shared/stress_solver/stress.cpp", ROOT / "Adapter/FPSBlast.cpp"]
    args = ["/nologo", "/c", "/O2", "/MD", "/EHsc", "/std:c++17", "/DNDEBUG", "/DNVBLAST_STATIC", "/DNV_STATIC_LIB", "/D_CRT_SECURE_NO_WARNINGS", "/MP4"]
    args += [f'/I"{SDK / entry}"' for entry in include]
    args += [f'/I"{ROOT / "Adapter"}"']
    args += [f'"{source}"' for source in sources]
    (out / "compile.rsp").write_text("\n".join(args), encoding="utf-8")
    batch = out / "build.cmd"
    batch.write_text(f'@echo off\ncall "{vcvars}" >nul\nif errorlevel 1 exit /b 1\ncl @compile.rsp\nif errorlevel 1 exit /b 1\nlib /nologo /OUT:"{library / "FPSBlast.lib"}" stress.obj FPSBlast.obj\n', encoding="utf-8")
    subprocess.run(["cmd", "/d", "/c", str(batch)], cwd=out, check=True)


if __name__ == "__main__":
    main()
