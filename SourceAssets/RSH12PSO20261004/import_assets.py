"""Import the rail-mounted PSO without altering the source rifle assets."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/RSH12/PSO20261004'
C=json.loads((O/'inputs.json').read_text());S=json.loads((O/'authoring.json').read_text())
F=json.loads((O.parent/'RSH12Optics20261004/finish_reference.json').read_text())
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt=dict(saved=[],complete=False,runtime_tested=False)
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing PSO input '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record()
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,dst,pin):
    n,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(n,out,dst,pin):raise RuntimeError('Connection '+pin)
def custom(m,label,code,inputs,size):
    n=node(m,u.MaterialExpressionCustom,description=label,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    pins=[]
    for k in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
    n.set_editor_property('inputs',pins)
    for k,v in inputs.items():wire(v,n,k)
    return n
def output(m,prop):
    p=getattr(u.MaterialProperty,'MP_'+prop);n=L.get_material_property_input_node(m,p)
    return n,str(L.get_material_property_input_node_output_name(m,p))
def input_of(m,n,pin):
    names=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]
    src=L.get_inputs_for_material_expression(m,n)[names.index(pin)]
    return src,str(L.get_input_node_output_name_for_material_expression(n,src))

source=next(s['material'] for s in C['meshes']['pso1_4x']['slots'] if 'Shell' in s['slot'])
wet_source=C['weather'][source];path=D+'/Materials/M_RSH12_PSO_Shell'
shell=load(path) if E.does_asset_exist(path) else E.duplicate_asset(wet_source,path)
if not shell:raise RuntimeError('Cannot copy PSO shell')
if E.get_metadata_tag(shell,'RSHPSOFinish')!='20261004':
    color_wet=output(shell,'BASE_COLOR')[0];rough_wet=output(shell,'ROUGHNESS')[0]
    color=input_of(shell,color_wet,'Base');rough=input_of(shell,rough_wet,'Base');metal=output(shell,'METALLIC')
    exterior=node(shell,u.MaterialExpressionTextureSample,texture=load('/Game/Weapons/PSO1Russian20260923/MatteFinish20260923/Textures/T_PSO_ExteriorMask'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    tint=node(shell,u.MaterialExpressionVectorParameter,parameter_name='RSH_FinishColor',default_value=u.LinearColor(*F['base_color'],1.))
    center=node(shell,u.MaterialExpressionScalarParameter,parameter_name='RSH_Roughness',default_value=F['roughness'][0])
    protect='float lum=dot(Colour,float3(.2126,.7152,.0722));float chroma=(max(Colour.r,max(Colour.g,Colour.b))-min(Colour.r,min(Colour.g,Colour.b)))/max(lum,.015);float w=saturate(Region)*smoothstep(.45,.85,Metal)*smoothstep(.002,.010,lum)*(1-smoothstep(.45,.95,chroma));'
    color_new=custom(shell,'RSH PSO exterior steel',protect+'float3 finish=Tint*pow(max(Colour,float3(.0001,.0001,.0001))/.058,.58);return lerp(Colour,finish,w*(1-smoothstep(.12,.32,lum)));',{'Colour':color,'Metal':metal,'Region':(exterior,'R'),'Tint':(tint,'RGB')},3)
    rough_new=custom(shell,'RSH PSO exterior roughness',protect+'return lerp(Base,clamp(Center+(Base-.5)*.28,.20,.85),w);',{'Colour':color,'Metal':metal,'Region':(exterior,'R'),'Center':center,'Base':rough},1)
    wire(color_new,color_wet,'Base');wire(rough_new,rough_wet,'Base')
    # Use the existing authored exterior mask on seam faces too, retaining one wet layer.
    for n in L.get_material_expressions(shell):
        if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='PSO exterior wetness':wire((exterior,'R'),n,'Region')
    E.set_metadata_tag(shell,'RSHPSOFinish','20261004')
for k in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):shell.set_editor_property(k,False)
errors=L.recompile_material(shell)
if errors:raise RuntimeError('PSO material compile '+str(errors))
save(shell)
mount=load('/Game/Weapons/RSH12/Optics20261004/Materials/MI_RSH12_RailSteel')
glass=load(next(s['material'] for s in C['meshes']['pso1_4x']['slots'] if 'OpticalGlass' in s['slot']))
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    task=u.AssetImportTask();task.filename=S['fbx'];task.destination_path=D+'/Meshes';task.destination_name='SM_RSH12_PSO1'
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=opt
    A.import_asset_tasks([task]);mesh=load(D+'/Meshes/SM_RSH12_PSO1');slots=list(mesh.static_materials)
    for i,s in enumerate(slots):
        name=str(s.material_slot_name)
        if 'Shell' in name:s.material_interface=shell
        elif 'OpticalGlass' in name:s.material_interface=glass
        elif 'MountSteel' in name:s.material_interface=mount
        else:raise RuntimeError('Unmapped PSO slot '+name)
        slots[i]=s
    mesh.set_editor_property('static_materials',slots)
    for name,p in S['sockets_cm'].items():
        socket=mesh.find_socket(name)
        if not socket:
            socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
        socket.set_editor_property('relative_location',u.Vector(*p))
    E.set_metadata_tag(mesh,'SourceAttribution','PSO-1 from SVD Dragunov by LeroyCake / CC BY 4.0. FPSGAME repaired UV/opaque seam partition; RSH private rail shoe, closed foot, steel finish and ADS frame.')
    E.set_metadata_tag(mesh,'RSHPSOMount','Fixed WPN_root, RSH common rail saddle, source optic size retained')
    save(mesh);receipt['mesh']=mesh.get_path_name();receipt['sockets_cm']=S['sockets_cm']
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
table=load('/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials')
backup=O/'Before/DA_RSH12_WetMaterials.uasset';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(P/'Content/Weapons/RSH12/Materials/DA_RSH12_WetMaterials.uasset',backup)
mapping=dict(table.get_editor_property('wet_materials'));mapping[shell.get_path_name()]=shell;table.set_editor_property('wet_materials',mapping);save(table)
receipt['complete']=True;record();print('RSH_PSO_IMPORTED_AND_SAVED',mesh.get_path_name(),flush=True)
