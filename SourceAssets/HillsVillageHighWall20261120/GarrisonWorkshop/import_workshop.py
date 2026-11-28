"""Save the completed workshop shell, furnishings and future workbench anchors in an authoring host."""
from pathlib import Path
import json
import os
import sys
import unreal as ue

src=Path(__file__).resolve().parent
root=src.parents[2]
os.environ["HIGH_VILLAGE_PROJECT"]=str(root)
sys.path.insert(0,str(root/"Tools/WorldGeneration/HighVillageDefense"))
import import_kit as kit

dest="/Game/WorldGeneration/TemperateHills/VillageMechanicalWorkshop"
hills="/Game/WorldGeneration/TemperateHills/"
chapel=hills+"OldChapel/Materials/M_Chapel"
smith=hills+"VillageBlacksmith/"
paths={"ChapelWall":hills+"HighVillageDefense/ChapelGatehouse/M_GatehouseChapelWall",
       "Footing":chapel+"Footing","Paving":chapel+"Flagstone","Coping":chapel+"YardCap",
       "Slate":chapel+"Slate","Plaster":chapel+"Limewash","Floorboard":chapel+"Timber",
       "Oak":smith+"ArtPassR2/Materials/M_VillageR2_Oak","Iron":smith+"SmeltingYard/Wear/M_SmithWornIron",
       "Rope":hills+"VillageStable/PropsR43/Materials/M_StableWeatheredRope",
       "Bronze":"/Game/Props/RomanColumn20260915/M_Bronze"}
materials={k:kit.require(v) for k,v in paths.items()}
kit.PACK=dest+"/Frontage"
kit.SOURCE=src/"Frontage"
for part in ("Materials","Textures"):
    kit.E.make_directory(kit.PACK+"/"+part)
parent=kit.require(chapel+"Artifact")
for role in ("SignOak","ForgedStrap","WheelBrass","HempCord"):
    materials[role]=kit.scan_material(role,parent)
front_only=os.environ.get("GARRISON_FRONT_ONLY")=="1"
kit.E.make_directory(dest)
receipt={"saved":{}}
run=Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
for role in (("SM_GarrisonWorkshop",) if front_only else ("SM_GarrisonWorkshop","SM_GarrisonAssemblyBay")):
    kit.create_role(role,materials,receipt,package_root=dest,source_dir=src,
                    receipt_file=run/"mesh-import.json",preserve_silhouette=True)
if not front_only:
    furniture=kit.require(dest+"/SM_GarrisonAssemblyBay")
    for name,xyz,yaw in (("UpgradeWorkbench",(-112,30,91),0),("UpgradeApproach",(-15,30,0),180)):
        socket=furniture.find_socket(name)
        if not socket:
            socket=ue.StaticMeshSocket(outer=furniture)
            socket.set_editor_property("socket_name",name)
            furniture.add_socket(socket)
        socket.set_editor_property("relative_location",ue.Vector(*xyz))
        socket.set_editor_property("relative_rotation",ue.Rotator(yaw=yaw))
    kit.save(furniture)
(run/"workshop-saved.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
