"""Fit accepted tactical-device bodies to ASH using the live Vibe3D service.

Only task-owned meshes/materials are created. No actors, PIE or preview renders.
Local centimetres: X forward, Y outboard, Z up. Runtime places this at the
measured ASH sight-frame coordinate (29.5, -3.19, -8.25) cm, with a 180-degree
local X rotation to seat the clamp on the left rail at unchanged scale.
"""
import json,math
from pathlib import Path
import unreal as u

O=Path(__file__).resolve().parent
D='/Game/Weapons/ASH12/TacticalDevices20260920'
S=u.ModelingService;A=u.AssetToolsHelpers.get_asset_tools()
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
handles=[];receipt={'tested':False,'mount_sight_cm':[29.5,-3.19,-8.25],'mount_roll_degrees':180,'parts':{}}

def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing source '+path)
    return obj

def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outer()],False):
        raise RuntimeError('Save failed '+obj.get_path_name())

def ok(result):
    if not result.success:raise RuntimeError(str(result.message))
    return result

def mesh():
    h=ok(S.create_mesh()).handle;handles.append(h);return h

def tr(location=(0,0,0),rotation=None,scale=(1,1,1)):
    return u.Transform(location=u.Vector(*location),rotation=(rotation or u.Quat(0,0,0,1)).rotator(),scale=u.Vector(*scale))

ID=tr()
BODY_TRANSFORM=tr((-32.,.6-2.7616973638534548,7.8),u.Quat(math.sqrt(.5),math.sqrt(.5),0,0))

def fitted(p):
    return u.Vector(p.y-32.,p.x+.6-2.7616973638534548,7.8-p.z)

def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n

def wire(src,n,pin):
    x,out=src if isinstance(src,tuple) else (src,'')
    if pin=='Input':
        names=list(map(str,L.get_material_expression_input_names(n)))
        if pin not in names:pin=names[0]
    if not L.connect_material_expressions(x,out,n,pin):raise RuntimeError('Connect '+pin)

def output(src,prop):
    x,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_property(x,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Output '+prop)

def custom(m,code,inputs,size,label):
    n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)),description=label)
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,src in inputs.items():wire(src,n,name)
    return n

def sample(m,path,uv=0,normal=False,masks=False):
    sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_MASKS if masks else u.MaterialSamplerType.SAMPLERTYPE_COLOR
    n=node(m,u.MaterialExpressionTextureSample,texture=load(path),sampler_type=sampler)
    wire(node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=uv),n,'UVs')
    return n

