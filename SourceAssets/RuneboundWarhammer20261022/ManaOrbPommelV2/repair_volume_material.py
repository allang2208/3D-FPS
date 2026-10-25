"""Repair only the loaded V2 nebula material through the existing UE editor."""
import ast,json,shutil,datetime
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/RuneboundWarhammer20261022/ManaOrbPommelV2'
TAG='RuneboundManaOrbOwner';OWNER='ManaOrbPommelV2_20261024'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project; preserve loaded assets')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
receipt={'complete':False,'assets':[],'repair':'Pixel-safe local position for the nebula raymarch','reported_error':"PreSkinnedPosition is not available in the EMaterialShaderFrequency::Pixel shader",'runtime_visual_tested':False,'timestamp':stamp}
target=ROOT/'Content/Weapons/RuneboundWarhammer20261022/ManaOrbPommelV2/M_RuneboundManaOrb_VolumeV2.uasset'
backup=P/'BeforePixelRepair'/stamp;backup.mkdir(parents=True,exist_ok=True)
shutil.copy2(target,backup/target.name)
helpers=ast.parse((P.parent/'RuneAndBellRefinement20261024/install_assets.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<material_helpers>','exec'))
_new_material=material
source=(P/'import_assets.py').read_text('utf-8')
author=ast.parse(source)
exec(compile(ast.Module(body=[n for n in author.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<pommel_material_helpers>','exec'))
def record():
    (P/'pixel_material_repair_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
record()
materials={}
start=source.index("m=material('M_RuneboundManaOrb_VolumeV2')")
end=source.index("\nm=material('M_RuneboundManaOrb_CoreV2')",start)
exec(compile(source[start:end],'<pixel_safe_nebula>','exec'))
receipt.update(complete=True,material=materials['M_ManaOrbV2_Volume'].get_path_name(),backup=str(backup/target.name),source_position='LocalPosition / Component / Exclude Material Shader Offsets')
record();print('MANA_ORB_PIXEL_MATERIAL_REPAIRED_AND_SAVED '+receipt['material'])
