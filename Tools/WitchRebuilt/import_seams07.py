import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');out=root/'Revision07';folder=Path(__file__).parent;dest='/Game/Monsters/WitchRebuilt'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; left intact')
if any(p.get_path_name().startswith(dest) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Witch candidate has unsaved edits; retained')
p=folder/'install_surface07.py';exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p)})
p=folder/'import_assets.py'
for stage in ('mesh','cloth'):
 exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p),'__name__':'__main__','WITCH_REBUILT_STAGE':stage,'WITCH_REBUILT_GARMENT_REFRESH':stage=='mesh','WITCH_REBUILT_IMPORT_VERTEX_COLORS':True})
mesh=u.load_asset(dest+'/SK_WitchRebuilt');names=[c.get_name() for c in mesh.get_editor_property('mesh_clothing_assets')]
if names!=['WitchRebuilt_LowerDrape07','WitchRebuilt_UpperDrape07']:raise RuntimeError('Drape07 native function not loaded: '+str(names))
u.EditorAssetLibrary.set_metadata_tag(mesh,'Cloth','Drape07: shared pelvis waist, longitudinal cuff pins, shortened ground hem, 1704 simulation vertices; Drape06 solver budget retained')
u.EditorAssetLibrary.set_metadata_tag(mesh,'Surface','Seams07: rebuilt turned cuffs and continuous folded waist; repaired panels use vertex alpha')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Drape07 save failed')
result={'cloth':names,'surface':'UpperFabric07; alpha masked sleeve/yoke material','animation_changed':False,'scale_changed':False,'simulation_vertices':1704,'gameplay_tested':False,'user_visual_acceptance':False}
(out/'ue_asset_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
p=root/'ue_delivery.json';delivery=json.loads(p.read_text(encoding='utf-8'));delivery.update(status='Seams07 / Drape07 installed; gameplay and user visual acceptance pending',revision07=result);p.write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result))
