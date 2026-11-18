"""Author the night portal's purple sky beacon only. No map load or gameplay."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
OUT=ROOT/'SourceAssets/HillsNightRaid20261115/SkyBeam'
DEST='/Game/WorldGeneration/HillsNightRaid'
OWNER='HillsNightPortalSkyBeam20261115'
HEIGHT=300000.
WIDTH=1200.
L=u.MaterialEditingLibrary
E=u.EditorAssetLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
report={'gameplay_started':False,'saved':[],'height_cm':HEIGHT,'width_cm':WIDTH}

def owned(name):
    path=DEST+'/'+name
    obj=u.load_asset(path) if E.does_asset_exist(path) else None
    if obj and E.get_metadata_tag(obj,'HillsSkyBeamOwner')!=OWNER:
        raise RuntimeError('Preserve unowned asset: '+path)
    return obj

def save(obj):
    E.set_metadata_tag(obj,'HillsSkyBeamOwner',OWNER)
    package=u.load_package(obj.get_path_name().split('.')[0])
    if not u.EditorLoadingAndSavingUtils.save_packages([package],False):
        raise RuntimeError('Save failed: '+obj.get_path_name())
    report['saved'].append(obj.get_path_name())

def node(cls):return L.create_material_expression(mat,cls)
def wire(source,target,pin,output=''):
    if not L.connect_material_expressions(source,output,target,pin):raise RuntimeError('Connect '+pin)
def prop(source,property):
    if not L.connect_material_property(source,'',property):raise RuntimeError('Connect material property '+str(property))
def scalar(name,value):
    result=node(u.MaterialExpressionScalarParameter)
    result.set_editor_property('parameter_name',name);result.set_editor_property('default_value',value)
    return result
def custom(source,inputs,output):
    result=node(u.MaterialExpressionCustom)
    result.set_editor_property('code',(OUT/source).read_text(encoding='utf-8'))
    result.set_editor_property('output_type',output)
    entries=[]
    for name in inputs:
        entry=u.CustomInput();entry.set_editor_property('input_name',name);entries.append(entry)
    result.set_editor_property('inputs',entries)
    for name,item in inputs.items():wire(item,result,name)
    return result

E.make_directory(DEST)
mat=owned('M_NightPortalSkyBeam') or AT.create_asset('M_NightPortalSkyBeam',DEST,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property('two_sided',True)
mat.set_editor_property('disable_depth_test',False)
mat.set_editor_property('compute_fog_per_pixel',True)
uv=node(u.MaterialExpressionTextureCoordinate)
position=node(u.MaterialExpressionWorldPosition)
center=node(u.MaterialExpressionObjectPositionWS)
camera=node(u.MaterialExpressionCameraPositionWS)
time=node(u.MaterialExpressionTime)
flow=custom('NightPortalSkyBeam.ush',{'UV':uv,'WorldPosition':position,'Center':center,
    'Time':time,'FlowTimeOffset':scalar('FlowTimeOffset',0.),'OpenAmount':scalar('OpenAmount',0.),
    'BeamHeight':scalar('BeamHeight',HEIGHT)},u.CustomMaterialOutputType.CMOT_FLOAT4)
rgb=node(u.MaterialExpressionComponentMask)
for channel in ('r','g','b'):rgb.set_editor_property(channel,True)
rgb.set_editor_property('a',False);wire(flow,rgb,str(L.get_material_expression_input_names(rgb)[0]))
exposure=node(u.MaterialExpressionEyeAdaptationInverse)
wire(rgb,exposure,str(L.get_material_expression_input_names(exposure)[0]))
prop(exposure,u.MaterialProperty.MP_EMISSIVE_COLOR)
alpha=node(u.MaterialExpressionComponentMask)
for channel in ('r','g','b'):alpha.set_editor_property(channel,False)
alpha.set_editor_property('a',True);wire(flow,alpha,str(L.get_material_expression_input_names(alpha)[0]))
fade=node(u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',40.)
wire(alpha,fade,'Opacity');prop(fade,u.MaterialProperty.MP_OPACITY)
facing=custom('NightPortalSkyBeamFacing.ush',{'UV':uv,'WorldPosition':position,'Center':center,
    'CameraPosition':camera,'BeamWidth':scalar('BeamWidth',WIDTH)},u.CustomMaterialOutputType.CMOT_FLOAT3)
prop(facing,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
errors=L.recompile_material(mat)
if errors:raise RuntimeError(str(errors))
save(mat)

# A single 128-triangle strip. The shader faces each view without a camera tick.
positions=[];normals=[];uvs=[];triangles=[]
for row in range(65):
    h=row/64.
    for side in (0.,1.):
        positions.append(((side-.5)*WIDTH,0.,h*HEIGHT))
        normals.append((0.,-1.,0.));uvs.append((side,h))
for row in range(64):
    a=row*2;triangles.extend(((a,a+1,a+3),(a,a+3,a+2)))
buffers=u.GeometryScriptSimpleMeshBuffers()
buffers.vertices=[u.Vector(*p) for p in positions]
buffers.normals=[u.Vector(*n) for n in normals]
buffers.uv0=[u.Vector2D(*v) for v in uvs]
buffers.triangles=[u.IntVector(*t) for t in triangles]
dynamic=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic,buffers)
mesh=owned('SM_NightPortalSkyBeam')
if mesh:
    _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,mesh,
        u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
else:
    mesh,outcome=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,DEST+'/SM_NightPortalSkyBeam',
        u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
            enable_collision=False,enable_nanite=False))
if not mesh or outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Beam mesh creation: '+str(outcome))
mesh.set_material(0,mat)
# The view-facing strip can rotate to any XY direction. Preserve its full envelope.
mesh.set_editor_property('positive_bounds_extension',u.Vector(0.,WIDTH*.5,0.))
mesh.set_editor_property('negative_bounds_extension',u.Vector(0.,WIDTH*.5,0.))
save(mesh)
report['triangles']=len(triangles)
(OUT/'beam-mesh-source.json').write_text(json.dumps({'vertices':positions,'normals':normals,'uv0':uvs,'triangles':triangles}),encoding='utf-8')
(OUT/'authoring-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('HILLS_NIGHT_SKY_BEAM_SAVED '+json.dumps(report,ensure_ascii=False))
