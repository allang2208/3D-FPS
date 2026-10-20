"""Explicit user-requested independent read-back of saved SVCH assets."""
import json,math,hashlib
from pathlib import Path
from collections import Counter
import unreal as u
O=Path(__file__).parent
P=Path(u.Paths.project_dir()).resolve()
ROOT=globals().get('ASSET_ROOT','/Game/Weapons/SVCH/Refined20261018')
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
checks=[];report={'checks':checks,'mesh':{},'materials':[],'profile':{}}
def check(name,passed,detail=None):
    checks.append({'name':name,'passed':bool(passed),'detail':detail})
def pick(value,cls):
    return next(x for x in (value if isinstance(value,tuple) else (value,)) if isinstance(x,cls))
mesh=u.load_asset(ROOT+'/'+globals().get('MESH_NAME','SK_SVCH_Refined_R4'))
check('saved_mesh',isinstance(mesh,u.SkeletalMesh))
slots=list(mesh.get_editor_property('materials'))
names=[str(s.material_slot_name) for s in slots]
check('material_identities',names==['SVCH_Body','SVCH_Polymer','SVCH_Rubber','SVCH_BarrelSteel','SVCH_BoltCarrier','SVCH_Cartridge','SVCH_MagRelease','SVCH_Magazine','SVCH_Selector','MI_Manny_01','MI_Manny_02'],names)
outfit=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8'))['profiles'][mesh.get_path_name()]
check('source_arm_hide_slots',outfit['hide_source_materials']==[9,10],outfit)
check('native_bare_skin_exists',E.does_asset_exist(outfit['native_bare_skin']))
native_shapes={'JC_'+name+'_'+side for side in ('L','R') for name in
               ('ElbowFlex20','ElbowFlex75','ElbowFlex110','ElbowFlex135','WristFlexA','WristFlexB','WristRadial','WristUlnar')}
native_shapes.update(('JC_Grip_L_21_51_77_60','JC_Grip_R_0_51_48_48'))
saved_shapes={m.get_name() for m in mesh.get_editor_property('morph_targets')}
check('native_arm_corrective_shapes',native_shapes<=saved_shapes,{'expected':18,'saved':len(saved_shapes),'missing':sorted(native_shapes-saved_shapes)})
for i,s in enumerate(slots[:9]):
    m=s.material_interface
    metallic=L.get_material_instance_scalar_parameter_value(m,'Metallic')
    rough=L.get_material_instance_scalar_parameter_value(m,'Roughness')
    normal=L.get_material_instance_texture_parameter_value(m,'SurfaceNormal')
    data={'slot':i,'name':names[i],'material':m.get_path_name(),'metallic':metallic,'roughness':rough,'normal':normal.get_path_name() if normal else None}
    report['materials'].append(data)
    check('surface_'+names[i],0<=metallic<=1 and 0<rough<=1 and normal is not None)
    if names[i] in ('SVCH_Polymer','SVCH_Rubber','SVCH_Magazine'):check('dielectric_'+names[i],metallic<.01)
    if normal:check('normal_map_'+names[i],not normal.get_editor_property('srgb') and normal.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_NORMALMAP)
mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);bones=[str(n) for n in mod.get_all_bone_names()]
profile=u.load_asset(ROOT+'/DA_SVCH_BaseGrip')
clips=list(profile.get_editor_property('clips'))
check('profile_family',str(profile.get_editor_property('family'))=='base')
check('profile_12_actions',len(clips)==12)
action_rows=[]
for c in clips:
    base=c.get_editor_property('base');duration=c.get_editor_property('duration');tracks=list(c.get_editor_property('tracks'))
    check('clip_'+base.get_name(),base.get_editor_property('skeleton')==mesh.skeleton and abs(base.get_play_length()-duration)<.001)
    for t in tracks:
        bone=str(t.get_editor_property('bone'));times=list(t.get_editor_property('times'));values=list(t.get_editor_property('values'))
        valid=bone in bones and len(values)==10*len(times) and bool(times) and all(math.isfinite(v) for v in values+times)
        valid=valid and all(a<b for a,b in zip(times,times[1:])) and times[0]>=0 and times[-1]<=duration+.001
        if valid:valid=all(abs(sum(v*v for v in values[k+3:k+7])-1)<.001 for k in range(0,len(values),10))
        check(base.get_name()+'/'+bone,valid)
    action_rows.append({'clip':base.get_path_name(),'duration':duration,'tracks':len(tracks),'keys':sum(len(t.get_editor_property('times')) for t in tracks)})
report['profile']={'asset':profile.get_path_name(),'actions':action_rows}

AU,Q,LU=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
AU.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
pos=LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,True),u.GeometryScriptVectorList))
tris=LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,True),u.GeometryScriptTriangleList))
ids=LU.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
check('finite_vertices',all(math.isfinite(x) for p in pos for x in (p.x,p.y,p.z)))
counts=Counter(int(i) for i in ids)
source=json.loads(Path(globals().get('MODEL_RECEIPT',O.parent/'model_receipt.json')).read_text())
expected=source['triangles'] if 'triangles' in source else source['arms']['triangles']+sum(p['after']['triangles'] for p in source['parts'].values())
check('saved_triangle_count',len(tris)==expected,{'saved':len(tris),'source':expected})
check('all_surface_sections_nonempty',set(counts)==set(range(11)),dict(counts))
degenerate=[]
for ti,t in enumerate(tris):
    a,b,c=pos[t.x],pos[t.y],pos[t.z]
    x=(b.y-a.y)*(c.z-a.z)-(b.z-a.z)*(c.y-a.y)
    y=(b.z-a.z)*(c.x-a.x)-(b.x-a.x)*(c.z-a.z)
    z=(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
    if x*x+y*y+z*z<1e-16:degenerate.append({'triangle':ti,'slot':int(ids[ti])})
check('saved_nonzero_area_triangles',not degenerate,degenerate)
normal_bad=0;normal_total=0;face_normal_variation=0;winding_bad=0
for ti,t in enumerate(tris):
    result=Q.get_triangle_normals(dm,ti)
    ns=[n for n in result if isinstance(n,u.Vector)]
    face=(pos[t.y]-pos[t.x]).cross(pos[t.z]-pos[t.x]);face=face/max(face.length(),1e-30)
    for n in ns:
        normal_total+=1
        length=n.x*n.x+n.y*n.y+n.z*n.z
        if not math.isfinite(length) or length<.98 or length>1.02:normal_bad+=1
        if face.dot(n)>0:winding_bad+=1
    if int(ids[ti])<9 and len(ns)==3:
        if max((ns[0]-ns[1]).length(),(ns[0]-ns[2]).length())>.01:face_normal_variation+=1
check('unit_saved_normals',normal_bad==0,{'bad':normal_bad,'total':normal_total})
check('native_ue_winding_and_normals',winding_bad==0,{'opposed_to_native':winding_bad,'total':normal_total})
check('continuous_surface_normals_present',face_normal_variation>100,face_normal_variation)
report['mesh']={'path':mesh.get_path_name(),'vertices':len(pos),'triangles':len(tris),'triangles_by_material':dict(counts),'skeleton':mesh.skeleton.get_path_name()}
report['passed']=all(c['passed'] for c in checks)
Path(globals().get('REPORT_PATH',O/'saved_assets.json')).write_text(json.dumps(report,indent=1),encoding='utf-8')
print('SVCH_SAVED_ASSETS_CHECK',json.dumps({'passed':report['passed'],'checks':len(checks),'failures':[c for c in checks if not c['passed']]}),flush=True)
