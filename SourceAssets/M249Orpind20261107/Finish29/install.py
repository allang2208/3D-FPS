"""Publish the M249 feed finish, retaining polymer identity and seam tangents."""
import unreal as u,json,hashlib,zipfile
from pathlib import Path
r=Path(__file__).resolve().parent
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
D='/Game/Weapons/M249/Surface20261108'
mesh_root='/Game/Weapons/M249/SideMagazine20261108/Meshes/'
inputs=json.loads((r/'current.json').read_text())
receipt=r/'install_receipt.json'
report=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'bindings':{},'complete':False}
def record():receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
def disk(p):return Path(u.Paths.project_content_dir())/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
    p=a.get_path_name().split('.')[0];report['saved'][p]=hashlib.sha256(disk(p).read_bytes()).hexdigest();record()
def clone(src,dst):
    if E.does_asset_exist(dst):
        if dst not in report['saved']:raise RuntimeError('Unowned destination '+dst)
        return load(dst)
    a=E.duplicate_asset(src,dst)
    if not a:raise RuntimeError('Clone '+src)
    return a
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Wire '+pin)
def custom(m,name,code,pins):
    n=node(m,u.MaterialExpressionCustom,description=name,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    rows=[]
    for k in pins:
        item=u.CustomInput();item.set_editor_property('input_name',k);rows.append(item)
    n.set_editor_property('inputs',rows)
    for k,(a,out) in pins.items():wire(a,out,n,k)
    return n
def apply(mi,scalars,vectors):
    for k,v in scalars.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
    for k,v in vectors.items():L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v))
    L.update_material_instance(mi);save(mi)
    report.setdefault('materials',{})[mi.get_path_name()]={
        'parent':mi.parent.get_path_name(),
        'base':mi.get_base_material().get_path_name(),
        'scalars':{k:L.get_material_instance_scalar_parameter_value(mi,k) for k in scalars},
        'vectors':{k:list(L.get_material_instance_vector_parameter_value(mi,k).to_tuple()) for k in vectors},
        'textures':{str(k):L.get_material_instance_texture_parameter_value(mi,k).get_path_name() for k in L.get_texture_parameter_names(mi) if L.get_material_instance_texture_parameter_value(mi,k)}}
    record()
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is running; finish remains prepared, assets untouched')
targets=[mesh_root+n for n in ('SM_m249_side_mag_30','SM_m249_side_mag_45','SM_M249_SidePort')]+[D+'/Materials/MI_M249_Surface__'+n for n in ('OldBox','NewBox')]
dirty={a.get_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in targets) or any(p.startswith(D) for p in dirty):raise RuntimeError('Unsaved target assets retained')
for p in targets:
    if hashlib.sha256(disk(p).read_bytes()).hexdigest()!=report['saved'].get(p,inputs['hashes'][p]):raise RuntimeError('Target changed '+p)
