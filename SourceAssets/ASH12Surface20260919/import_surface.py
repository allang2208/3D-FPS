"""Install ASH-12-only mesh, PBR, optics and private weather mapping.

Saves only explicitly authored assets. Keeps the existing skeleton and every
animation reference; no shared weapon material or weather table is overwritten.
"""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;ROOT=O.parents[1]
D='/Game/Weapons/ASH12/Surface20260919'
OLD='/Game/Weapons/ASH12/Integrated20260917/SK_ASH12_Manny'
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt={'mesh':{},'materials':{},'optics':{},'wet_mapping':{},'tested':False}
author=json.loads((O/'authoring.json').read_text())
COLOURS={'Upper':(.085,.090,.098),'Lower':(.080,.085,.092),'Front':(.090,.095,.103),
         'Sights':(.065,.068,.072),'Flash_Hider':(.320,.330,.340),'Magazine':(.05,.05,.052),'Magazine_Base':(.044,.044,.046)}
def load(p):
    obj=u.load_asset(p)
    if not obj:raise RuntimeError('Missing authoring asset '+p)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
def clone(src,dest):
    return load(dest) if E.does_asset_exist(dest) else E.duplicate_asset(src,dest)
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,n,pin):
    a,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(a,out,n,pin):raise RuntimeError('Cannot wire '+pin)
def prop(src,name):
    a,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Cannot connect '+name)
def c(m,v):return node(m,u.MaterialExpressionConstant,r=v)
def vec(m,v):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
def scalar(m,name,v):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=v)
def custom(m,code,inputs,size,label):
    n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)),description=label)
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,src in inputs.items():wire(src,n,name)
    return n
def input_for(m,name):
    p=getattr(u.MaterialProperty,'MP_'+name)
    n=L.get_material_property_input_node(m,p)
    return (n,L.get_material_property_input_node_output_name(m,p)) if n else None
def texture(path,normal):
    t=u.AssetImportTask();t.filename=path;t.destination_path=D+'/Textures';t.destination_name=Path(path).stem
    t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
    tex=load(t.destination_path+'/'+t.destination_name);tex.srgb=False
    tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    if normal:tex.set_editor_property('flip_green_channel',False)
    E.set_metadata_tag(tex,'ASH12Source','Original packed TGA RGB, opaque DX normal; local cavity bake and restrained finish')
    save(tex);return tex
def sample(m,tex,normal=False):
    return node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
def new_material(name):
    path=D+'/Materials/'+name
    m=load(path) if E.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    return m
def finish(m):
    E.set_metadata_tag(m,'ASH12SurfaceRevision','20260919');L.recompile_material(m);save(m)
dry={};wet_mapping={}
for part,files in author['textures'].items():
    normal=texture(files['normal'],True);orm=texture(files['orm'],False)
    m=new_material('M_ASH12_'+part);ns=sample(m,normal,True);packed=sample(m,orm)
    region=node(m,u.MaterialExpressionVertexColor)
    prop(custom(m,'return lerp(lerp(lerp(Base,float3(.025,.026,.028),Mask.r),float3(.22,.24,.26),Mask.g),float3(.010,.011,.012),Mask.b);',
        {'Base':vec(m,COLOURS[part]),'Mask':region},3,'Preserve coat, polymer, bolt steel and bore identity'),'BASE_COLOR')
    prop(custom(m,'return lerp(lerp(lerp(Base,.62,Mask.r),.30,Mask.g),.87,Mask.b);',{'Base':(packed,'G'),'Mask':region},1,'Regional roughness'),'ROUGHNESS')
    prop(custom(m,'return lerp(lerp(lerp(Base,.03,Mask.r),.90,Mask.g),.05,Mask.b);',{'Base':(packed,'B'),'Mask':region},1,'Regional metalness'),'METALLIC')
    prop(ns,'NORMAL');prop((packed,'R'),'AMBIENT_OCCLUSION');prop(c(m,.5),'SPECULAR')
    finish(m);dry[part]=m
    receipt['materials'][part]={'dry':m.get_path_name(),'normal':normal.get_path_name(),'orm':orm.get_path_name()}

