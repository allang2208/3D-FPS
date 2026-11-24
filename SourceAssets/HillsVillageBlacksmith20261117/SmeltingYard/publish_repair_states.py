"""Save the ruin group, the cropped pre-repair soil and both active ground material bindings."""
from pathlib import Path
import hashlib
import sys
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
here=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'Tools/WorldGeneration/AbandonedVillage'))
from smith_yard_material import bind,ROOT
from smith_yard_states import build
from smith_yard_clearance import clear_yard
if not globals().get('use_saved_mask',False):
    task=u.AssetImportTask()
    task.automated=True
    task.replace_existing=True
    task.filename=str(here/'RuinedGround.png')
    task.destination_path=ROOT
    task.destination_name='T_SmithYardBefore'
    task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=next((o for o in task.get_objects() if isinstance(o,u.Texture2D)),None)
    if not tex: raise RuntimeError('Could not import ruined ground mask')
    tex.srgb=False
    tex.compression_no_alpha=False
    tex.compression_settings=u.TextureCompressionSettings.TC_MASKS
    tex.address_x=tex.address_y=u.TextureAddress.TA_CLAMP
    if not u.EditorAssetLibrary.save_loaded_asset(tex,False): raise RuntimeError(tex.get_path_name())

def ondisk(package,extension):
    return root/'Content'/(package.removeprefix('/Game/')+extension)
def digest(path):
    return hashlib.sha256(path.read_bytes()).digest()
for suffix in ('M_TemperateGround','PebbleShore/M_PebbleShoreGround'):
    package='/Game/WorldGeneration/TemperateHills/'+suffix
    disk=ondisk(package,'.uasset')
    before=digest(disk)
    mat=u.load_asset(package)
    changed=bind(mat)
    layers=[str(n.get_editor_property('desc')) for n in u.MaterialEditingLibrary.get_material_expressions(mat)
            if isinstance(n,u.MaterialExpressionCustom) and '// Smith yard before restoration' in n.get_editor_property('code')]
    if not {'VillageTerrainRoad','VillageRoadEdge20261115'}.issubset(layers):
        raise RuntimeError('Missing visible or RVT yard binding in '+package+': '+str(layers))
    if changed:
        u.MaterialEditingLibrary.recompile_material(mat)
        if digest(disk)!=before: raise RuntimeError('Ground material changed during authoring: '+package)
        if not u.EditorAssetLibrary.save_loaded_asset(mat,False): raise RuntimeError(package)
    u.log('SMITH_YARD_GROUND_BOUND '+package)
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
disk=ondisk(level,'.umap')
before=digest(disk)
world=u.load_asset(level)
if not world: raise RuntimeError('Cannot open '+level)
removed=clear_yard(world)
if build(world) or removed:
    if digest(disk)!=before: raise RuntimeError('Village changed during authoring: retry with current level')
    if not u.EditorLoadingAndSavingUtils.save_packages([world.get_outermost()],False): raise RuntimeError('Cannot save '+level)
u.log('SMITH_YARD_REPAIR_STATES_SAVED '+level)
