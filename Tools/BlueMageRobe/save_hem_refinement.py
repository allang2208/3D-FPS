"""Replace only hem material bindings and refresh the approved robe icon."""
import json,hashlib,sys,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';BASE=R/'HemContinuity20261019';OUT=R/'HemRefine20261020';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'Tools/BlueMageRobe'));import hem_materials
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
saved=json.loads((BASE/'saved_assets.json').read_text());receipt_path=OUT/'saved_assets.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(meshes={},runtime_tested=False,network_transport_tested=False)
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Preserve current PIE before replacing hem materials')
receipt['completed']=False;record()
for row in json.loads((BASE/'authored.json').read_text())['rows']:
    if not row['hidden_source_triangles']:continue
    key=row['key'];path=saved['saved'][key]['asset'];asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing current continuous underlayer '+path)
    raw=Path(row['authored']).read_bytes();d=json.loads(raw);sha=hashlib.sha256(raw+hem_materials.REV.encode()).hexdigest()
    slots=list(asset.get_editor_property('materials'))
    if key not in receipt['meshes']:
        receipt['meshes'][key]=dict(asset=path,previous_materials=[slot.material_interface.get_path_name() if slot.material_interface else None for slot in slots],saved=False);record()
    if E.get_metadata_tag(asset,'RobeHemSourceSHA')!=sha:
        for i,slot in enumerate(slots):
            if str(slot.material_slot_name).startswith('RobeStairHidden_'):
                original=u.load_asset(d['materials'][i]);slot.set_editor_property('material_interface',hem_materials.make(original))
        asset.set_editor_property('materials',slots)
        E.set_metadata_tag(asset,'RobeHemSourceSHA',sha);E.set_metadata_tag(asset,'RobeHemRefinement','20261020-cross-section-v3')
        if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save hem materials '+path)
    for slot in asset.get_editor_property('materials'):
        if str(slot.material_slot_name).startswith('RobeStairHidden_'):
            material=slot.material_interface
            if 'RobeHemStrength' not in {str(n) for n in L.get_scalar_parameter_names(material)}:raise RuntimeError('Hem parameter missing after material save '+path)
    receipt['meshes'][key].update(saved=True,source_sha256=sha,lod_count=S.get_lod_count(asset));record()
    saved['saved'][key]['source_sha256']=sha
    print('ROBE_HEM_REFINED',key,flush=True);del d,asset,slots;gc.collect();u.SystemLibrary.collect_garbage()
sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'));from save_icons import apply_item
receipt['icon']=apply_item('ue_blue_mage_robe')
saved.setdefault('materials',{}).update({k:v.get_path_name() for k,v in hem_materials.cache.items()});saved['shader_revision']=hem_materials.REV;saved['hem_refinement']='20261020-cross-section-v3';(BASE/'saved_assets.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
receipt['completed']=True;receipt['shader_revision']=hem_materials.REV;receipt['geometry_and_lods_preserved']=True;record();print('ROBE_HEM_REFINEMENT_SAVED',len(receipt['meshes']),flush=True)
