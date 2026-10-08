"""Pin only this blade's four close-view maps; record GPU dimensions before/after."""
import json,runpy,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
D='/Game/Weapons/XuanChiZhenYue20261004/BladeV3'
E=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
report={'before':{},'after':{},'saved':[]}
def node(mat,cls,**kw):
    n=E.create_material_expression(mat,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def link(a,pin,b,slot=''):
    if not E.connect_material_expressions(a,pin,b,slot):raise RuntimeError('Connection '+slot)
def dimensions(tex,tag):
    mat=A.create_asset('M_Dimensions_'+tag,D+'/TextureRepair/Unsaved',u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    obj=node(mat,u.MaterialExpressionTextureObject,texture=tex,
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if tag.endswith('Normal') else u.MaterialSamplerType.SAMPLERTYPE_COLOR if tag.endswith('BaseColor') else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    shader=node(mat,u.MaterialExpressionCustom,code='uint w,h,levels; Tex.GetDimensions(0,w,h,levels); return float3(w,h,levels);',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    pin=u.CustomInput();pin.set_editor_property('input_name','Tex');shader.set_editor_property('inputs',[pin]);link(obj,'',shader,'Tex')
    unlit=node(mat,u.MaterialExpressionSubstrateUnlitBSDF);link(shader,'',unlit)
    E.connect_material_property(unlit,'',u.MaterialProperty.MP_FRONT_MATERIAL);E.connect_material_property(shader,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=E.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    rt=u.RenderingLibrary.create_render_target2d(world,4,4,u.TextureRenderTargetFormat.RTF_RGBA16F)
    u.RenderingLibrary.draw_material_to_render_target(world,rt,mat)
    color=u.RenderingLibrary.read_render_target_raw_pixel(world,rt,1,1,False)
    return {'gpu_dimensions':[float(color.r),float(color.g)],'gpu_mips':float(color.b),
        'never_stream':tex.get_editor_property('never_stream'),'lod_bias':tex.get_editor_property('lod_bias'),
        'lod_group':str(tex.get_editor_property('lod_group')),'max_texture_size':tex.get_editor_property('max_texture_size')}
textures={ch:u.load_asset(D+'/Textures/T_XuanChi_Blade_'+ch+'_V3') for ch in ['BaseColor','Normal','ORM','Relief']}
for ch,tex in textures.items():report['before'][ch]=dimensions(tex,'Before_'+ch)
(P/'residency_before.json').write_text(json.dumps(report['before'],indent=2))
backup=P/'BeforeResidencyFix';backup.mkdir(exist_ok=True)
for ch,tex in textures.items():
    source=ROOT/'Content/Weapons/XuanChiZhenYue20261004/BladeV3/Textures'/('T_XuanChi_Blade_'+ch+'_V3.uasset')
    if not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if ch=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
    tex.set_editor_property('max_texture_size',4096);tex.set_editor_property('lod_bias',0)
    tex.set_editor_property('never_stream',True)
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Texture save failed: '+ch)
    report['saved'].append(tex.get_path_name())
    report['after'][ch]=dimensions(tex,'After_'+ch)
(P/'residency_repair.json').write_text(json.dumps(report,indent=2))
runpy.run_path(str(P/'probe_sampling.py'),init_globals={'OUTPUT_PREFIX':'after_'},run_name='__main__')
print('XUANCHI_RESIDENCY_REPAIR '+json.dumps(report))
