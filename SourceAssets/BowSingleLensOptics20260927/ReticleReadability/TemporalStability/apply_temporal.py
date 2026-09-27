"""Save local reticle motion/history settings; preserve appearance and gameplay."""
from pathlib import Path
from datetime import datetime
import importlib.util
import json
import shutil
import unreal as u

P=Path(__file__).parent
L=u.MaterialEditingLibrary
E=u.EditorAssetLibrary
spec=importlib.util.spec_from_file_location('bow_reticle_author',P.parent/'materials.py')
author=importlib.util.module_from_spec(spec)
spec.loader.exec_module(author)
dest='/Game/Weapons/DarkBow20260925/SingleLensOptics20260927'
paths=[dest+'/M_BowOptic_Glass'+str(power)+'x' for power in (2,4)]
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('End PIE before saving bow lens materials')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
       if p.get_name() in paths]
if dirty:
    raise RuntimeError('Preserve unsaved target materials: '+str(dirty))

properties=('translucency_pass','output_translucent_velocity',
            'is_translucency_velocity_from_depth','opacity_mask_clip_value',
            'disable_depth_test','enable_responsive_aa')
targets=[]
for path in paths:
    mat=u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing bow lens: '+path)
    nodes=L.get_material_expressions(mat)
    shapes=[n for n in nodes if isinstance(n,u.MaterialExpressionCustom)
            and str(n.get_editor_property('description')).startswith('Fine etched reticle:')]
    if len(shapes)!=1:
        raise RuntimeError('Ambiguous bow reticle shader: '+path)
    version=E.get_metadata_tag(mat,'BowReticleTemporalVersion')
    if version!='coverage-velocity-v1' and any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in nodes):
        raise RuntimeError('Preserve an existing temporal response authored elsewhere: '+path)
    targets.append((path,mat,shapes[0],version))

backup=P/'Before'
backup.mkdir(exist_ok=True)
receipt={'saved':[],'saved_at':datetime.now().isoformat(),'runtime_tested':False,
         'appearance_changed':False,'global_render_settings_changed':False,
         'temporal_response':'reticle coverage * 0.75; strict rejection above 0.5',
         'before':{}}
for path,mat,shape,version in targets:
    source=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
    if not (backup/source.name).exists():
        shutil.copy2(source,backup/source.name)
    receipt['before'][path]={key:str(mat.get_editor_property(key)) for key in properties}
    if version!='coverage-velocity-v1':
        coverage=author.node(mat,u.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False)
        author.wire(shape,coverage,'')
        author.configure_temporal_response(mat,coverage)
    errors=L.recompile_material(mat)
    if errors:
        raise RuntimeError('Bow material compilation failed: '+str(errors))
    if not E.save_loaded_asset(mat,False):
        raise RuntimeError('Bow lens save failed: '+path)
    receipt['saved'].append({'asset':mat.get_path_name(),
                             'settings':{key:str(mat.get_editor_property(key)) for key in properties}})
    (P/'apply-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('BOW_RETICLE_TEMPORAL_SAVED',mat.get_path_name(),flush=True)
