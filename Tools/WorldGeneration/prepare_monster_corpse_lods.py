"""Prepare CPU-readable distant geometry for the live dungeon monster rigs."""
import json
import shutil
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
task=root/'SourceAssets/HillsEcologyUpgrade20261114'
lib=u.EditorAssetLibrary
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
paths=['/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy','/Game/Monsters/HangingBellM09/V04/SK_M09','/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw']
def prepare():
    m10=u.get_default_object(lib.load_blueprint_class('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler'))
    active_paths=list(paths)
    active_paths.append(m10.get_editor_property('visual_mesh').get_path_name().split('.')[0])
    saved=[]
    for path in active_paths:
        mesh=u.load_asset(path)
        if not mesh:raise RuntimeError(path)
        for ext in ['.uasset','.uexp','.ubulk']:
            relative=path.removeprefix('/Game/')+ext
            before=task/'Before/Content'/relative
            current=root/'Content'/relative
            if current.exists() and not before.exists():
                before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(current,before)
        dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if path in dirty:raise RuntimeError('Unsaved edits in '+path)
        count=editor.get_lod_count(mesh)
        index=u.MonsterCorpseMeshComponent.prepare_frozen_proxy_lod(mesh)
        if index<0:raise RuntimeError('Unable to prepare frozen LOD '+path)
        if index>=count:
            if not editor.regenerate_lod(mesh,index+1,False,False):raise RuntimeError('Unable to build frozen LOD '+path)
        if not lib.save_loaded_asset(mesh,False):raise RuntimeError('Unable to save '+path)
        saved.append({'mesh':path,'lod':index,'vertices':editor.get_num_verts(mesh,index)})
        (task/'corpse-lods-saved.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
    (task/'corpse-lods-complete.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
    u.log('MONSTER_FROZEN_LODS_SAVED')

if not (task/'corpse-lods-complete.json').exists():prepare()
