import unreal as u,json
from pathlib import Path
folder=Path(__file__).parent;root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');out=root/'Spike20260922';dest='/Game/Monsters/WitchRebuilt'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; binding update deferred')
path=folder/'import_assets.py'
for stage in ('mesh','cloth'):
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__file__':str(path),'__name__':'__main__','WITCH_REBUILT_STAGE':stage,'WITCH_REBUILT_GARMENT_REFRESH':stage=='mesh'})
mesh=u.load_asset(dest+'/SK_WitchRebuilt');names=[c.get_name() for c in mesh.get_editor_property('mesh_clothing_assets')]
if names!=['WitchRebuilt_LowerDrape05Stable','WitchRebuilt_UpperDrape05Stable']:raise RuntimeError('Unexpected cloth bindings: '+str(names))
u.EditorAssetLibrary.set_metadata_tag(mesh,'Cloth','Drape05: bounded render-to-simulation prisms; original two proxies retained; unmatched local vertices retain authored skin')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed')
u.SystemLibrary.execute_console_command(None,'WitchRebuilt.DescribeDrapeMapping')
mapping=(root.parent.parent/'Saved/WitchRebuilt-DrapeMapping.txt').read_text(encoding='utf-8-sig')
(out/'mapping_after.txt').write_text(mapping,encoding='utf-8')
result={'cloth':names,'cloth_classes':[c.get_class().get_path_name() for c in mesh.get_editor_property('mesh_clothing_assets')],'native_build':'Saved/BuildEditor/build-20260922-140814.log','runtime_tested':False,'visible_geometry_changed':False,'animation_changed':False,'dirty_candidate':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(dest)]}
(out/'ue_asset_result.json').write_text(json.dumps(result,indent=2))
delivery_path=root/'ue_delivery.json';delivery=json.loads(delivery_path.read_text(encoding='utf-8'))
delivery.update(status='Drape05 bounded binding installed; runtime cloth test remains manual',runtime_tested=False,visual_tested=False,spike_revision=result)
delivery_path.write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result));print(mapping)
