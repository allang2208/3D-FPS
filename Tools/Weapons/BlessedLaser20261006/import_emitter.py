"""Import and save the approved blessed emitter models and shared PBR materials."""
import json
import re
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parents[3]
O=P/'SourceAssets/BlessedLaser20261006/Model'
D='/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report={'saved':[],'models':{},'materials':{},'game_tested':False}
receipt=O/'import-receipt.json'


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')


def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n


def wire(source,target,pin,output=''):
    if not L.connect_material_expressions(source,output,target,pin):raise RuntimeError('Material connection failed: '+pin)


def prop(source,property):
    if not L.connect_material_property(source,'',property):raise RuntimeError('Material output failed')


def custom(mat,code,sources,kind):
    n=node(mat,u.MaterialExpressionCustom,code=code,output_type=kind)
    pins=[]
    for name in sources:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,source in sources.items():wire(source,n,name)
    return n


materials={}
for key,color,metal,rough in [
    ('Blessed_Graphite',(.045,.051,.06),.8,.34),
    ('Blessed_Gold',(.68,.43,.14),.92,.25),
    ('Blessed_Black',(.009,.011,.014),.25,.50),
    ('Blessed_Optic',(.19,.064,.004),.72,.16),
    ('Blessed_Aperture',(1,.32,.004),.15,.22),
]:
    name='M_'+key
    path=D+'/Materials/'+name
    m=u.find_object(None,path+'.'+name) or u.load_object(None,path+'.'+name)
    if m is None:m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    if m is None:raise RuntimeError('Unable to create or load material '+path)
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('two_sided',False)
    base=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1))
    wet=node(m,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
    uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    # Filter the tiny satin grain rather than shimmer at distance. Physical UV
    # tiling comes from the authored surface; each material retains its identity.
    grain=custom(m,'float2 q=UV*420.0; float footprint=max(length(ddx(q)),length(ddy(q))); float n=frac(sin(dot(floor(q),float2(12.9898,78.233)))*43758.5453); return (n-.5)*saturate(1.0-footprint);',{'UV':uv},u.CustomMaterialOutputType.CMOT_FLOAT1)
    color_node=custom(m,'return Base*(1.0-saturate(Wet)*.12)*(1.0+Grain*.055);',{'Base':base,'Wet':wet,'Grain':grain},u.CustomMaterialOutputType.CMOT_FLOAT3)
    prop(color_node,u.MaterialProperty.MP_BASE_COLOR)
    r=node(m,u.MaterialExpressionConstant,r=rough)
    rough_node=custom(m,'return clamp(lerp(Rough,max(.10,Rough*.6),saturate(Wet))+Grain*.035,.08,1.0);',{'Rough':r,'Wet':wet,'Grain':grain},u.CustomMaterialOutputType.CMOT_FLOAT1)
    prop(rough_node,u.MaterialProperty.MP_ROUGHNESS)
    prop(node(m,u.MaterialExpressionConstant,r=metal),u.MaterialProperty.MP_METALLIC)
    prop(node(m,u.MaterialExpressionConstant,r=.5),u.MaterialProperty.MP_SPECULAR)
    if key=='Blessed_Aperture':
        emission=node(m,u.MaterialExpressionMultiply,const_b=2.2)
        wire(base,emission,'A')
        exposure=node(m,u.MaterialExpressionEyeAdaptationInverse)
        light_pin=next(p for p in L.get_material_expression_input_names(exposure) if 'LightValue' in p)
        wire(emission,exposure,light_pin)
        prop(exposure,u.MaterialProperty.MP_EMISSIVE_COLOR)
    E.set_metadata_tag(m,'BlessedEmitter','Approved concept 01; solid PBR shell; only the separate aperture emits')
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    save(m);materials[key]=m;report['materials'][key]=m.get_path_name()

auth=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
entries={'Master':{'fbx':str(O/'Exports/SM_BlessedLaser_Master.fbx'),'retained_materials':{},'sockets_ue_cm':{'Emitter':[0,0,0],'AimGuide':[3,0,0]}}}
entries.update(auth)
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for family,entry in entries.items():
        name='SM_BlessedLaser_'+family
        options=u.FbxImportUI()
        options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
        options.override_full_name=True
        data=options.static_mesh_import_data
        data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=D+'/Models';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
        A.import_asset_tasks([task])
        mesh=u.load_asset(D+'/Models/'+name)
        if mesh is None:raise RuntimeError('Model import failed: '+family)
        slots=list(mesh.static_materials)
        bindings={}
        for i,slot in enumerate(slots):
            label=str(slot.material_slot_name)
            clean=re.sub(r'[._]\d{3}$','',label)
            key=next((k for k in materials if clean==k),None)
            if key:mat=materials[key]
            else:
                oldkey=next((k for k in entry['retained_materials'] if re.sub(r'[._]\d{3}$','',k)==clean),None)
                if oldkey is None:raise RuntimeError('Missing contact material binding: '+family+'/'+label)
                mat=u.load_asset(entry['retained_materials'][oldkey])
            if mat is None:raise RuntimeError('Unavailable material '+label)
            slot.material_interface=mat;slots[i]=slot;bindings[label]=mat.get_path_name()
        mesh.set_editor_property('static_materials',slots)
        for socket_name,position in entry['sockets_ue_cm'].items():
            socket=mesh.find_socket(socket_name)
            if socket is None:
                socket=u.StaticMeshSocket(outer=mesh)
                socket.set_editor_property('socket_name',socket_name)
                mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*position))
        E.set_metadata_tag(mesh,'BlessedEmitterModel','concept-01-hard-surface-mount-v'+str(entry.get('mount_revision',1)))
        E.set_metadata_tag(mesh,'Source',str(O/'BlessedLaser_Master.blend'))
        E.set_metadata_tag(mesh,'MountSource',entry.get('source','canonical'))
        save(mesh)
        report['models'][family]={'path':mesh.get_path_name(),'materials':bindings,'sockets_ue_cm':entry['sockets_ue_cm'],'source':entry['fbx']}
        receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))

# These new materials handle WeaponWetness directly; default weather discovery
# creates its usual bounded dynamic instances without a new per-frame loader.
for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library=u.load_asset(path)
    mapping=dict(library.get_editor_property('wet_materials'))
    mapping.update({m.get_path_name():m for m in materials.values()})
    library.set_editor_property('wet_materials',mapping)
    save(library)
report['status']='models_materials_and_weather_bindings_saved'
receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BLESSED_EMITTER_MODELS_SAVED '+json.dumps({'models':len(report['models']),'materials':len(materials),'receipt':str(receipt)}))
