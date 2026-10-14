"""Apply authored surface deltas and private finishes to current fitted assets.
No game, preview, screenshot or automated acceptance pass is started.
"""
import array, hashlib, json, shutil
from pathlib import Path
import unreal as u

O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
ROOT='/Game/Weapons/RearGripSurface20261007';VERSION='RearGripSurface01-20261007'
C=json.loads((O/'Input/current.json').read_text())
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
AU,Q,ED,NRM=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_MeshEdits,u.GeometryScript_Normals
RP=O/'install_receipt.json'
R=json.loads(RP.read_text()) if RP.exists() else {'version':VERSION,'materials':{},'meshes':{},'weather':{},'complete':False,'runtime_tested':False}
def record():RP.write_text(json.dumps(R,indent=2))
def disk(p):return P/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing asset '+p)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def backup(p):
    dest=O/'Before'/(p.split('.')[0].removeprefix('/Game/')+'.uasset');dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(disk(p),dest)
def outcome(r):
    if isinstance(r,tuple) and any(isinstance(x,u.GeometryScriptOutcomePins) and x!=u.GeometryScriptOutcomePins.SUCCESS for x in r):
        raise RuntimeError('Geometry write failed')
def body_slot(name):
    s=name.lower()
    return not any(x in s for x in ('interface','collar','neck')) and not (s.endswith('_1') and s.startswith(('a762_','pkm14_')))

dirty=set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed and ed.get_game_world():raise RuntimeError('PIE active; preserve the current session')
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key,row in C['meshes'].items():
    if row['path'] in dirty:raise RuntimeError('Unsaved target '+row['path'])
    if key not in R['meshes'] and sha(row['path'])!=row['sha256']:raise RuntimeError('Concurrent mesh edit '+key)

# Read the same libraries merged by the existing weather component; append only
# our private material keys, leaving all original pairs and other tasks intact.
tables=['/Game/Weather/RainVisibility/DA_WeatherPresentation',
 '/Game/Weapons/HK416/Reworked20260930/DA_HK416_WetMaterials',
 '/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials',
 '/Game/Weapons/PKMLowpoly20260922/Finish20/DA_PKM_WetMaterials',
 '/Game/Weapons/M16A2/UniversalAttachments20260920/DA_M16_AttachmentWetMaterials']
wetmap={}
for p in tables:
    a=load(p)
    wetmap.update({str(k):v.get_path_name() for k,v in a.get_editor_property('wet_materials').items() if v})
newpairs={}

def scalar_adjustments(source,kind):
    names=L.get_scalar_parameter_names(source.get_base_material())
    values={str(n):L.get_material_instance_scalar_parameter_value(source,n) for n in names}
    out={}
    for name,value in values.items():
        if name in ('GrainRoughness','R01_Grain','R01_GrainRoughness'):out[name]=value*.50
        elif name in ('MottleRoughness','R01_Variation','R01_VariationRoughness','R01_MottleRoughness'):out[name]=value*.30
        elif name in ('Stipple','R01_PolymerStipple'):out[name]=value*.45
        elif name in ('SourceRoughnessWeight','R01_SourceRoughnessWeight','R01_PolymerSourceWeight'):out[name]=value*.4
        elif name=='PKM_MicroScratchStrength':out[name]=0.
    if 'R01_PolymerRoughness' in values:out['R01_PolymerRoughness']=.59 if kind=='stable' else values['R01_PolymerRoughness']
    if 'G43_Roughness' in values:out['G43_Roughness']=.61 if kind=='stable' else .52
    if 'Roughness' in values and values.get('Metallic',1)<.01:out['Roughness']=.62 if kind=='stable' else .52
    if kind=='stable' and 'R01_Roughness' in values and 'R01_PolymerStipple' in values and values['R01_PolymerStipple']>0:
        out['R01_Roughness']=.60
    return out

def soften_legacy_roughness(mat,kind):
    # Keep the gun-specific metal response and color/normal maps. Only the
    # polymer branch is refined; the correction fades out in the existing wet state.
    old=L.get_material_property_input_node(mat,u.MaterialProperty.MP_ROUGHNESS)
    output=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_ROUGHNESS)
    node=L.create_material_expression(mat,u.MaterialExpressionCustom)
    node.set_editor_property('description','Rear grip polymer surface refinement 20261007')
    node.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    node.set_editor_property('code','float r=Center+(R-Center)*0.22; return lerp(R,saturate(r),saturate(Polymer)*(1-saturate(Wet)));')
    inputs=[]
    for name in ('R','Center','Polymer','Wet'):
        entry=u.CustomInput();entry.set_editor_property('input_name',name);inputs.append(entry)
    node.set_editor_property('inputs',inputs)
    def constant(value):
        c=L.create_material_expression(mat,u.MaterialExpressionConstant);c.r=value;return c
    L.connect_material_expressions(old,output,node,'R')
    L.connect_material_expressions(constant(.62 if kind=='stable' else .52),'',node,'Center')
    if kind=='stable':poly=constant(1.)
    else:
        color=L.create_material_expression(mat,u.MaterialExpressionVertexColor)
        poly=L.create_material_expression(mat,u.MaterialExpressionOneMinus)
        L.connect_material_expressions(color,'R',poly,'Input')
    L.connect_material_expressions(poly,'',node,'Polymer')
    wet=L.create_material_expression(mat,u.MaterialExpressionScalarParameter)
    wet.set_editor_property('parameter_name','WeaponWetness');wet.set_editor_property('default_value',0.)
    L.connect_material_expressions(wet,'',node,'Wet')
    L.connect_material_property(node,'',u.MaterialProperty.MP_ROUGHNESS)
    mat.set_editor_property('automatically_set_usage_in_editor',False)
    for prop in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):mat.set_editor_property(prop,False)
    L.recompile_material(mat)

