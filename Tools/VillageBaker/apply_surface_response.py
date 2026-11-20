"""Update an existing baker's bound UE materials and reimport his two native skin masks."""
import json
import os
from pathlib import Path
import sys

import unreal as u

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from surface_response import SPECULAR, connect

GAME = "/Game/Characters/VillageBaker"
PNG = TOOLS.parents[1] / "SourceAssets/VillageBaker/WardrobeR1/Textures"
receipt = []
editor = u.EditorAssetLibrary


def save(asset):
    if not asset or not editor.save_loaded_asset(asset, False):
        raise RuntimeError("Cannot save " + str(asset))
    receipt.append(asset.get_path_name().split(".")[0])


for name in ("T_Baker_Skin_ORM", "T_Baker_NativeNeck_ORM"):
    task = u.AssetImportTask()
    task.filename = str(PNG / (name + ".png"))
    task.destination_path = GAME + "/Textures"
    task.destination_name = name
    task.automated = task.replace_existing = True
    task.replace_existing_settings = task.save = False
    task.factory = u.TextureFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    result = task.get_objects()
    if len(result) != 1 or not isinstance(result[0], u.Texture2D):
        raise RuntimeError("Failed to reimport " + name)
    result[0].set_editor_property("compression_settings", u.TextureCompressionSettings.TC_MASKS)
    result[0].set_editor_property("srgb", False)
    save(result[0])

for name in SPECULAR:
    mat = editor.load_asset(GAME + "/Materials/" + name)
    slab = u.MaterialEditingLibrary.get_material_property_input_node(mat, u.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(slab, u.MaterialExpressionSubstrateShadingModels):
        raise RuntimeError("Unexpected surface graph on " + name)
    connect(mat, slab)
    u.MaterialEditingLibrary.recompile_material(mat)
    save(mat)

if os.environ.get("BAKER_RESPONSE_RECEIPT"):
    Path(os.environ["BAKER_RESPONSE_RECEIPT"]).write_text(json.dumps(receipt, indent=2))
print("Saved baker response packages", len(receipt), flush=True)
