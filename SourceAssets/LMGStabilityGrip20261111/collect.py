"""Read authored contacts and export existing rigid parts for the new shared grip."""
from pathlib import Path
import unreal as u,json,hashlib
HERE=Path(__file__).resolve().parent
HERE.joinpath('Inputs').mkdir(exist_ok=True)
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def profile(path):
    a=u.load_asset(path)
    if not a:return None
    get=lambda a,k:a.get_editor_property(k)
    return dict(path=path,family=str(get(a,'family')),clips=[dict(base=get(c,'base').get_path_name(),retained=get(c,'retained').get_path_name() if get(c,'retained') else None,duration=get(c,'duration'),tracks=[dict(bone=str(get(t,'bone')),times=list(get(t,'times')),values=list(get(t,'values'))) for t in get(c,'tracks')]) for c in get(a,'clips')])
data={}
specs={
 'M249':('/Game/Weapons/M249/SK_M249_V7','/Game/Weapons/M249/Animations/A_M249_idle',{'base':'/Game/Weapons/M249/Bipod/DA_M249_SupportGrip'}),
 'LMG201':('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10','/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle',{'base':'/Game/Weapons/AnimationProfiles20261001/ue_lmg201/DA_base','vertical':'/Game/Weapons/AnimationProfiles20261001/ue_lmg201/DA_vertical'}),
 'PKM':('/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular','/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_idle',{'vertical':'/Game/Weapons/AnimationProfiles20261001/ue_pkm_lowpoly/DA_vertical'})}
for key,(path,clip,profiles) in specs.items():
    mesh=u.load_asset(path)
    dm,_=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm);bones=sorted(bones,key=lambda b:b.index)
    names=[str(b.name) for b in bones];a=u.load_asset(clip)
    data[key]=dict(mesh=path,names=names,parents=[b.parent_index for b in bones],bind=[tr(b.world_transform) for b in bones],idle=clip+'.'+clip.rsplit('/',1)[-1],local=[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,0.,False,mesh)],profiles={k:profile(v) for k,v in profiles.items()})
    for family,p in data[key]['profiles'].items():
        if not p:continue
        row=next((c for c in p['clips'] if c['base']==a.get_path_name()),None)
        if row and row['retained']:
            retained=u.load_asset(row['retained'])
            row['retained_idle']=[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(retained,names,0.,False,mesh)]
    del dm
parts={'factory':'/Game/Weapons/M249/Assembly/SM_M249_foregrip','handguard':'/Game/Weapons/M249/Assembly/SM_M249_handguard',
       'LMG201_vertical':'/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_vertical',
       'PKM_vertical':'/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_vertical'}
exports={}
for key,path in parts.items():
    a=u.load_asset(path)
    target=HERE/'Inputs'/(key+'.fbx')
    task=u.AssetExportTask();task.object=a;task.filename=str(target);task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+path)
    exports[key]=dict(path=path,file=str(target),materials=[dict(slot=str(m.material_slot_name),path=m.material_interface.get_path_name()) for m in a.static_materials])
data['parts']=exports
(HERE/'inputs.json').write_text(json.dumps(data),encoding='utf-8')
print('LMG shared-grip authoring inputs exported; no runtime test or asset mutation.')
