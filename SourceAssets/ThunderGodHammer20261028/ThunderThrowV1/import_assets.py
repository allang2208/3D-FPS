"""Save the exclusive seat and three native arm clips; derive the real release frame."""
import unreal as u,json,math,re
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'complete':False,'saved':[],'runtime_tested':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+str(asset))
    receipt['saved'].append(asset.get_path_name());record();return asset
def node(mat,cls,**props):
    result=L.create_material_expression(mat,cls)
    for key,value in props.items():result.set_editor_property(key,value)
    return result
def mat(name,color,metal,rough):
    m=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m);m.set_editor_property('used_with_nanite',True)
    s=node(m,u.MaterialExpressionSubstrateShadingModels)
    inputs={'basecolor':node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1)),
            'metallic':node(m,u.MaterialExpressionConstant,r=metal),'roughness':node(m,u.MaterialExpressionConstant,r=rough)}
    names={str(n).replace(' ','').lower():str(n) for n in L.get_material_expression_input_names(s)}
    legacy={'basecolor':u.MaterialProperty.MP_BASE_COLOR,'metallic':u.MaterialProperty.MP_METALLIC,'roughness':u.MaterialProperty.MP_ROUGHNESS}
    for key,n in inputs.items():
        if not L.connect_material_expressions(n,'',s,names[key]):raise RuntimeError('Material connection failed')
        L.connect_material_property(n,'',legacy[key])
    L.connect_material_property(s,'',u.MaterialProperty.MP_FRONT_MATERIAL);L.layout_material_expressions(m)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    return save(m)
def imp(name,opt):
    t=u.AssetImportTask();t.filename=str(P/'Export'/(name+'.fbx'));t.destination_path=D;t.destination_name=name
    t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True;t.options=opt
    A.import_asset_tasks([t]);asset=u.load_asset(D+'/'+name)
    if not asset:raise RuntimeError('Import failed '+name)
    return asset
record()
materials={'M_ThunderGodHammerSurface':u.load_asset('/Game/Weapons/ThunderGodHammer20261028/Materials/M_ThunderGodHammerSurface'),
           'M_ThunderThrowSilver':mat('M_ThunderThrowSilver',(.48,.53,.59),.95,.24),
           'M_ThunderThrowRune':mat('M_ThunderThrowRune',(.015,.18,.38),.65,.27)}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
mesh=imp('SM_ThunderHammer_GuanLeiSeat',opt)
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    key=re.sub(r'(?:[._]\d{3})+$','',str(slot.material_slot_name));mesh.set_material(i,materials[key])
settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;settings.explicit_tangents=True
settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings);save(mesh)
arms=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
source=json.loads((P/'motion.json').read_text(encoding='utf-8'))
for name in source['clips']:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=arms.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    anim=imp(name,opt);anim.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(anim):raise RuntimeError('Cannot finalize '+name)
    save(anim)
# Convert the imported WPN_root + actual modular mount into camera-local release space.
# The runtime rotating assembly uses its 70 cm shaft centre, not the FBX origin.
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.SOURCE;opt.optional_skeletal_mesh=arms
pose=u.AnimPoseExtensions.get_anim_pose_at_time(u.load_asset(D+'/A_ThunderHammer_ThrowRelease'),.24,opt)
t=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
mount=json.loads((R/'Content/ColdSteelData/thunder-god-hammer-modules.json').read_text(encoding='utf-8'))['bone_mount']
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def rotate(q,v):
    tmp=[2*x for x in cross(q[:3],v)];c=cross(q[:3],tmp)
    return [v[i]+q[3]*tmp[i]+c[i] for i in range(3)]
def mul(a,b):
    c=cross(a[:3],b[:3]);return [a[3]*b[i]+b[3]*a[i]+c[i] for i in range(3)]+[a[3]*b[3]-sum(a[i]*b[i] for i in range(3))]
v=rotate(mount['rotation_xyzw'],[0,0,70*mount['scale'][2]])
v=[v[i]+mount['location_cm'][i] for i in range(3)]
v=[v[i]*[t.scale3d.x,t.scale3d.y,t.scale3d.z][i] for i in range(3)]
q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w];v=rotate(q,v)
v=[v[i]+[t.translation.x,t.translation.y,t.translation.z][i] for i in range(3)]
yaw=[0,0,math.sqrt(.5),math.sqrt(.5)];v=rotate(yaw,v);q=mul(mul(yaw,q),mount['rotation_xyzw'])
header='#pragma once\n#include "CoreMinimal.h"\n// Authored release at .24s, imported WPN_root and current module mount.\nnamespace ThunderHammerThrow {\ninline const FVector LaunchOffsetCM('+','.join(format(x,'.9f') for x in v)+');\ninline const FQuat MeshRotation('+','.join(format(x,'.12f') for x in q)+');\n}\n'
(R/'Source/FPSGAME/Production/ThunderHammerThrowLaunch.h').write_text(header,encoding='utf-8')
receipt.update(complete=True,launch_offset_cm=v,mesh_rotation_xyzw=q,icon_storage='staged PNG');record()
print('THUNDER_THROW_ASSETS_SAVED '+json.dumps(receipt))
