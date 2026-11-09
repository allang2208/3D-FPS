"""Fresh production animation, material and presentation inputs for Repair20."""
import unreal as u,pickle,json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent
d=pickle.load(open(r.parent/'Repair19/native.pkl','rb'));d['clips']={}
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
out={'hashes':{},'meshes':{},'materials':{}}
def record(a):
    p=a.get_path_name().split('.')[0];f=Path(u.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset');out['hashes'][p]=hashlib.sha256(f.read_bytes()).hexdigest()
def path(a):return a.get_path_name() if a else None
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');record(mesh)
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=mesh;opt.should_retarget=True
for folder,prefix,roles in [('Animations','A_M249_',('idle','reload','reload_empty')),('SideMagazine20261108/Animations','A_M249_side_',('reload','reload_empty'))]:
    for role in roles:
        a=u.load_asset('/Game/Weapons/M249/'+folder+'/'+prefix+role);record(a);fps=120;duration=a.get_play_length();rows=[]
        for i in range(1 if role=='idle' else round(duration*fps)+1):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,min(i/fps,duration),opt)
            rows.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in d['names']])
        d['clips'][a.get_path_name()]=dict(fps=fps,duration=duration,frames=rows)
for family,p in d['profiles'].items():
    a=u.load_asset(p['asset']);record(a);rows=[]
    for c in a.get_editor_property('clips'):
        v=c.get_editor_property;retained=v('retained')
        rows.append(dict(base=v('base').get_path_name(),retained=path(retained),duration=v('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in v('tracks')]))
    p['clips']=rows
def material(a):
    if not a or path(a) in out['materials']:return
    record(a);base=a.get_base_material();record(base)
    row={'base':path(base)}
    if isinstance(a,u.MaterialInstanceConstant):
        row.update(parent=path(a.parent),scalars={str(n):L.get_material_instance_scalar_parameter_value(a,n) for n in L.get_scalar_parameter_names(a)},vectors={str(n):list(L.get_material_instance_vector_parameter_value(a,n).to_tuple()) for n in L.get_vector_parameter_names(a)},textures={str(n):path(L.get_material_instance_texture_parameter_value(a,n)) for n in L.get_texture_parameter_names(a)})
    row['customs']=[dict(description=str(n.get_editor_property('description')),code=n.get_editor_property('code')) for n in L.get_material_expressions(base) if isinstance(n,u.MaterialExpressionCustom)]
    out['materials'][path(a)]=row
for a in [mesh]+[u.load_asset('/Game/Weapons/M249/SideMagazine20261108/Meshes/'+n) for n in ('SM_m249_side_mag_30','SM_m249_side_mag_45','SM_M249_SidePort')]:
    record(a);slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
    out['meshes'][path(a)]=[dict(slot=str(s.material_slot_name),material=path(s.material_interface)) for s in slots]
    for s in slots:material(s.material_interface)
for p in ('/Game/Weapons/M249/Surface20261108/Materials/MI_M249_CommonRail','/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanPolymer','/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanSatinSteel'):material(u.load_asset(p))
out['camera_cvar']=u.SystemLibrary.get_console_variable_float_value('fps.WeaponActionCameraScale')
with (r/'native.pkl').open('wb') as f:pickle.dump(d,f)
(r/'inputs.json').write_text(json.dumps(out,indent=2))
print('M249_REPAIR20_CURRENT_INPUTS_SAVED',len(d['clips']),len(out['materials']),flush=True)