if not (r/'Before.zip').exists():
    with zipfile.ZipFile(r/'Before.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in targets:z.write(disk(p),p.removeprefix('/Game/')+'.uasset')
master=clone('/Game/Weapons/M249/SideMagazine20261108/Finish20/M_M249MagazineSurface',D+'/Master/M_M249MagazineSurface29')
# Keep the graph with the M249 WS1 masters. ResolveWet detects its existing
# WeaponWetness parameter; retain that single layer and its source textures.
if E.get_metadata_tag(master,'M249FeedFinish')!='Finish29':
    expr=list(L.get_material_expressions(master));params={str(n.get_editor_property('parameter_name')):n for n in expr if isinstance(n,u.MaterialExpressionTextureSampleParameter2D)}
    uv=node(master,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
    packed=[node(master,u.MaterialExpressionTextureCoordinate,coordinate_index=i) for i in range(2,7)]
    channel=node(master,u.MaterialExpressionComponentMask,r=True,g=False,b=False,a=False);wire(packed[0],'',channel,'')
    enabled=node(master,u.MaterialExpressionScalarParameter,parameter_name='SeamEnabled',default_value=0.)
    weight=node(master,u.MaterialExpressionMultiply);wire(channel,'',weight,'A');wire(enabled,'',weight,'B')
    for key in ('SourceBaseColor','SourceRoughness','SurfaceNormal'):
        sample=params[key];consumers=[]
        for n in expr:
            for source,pin in zip(L.get_inputs_for_material_expression(master,n),L.get_material_expression_input_names(n)):
                if source==sample:
                    output=L.get_input_node_output_name_for_material_expression(n,sample)
                    if isinstance(output,tuple):output=next(x for x in output if isinstance(x,str))
                    consumers.append((n,str(pin),output or 'RGB'))
        alt=node(master,u.MaterialExpressionTextureSampleParameter2D,parameter_name=key,texture=sample.get_editor_property('texture'),sampler_type=sample.get_editor_property('sampler_type'),sampler_source=sample.get_editor_property('sampler_source'))
        wire(uv,'',alt,'UVs')
        if key=='SurfaceNormal':
            rotated=custom(master,'M249 seam tangent conversion','return float3(dot(N,float3(A.g,-B.r,B.g)),dot(N,float3(-C.r,C.g,-D.r)),dot(N,float3(D.g,-E.r,E.g)));',dict(N=(alt,'RGB'),**{k:(v,'') for k,v in zip('ABCDE',packed)}))
            blend=custom(master,'M249 seam normal continuity','return normalize(lerp(N0,N1,W));',{'N0':(sample,'RGB'),'N1':(rotated,''),'W':(weight,'')})
        else:
            blend=node(master,u.MaterialExpressionLinearInterpolate);wire(sample,'RGB',blend,'A');wire(alt,'RGB',blend,'B');wire(weight,'',blend,'Alpha')
        for n,pin,output in consumers:
            if output in ('R','G','B'):
                mask=node(master,u.MaterialExpressionComponentMask,r=output=='R',g=output=='G',b=output=='B',a=False);wire(blend,'',mask,'');wire(mask,'',n,pin)
            elif output in ('','RGB'):wire(blend,'',n,pin)
            else:raise RuntimeError('Unexpected source channel '+output)
    E.set_metadata_tag(master,'M249FeedFinish','Finish29')
for k in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):master.set_editor_property(k,False)
errors=list(L.recompile_material(master) or [])
if errors:raise RuntimeError('Shader compilation '+str(errors))
save(master)
receiver=inputs['materials'][D+'/Materials/MI_M249_Factory_Receiver.MI_M249_Factory_Receiver']
shared={k:receiver['scalars'][k] for k in ('Specular','GrainTileCm','GrainRoughness','MottleRoughness','MottleColor','CavityDarken','CavityRoughness','EdgeHighlight','AOStrength')}
bindings={}
for capacity in (30,45):
    mi=clone('/Game/Weapons/M249/SideMagazine20261108/Finish20/MI_M249_Magazine',D+'/Materials/MI_M249_SideMagazine'+str(capacity)+'_29')
    L.set_material_instance_parent(mi,master)
    apply(mi,dict(shared,Metallic=0.,EdgeMetallic=0.,Roughness=receiver['scalars']['PolymerRoughness'],SourceColorWeight=.06,SourceRoughnessWeight=.08,Stipple=0.,EdgeWear=0.,EdgeBreakup=0.,ScratchAmount=0.,HandlingPolish=0.,RainSurfaceResponse=3.,SeamEnabled=float(capacity==45)),{'FinishColor':receiver['vectors']['PolymerColor']})
    bindings[mesh_root+'SM_m249_side_mag_'+str(capacity)]=mi
port=clone('/Game/Weapons/M249/SideMagazine20261108/Finish20/MI_M249_Port',D+'/Materials/MI_M249_SidePort29')
L.set_material_instance_parent(port,load(D+'/Master/M_M249RailSurface'))
apply(port,dict(shared,**{k:receiver['scalars'][k] for k in ('Roughness','Metallic','EdgeWear','EdgeBreakup','EdgeContrast','EdgeRoughness','EdgeMetallic','ScratchAmount','HandlingPolish')},SourceColorWeight=0.,SourceRoughnessWeight=0.,RainSurfaceResponse=1.),{k:receiver['vectors'][k] for k in ('FinishColor','EdgeColor')})
bindings[mesh_root+'SM_M249_SidePort']=port
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report['uv_channels']={}
for p,mi in bindings.items():
    m=load(p)
    report['uv_channels'][p]=sub.get_num_uv_channels(m,0)
    if p.endswith('_45') and report['uv_channels'][p]<7:raise RuntimeError('45-round seam UV channels missing; mesh retained')
    for i in range(len(m.static_materials)):m.set_material(i,mi)
    save(m);report['bindings'][p]=[s.material_interface.get_path_name() for s in m.static_materials]
for suffix in ('OldBox','NewBox'):
    mi=load(D+'/Materials/MI_M249_Surface__'+suffix)
    apply(mi,{k:receiver['scalars'][k] for k in ('GrainTileCm','GrainRoughness','MottleRoughness')}|{'RainSurfaceResponse':0.},{})
report.update(complete=True,runtime_visual_tested=False,animations_changed=False,polymer_metallic=0.,weather='Existing WeaponWetness parameter detection; mixed boxes use authored metalness',seams='UV1 alternate sampling; UV2-6 tangent conversion; only 45-round enables blending')
record();print('M249_FINISH29_SAVED',len(report['saved']),flush=True)
