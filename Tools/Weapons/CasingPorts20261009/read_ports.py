"""User-requested read-only ejection-port inventory; no gameplay or asset saves."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).parent
P=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project '+str(P))
(O/'Meshes').mkdir(exist_ok=True)
specs={}
for filename in ('motion_before.json','remaining_motion.json'):
    for key,row in json.loads((O.parent/'RifleAxialRecoil20261008'/filename).read_text())['weapons'].items():
        specs[key]={'mesh':row['mesh'],'fire':row['clips']['fire']['asset'],'aim_fire':row['clips']['aim_fire']['asset']}
specs.update({
 'm1911':{'mesh':'/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny','fire':'/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_fire'},
 'g18':{'mesh':'/Game/Weapons/G18/Integrated20260929/Single/SK_G18_Manny','fire':'/Game/Weapons/G18/Integrated20260929/Single/Animations/A_G18_fire'},
 'pit_viper2011':{'mesh':'/Game/Weapons/PitViper2011/Integrated20261002/Single/SK_PitViper2011_Manny','fire':'/Game/Weapons/PitViper2011/Integrated20261002/Single/Animations/A_PitViper2011_fire'},
 'super90':{'mesh':'/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7','fire':'/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_fire'},
 'dw715':{'mesh':'/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny','revolver':True},
 'rsh12':{'mesh':'/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny','revolver':True},
})
for key,root,stem in (
 ('m1911','/Game/Weapons/PistolDualWield20260914/M1911','M1911'),
 ('dw715','/Game/Weapons/PistolDualWield20260914/DW715','DW715'),
 ('g18','/Game/Weapons/G18/Integrated20260929/Dual','G18'),
 ('pit_viper2011','/Game/Weapons/PitViper2011/Integrated20261002/Dual','PitViper2011'),
 ('rsh12','/Game/Weapons/RSH12/Native71520261003','RSH12')):
    for side in ('r','l'):
        specs[key+'_'+side]={'mesh':f'{root}/{side}/SK_Dual_{stem}_{side}','dual':True,'revolver':key in ('dw715','rsh12')}

def tf(t):
    v,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=[v.x,v.y,v.z],q=[q.x,q.y,q.z,q.w],s=[s.x,s.y,s.z])
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing asset '+path)
    return a
report={'project':str(P),'read_only':True,'game_started':False,'weapons':{}}
for key,spec in specs.items():
    mesh=load(spec['mesh'])
    ref=u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
    names={str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)}
    selected=[n for n in names if n.startswith('WPN_') or n.startswith(('PKM_Charge','PKM_Cover'))]
    row=dict(spec,reference={n:tf(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in sorted(selected)},clips={})
    try:row['import_files']=list(mesh.get_editor_property('asset_import_data').extract_filenames())
    except Exception as e:row['import_files_error']=str(e)
    opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    opts.optional_skeletal_mesh=mesh;opts.should_retarget=True
    for role in ('fire','aim_fire'):
        if role not in spec:continue
        clip=load(spec[role]);samples=[]
        for time in (0.,1/60,2/60,3/60,4/60,.1):
            time=min(time,clip.get_play_length())
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
            samples.append(dict(time=time,bones={n:tf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in selected}))
        row['clips'][role]={'asset':clip.get_path_name(),'samples':samples}
    if not spec.get('dual'):
        file=O/'Meshes'/(key+'.fbx')
        if not file.exists():
            task=u.AssetExportTask();task.object=mesh;task.filename=str(file)
            task.automated=True;task.prompt=False;task.replace_identical=True
            task.exporter=u.SkeletalMeshExporterFBX()
            opt=u.FbxExportOption();opt.set_editor_property('level_of_detail',False)
            opt.set_editor_property('collision',False)
            opt.set_editor_property('bake_material_inputs',u.FbxMaterialBakeMode.DISABLED)
            task.options=opt
            if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Mesh export failed '+key)
        row['export']=str(file)
    report['weapons'][key]=row
    (O/'ports_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CASING_PORT_READ',key,flush=True)
print('CASING_PORT_INVENTORY_COMPLETE',len(report['weapons']),flush=True)
