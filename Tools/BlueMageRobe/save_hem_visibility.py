"""Install covered-region masks on the currently published robe inner layers."""
import json, gc, sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/OwnerLayerRepair20261020'
R.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
import hem_materials
E=u.EditorAssetLibrary
record_path=R/'saved_assets.json'
receipt=json.loads(record_path.read_text()) if record_path.exists() else dict(meshes={},runtime_tested=False)
def record():record_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End play before saving robe coverage materials')
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
mapping=cfg['items']['ue_blue_mage_robe']['underlayer_meshes']
receipt['completed']=False;receipt['mapping']=mapping;record()
for path in sorted(set(mapping.values())):
    if not path:continue
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Current inner layer missing '+path)
    slots=list(mesh.get_editor_property('materials'))
    selected=[i for i,slot in enumerate(slots) if str(slot.material_slot_name).startswith('RobeStairHidden_')]
    if not selected:continue
    if not path.startswith('/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/'):
        raise RuntimeError('Coverage must not modify original equipment '+path)
    row=receipt['meshes'].setdefault(path,dict(previous_materials=[s.material_interface.get_path_name() if s.material_interface else None for s in slots],saved=False))
    if E.get_metadata_tag(mesh,'RobeHemVisibilitySHA')!=hem_materials.REV:
        for i in selected:
            old=slots[i].material_interface;original=E.get_metadata_tag(old,'RobeHemOriginalMaterial')
            if not original:raise RuntimeError('Missing original surface provenance '+old.get_path_name())
            slots[i].set_editor_property('material_interface',hem_materials.make(u.load_asset(original)))
        mesh.set_editor_property('materials',slots)
        E.set_metadata_tag(mesh,'RobeHemVisibilitySHA',hem_materials.REV)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save covered-region materials '+path)
    row.update(saved=True,shader_revision=hem_materials.REV,geometry_unchanged=True)
    record();print('ROBE_COVERAGE_SAVED',mesh.get_name(),flush=True)
    del mesh,slots;gc.collect();u.SystemLibrary.collect_garbage()
receipt['completed']=True;receipt['shader_revision']=hem_materials.REV;record()
print('ROBE_COVERAGE_COMPLETE',len(receipt['meshes']),flush=True)
