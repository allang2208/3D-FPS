"""Write new display/pickup packages and a UI texture in the shoulder revision."""
import gc
import importlib.util
import json
from pathlib import Path

import unreal as ue

P=Path("D:/FPS3D/FPSGAME")
R=P/"SourceAssets/ModernTacticalSet20261113/ShoulderFit20261118"
DEST="/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/ShoulderFit20261118/Display"


def load_module(name,file):
    spec=importlib.util.spec_from_file_location(name,P/file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


io=load_module("shoulder_static","Tools/ChainmailPants/save_assets.py")
io.DEST=DEST
buffers=load_module("shoulder_buffers","Tools/FieldHat/save_icon.py")
art=json.loads((R/"artwork.json").read_bytes())
result={}
for kind,file in (("pickup",art["pickup"]),("display",art["icon"]["display"])):
    data=json.loads(Path(file).read_bytes())
    materials=[ue.load_asset(path) for path in data["materials"]]
    if not all(materials):
        raise RuntimeError("Missing vest PBR material")
    mesh=buffers.dynamic(data)
    result[kind]=io.static(mesh,DEST+"/SM_TS01_vest_"+kind,materials)
    del mesh,data
    gc.collect()
    ue.SystemLibrary.collect_garbage()
task=ue.AssetImportTask()
task.filename=art["icon"]["png"]
task.destination_path=DEST
task.destination_name="T_TS01_vest_Icon"
task.automated=True
task.save=False
ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=ue.load_asset(DEST+"/T_TS01_vest_Icon")
for k,v in dict(srgb=True,compression_settings=ue.TextureCompressionSettings.TC_EDITOR_ICON,
                lod_group=ue.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=ue.TextureMipGenSettings.TMGS_NO_MIPMAPS).items():
    texture.set_editor_property(k,v)
if not ue.EditorAssetLibrary.save_loaded_asset(texture,False):
    raise RuntimeError("Unable to save vest icon")
result["texture"]=texture.get_path_name()
(R/"inventory-saved.json").write_text(json.dumps(result,indent=2))
