"""Read current kitchen material/mesh and asset-save state without map writes."""
from pathlib import Path
import json,unreal as u
R=Path(__file__).resolve().parent;B='/Game/Props/CyberpunkApartmentKitchen20261024';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
row=dict(materials={},meshes=[],dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
for role in ['Enamel','Steel']:
    m=u.load_asset(B+'/Materials/M_KP_'+role)
    row['materials'][role]=dict(exists=bool(m),connections={} if not m else {p:bool(L.get_material_property_connection(m,getattr(u.MaterialProperty,'MP_'+p))) for p in ['BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AMBIENT_OCCLUSION']})
for key in ['BaseBody','BaseFront','OvenFront','Cooking','FridgeLowerDoor']:
    row['meshes'].append(dict(key=key,exists=E.does_asset_exist(B+'/Meshes/SM_KP_'+key)))
print('KITCHEN_ASSET_READBACK '+json.dumps(row),flush=True)
(R/'asset_readback.json').write_text(json.dumps(row,indent=2),encoding='utf8')
