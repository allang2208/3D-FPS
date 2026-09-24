"""User-requested square diagnosis: transient GPU alpha read, no PIE or saved assets."""
import json
from pathlib import Path
import unreal as u

out=Path(u.Paths.project_dir())/'SourceAssets/RiverSplashNatural20260924/CardFix'
lib=u.MaterialEditingLibrary
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if not world:raise RuntimeError('No editor world for isolated render-target diagnosis')
tex=u.load_asset('/Game/Fluids/RiverSplashNatural20260924/T_RiverSplashPacked')
m=u.new_object(u.Material, name='RiverSquareAlphaRead')
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
uv=lib.create_material_expression(m,u.MaterialExpressionTextureCoordinate)
t=lib.create_material_expression(m,u.MaterialExpressionTextureObject)
t.set_editor_property('texture',tex)
t.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
c=lib.create_material_expression(m,u.MaterialExpressionCustom)
c.set_editor_property('code','return Texture2DSampleLevel(Atlas,AtlasSampler,UV,0).aaa;')
c.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
inputs=[]
for name in ['Atlas','UV']:
    p=u.CustomInput();p.set_editor_property('input_name',name);inputs.append(p)
c.set_editor_property('inputs',inputs)
lib.connect_material_expressions(t,'',c,'Atlas')
lib.connect_material_expressions(uv,'',c,'UV')
lib.connect_material_property(c,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
errors=lib.recompile_material(m)
if errors:raise RuntimeError(str(errors))
rt=u.RenderingLibrary.create_render_target2d(world,128,256,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,0))
u.RenderingLibrary.draw_material_to_render_target(world,rt,m)
pixels=u.RenderingLibrary.read_render_target_raw(world,rt,False)
values=[float(p.r) for p in pixels]
report={'gpu_alpha':{'min':min(values),'max':max(values),'count':len(values),
        'zero_count':sum(x<.001 for x in values),'opaque_count':sum(x>.99 for x in values),
        'corners':[values[0],values[127],values[-128],values[-1]]},'components':[]}
manifest=json.loads((out.parent/'bake-manifest.json').read_text(encoding='utf-8'))
report['empty_frame_max_alpha']={}
for variant, frames in manifest.get('empty_frames',{}).items():
    for frame in frames:
        index=int(variant)*32+frame-1
        x,y=(index%8)*16,(index//8)*16
        tile=[values[(y+dy)*128+x+dx] for dy in range(16) for dx in range(16)]
        report['empty_frame_max_alpha'][str(variant)+':'+str(frame)]=max(tile)
(out/globals().get('REPORT_FILENAME','gpu-alpha-before.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('RIVER_GPU_ALPHA '+json.dumps(report))
if globals().get('REQUIRE_EMPTY_FRAMES',False):
    if not report['empty_frame_max_alpha'] or max(report['empty_frame_max_alpha'].values())>.001:
        raise RuntimeError('Empty liquid frame is still visible in GPU alpha')
    if max(values)<.5:
        raise RuntimeError('Liquid coverage unexpectedly missing from the entire atlas')
