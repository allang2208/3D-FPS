"""Super90-only surface candidate and publication; never edit the shared V7 rig."""
import gzip,hashlib,json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1]
DEST='/Game/Weapons/Super90/JointSurface20261012'
SOURCE='/Game/Weapons/Super90/SkinClean20261011/Materials'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries
def read(name):return json.loads(gzip.decompress((O/name).read_bytes()))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def xyz(v):return [v.x,v.y,v.z]
def file_for(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def backup(path):
 f=file_for(path);out=O/'Before'/f.relative_to(P);out.parent.mkdir(parents=True,exist_ok=True)
 if not out.exists():shutil.copy2(f,out)
def make_shader():
 code=(O.parent/'Super90SkinClean20261011/M_Super90SkinClean_Hands.hlsl').read_text()
 d=read('arms_before.json.gz')
 def const(v):return 'float3('+','.join(format(x,'.9g') for x in v)+')'
 # Native pre-skin position avoids transporting M4's packed coordinates through
 # FBX V-axis conversion. Both sections now evaluate exactly the same field.
 frames=[]
 for side in ('l','r'):
  w=d['bones']['hand_'+side]['position'];e=d['bones']['lowerarm_'+side]['position']
  f=[a-b for a,b in zip(w,e)];length=sum(x*x for x in f)**.5
  frames.append((const(w),const([x/length for x in f])))
 start=code.index('float side=');end=code.index('float nail=',start)
 block=('float3 wrist=RestPosition.x<0?'+frames[0][0]+':'+frames[1][0]+';\n'
        'float3 forward=RestPosition.x<0?'+frames[0][1]+':'+frames[1][1]+';\n'
        'float longitudinal=dot(RestPosition-wrist,forward);\n'
        'float handAnatomy=smoothstep(.8,4.5,longitudinal)*(1-ForearmMode);\n'
        'float palmDetail=saturate(Surface.a)*handAnatomy;\n'
        'float palmar=palmDetail;\n')
 code=code[:start]+block+code[end:]
 code=code.replace('float cleanPalm=saturate(Surface.a)*(1-ForearmMode);','float cleanPalm=palmDetail;')
 code=code.replace('lerp(.11,.065,cleanPalm)','lerp(.12,.065,cleanPalm)')
 # Atlas relief starts only inside the hand; there is no normal-map seam on
 # the rebuilt wrist bridge. Nails retain their authored surface.
 code=code.replace('lerp(.42,.62,cleanPalm)*lerp(.75,1,handAnatomy)','lerp(.32,.54,cleanPalm)*handAnatomy')
 code=code.replace('float broad=f.noise(RestPosition.xy*.12+RestPosition.z*.07)-.5;',
  'float broad=f.noise(RestPosition.xy*.12+RestPosition.z*.07)-.5;\n'
  'float warm=f.noise(RestPosition.xz*.21+float2(13.2,5.4))-.5;')
 code=code.replace('WristTint*float3(1.015,1,.99)*(1+broad*.018*forearmVariation)',
  'WristTint*float3(1.015,1,.99)*(1+broad*.030)*float3(1+warm*.025,1+warm*.008,1-warm*.018)')
 code=code.replace('ColourDetailStrength*.065*skinDetail*fade','ColourDetailStrength*.025*skinDetail*fade')
 code=code.replace('float sharedRough=.50-.02*palmar+.004*broad;',
  'float sharedRough=.50-.018*palmar+.024*broad;')
 code=code.replace('*skinDetail*.045*fade','*skinDetail*.055*fade')
 return '// Super90 20261012: native reference coordinates and continuous wrist field.\n'+code
def create_materials():
 code=make_shader();report={}
 for suffix in ('Arms','Hands'):
  name='M_Super90JointSkin_'+suffix;parent=u.load_asset(DEST+'/Materials/'+name)
  if not parent:parent=A.duplicate_asset(name,DEST+'/Materials',u.load_asset(SOURCE+'/M_Super90SkinClean_'+suffix))
  custom=L.get_material_property_input_node(parent,u.MaterialProperty.MP_NORMAL)
  # Connect engine native reference attributes rather than mutating any UV.
  if E.get_metadata_tag(parent,'Super90NativeSkinCoordinates')!='20261012':
   for pin,cls in [('RestPosition',u.MaterialExpressionPreSkinnedPosition),('RestNormal',u.MaterialExpressionPreSkinnedNormal)]:
    source=L.create_material_expression(parent,cls);interp=L.create_material_expression(parent,u.MaterialExpressionVertexInterpolator)
    assert L.connect_material_expressions(source,'',interp,'')
    assert L.connect_material_expressions(interp,'',custom,pin)
   E.set_metadata_tag(parent,'Super90NativeSkinCoordinates','20261012')
  custom.set_editor_property('code',code)
  errors=L.recompile_material(parent)
  if errors:raise RuntimeError('Skin shader compile: '+str(errors))
  save(parent)
  iname='MI_Super90JointSkin_'+suffix;instance=u.load_asset(DEST+'/Materials/'+iname)
  if not instance:instance=A.duplicate_asset(iname,DEST+'/Materials',u.load_asset(SOURCE+'/MI_Super90SkinClean_'+suffix))
  L.set_material_instance_parent(instance,parent);L.update_material_instance(instance);save(instance)
  report[suffix]=instance.get_path_name()
 (O/'skin.hlsl').write_text(code);(O/'materials_saved.json').write_text(json.dumps(report,indent=2))
 return report
def bind_materials(mesh):
 slots=[s.copy() for s in mesh.materials];count=0
 for slot in slots:
  name=str(slot.material_slot_name)
  if name.startswith('Manny_S90_Skin_'):
   suffix='Hands' if 'hand' in name.lower() else 'Arms'
   slot.material_interface=u.load_asset(DEST+'/Materials/MI_Super90JointSkin_'+suffix);assert slot.material_interface
   count+=1
 assert count==3
 mesh.set_editor_property('materials',slots)
def apply_patch(mesh,patch,source_mesh=None):
 source=source_mesh or mesh
 slots=[s.copy() for s in source.materials]
 dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());assert status==u.GeometryScriptOutcomePins.SUCCESS
 for vi,p in patch['positions']:
  _,ok=u.GeometryScript_MeshEdits.set_vertex_position(dm,vi,u.Vector(*p),True);assert ok
 for vi,n in patch['normals']:
  _,ok=u.GeometryScript_Normals.update_vertex_normal(dm,vi,True,u.Vector(*n),False,u.Vector(1,0,0),u.Vector(0,1,0),False,True);assert ok
 # DynamicMesh polygon IDs alone do not retain imported material names. Supply
 # the existing slot identities so rebuilding cannot reuse stale section order.
 options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
  replace_materials=True,new_materials=[s.material_interface for s in slots],
  new_material_slot_names=[s.get_editor_property('imported_material_slot_name') for s in slots],
  bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD());assert status==u.GeometryScriptOutcomePins.SUCCESS
 mesh.set_editor_property('materials',slots)
 bind_materials(mesh)
 E.set_metadata_tag(mesh,'Super90JointSurface','20261012 local positions/normals; native weights and animation unchanged')
 save(mesh)
