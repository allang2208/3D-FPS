"""Publish the three checked collar-transition packages under the project editor batch mutex."""
import json,sys
from pathlib import Path
from pattern import ROOT
sys.path.insert(0,str(ROOT/"Tools/WorldGeneration/VillageWindmill"))
from publish_mill_yard import replace, digest

def main(batch):
    saved=json.loads((batch/"skin-saved.json").read_text())
    allowed={"/Game/Characters/VillageMasterArtisan/WorkwearR6/Textures/T_ArtisanCollarSeam",
             "/Game/Characters/VillageMasterArtisan/HeadR4/Materials/M_ArtisanNeck",
             "/Game/Characters/VillageMasterArtisan/HeadR4/Materials/M_ArtisanHead"}
    if set(saved)!=allowed:raise RuntimeError("Unexpected collar material package set")
    operations=[]
    for pkg in saved:
        rel=Path(pkg.removeprefix("/Game/")+".uasset")
        source=batch/"Host/Content"/rel;dest=ROOT/"Content"/rel
        before=digest(batch/"Before"/rel.name);now=digest(dest);new=digest(source)
        if not new or now not in (before,new):raise RuntimeError("Concurrent change "+pkg)
        operations.append((source,dest,before,new,pkg))
    for source,dest,before,new,pkg in operations:
        if digest(dest)!=new:replace(source,dest,before)
    receipt=batch/"published.json"
    report=json.loads(receipt.read_text())
    report["collar_skin_packages"]={pkg:new for _,_,_,new,pkg in operations}
    receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")

if __name__=="__main__":main(Path(sys.argv[1]))
