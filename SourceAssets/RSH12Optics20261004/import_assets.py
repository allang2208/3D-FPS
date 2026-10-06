"""Save RSH common-optic variants, measured saddles and private surface adapters.

Runs in the background authoring commandlet. No game/preview/render tests.
"""
import json,shutil,runpy
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/RSH12/Optics20261004'
C=json.loads((O/'inputs.json').read_text());M=json.loads((O/'mounts.json').read_text())
F=json.loads((O/'finish_reference.json').read_text());E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt=dict(saved=[],meshes={},materials={},complete=False,runtime_tested=False)
wet_materials={}
compact_import=O.parent/'RSH12CompactOptics20261004/import_assets.py'
has_compact_revision=(compact_import.parent/'authoring.json').exists()

def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing authoring dependency '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record();return a
def clone(source,path):
    a=load(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)
    if not a:raise RuntimeError('Cannot duplicate '+source)
    return a
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,dst,pin):
    n,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(n,out,dst,pin):raise RuntimeError('Cannot connect '+pin)
def custom(m,label,code,inputs,size):
    n=node(m,u.MaterialExpressionCustom,description=label,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    pins=[]
    for k in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
    n.set_editor_property('inputs',pins)
    for k,v in inputs.items():wire(v,n,k)
    return n
def source_output(m,prop):
    n=L.get_material_property_input_node(m,prop)
    if not n:raise RuntimeError('Missing material source '+str(prop))
    return n,str(L.get_material_property_input_node_output_name(m,prop))
def input_of(m,n,pin):
    names=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]
    src=L.get_inputs_for_material_expression(m,n)[names.index(pin)]
    return src,str(L.get_input_node_output_name_for_material_expression(n,src))
def static_master(m):
    for key in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):m.set_editor_property(key,False)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compile '+m.get_path_name()+': '+str(errors))
    save(m)
def instance(path,parent,source=None):
    if source:mi=clone(source,path)
    elif E.does_asset_exist(path):mi=load(path)
    else:
        folder,name=path.rsplit('/',1);mi=A.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,parent)
    return mi

def finish_body(key,source):
    mat=load(source);graph=clone(mat.get_base_material().get_path_name(),D+'/Materials/M_RSH12_'+key)
    if key=='eoth_holographic' and E.get_metadata_tag(graph,'RSHOpticFinish')!='20261004':
        # Fit the dry steel response before the existing single rain layer.
        color_wet=source_output(graph,u.MaterialProperty.MP_BASE_COLOR)[0]
        rough_wet=source_output(graph,u.MaterialProperty.MP_ROUGHNESS)[0]
        color=input_of(graph,color_wet,'Base');rough=input_of(graph,rough_wet,'Base')
        metal=source_output(graph,u.MaterialProperty.MP_METALLIC)
        tint=node(graph,u.MaterialExpressionVectorParameter,parameter_name='RSH_FinishColor',default_value=u.LinearColor(*F['base_color'],1.))
        center=node(graph,u.MaterialExpressionScalarParameter,parameter_name='RSH_Roughness',default_value=F['roughness'][0])
        protection='float lum=dot(Colour,float3(.2126,.7152,.0722));float chroma=(max(Colour.r,max(Colour.g,Colour.b))-min(Colour.r,min(Colour.g,Colour.b)))/max(lum,.015);float w=smoothstep(.45,.85,Metal)*smoothstep(.002,.010,lum)*(1-smoothstep(.45,.95,chroma));'
        col=custom(graph,'RSH optic steel colour',protection+'float wear=smoothstep(.12,.32,lum);float3 finish=Tint*pow(max(Colour,float3(.0001,.0001,.0001))/.058,.58);return lerp(Colour,finish,w*(1-wear));',{'Colour':color,'Metal':metal,'Tint':(tint,'RGB')},3)
        r=custom(graph,'RSH optic steel roughness',protection+'float finish=clamp(Center+(Base.r-.5)*.28,.20,.85);return lerp(Base.r,finish,w);',{'Colour':color,'Metal':metal,'Base':rough,'Center':center},1)
        wire(col,color_wet,'Base');wire(r,rough_wet,'Base')
    E.set_metadata_tag(graph,'RSHOpticFinish','20261004');static_master(graph)
    mi=instance(D+'/Materials/MI_RSH12_'+key,graph,source if isinstance(mat,u.MaterialInstanceConstant) else None)
    if key!='eoth_holographic':
        # The accepted optic graph already masks rubber, markings and the dark bore.
        L.set_material_instance_vector_parameter_value(mi,'R01_ToneScale',u.LinearColor(*[c/.058 for c in F['base_color']],1.))
        L.set_material_instance_scalar_parameter_value(mi,'R01_Roughness',F['roughness'][0])
        L.set_material_instance_scalar_parameter_value(mi,'R01_Grain',.004)
        L.set_material_instance_scalar_parameter_value(mi,'R01_Variation',.002)
    L.set_material_instance_scalar_parameter_value(mi,'WeaponWetness',0.)
    L.update_material_instance(mi);E.set_metadata_tag(mi,'WeaponFinishReference','/Game/Weapons/RSH12/Materials/MI_RSH12_SourcePBR; upper rail UV0 source PBR')
    save(mi);wet_materials[mi.get_path_name()]=mi;receipt['materials'][key]=dict(asset=mi.get_path_name(),source=source)
    return mi

