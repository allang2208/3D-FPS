import unreal as u,json
from pathlib import Path
folder=Path(__file__).parent;root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');out=root/'Revision06';dest='/Game/Monsters/WitchRebuilt'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End current play before Witch import')
path=folder/'import_assets.py'
for stage in (() if globals().get('WITCH_REVISION06_FINISH_ONLY',False) else ('mesh','cloth','animations_a')):
    settings={'__file__':str(path),'__name__':'__main__','WITCH_REBUILT_STAGE':stage,'WITCH_REBUILT_GARMENT_REFRESH':stage=='mesh'}
    if stage=='animations_a':settings['WITCH_REBUILT_ROLES']=('Idle','Walk','CastPoison','Hit','TurnLeft','TurnRight','ThrowPoisonBottle')
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),settings)
path=folder/'install_surface06.py';exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__file__':str(path)})
mesh=u.load_asset(dest+'/SK_WitchRebuilt');names=[c.get_name() for c in mesh.get_editor_property('mesh_clothing_assets')]
if names!=['WitchRebuilt_LowerDrape06','WitchRebuilt_UpperDrape06']:raise RuntimeError('Unexpected installed cloth: '+str(names))
u.EditorAssetLibrary.set_metadata_tag(mesh,'Cloth','Drape06: regular 1704-vertex proxies; bounded binding; skirt sphere self collision; sleeve/body collisions; 4/6 iterations, one substep')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed')
u.SystemLibrary.execute_console_command(None,'WitchRebuilt.DescribeDrapeMapping')
mapping=(root.parent.parent/'Saved/WitchRebuilt-DrapeMapping.txt').read_text(encoding='utf-8-sig');(out/'mapping_after.txt').write_text(mapping,encoding='utf-8')
result={'cloth':names,'surface':'UpperFabric06 / Lining06','animation':'Arm06, 1.5 s throw / 0.75 s release','physics_and_material_performance':'see performance captures','user_visual_acceptance':False,'dirty_candidate':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(dest)]}
(out/'ue_asset_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
p=root/'ue_delivery.json';delivery=json.loads(p.read_text(encoding='utf-8'));delivery.update(status='Drape06 / Surface06 / Arm06 installed; user visual acceptance pending',revision06=result);p.write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result));print('\n'.join(x for x in mapping.splitlines() if x.startswith('section=')))