def readback(mesh,key):
 dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());assert status==u.GeometryScriptOutcomePins.SUCCESS
 _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps)
 _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
 _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
 result=dict(path=mesh.get_path_name(),positions=[xyz(p) for p in ps],triangles=[xyz(t) for t in ts],weights=[],uv=[[],[],[],[]],normals=[],materials=[],skeleton=mesh.skeleton.get_path_name(),bones={})
 for b in bones:
  tr=b.world_transform;p=tr.translation
  result['bones'][str(b.name)]=dict(index=b.index,parent=b.parent_index,position=xyz(p),axes=[xyz(tr.transform_location(v)-p) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))])
 for vi in range(len(ps)):
  _,ws,ok=B.get_vertex_bone_weights(dm,vi);assert ok
  result['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
 for ti in range(len(ts)):
  result['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0])
  _,a,b,c,ok=Q.get_triangle_normals(dm,ti);assert ok
  result['normals'].append([xyz(n) for n in (a,b,c)])
  for ch in range(4):
   v=Q.get_triangle_u_vs(dm,ch,ti);result['uv'][ch].append([[a.x,a.y] for a in v[:3]] if v[-1] else None)
 with gzip.open(O/(key+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(result,f,separators=(',',':'))
def stage():
 if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
  raise RuntimeError('Stop PIE before saving Super90 candidates.')
 create_materials();patches=json.loads((O/'patches.json').read_text())
 for key,patch in patches.items():
  source=u.load_asset(patch['path']);assert source
  assert hashlib.sha256(file_for(patch['path']).read_bytes()).hexdigest()==patch['source_sha256']
  name='SK_Super90JointCandidate_'+key;candidate=u.load_asset(DEST+'/Candidates/'+name)
  if not candidate:candidate=A.duplicate_asset(name,DEST+'/Candidates',source)
  apply_patch(candidate,patch,source);readback(candidate,key+'_candidate')
  print('SUPER90_CANDIDATE_SAVED',key,flush=True)
