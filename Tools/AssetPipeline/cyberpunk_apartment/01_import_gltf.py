"""Import the apartment glTF into the FPSGAME project (Unreal 5.8, headless).

Run:
  UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
      -unattended -nop4 -nosplash

Writes a JSON report next to itself so the result is inspectable without
parsing the engine log.
"""
import json
import os

import unreal

SRC = r"D:\CyberpunkApartment\export\CyberpunkApartment.gltf"
DEST = "/Game/Props/CyberpunkApartment20261020"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_import_report.json"

report = {"source": SRC, "dest": DEST, "steps": [], "assets": [], "errors": []}


def log(msg):
    report["steps"].append(msg)


try:
    # make sure the destination folder exists
    if not unreal.EditorAssetLibrary.does_directory_exist(DEST):
        unreal.EditorAssetLibrary.make_directory(DEST)
        log("created " + DEST)
    else:
        log("dir exists " + DEST)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", SRC)
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("destination_name", "SM_CyberpunkApartment")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    # leave `options` at its default: UE 5.8 routes glTF through Interchange and
    # an explicit None breaks the pipeline selection

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    log("import_asset_tasks returned")

    for path in task.get_editor_property("imported_object_paths"):
        report["assets"].append(str(path))
    log("imported %d object paths" % len(report["assets"]))

except Exception as exc:  # noqa: BLE001
    report["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2)

unreal.log("IMPORT_REPORT_WRITTEN " + REPORT)