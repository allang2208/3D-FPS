"""Save HeQue's new continuous corpse and bind it to the existing living mesh."""
import json,sys,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/SoftDeathV02'
DEST='/Game/Monsters/HeQue/SoftCorpseV02';E=u.EditorAssetLibrary
sys.path.insert(0,str(PROJECT/'Tools/MonsterSoftCorpse'));import corpse_materials
corpse_materials.DEST=DEST+'/Materials'
report={'stage':'binding','saved':[],'gameplay_tested':False,'rendered':False}
def record():(ROOT/'Records/ue-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(a):
    if not a or not E.save_loaded_asset(a,False):raise RuntimeError('Corpse save failed: '+str(a))
    if a.get_path_name() not in report['saved']:report['saved'].append(a.get_path_name())
    record()
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE before binding HeQue corpse')
    if any(p.get_path_name().startswith('/Game/Monsters/HeQue') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved HeQue assets')
    item=json.loads((ROOT/'sources.json').read_text('utf8'))[0]
    source=u.load_asset(item['source']);mesh=u.load_asset(item['corpse']);skeleton=u.load_asset(item['skeleton'])
    data=u.load_asset(DEST+'/DA_HeQue_SoftCorpseV02')
    if not data:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
        data=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_HeQue_SoftCorpseV02',DEST,u.M14SoftBodyData,factory)
    if data.get_editor_property('corpse_mesh')!=mesh:
        count=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh)
        if count>1 and not u.SkeletalMeshEditorSubsystem.remove_lods(mesh,list(range(1,count))):raise RuntimeError('Corpse LOD cleanup failed')
        if not u.M14SoftBodyData.build_corpse(mesh,skeleton,data,str(ROOT/'HeQue/cage.json'),str(ROOT/'HeQue/embedding.bin')):
            raise RuntimeError('Continuous HeQue corpse binding failed')
    slots=list(source.materials);saved=set()
    for slot in slots:slot.material_interface=corpse_materials.make(slot.material_interface,saved)
    mesh.set_editor_property('materials',slots);report['saved'].extend(sorted(saved))
    save(mesh);save(skeleton);save(data)
    u.M14SoftBodyData.bind_to_living_mesh(source,data);save(source)
    authored=json.loads((ROOT/'Records/authoring.json').read_text('utf8'))
    report.update(stage='continuous_corpse_v02_saved',source=source.get_path_name(),corpse=mesh.get_path_name(),data=data.get_path_name(),
        soft_nodes=authored['soft_nodes'],rigid_patches=authored['rigid_patches'],proxy_counts_source='authoring data passed to BuildCorpse',
        unsupported_nodes=len(data.get_editor_property('unsupported_nodes')),collapse_in_place=bool(data.get_editor_property('collapse_in_place')),
        standard='M14 V19 complete continuous field, locally reinforced metal, zero rigid patches',handoff_seconds=0.)
    record();print('HEQUE_CONTINUOUS_CORPSE_V02_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
