"""Build saved garment derivatives with each existing native skeleton, then publish recipes."""
import json,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];ROOT='/Game/Characters/ModularOutfit20260924/Super90Source20261006';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
manifest=json.loads((O/'equipment_manifest.json').read_text());out=O/'EquipmentSaved';out.mkdir(exist_ok=True)

def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing equipment dependency '+p)
 return a

def save(a):
 if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError('Unable to save '+a.get_path_name())

for entry in manifest:
 file=Path(entry['file']);raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest();d=json.loads(raw);profile=entry['profile'];item=entry['item'];name='SK_'+profile+'_'+item;path=ROOT+'/'+profile+'/'+name;rp=out/(profile+'_'+item+'.json')
 if rp.exists() and json.loads(rp.read_text()).get('sha256')==sha and E.does_asset_exist(path):continue
 source=load(d['binding_source']);native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Unable to read binding '+profile)
 _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones};vertices=[];normals=[];uv=[];weights=[];triangles=[];seen={}
 for fi,face in enumerate(d['triangles']):
  faceout=[]
  for j,vi in enumerate(face):
   n=d['normals'][fi][j];t=d['uv'][fi][j];key=(vi,*[round(x,7) for x in n+t])
   if key not in seen:
    seen[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n));uv.append(u.Vector2D(*t));weights.append(d['weights'][vi])
   faceout.append(seen[key])
  triangles.append(u.IntVector(*faceout))
 dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=triangles),0,True);B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
 for vi,row in enumerate(weights):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in row.items()])
 for i,m in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,int(m),True)
 mesh=u.load_asset(path) or A.duplicate_asset(name,ROOT+'/'+profile,source)
 if not mesh:raise RuntimeError('Unable to create '+path)
 opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[load(p) for p in d['materials']],new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Unable to author '+path)
 mesh.set_editor_property('physics_asset',None);E.set_metadata_tag(mesh,'Super90GarmentSHA256',sha)
 u.FPSModularOutfitComponent.configure_outfit_lods(mesh);u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh,3,True,False);save(mesh)
 rp.write_text(json.dumps({'profile':profile,'item':item,'mesh':mesh.get_path_name(),'sha256':sha,'runtime_tested':False},indent=2));print('SUPER90_GARMENT_SAVED',profile,item,flush=True)

# Merge at the end; never expose paths for unfinished garment batches.
cp=P/'Content/ColdSteelData/modular_outfits.json';c=json.loads(cp.read_text(encoding='utf-8-sig'));receipt=json.loads((O/'import_receipt.json').read_text());slots=receipt['outfit_material_slots']['bare']
hands=[i for i,n in enumerate(slots) if 'hand' in n.lower()];arms=[i for i,n in enumerate(slots) if i not in hands]
bare=receipt['outfit']['bare'];c['profiles'][receipt['mesh']]={'rig_profile':'Super90','base':bare,'native_bare_skin':bare,'bare_arms_candidate':bare,'native_bare_arms':True,'hide_source_materials':receipt['arm_materials'],'shirt_covers':arms,'glove_covers':hands,'shirt':receipt['outfit']['shirt'],'gloves':receipt['outfit']['gloves'],'separate_gloves':True}
for item,role,slot in [('ue_hardknuckle_gloves','gloves',3),('ue_st6_sleeves','shirt',7)]:
 c['items'][item]={'slot':slot,'material':'','appearance_family':'Super90Source20261006','rig_meshes':{'Super90':receipt['outfit'][role]}}
 if role=='shirt':c['items'][item]['world_covers']=[0,1]
for entry in manifest:
 r=json.loads((out/(entry['profile']+'_'+entry['item']+'.json')).read_text());c['items'][r['item']]['rig_meshes'][r['profile']]=r['mesh']
# Sleeves cover the arms only; the source has no torso garment.
for path,profile in c['profiles'].items():
 if profile['rig_profile'] in ('Jason','Body'):
  c['items']['ue_st6_sleeves'].setdefault('rig_world_covers',{})[profile['rig_profile']]=[0,1]
cp.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'equipment_delivery.json').write_text(json.dumps({'saved_derivatives':len(manifest),'source_equipment':receipt['outfit'],'runtime_tested':False},indent=2))
print('SUPER90_EQUIPMENT_RECIPES_SAVED',len(manifest),flush=True)
