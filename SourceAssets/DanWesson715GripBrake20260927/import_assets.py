"""Import the three produced game attachments and save their dedicated materials."""
import ast, json
from pathlib import Path
import unreal as u

O=Path(__file__).parent;ROOT=O.parents[1]
D='/Game/Weapons/DanWesson715/GripBrake20260927'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
report={'parts':{},'materials':{},'saved':[]}

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    return asset

def checkpoint():
    (O/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

# Reuse the project's accepted raindrop material graph helper functions.
tree=ast.parse((ROOT/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf-8'))
names={'node','wire','prop','scalar','constant','vector','custom'}
helpers={'unreal':u,'LIB':L}
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names],type_ignores=[]),'weather_graph_helpers','exec'),helpers)
node=helpers['node'];custom=helpers['custom'];prop=helpers['prop'];scalar=helpers['scalar']
beadcode=(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text()
materials={}
for key,maps in auth['textures'].items():
    textures={}
    for kind,file in maps.items():
        path=D+'/Textures/'+Path(file).stem
        if E.does_asset_exist(path):tex=u.load_asset(path)
        else:
            t=u.AssetImportTask();t.filename=file;t.destination_path=D+'/Textures';t.destination_name=Path(file).stem;t.automated=True;t.save=False
            A.import_asset_tasks([t]);tex=u.load_asset(path)
            if not tex:raise RuntimeError('Texture import failed '+file)
            tex.set_editor_property('srgb',kind=='BaseColor')
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_BC7)
            if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
            tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
            save(tex)
        textures[kind]=tex
    path=D+'/Materials/M_DW715_'+key
    if E.does_asset_exist(path):mat=u.load_asset(path)
    else:
        mat=A.create_asset('M_DW715_'+key,D+'/Materials',u.Material,u.MaterialFactoryNew())
        samples={}
        for kind,tex in textures.items():
            n=node(mat,u.MaterialExpressionTextureSample)
            n.set_editor_property('texture',tex)
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            samples[kind]=n
        wet=scalar(mat,'WeaponWetness',0)
        uv=node(mat,u.MaterialExpressionTextureCoordinate)
        beads=custom(mat,beadcode,dict(UV=uv,Wet=wet),4,'DW715 surface rain')
        prop(custom(mat,'return Base*(1-Data.a*.09);',dict(Base=samples['BaseColor'],Data=beads),3),'BASE_COLOR')
        prop(custom(mat,'return lerp(lerp(ORM.g,max(.085,ORM.g*.70),Data.a),.065,Data.b*.8);',dict(ORM=samples['ORM'],Data=beads),1),'ROUGHNESS')
        prop(custom(mat,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=samples['Normal'],Data=beads),3),'NORMAL')
        L.connect_material_property(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        L.connect_material_property(samples['ORM'],'B',u.MaterialProperty.MP_METALLIC)
        E.set_metadata_tag(mat,'Source','Original procedural finish; 10 cm physical UV; DanWesson715GripBrake20260927')
        L.recompile_material(mat);save(mat)
    materials['DW715_'+key]=mat;report['materials'][key]=mat.get_path_name();checkpoint()

for key,part in auth['parts'].items():
    name='SM_'+key;path=D+'/Meshes/'+name
    if E.does_asset_exist(path):mesh=u.load_asset(path)
    else:
        t=u.AssetImportTask();t.filename=part['fbx'];t.destination_path=D+'/Meshes';t.destination_name=name;t.automated=True;t.save=False
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        t.options=opt;A.import_asset_tasks([t]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed '+key)
    slots=mesh.get_editor_property('static_materials')
    for i,slot in enumerate(slots):
        label=str(slot.material_slot_name)
        slot.material_interface=materials[label];slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'Fitting','Accepted 715 source. +X forward / +Z up. '+part['mount'])
    save(mesh);report['parts'][key]=mesh.get_path_name();checkpoint()

path=D+'/DA_DW715_GripBrakeWetMaterials'
if E.does_asset_exist(path):library=u.load_asset(path)
else:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
    library=A.create_asset('DA_DW715_GripBrakeWetMaterials',D,u.WeatherPresentationAssets,factory)
# These surfaces already contain the dry-to-wet graph; runtime creates its pooled MID from it.
library.set_editor_property('wet_materials',{m.get_path_name():m for m in materials.values()});save(library)
report['wet_library']=library.get_path_name()
report['state']='Imported and saved; no gameplay or visual acceptance testing.';checkpoint()
u.log('DW715_GRIP_BRAKE_SAVED '+str(len(report['parts']))+' parts, '+str(len(materials))+' surface materials')