BEADS=(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text()
def make_wet(src,name,optic=False):
    w=clone(src.get_path_name(),D+'/Materials/'+name+'_Wet')
    if E.get_metadata_tag(w,'ASH12WetRevision')=='20260919':return w
    base=input_for(w,'BASE_COLOR');rough=input_for(w,'ROUGHNESS');normal=input_for(w,'NORMAL') or vec(w,(0,0,1))
    if optic:
        # Preserve the existing outside/white-mark/optical-aperture mask.
        alpha=L.get_inputs_for_material_expression(w,rough[0])[2]
    else:
        alpha=custom(w,'return 1-Mask.b;',{'Mask':node(w,u.MaterialExpressionVertexColor)},1,'Exclude the muzzle bore')
    wet=custom(w,'return saturate(Wet)*saturate(Exterior);',{'Wet':scalar(w,'WeaponWetness',0.),'Exterior':alpha},1,'Local exposed wetness')
    beads=custom(w,BEADS,{'UV':node(w,u.MaterialExpressionTextureCoordinate),'Wet':wet},4,'ASH12 adhered water beads')
    prop(custom(w,'return Base*(1-Data.a*.055);',{'Base':base,'Data':beads},3,'Thin water film color'),'BASE_COLOR')
    prop(custom(w,'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',{'Base':rough,'Data':beads},1,'Film and bead specular response'),'ROUGHNESS')
    prop(custom(w,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',{'Base':normal,'Data':beads},3,'Beads over structural normals'),'NORMAL')
    E.set_metadata_tag(w,'ASH12WetRevision','20260919');finish(w);return w
for part,m in dry.items():
    wet=make_wet(m,m.get_name());wet_mapping[m.get_path_name()]=wet
    receipt['materials'][part]['wet']=wet.get_path_name()

# Import new mesh on its existing skeleton. Preserve material-slot names and
# accepted hand materials; the reload/sprint clips remain on this same skeleton.
old=load(OLD);bindings={str(s.material_slot_name):s.material_interface for s in old.materials}
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True
options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
options.create_physics_asset=False;options.skeleton=old.skeleton
imp=options.skeletal_mesh_import_data;imp.set_editor_property('update_skeleton_reference_pose',False)
imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
imp.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
imp.vertex_color_import_option=u.VertexColorImportOption.REPLACE
task=u.AssetImportTask();task.filename=str(O/'SK_ASH12_Surface.fbx');task.destination_path=D;task.destination_name='SK_ASH12_Surface'
task.options=options;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
mesh=load(D+'/SK_ASH12_Surface');slots=mesh.materials
for i,s in enumerate(slots):
    label=str(s.material_slot_name);s.material_interface=dry[label.removeprefix('M_ASH12_')] if label.startswith('M_ASH12_') else bindings[label];slots[i]=s
mesh.set_editor_property('materials',slots);E.set_metadata_tag(mesh,'ASH12SurfaceSource',OLD);save(mesh)
receipt['mesh']={'path':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'editable':str(O/'ASH12_Surface_Editable.blend')}

# Each optic already has a protected exterior blend. Replace only its coating
# branch; keep original UV0 normal, AO, markings, glass and reticle assets.
installed=json.loads((ROOT/'SourceAssets/WeaponAttachmentFinish20260913/installed.json').read_text())
for kind in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring'):
    info=installed['M4/'+kind];source=load(info['mesh'])
    dst=D+'/Optics/'+source.get_name();target=clone(source.get_path_name(),dst)
    slots=target.static_materials;parts={}
    for i,slot in enumerate(slots):
        label=str(slot.material_slot_name)
        if label not in info['changed_slots']:continue
        original=slot.material_interface
        name='M_ASH12_Optic_'+kind
        if isinstance(original,u.MaterialInstanceConstant):
            raise RuntimeError('Optic authoring graph changed to an instance: '+original.get_path_name())
        mat=clone(original.get_path_name(),D+'/Materials/'+name)
        if E.get_metadata_tag(mat,'ASH12OpticCoat')!='20260919':
            for channel,value in [('BASE_COLOR',vec(mat,COLOURS['Sights'])),('METALLIC',c(mat,.65)),('SPECULAR',c(mat,.5))]:
                final=input_for(mat,channel)[0]
                if not isinstance(final,u.MaterialExpressionLinearInterpolate):raise RuntimeError('Expected exterior blend '+kind+' '+channel)
                wire(value,final,'B')
            final=input_for(mat,'ROUGHNESS')[0];original_detail=L.get_inputs_for_material_expression(mat,final)[0]
            coat=custom(mat,'return clamp(.50+(Detail-.5)*.025,.42,.58);',{'Detail':original_detail},1,'ASH12 sight coat with original optic detail')
            wire(coat,final,'B');E.set_metadata_tag(mat,'ASH12OpticCoat','20260919');finish(mat)
        slot.material_interface=mat;slots[i]=slot
        wet=make_wet(mat,name,True);wet_mapping[mat.get_path_name()]=wet;parts[label]=mat.get_path_name()
    target.set_editor_property('static_materials',slots);E.set_metadata_tag(target,'WeaponFinishReference',dry['Sights'].get_path_name());save(target)
    receipt['optics'][kind]={'mesh':target.get_path_name(),'exterior':parts}

name='DA_ASH12_WetMaterials';path=D+'/'+name
if E.does_asset_exist(path):library=load(path)
else:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
    library=A.create_asset(name,D,u.WeatherPresentationAssets,factory)
library.set_editor_property('wet_materials',wet_mapping);save(library)
receipt['wet_mapping']={k:v.get_path_name() for k,v in wet_mapping.items()}
receipt['weather_library']=library.get_path_name()
(O/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ASH12_SURFACE_IMPORT_COMPLETE')
