"""Build the seven carpenter prop packages in the offline asset-only host."""
import json
from pathlib import Path
import unreal as ue

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageCarpenter/Props'
DEST='/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props'
RURAL='/Game/UnrealNormandy/Textures/T_'
CHAPEL='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_'
E=ue.EditorAssetLibrary
A=ue.AssetToolsHelpers.get_asset_tools()
L=ue.MaterialEditingLibrary
S=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
packages=[]

def get(path):
    obj=ue.load_asset(path)
    if not obj:raise RuntimeError('Missing asset '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    packages.append(obj.get_path_name().split('.')[0])
def node(mat,kind):
    return L.create_material_expression(mat,getattr(ue,'MaterialExpression'+kind))
def link(a,output,b,pin):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Unconnected '+pin)
def prop(a,output,key):
    if not L.connect_material_property(a,output,getattr(ue.MaterialProperty,'MP_'+key)):raise RuntimeError('Unconnected '+key)
def vec(mat,color):
    n=node(mat,'Constant3Vector');n.constant=ue.LinearColor(*color,1.);return n
def scalar(mat,value):
    n=node(mat,'Constant');n.r=value;return n
def texture(path,suffix):
    task=ue.AssetImportTask()
    task.filename=str(OUT/'Authored'/(suffix+'.png'));task.destination_path=DEST+'/Surfaces'
    task.destination_name='T_Carpenter'+suffix;task.automated=True;task.replace_existing=False
    if not E.does_asset_exist(path):A.import_asset_tasks([task])
    tex=get(path);tex.srgb=suffix.endswith('Color')
    tex.compression_settings=(ue.TextureCompressionSettings.TC_NORMALMAP if suffix.endswith('Normal')
                              else ue.TextureCompressionSettings.TC_DEFAULT if tex.srgb else ue.TextureCompressionSettings.TC_MASKS)
    if suffix=='CarpenterPaint':tex.address_x=tex.address_y=ue.TextureAddress.TA_CLAMP
    save(tex)
def sample(mat,path,kind,uv=None):
    n=node(mat,'TextureSample');n.texture=get(path);n.sampler_type=getattr(ue.MaterialSamplerType,'SAMPLERTYPE_'+kind)
    if uv:link(uv,'',n,'UVs')
    return n

surf=DEST+'/Surfaces/T_Carpenter'

def material(name,source,style,tint,bias=(0,0,0),metal=None,rough_scale=1.,rough_bias=0.,sign=False,packed_texture=None):
    path=DEST+'/Surfaces/M_Carpenter'+name
    mat=get(path) if E.does_asset_exist(path) else A.create_asset('M_Carpenter'+name,DEST+'/Surfaces',ue.Material,ue.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    channels={'normandy':('BaseColor','Normal','RHAOM','R','B'),'chapel':('Color','NormalDX','ARH','G','R'),
              'end':('Color','Normal','ORM','G','R')}[style]
    color=sample(mat,source+channels[0],'COLOR');norm=sample(mat,source+channels[1],'NORMAL')
    pack=sample(mat,packed_texture or source+channels[2],'MASKS')
    mul=node(mat,'Multiply');link(color,'RGB',mul,'A');link(vec(mat,tint),'',mul,'B');tone=mul
    if any(bias):
        add=node(mat,'Add');link(mul,'',add,'A');link(vec(mat,bias),'',add,'B');tone=add
    if sign:
        uv=node(mat,'TextureCoordinate');uv.coordinate_index=1
        paint=sample(mat,surf+'CarpenterPaint','MASKS',uv)
        mix=node(mat,'LinearInterpolate');link(tone,'',mix,'A');link(vec(mat,(.59,.48,.30)),'',mix,'B');link(paint,'R',mix,'Alpha')
        tone=mix
    prop(tone,'','BASE_COLOR');prop(norm,'RGB','NORMAL');prop(pack,channels[4],'AMBIENT_OCCLUSION')
    if rough_scale!=1 or rough_bias:
        atten=node(mat,'Multiply');link(scalar(mat,rough_scale),'',atten,'B');link(pack,channels[3],atten,'A')
        rough=node(mat,'Add');link(scalar(mat,rough_bias),'',rough,'B');link(atten,'',rough,'A');prop(rough,'','ROUGHNESS')
    else:prop(pack,channels[3],'ROUGHNESS')
    if metal is not None:
        value=node(mat,'Constant');value.r=metal;prop(value,'','METALLIC')
    L.recompile_material(mat);save(mat);return mat

def build_metals():
    # The donor's RHAOM source was imported as a normal map. A mask-compressed local
    # copy preserves the scan's original R (roughness) and B (AO) channels.
    packed_path=surf+'Metal_RHAOM'
    donor=RURAL+'MetalRust_00A_RHAOM'
    packed=get(packed_path) if E.does_asset_exist(packed_path) else E.duplicate_asset(donor,packed_path)
    if not packed:raise RuntimeError('Could not duplicate '+donor)
    packed.set_editor_property('compression_settings',ue.TextureCompressionSettings.TC_MASKS)
    packed.set_editor_property('srgb',False)
    packed.set_editor_property('lod_group',ue.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR)
    packed.set_editor_property('compression_no_alpha',True)
    resized=ue.TextureAssetActionsBlueprintFns.resize_texture_source(packed,1024)
    if resized==ue.TextureAssetActionsBlueprintReturn.ERROR:raise RuntimeError('Could not resize '+packed_path)
    packed.set_editor_property('lod_bias',0)
    save(packed)
    alloys={}
    # Worn cutting edge, forged cheek and ferrule share the scanned micro-surface with different alloys.
    for key,tint,bias,metal,rough_scale,rough_bias in [
            ('Iron',(.12,.12,.12),(.06,.063,.062),.83,.56,.13),
            ('Steel',(.10,.10,.1),(.43,.46,.47),.94,.36,.12),
            ('Brass',(.08,.072,.04),(.46,.29,.105),.91,.35,.16)]:
        alloys[key]=material(key,RURAL+'MetalRust_00A_','normandy',tint,bias,metal,rough_scale,rough_bias,packed_texture=packed_path)
    return alloys


def build_props():
    for suffix in ('Cut_Color','Cut_Normal','Cut_ORM','CarpenterPaint'):texture(surf+suffix,suffix)
    mats={
        'Oak':get('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
        'Sawn':material('Sawn',RURAL+'WoodSurface_00A_','normandy',(1.06,.91,.68),(.085,.058,.026)),
        'Rot':material('Rot',RURAL+'RottenWoodSurface_00A_','normandy',(.85,.84,.76)),
        'Bark':material('Bark',RURAL+'LS_BlackAlderBark_00A_','normandy',(.88,.85,.80)),
        'Endgrain':material('Cut',surf+'Cut_','end',(1.,1.,1.)),
        'Sign':material('Sign',CHAPEL,'chapel',(.65,.61,.52),sign=True)}
    mats.update(build_metals())
    rows=json.loads((OUT/'models.json').read_text(encoding='utf-8'))
    saved=[]
    for row in rows:
        name=row['name'];path=DEST+'/'+name
        if not E.does_asset_exist(path):
            task=ue.AssetImportTask();task.filename=row['fbx'];task.destination_path=DEST;task.destination_name=name
            task.automated=True;task.replace_existing=False
            opts=ue.FbxImportUI();opts.import_mesh=True;opts.import_as_skeletal=False;opts.import_materials=False;opts.import_textures=False
            opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH
            d=opts.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True
            d.transform_vertex_to_absolute=True;d.import_mesh_lods=True;d.generate_lightmap_u_vs=False;d.auto_generate_collision=False
            d.normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            task.options=opts;task.factory=ue.FbxFactory();A.import_asset_tasks([task])
        mesh=get(path)
        for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,mats[str(slot.material_slot_name)])
        S.set_lod_screen_sizes(mesh,[1.,.26,.07])
        body=mesh.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom');boxes=[]
        for c,size in row['boxes']:
            box=ue.KBoxElem();box.set_editor_property('center',ue.Vector(*c))
            for k,v in zip(('x','y','z'),size):box.set_editor_property(k,v)
            boxes.append(box)
        agg.set_editor_property('box_elems',boxes);agg.set_editor_property('convex_elems',[])
        body.set_editor_property('agg_geom',agg);body.set_editor_property('collision_trace_flag',ue.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        slots=list(mesh.static_materials)
        for slot in slots:
            uv=slot.get_editor_property('uv_channel_data')
            uv.set_editor_property('bOverrideDensities',True);uv.set_editor_property('LocalUVDensities',[100.,100.,0.,0.])
        mesh.set_editor_property('static_materials',slots);save(mesh)
        box=mesh.get_bounding_box()
        saved.append(dict(path=path,lods=S.get_lod_count(mesh),bounds_cm=[[v.x,v.y,v.z] for v in (box.min,box.max)],collision_boxes=len(boxes)))
    (OUT/'saved.json').write_text(json.dumps(dict(packages=packages,meshes=saved),indent=2),encoding='utf-8')
    ue.log('CARPENTER_PROP_PACKAGES_SAVED '+str(len(packages)))

if __name__=='__main__':
    build_props()