# A private static version of the common surface graph is used only by new clamps.
mount_graph=clone('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',D+'/Materials/M_RSH12_RailSteel')
static_master(mount_graph)
mount_material=instance(D+'/Materials/MI_RSH12_RailSteel',mount_graph)
for key,value in dict(SourceColorWeight=0.,SourceRoughnessWeight=0.,Roughness=F['roughness'][0],Metallic=F['metallic'][0],GrainTileCm=4.,GrainRoughness=.004,MottleRoughness=.002,MottleColor=0.,Stipple=0.,EdgeWear=0.,EdgeHighlight=0.,CavityDarken=0.,CavityRoughness=0.,HandlingPolish=0.,ScratchAmount=0.,WeaponWetness=0.,BeadScale=78.).items():L.set_material_instance_scalar_parameter_value(mount_material,key,value)
L.set_material_instance_vector_parameter_value(mount_material,'FinishColor',u.LinearColor(*F['base_color'],1.))
L.update_material_instance(mount_material);save(mount_material);wet_materials[mount_material.get_path_name()]=mount_material

def socket(mesh,name,p):
    s=mesh.find_socket(name)
    if not s:
        s=u.new_object(u.StaticMeshSocket,outer=mesh);s.set_editor_property('socket_name',name);mesh.add_socket(s)
    s.set_editor_property('relative_location',u.Vector(*p))

centers={'holographic':[-.653782,0,5.175324],'panoramic_red_dot':[2.125,0,3.25],'prism_scope_2x':[-6.15,0,4.],'lpvo_1_6x':[-12.15,0,4.]}
for key,info in C['meshes'].items():
    if has_compact_revision and key in ('holographic','eoth_holographic'):continue
    mesh=clone(info['source'],D+'/Meshes/SM_RSH12_'+key);slots=list(mesh.static_materials)
    for i,s in enumerate(slots):
        label=str(s.material_slot_name).lower()
        if any(p in label for p in ('reticle','glass','red_dot')):continue
        s.material_interface=finish_body(key,info['slots'][i]['material']);slots[i]=s
    mesh.set_editor_property('static_materials',slots)
    if key in centers:
        r=centers[key];socket(mesh,'AimCenter',r);socket(mesh,'SightRear',r)
        socket(mesh,'SightFront',[r[0]+10,r[1],r[2]]);socket(mesh,'SightUp',[r[0],r[1],r[2]+1])
    if key=='lpvo_1_6x':socket(mesh,'ZoomRing',[-7.1,0,4.])
    E.set_metadata_tag(mesh,'RSHOpticSource',info['source']);E.set_metadata_tag(mesh,'RSHOpticRail','Measured 2_l upper rail, fixed WPN_root frame; source size and UVs retained')
    save(mesh);receipt['meshes'][key]=dict(asset=mesh.get_path_name(),source=info['source'],materials={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots})

flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,info in M['parts'].items():
        if has_compact_revision and key in ('holographic','eoth_holographic'):continue
        task=u.AssetImportTask();task.filename=info['fbx'];task.destination_path=D+'/Meshes';task.destination_name=info['name']
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory()
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;task.options=opt
        A.import_asset_tasks([task]);mesh=load(D+'/Meshes/'+info['name']);slots=list(mesh.static_materials)
        for s in slots:s.material_interface=mount_material
        mesh.set_editor_property('static_materials',slots)
        E.set_metadata_tag(mesh,'SourceAttribution','Original RSH rail adapter geometry authored for FPSGAME; fit to Rsh-12 by Medji (CC BY 4.0).')
        save(mesh);receipt['meshes']['rail_'+key]=dict(asset=mesh.get_path_name(),fbx=info['fbx'],body_offset_cm=info['body_offset_cm'])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))

# Merge only these new materials into the existing per-RSH rain registration.
wet_path='/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials';table=load(wet_path)
disk=P/'Content/Weapons/RSH12/Materials/DA_RSH12_WetMaterials.uasset';backup=O/'Before/DA_RSH12_WetMaterials.uasset';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(disk,backup)
mapping=dict(table.get_editor_property('wet_materials'));mapping.update(wet_materials);table.set_editor_property('wet_materials',mapping);save(table)
receipt['weather']={k:v.get_path_name() for k,v in wet_materials.items()};receipt['complete']=True;record()
if has_compact_revision:runpy.run_path(str(compact_import),run_name='__main__')
print('RSH_OPTICS_IMPORTED_AND_SAVED',len(receipt['meshes']),len(receipt['saved']),flush=True)
