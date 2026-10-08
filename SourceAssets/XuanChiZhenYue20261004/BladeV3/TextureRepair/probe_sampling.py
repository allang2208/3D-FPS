"""Offscreen GPU comparison of direct texture sampling and the live blade graph."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;D='/Game/Weapons/XuanChiZhenYue20261004/BladeV3'
prefix=globals().get('OUTPUT_PREFIX','')
E=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
mat=u.load_asset(D+'/Materials/M_XuanChi_SteelRelief_V3')
report={'shader_errors':list(E.recompile_material(mat)),'probes':[]}
def node(m,cls,**kw):
    n=E.create_material_expression(m,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def link(a,pin,b,slot=''):
    if not E.connect_material_expressions(a,pin,b,slot):raise RuntimeError('Probe connection '+slot)
for mode in ['direct','graph_color','graph_normal']:
    probe=A.duplicate_asset('M_Probe_'+prefix+mode,D+'/TextureRepair/Unsaved',mat)
    probe.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    if mode=='direct':
        tex=u.load_asset(D+'/Textures/T_XuanChi_Blade_BaseColor_V3')
        output=node(probe,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        pin='RGB'
    else:
        prop=u.MaterialProperty.MP_NORMAL if mode=='graph_normal' else u.MaterialProperty.MP_BASE_COLOR
        output=E.get_material_property_input_node(probe,prop);pin=E.get_material_property_input_node_output_name(probe,prop)
        if mode=='graph_normal':
            mul=node(probe,u.MaterialExpressionMultiply,const_b=.5);link(output,pin,mul,'A')
            add=node(probe,u.MaterialExpressionAdd,const_b=.5);link(mul,'',add,'A');output=add;pin=''
    unlit=node(probe,u.MaterialExpressionSubstrateUnlitBSDF)
    link(output,pin,unlit)
    E.connect_material_property(unlit,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    E.connect_material_property(output,pin,u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=list(E.recompile_material(probe))
    if errors:raise RuntimeError(str(errors))
    rt=u.RenderingLibrary.create_render_target2d(world,512,2048,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(0,0,0,1))
    u.RenderingLibrary.draw_material_to_render_target(world,rt,probe)
    u.RenderingLibrary.export_render_target(world,rt,str(P),prefix+mode+'.png')
    report['probes'].append({'mode':mode,'shader_errors':errors,'path':str(P/(prefix+mode+'.png'))})
(P/(prefix+'sampling_report.json')).write_text(json.dumps(report,indent=2))
print('BLADE_SAMPLING_PROBE_COMPLETE '+json.dumps(report))
