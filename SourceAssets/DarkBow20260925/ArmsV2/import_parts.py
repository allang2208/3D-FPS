"""Restore only the active riser, wooden arrow and materials; no retired arms."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
DEST='/Game/Weapons/DarkBow20260925/ArmsV2'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
INFO={'fps':120}  # Static import uses no animation sampling.
receipt={'saved':{},'runtime_tested':False}
receipt_file=P/'parts_receipt.json'
if receipt_file.exists():receipt=json.loads(receipt_file.read_text())
# Every output is in this new candidate directory. Running play may continue:
# no active gameplay asset or class is overwritten by this import batch.
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserve unsaved Bow candidate edits: '+str(dirty))
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved'][asset.get_name()]=asset.get_path_name()
    receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def import_fbx(name,kind,skeleton=None):
    if name in receipt['saved'] and E.does_asset_exist(DEST+'/'+name):return u.load_asset(receipt['saved'][name])
    if E.does_asset_exist(DEST+'/'+name):raise RuntimeError('Preserve pre-existing unowned asset '+name)
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=kind;opt.import_materials=False;opt.import_textures=False
    opt.import_mesh=kind!=u.FBXImportType.FBXIT_ANIMATION
    opt.import_animations=kind==u.FBXImportType.FBXIT_ANIMATION
    if skeleton:opt.skeleton=skeleton
    if kind==u.FBXImportType.FBXIT_ANIMATION:
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',INFO['fps'])
        opt.anim_sequence_import_data.set_editor_property('remove_redundant_keys',False)
    if kind==u.FBXImportType.FBXIT_SKELETAL_MESH:
        opt.import_as_skeletal=True
        opt.create_physics_asset=False
        opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    if kind==u.FBXImportType.FBXIT_STATIC_MESH:
        opt.static_mesh_import_data.combine_meshes=True
        opt.static_mesh_import_data.auto_generate_collision=False
    task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'))
    task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=False
    task.options=opt;task.save=False;A.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Import did not produce '+name)
    return asset
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
# Remove only the long, separate baked string island. Its material is also on
# the grip and both tips, so hiding that whole material would damage the bow.
name='SM_DarkBow_Riser'
if name not in receipt['saved']:
    src=u.load_asset('/Game/Weapons/DarkBow20260925/SK_DarkBow')
    source=json.loads((P/'bow_surface.json').read_text())
    vertices=[];normals=[];uv=[];triangles=[];materials=[]
    removed=0
    for i,face in enumerate(source['triangles']):
        p=[source['positions'][v] for v in face]
        if all(-21.79<=v[0]<=-21.13 and -1.26<=v[1]<=-.61 and -64.05<=v[2]<=64.12 for v in p):
            removed+=1;continue
        base=len(vertices);vertices.extend(u.Vector(*v) for v in p)
        normals.extend(u.Vector(*v) for v in source['normals'][i]);uv.extend(u.Vector2D(*v) for v in source['uv'][i])
        triangles.append(u.IntVector(base,base+1,base+2));materials.append(source['materials'][i])
    if removed!=124:raise RuntimeError('Source string topology changed; preserve original bow')
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=triangles),0,True)
    for i,m in enumerate(materials):u.GeometryScript_Materials.set_triangle_material_id(dm,i,m,True)
    riser=A.duplicate_asset(name,DEST,src)
    _,outcome=G.copy_mesh_to_static_mesh(dm,riser,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Riser authoring failed')
    save(riser);receipt['separated_string_triangles']=removed
arrow=import_fbx('SM_Bow_WoodArrow',u.FBXImportType.FBXIT_STATIC_MESH)
def material(name,colour,metal,rough):
    path=DEST+'/Materials/'+name;m=u.load_asset(path)
    if m:return m
    m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L=u.MaterialEditingLibrary
    c=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(*colour,1)
    L.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
    for value,prop in ((metal,u.MaterialProperty.MP_METALLIC),(rough,u.MaterialProperty.MP_ROUGHNESS)):
        n=L.create_material_expression(m,u.MaterialExpressionConstant);n.r=value;L.connect_material_property(n,'',prop)
    L.recompile_material(m);save(m);return m
specs={'Wood':((.13,.055,.018),0,.61),'Steel':((.17,.19,.21),.85,.28),'Feather':((.19,.20,.16),0,.8),'Nock':((.09,.075,.05),0,.52)}
for i,s in enumerate(arrow.static_materials):
    label=str(s.material_slot_name).replace('Arrow','');values=specs.get(label,specs['Wood'])
    arrow.set_material(i,material('M_Arrow'+label,*values))
save(arrow)
material('M_BowString',(.035,.026,.016),0,.74)
receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('BOW_STATIC_PARTS_SAVED',len(receipt['saved']))
