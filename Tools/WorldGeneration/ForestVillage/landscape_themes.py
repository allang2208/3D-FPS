"""Editor entry point for one saved hill or road landscape composition."""
import json
import os
from pathlib import Path
import unreal as u

catalog=json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8-sig'))
def preset(name):
    for theme in catalog['themes']:
        if name in (theme['name'],theme['id'],*theme['aliases']):return theme
    raise ValueError('Choose 丘陵景观 or 道路景观')

def source_root():
    project=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
    configured=os.environ.get('FPS_FOREST_THEMES_SOURCE')
    if configured:return Path(configured)
    local=project/catalog['source']
    return local if local.is_dir() else Path(__file__).resolve().parents[3]/catalog['source']

def point_input(theme,source):
    folder=Path(source) if source is not None else source_root()/theme['id']
    if (folder/'theme.id').read_text(encoding='ascii').strip()!=theme['id']:
        raise ValueError('Wrong point set for '+theme['name'])
    files=['planting.bin','reference-meshes.txt']
    if theme['id']=='HillsLandscape':files+=['harvest-trees.f32','study-granite.i32']
    for f in files:
        if not (folder/f).is_file():raise FileNotFoundError(folder/f)
    return str(folder/'planting.bin')

def _bake(requests):
    # Resolve sources before touching the shared map; a two-theme build saves it only once.
    inputs=[(theme,point_input(theme,source)) for theme,source in requests]
    save=u.EditorLoadingAndSavingUtils;world=save.load_map(catalog['map'])
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):
        raise RuntimeError('Cannot select persistent forest village map')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    region=next(a for a in actors if isinstance(a,u.ForestVillageRegion) and a.get_path_name().startswith(catalog['map']+'.'))
    templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name()
               for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    for theme,file in inputs:
        if not templates or not region.bake_vegetation(file,templates,theme['id']):
            raise RuntimeError('Could not rebuild '+theme['name'])
    if not save.save_map(world,catalog['map']):raise RuntimeError('Cannot save landscape theme changes')

def build(name,source=None):
    """Rebuild only the selected PCG component in the authoring host."""
    theme=preset(name)
    _bake([(theme,source)])
    return theme['graph']

def build_all():
    """Explicitly compose both saved point sets, including any independent theme edits."""
    _bake([(theme,None) for theme in catalog['themes']])

if __name__=='__main__':print(build(os.environ['FPS_LANDSCAPE_THEME']))