def finish(source_path,kind,suffix='dry'):
    source=load(source_path);ident=source_path+'|'+kind+'|'+suffix
    if ident in R['materials']:return load(R['materials'][ident]['path'])
    if source_path.split('.')[0] in dirty:raise RuntimeError('Unsaved material '+source_path)
    expected=C['materials'].get(source_path,{}).get('sha256')
    if expected and sha(source_path)!=expected:raise RuntimeError('Changed input material '+source_path)
    name=('MI_' if isinstance(source,u.MaterialInstanceConstant) else 'M_')+'RG01_'+kind+'_'+hashlib.sha256(ident.encode()).hexdigest()[:12]
    path=ROOT+'/Materials/'+name
    if E.does_asset_exist(path):raise RuntimeError('Unrecorded material destination '+path)
    result=E.duplicate_asset(source_path,path)
    if not result:raise RuntimeError('Cannot duplicate '+source_path)
    adjustments={}
    if isinstance(result,u.MaterialInstanceConstant):
        adjustments=scalar_adjustments(source,kind)
        for n,v in adjustments.items():L.set_material_instance_scalar_parameter_value(result,n,v)
        L.update_material_instance(result)
    else:soften_legacy_roughness(result,kind)
    E.set_metadata_tag(result,'RearGripSurfaceSource',source_path)
    E.set_metadata_tag(result,'RearGripSurfaceVersion',VERSION);save(result)
    R['materials'][ident]={'path':result.get_path_name(),'source':source_path,'scalars':adjustments,'saved':True};record()
    return result

bindings={}
for key,row in C['meshes'].items():
    binds={}
    for index,(slot,source) in enumerate(zip(row['slots'],row['materials'])):
        # LMG201 uses one self-wetting surface for body and neck; preserve that
        # continuity by updating both slots to the same private instance.
        if not source or not (body_slot(slot) or row['family']=='LMG201'):continue
        mi=finish(source,row['kind']);binds[index]=mi
        partner=wetmap.get(source)
        if partner:
            wet=mi if partner==source else finish(partner,row['kind'],'wet')
            newpairs[mi.get_path_name()]=wet
        elif mi.get_base_material().get_path_name().startswith('/Game/Weapons/WeaponSurface/Master/'):
            pass # Existing native self-wet discovery covers shared WS1 instances.
    bindings[key]=binds

weather=load(tables[0])
if tables[0] in dirty:raise RuntimeError('Unsaved weather library')
if newpairs:
    backup(tables[0]);mapping=dict(weather.get_editor_property('wet_materials'));mapping.update(newpairs)
    weather.set_editor_property('wet_materials',mapping);save(weather)
    R['weather']={'path':tables[0],'added':{k:v.get_path_name() for k,v in newpairs.items()},'saved':True};record()

for key,row in C['meshes'].items():
    if key in R['meshes']:continue
    mesh=load(row['path']);backup(row['path'])
    dm=u.DynamicMesh();outcome(AU.copy_mesh_from_static_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),
        u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)))
    with (O/'Plans'/(key+'.bin')).open('rb') as f:
        head=json.loads(f.readline())
        if head['source_sha256']!=sha(row['path']):raise RuntimeError('Source changed before write '+key)
        def read(code,n):
            a=array.array(code);a.fromfile(f,n);return a
        moved=read('i',head['moved']);pos=read('f',head['moved']*3)
        tids=read('i',head['normal_triangles']);normals=read('f',head['normal_triangles']*9)
    for i,vid in enumerate(moved):ED.set_vertex_position(dm,vid,u.Vector(*pos[3*i:3*i+3]),True)
    for i,tid in enumerate(tids):
        n=u.GeometryScriptTriangle();j=9*i
        n.vector0=u.Vector(*normals[j:j+3]);n.vector1=u.Vector(*normals[j+3:j+6]);n.vector2=u.Vector(*normals[j+6:j+9])
        NRM.set_mesh_triangle_normals(dm,tid,n,True)
    slots=list(mesh.get_editor_property('static_materials'))
    for index,mi in bindings[key].items():
        slot=slots[index];slot.material_interface=mi;slots[index]=slot
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],
        new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,
        enable_remove_degenerates=False,use_original_vertex_order=True)
    outcome(AU.copy_mesh_to_static_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD(lod_index=0)))
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'RearGripSurfaceVersion',VERSION)
    E.set_metadata_tag(mesh,'RearGripSurfaceAuthor','SourceAssets/RearGripSurface20261007/README.md')
    # Export the polished current mesh as the new reimport source, so reimport
    # does not silently restore a pre-polish FBX or an older receiver interface.
    exports=O/'Exports';exports.mkdir(exist_ok=True);fbx=exports/(key+'.fbx')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(fbx);task.automated=True;task.prompt=False;task.replace_identical=True
    task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False;task.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Author FBX export failed '+key)
    mesh.get_editor_property('asset_import_data').scripted_add_filename(str(fbx),0,'RearGripSurface01 current fitted source')
    save(mesh)
    R['meshes'][key]={'path':row['path'],'sha256':sha(row['path']),'fbx':str(fbx),'moved_vertices':head['moved'],
        'normal_triangles':head['normal_triangles'],'slots':[str(s.material_slot_name) for s in mesh.static_materials],
        'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.static_materials],
        'triangles':row['triangles'],'uv_sets':row['uv_sets'],'topology_changed':False,'saved':True};record()
    print('REARGRIP_SURFACE_SAVED',key,flush=True)
R['complete']=len(R['meshes'])==len(C['meshes']);record()
print('REARGRIP_SURFACE_COMPLETE',R['complete'],len(R['meshes']),len(R['materials']),flush=True)
