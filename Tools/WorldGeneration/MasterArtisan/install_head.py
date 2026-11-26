"""Publish the selected head surfaces first, then update the mesh used by the resident."""
import json
import os
import sys
from pathlib import Path
from runpy import run_path

try:
    import unreal as ue
except ImportError:
    ue=None

ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/"SourceAssets/HillsVillageHighWall20261120/MasterArtisan"
sys.path.insert(0,str(ROOT/"Tools/WorldGeneration/VillageWindmill"))
from publish_mill_yard import digest, replace

def install(batch,revision):
    if revision not in ("R2","R3","R4","WorkwearR5","WorkwearR6"):raise ValueError("Unknown master artisan appearance revision")
    if (batch/"superseded.txt").exists():raise RuntimeError("Superseded head revision")
    outfit=revision.startswith("Workwear")
    part="Workwear" if outfit else "Head"
    folder=revision if outfit else "Head"+revision
    subject="/Game/Characters/VillageMasterArtisan/SK_MasterArtisan_"+part
    prefix="/Game/Characters/VillageMasterArtisan/"+folder+"/"
    report=json.loads((SRC/folder/"saved.json").read_text())
    production=ROOT/"Content"
    stage=batch/"Host/Content"
    head=Path(subject[6:]+".uasset")
    before=digest(batch/"Before"/head.name)
    if not before:raise RuntimeError("Missing previous "+part+" recovery package")
    current=digest(production/head)
    staged=digest(stage/head)
    previous=batch/"published.json"
    key=part.lower()
    if previous.exists() and current==json.loads(previous.read_text(encoding="utf-8-sig")).get(key+"_sha256"):
        return
    if current not in (before,staged):raise RuntimeError("Concurrent edit to the workshop head")
    held=None
    if ue:
        if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve()!=ROOT.resolve():
            raise RuntimeError("Unexpected editor project")
        if any(pkg.get_path_name()==subject for pkg in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError("Master artisan head has unsaved edits")
        held=ue.find_object(None,subject)
    additions=[]
    for pkg in report["packages"]:
        if pkg==subject:continue
        if not pkg.startswith(prefix):raise RuntimeError("Unexpected output "+pkg)
        rel=Path(pkg[6:]+".uasset")
        current_hash=digest(production/rel)
        new_hash=digest(stage/rel)
        if not new_hash:raise RuntimeError("Missing staged package "+pkg)
        if current_hash==new_hash:continue
        if current_hash or (ue and ue.find_object(None,pkg)):raise RuntimeError("Independent surface at "+pkg)
        additions.append(rel)
    for rel in additions:
        replace(stage/rel,production/rel,None)
    if ue:
        registry=ue.AssetRegistryHelpers.get_asset_registry()
        registry.scan_paths_synchronous([prefix.rstrip("/")],True)
        if held and ue.EditorLevelLibrary.get_pie_worlds(False):
            (batch/"waiting-for-PIE.txt").write_text(revision+" surfaces installed. The current play session has the old "+key+" loaded.")
            print("ARTISAN_WAITING_FOR_PIE")
            return
    if current!=staged:
        if held:
            # Replace the geometry through the existing clean editor object, leaving its users attached.
            run_path(str(Path(__file__).with_name("save_assets.py")),init_globals={"head_revision":revision,"use_published_surfaces":True})
        else:
            replace(stage/head,production/head,before)
            if ue:registry.scan_modified_asset_files([str(production/head)])
    report.update(version="MasterArtisan "+folder,in_editor=bool(ue),runtime_tested=False)
    report.update({key:subject,"previous_"+key+"_sha256":before,key+"_sha256":digest(production/head),"updated_loaded_"+key:bool(held)})
    previous.write_text(json.dumps(report,indent=2),encoding="utf8")
    (batch/"waiting-for-PIE.txt").unlink(missing_ok=True)
    print("ARTISAN_PUBLISHED",revision,len(report["packages"]))

if __name__=="__main__":
    install(Path(os.environ["MASTER_ARTISAN_BATCH"]),os.environ["MASTER_ARTISAN_HEAD_REVISION"])