def body_material(kind,emitter):
    name='M_ASH12_'+kind+'_Body';folder=D+'/Materials'
    m=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    prefix='/Game/Weapons/TacticalDevices20260913'+('/HunyuanV3' if kind=='flashlight' else '')+'/Textures/T_'+kind+'_'
    color=sample(m,prefix+'BaseColor');mr=sample(m,prefix+'MetalRough',masks=True)
    coat=sample(m,'/Game/Weapons/ASH12/UniversalAttachments20260919/Textures/T_ASH12_AttachmentCoat_ORM',uv=1,masks=True)
    vertex=node(m,u.MaterialExpressionVertexColor)
    position=node(m,u.MaterialExpressionTransformPosition,
        transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
        transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    wire(node(m,u.MaterialExpressionWorldPosition),position,'Input')
    # Generated optical pixels are retained only on the physical front lens;
    # tail caps and the remainder of the housing use the ASH metal response.
    mask=custom(m,'return P.x < Front-0.65 ? 1.0 : saturate(Region);',
        {'P':position,'Front':node(m,u.MaterialExpressionConstant,r=emitter.x),'Region':(vertex,'R')},1,'ASH housing / front lens mask')
    output(custom(m,'return lerp(Base,float3(.09,.095,.103),Mask);',{'Base':(color,'RGB'),'Mask':mask},3,'ASH receiver black metal'),'BASE_COLOR')
    output(custom(m,'return lerp(Base,Coat,Mask);',{'Base':(mr,'G'),'Coat':(coat,'G'),'Mask':mask},1,'Optics and coating roughness'),'ROUGHNESS')
    output(custom(m,'return Mask*.70;',{'Mask':mask},1,'Coated metal, nonmetal optics'),'METALLIC')
    output(node(m,u.MaterialExpressionConstant,r=.5),'SPECULAR')
    output((coat,'R'),'AMBIENT_OCCLUSION')
    if kind=='flashlight':
        normal=sample(m,prefix+'Normal',normal=True)
    else:
        normal=sample(m,'/Game/Weapons/ASH12/UniversalAttachments20260919/Textures/T_ASH12_AttachmentCoat_NormalDX',normal=True)
    output((normal,'RGB'),'NORMAL')
    if kind=='laser':
        center=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(emitter.x-.2,emitter.y,emitter.z,1))
        emission=custom(m,'float aperture=saturate(1-length(P-Center)/.65);float red=saturate((Base.r-max(Base.g,Base.b))*12);return float3(16,.001,.0005)*red*aperture;',
            {'P':position,'Center':center,'Base':(color,'RGB')},3,'Only the local red aperture emits')
        output(emission,'EMISSIVE_COLOR')
    E.set_metadata_tag(m,'WeaponFinishReference','/Game/Weapons/ASH12/Surface20260919/Materials/M_ASH12_Front')
    E.set_metadata_tag(m,'TacticalOptics','UV0 and front lens retained; physical aperture mask')
    L.recompile_material(m);save(m)
    wet_name=name+'_Wet';w=u.load_asset(folder+'/'+wet_name) or A.duplicate_asset(wet_name,folder,m)
    # A fresh duplicate is used on the first installation. Preserve generated
    # expressions on reruns instead of stacking a second water layer.
    if E.get_metadata_tag(w,'ASHDeviceWater')!='1':
        def current(prop):
            p=getattr(u.MaterialProperty,'MP_'+prop)
            return (L.get_material_property_input_node(w,p),L.get_material_property_input_node_output_name(w,p))
        base,rough,norm=current('BASE_COLOR'),current('ROUGHNESS'),current('NORMAL')
        wetness=node(w,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
        region=custom(w,'return Wet*saturate(Metal/.70);',{'Wet':wetness,'Metal':current('METALLIC')},1,'Keep lens dry, wet the metal tail')
        beads=custom(w,(O.parent/'WeatherNatural20260912/WeaponBeads.hlsl').read_text(),
            {'UV':node(w,u.MaterialExpressionTextureCoordinate),'Wet':region},4,'Adhered ASH water beads')
        output(custom(w,'return Base*(1-Data.a*.055);',{'Base':base,'Data':beads},3,'Thin water film'),'BASE_COLOR')
        output(custom(w,'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',{'Base':rough,'Data':beads},1,'Wet coating'),'ROUGHNESS')
        output(custom(w,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',{'Base':norm,'Data':beads},3,'Water over structural normal'),'NORMAL')
        E.set_metadata_tag(w,'ASHDeviceWater','1');L.recompile_material(w);save(w)
    return m,w

def build_saddle():
    h=mesh()
    # Side-rail crown and two hooked shoulders. Body starts at Y=.6 cm.
    ok(S.append_box(h,tr((0,.29,0)),3.8,.66,1.9,origin='Center',material_id=1))
    for z in (-1.05,1.05):
        ok(S.append_box(h,tr((0,.10,z)),3.8,.90,.32,origin='Center',material_id=1))
    ok(S.compute_polygroups(h,'Angle',25.,1))
    ok(S.bevel_polygroups(h,distance=.035,subdivisions=2,round_weight=1.))
    for x in (-1.25,1.25):
        for z in (-1.05,1.05):
            ok(S.append_cylinder(h,tr((x,.60,z),u.Quat(-math.sqrt(.5),0,0,math.sqrt(.5))),radius=.22,height=.12,radial_steps=12,origin='Center',material_id=1))
    ok(S.set_num_uv_layers(h,4))
    for layer in range(4):ok(S.project_uv(h,'Box',tr(scale=(4,4,4)),layer,''))
    ok(S.set_vertex_color(h,'',u.LinearColor(1,1,1,1)))
    ok(S.recompute_normals(h,38.))
    return h

def main():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Stop PIE before building static mesh assets.')
    collar=load('/Game/Weapons/ASH12/UniversalAttachments20260919/Materials/M_ASH12_GripMetal_Coat')
    saddle=build_saddle();wet_mapping={}
    for kind in ('laser','flashlight'):
        source='/Game/Weapons/TacticalDevices20260913'+('/HunyuanV3' if kind=='flashlight' else '')+'/M4/'+kind+'/SM_TacticalDevice'
        original=load(source)
        emitter=fitted(original.find_socket('Emitter').relative_location)
        guide=fitted(original.find_socket('AimGuide').relative_location)
        h=ok(S.load_mesh_from_static_mesh(source)).handle;handles.append(h)
        for index,slot in enumerate(original.static_materials):
            if 'Collar' in str(slot.material_slot_name):
                S.select_by_material_id(h,'OldM4Saddle',index)
                ok(S.delete_faces(h,'OldM4Saddle'))
        ok(S.transform_mesh(h,BODY_TRANSFORM))
        ok(S.set_num_uv_layers(h,4))
        ok(S.project_uv(h,'Box',tr(scale=(4,4,4)),1,''))
        ok(S.append_mesh(h,saddle,ID))
        body,wet=body_material(kind,emitter);wet_mapping[body.get_path_name()]=wet
        name='SM_ASH12_'+kind;path=D+'/'+kind+'/'+name
        result=ok(S.save_mesh_to_static_mesh(h,path,replace_existing=True,enable_collision=False,enable_nanite=False,save_asset=False))
        asset=load(result.asset_path)
        slots=[]
        for label,mat in [('M_Tactical_'+kind,body),('ASH_GripMetal',collar)]:
            slot=u.StaticMaterial();slot.material_slot_name=label;slot.material_interface=mat;slots.append(slot)
        asset.set_editor_property('static_materials',slots)
        for label,p in [('Emitter',emitter),('AimGuide',guide)]:
            socket=asset.find_socket(label)
            if not socket:
                socket=u.new_object(u.StaticMeshSocket,outer=asset);socket.set_editor_property('socket_name',label);asset.add_socket(socket)
            socket.relative_location=p;socket.relative_rotation=u.Rotator()
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(asset)
        editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
        settings=editor.get_lod_build_settings(asset,0)
        for k,v in {'recompute_normals':False,'recompute_tangents':True,'use_mikk_t_space':True,
                    'use_high_precision_tangent_basis':True,'use_full_precision_u_vs':True,'generate_lightmap_u_vs':False}.items():settings.set_editor_property(k,v)
        editor.set_lod_build_settings(asset,0,settings)
        E.set_metadata_tag(asset,'ASHSourceDevice',source)
        E.set_metadata_tag(asset,'ASHMount','Sight frame (29.5,-3.19,-8.25) cm; left side; local X roll 180 degrees; unit body scale')
        save(asset)
        task=u.AssetExportTask();task.object=asset;task.filename=str(O/(name+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
        task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.collision=False;task.options.level_of_detail=False
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Source FBX export failed '+kind)
        receipt['parts'][kind]={'asset':asset.get_path_name(),'source':source,'fbx':task.filename,
            'emitter_cm':[emitter.x,emitter.y,emitter.z],'guide_cm':[guide.x,guide.y,guide.z],
            'dry':body.get_path_name(),'wet':wet.get_path_name(),'saved':True}
        (O/'installed.json').write_text(json.dumps(receipt,indent=2))
        u.log('ASH_TACTICAL_SAVED '+kind)
    library=load('/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials')
    mapping=dict(library.get_editor_property('wet_materials'));mapping.update(wet_mapping)
    library.set_editor_property('wet_materials',mapping);save(library)
    receipt['weather_library']=library.get_path_name();(O/'installed.json').write_text(json.dumps(receipt,indent=2))
    u.log('ASH_TACTICAL_INSTALL_COMPLETE')

try:main()
finally:
    for h in handles:S.release_mesh(h)
