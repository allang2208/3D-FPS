"""Import only the owned timber revision. No map load, PIE, render or global save."""
import unreal as u, json
from pathlib import Path
ROOT=Path(__file__).parent;OUT=ROOT/'Delivery';DEST='/Game/Items/HarvestTimber'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
E.make_directory(DEST);report={}

def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
def asset(name,cls,factory):
    return u.load_asset(DEST+'/'+name) or A.create_asset(name,DEST,cls,factory)
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,out,b,pin):
    names=list(map(str,L.get_material_expression_input_names(b)))
    if pin not in names and pin in ('Coordinates','Input') and names:pin=names[0]
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def output(n,out,p):
    if not L.connect_material_property(n,out,p):raise RuntimeError('Cannot connect '+str(p))
def scalar(mat,name,value):return node(mat,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def custom(mat,code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    n=node(mat,u.MaterialExpressionCustom,code=code,output_type=kind,inputs=pins)
    for k,(src,pin) in inputs.items():link(src,pin,n,k)
    return n
def import_file(path,name,options=None):
    t=u.AssetImportTask();t.filename=str(path);t.destination_path=DEST;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False
    if options:t.options=options
    A.import_asset_tasks([t]);obj=u.load_asset(DEST+'/'+name)
    if obj is None:raise RuntimeError('Import failed '+name)
    return obj

reference=import_file(ROOT/'cut_surface_reference.png','T_PoplarEndReference')
reference.srgb=True;save(reference)
cap=asset('M_PoplarEnd',u.Material,u.MaterialFactoryNew())
for old in list(L.get_material_expressions(cap)):L.delete_material_expression(cap,old)
cap.set_editor_property('two_sided',True);cap.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
uv=node(cap,u.MaterialExpressionTextureCoordinate)
crop=custom(cap,'return UV*float2(.28,.56)+float2(.65,.27);',{'UV':(uv,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
tex=node(cap,u.MaterialExpressionTextureSample,texture=reference);link(crop,'',tex,'Coordinates')
output(tex,'RGB',u.MaterialProperty.MP_BASE_COLOR)
rough=node(cap,u.MaterialExpressionConstant,r=.82);output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
fade=scalar(cap,'HarvestFade',1)
mask=custom(cap,'return step(frac(sin(dot(UV,float2(127.1,311.7)))*43758.5453),Fade);',{'UV':(uv,''),'Fade':(fade,'')})
output(mask,'',u.MaterialProperty.MP_OPACITY_MASK);L.recompile_material(cap);save(cap)

source=u.load_asset('/Game/WorldGeneration/TemperateHills/MI_BlackPoplarPCG_Bark')
if source is None:raise RuntimeError('Missing existing poplar bark material')
master_path=DEST+'/M_FallingPoplar'
master=u.load_asset(master_path)
if master is None:
    master=E.duplicate_asset(source.get_base_material().get_path_name(),master_path)
    report['source_uses_attributes']=master.get_editor_property('use_material_attributes')
    attribute_set=None
    if report['source_uses_attributes']:
        # Preserve the complete existing attributes (including foliage transmission).
        attributes=L.get_material_property_input_node(master,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        attributes_output=L.get_material_property_input_node_output_name(master,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        # Fixed Break outputs are available without an open material-editor graph.
        getter=node(master,u.MaterialExpressionBreakMaterialAttributes)
        link(attributes,attributes_output,getter,'Input')
        outputs=list(map(str,L.get_material_expression_output_names(getter)))
        original_mask=getter;mask_output=next(p for p in outputs if p.replace(' ','')=='OpacityMask')
        source_wpo=getter;source_output=next(p for p in outputs if p.replace(' ','')=='WorldPositionOffset')
        attribute_set=node(master,u.MaterialExpressionSetMaterialAttributes)
        # UE Python cannot access the protected Inputs array. The native bridge
        # creates both pins through the engine API, without a material editor.
        if not u.TimberAssetEditor.prepare_fall_attribute_inputs(attribute_set):
            raise RuntimeError('Cannot create falling-tree attribute inputs')
        attribute_inputs=list(map(str,L.get_material_expression_input_names(attribute_set)))
        link(attributes,attributes_output,attribute_set,attribute_inputs[0])
    else:
        original_mask=L.get_material_property_input_node(master,u.MaterialProperty.MP_OPACITY_MASK)
        mask_output=L.get_material_property_input_node_output_name(master,u.MaterialProperty.MP_OPACITY_MASK)
        source_wpo=L.get_material_property_input_node(master,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        source_output=L.get_material_property_input_node_output_name(master,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    if original_mask is None:original_mask=node(master,u.MaterialExpressionConstant,r=1);mask_output=''
    position=node(master,u.MaterialExpressionPreSkinnedPosition)
    interpolated=node(master,u.MaterialExpressionVertexInterpolator);link(position,'',interpolated,'Input')
    height=scalar(master,'HarvestCutHeight',42);fade=scalar(master,'HarvestFade',1)
    clipped=custom(master,'return O*step(H,P.z)*step(frac(sin(dot(P,float3(12.9898,78.233,37.719)))*43758.5453),F);',
        {'O':(original_mask,mask_output),'P':(interpolated,''),'H':(height,''),'F':(fade,'')})
    if attribute_set:link(clipped,'',attribute_set,attribute_inputs[1])
    else:output(clipped,'',u.MaterialProperty.MP_OPACITY_MASK)
    tree_height=scalar(master,'HarvestTreeHeight',3000)
    bend=node(master,u.MaterialExpressionVectorParameter,parameter_name='HarvestCrownBend',default_value=u.LinearColor(0,0,0,0))
    local_bend=custom(master,'return Bend*pow(saturate((P.z-42)/max(Height-42,1)),2);',
        {'Bend':(bend,'RGB'),'P':(position,''),'Height':(tree_height,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    world_bend=node(master,u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    link(local_bend,'',world_bend,'Input')
    if source_wpo:
        add=node(master,u.MaterialExpressionAdd);link(source_wpo,source_output,add,'A');link(world_bend,'',add,'B');world_bend=add
    if attribute_set:
        link(world_bend,'',attribute_set,attribute_inputs[2]);output(attribute_set,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
    else:output(world_bend,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    master.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    master.set_editor_property('used_with_skeletal_mesh',True)
    master.set_editor_property('max_world_position_offset_displacement',90)
    L.recompile_material(master);save(master)
for kind in ('Bark','Foliage'):
    original='/Game/WorldGeneration/TemperateHills/MI_BlackPoplarPCG_'+kind
    path=DEST+'/MI_FallingPoplar_'+kind
    mi=u.load_asset(path) or E.duplicate_asset(original,path)
    L.set_material_instance_parent(mi,master);save(mi)

atten=asset('SA_Timber',u.SoundAttenuation,u.SoundAttenuationFactory())
settings=atten.get_editor_property('attenuation')
settings.set_editor_property('attenuate',True);settings.set_editor_property('spatialize',True)
settings.set_editor_property('attenuation_shape_extents',u.Vector(250,0,0));settings.set_editor_property('falloff_distance',2400)
atten.set_editor_property('attenuation',settings);save(atten)
for name in ('S_TreeCrack','S_TreeLanding'):
    sound=import_file(OUT/(name+'.wav'),name);sound.set_editor_property('attenuation_settings',atten);save(sound)

if (OUT/'authoring.json').exists():
    author=json.loads((OUT/'authoring.json').read_text());textures={}
    for kind,filename in author['textures'].items():
        texture=import_file(OUT/filename,'T_Poplar_'+kind)
        texture.srgb=kind=='BaseColor'
        if kind=='Normal':
            texture.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
            texture.set_editor_property('flip_green_channel',True)
        elif kind=='ORM':texture.compression_settings=u.TextureCompressionSettings.TC_MASKS
        save(texture);textures[kind]=texture
    bark=asset('M_PoplarBark',u.Material,u.MaterialFactoryNew())
    for old in list(L.get_material_expressions(bark)):L.delete_material_expression(bark,old)
    for kind,prop,pin in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR,'RGB'),('ORM',u.MaterialProperty.MP_ROUGHNESS,'G'),('Normal',u.MaterialProperty.MP_NORMAL,'RGB')]:
        if kind in textures:
            tex=node(bark,u.MaterialExpressionTextureSample,texture=textures[kind])
            if kind=='Normal':tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            elif kind=='ORM':tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            output(tex,pin,prop)
    if 'ORM' not in textures:output(node(bark,u.MaterialExpressionConstant,r=.85),'',u.MaterialProperty.MP_ROUGHNESS)
    L.recompile_material(bark);save(bark)
    for name in author['meshes']:
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_materials=False;options.import_textures=False;options.import_animations=False
        options.static_mesh_import_data.set_editor_property('combine_meshes',True)
        mesh=import_file(OUT/(name+'.fbx'),name,options)
        slots=mesh.get_editor_property('static_materials')
        for index,slot in enumerate(slots):
            slot.material_interface=cap if 'EndGrain' in str(slot.material_slot_name) else bark;slots[index]=slot
        mesh.set_editor_property('static_materials',slots);save(mesh)
        report[name]={'path':mesh.get_path_name(),'bounds':str(mesh.get_bounds()),'slots':[str(s.material_slot_name) for s in slots]}
(ROOT/'import.json').write_text(json.dumps(report,indent=2))
u.log('HARVEST_TIMBER_IMPORT_COMPLETE meshes='+str(sum(name.startswith('SM_') for name in report)))
