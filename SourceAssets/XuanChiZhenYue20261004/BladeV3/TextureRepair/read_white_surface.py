import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
E=u.MaterialEditingLibrary
def path(x):return x.get_path_name() if x else None
def prop(x,k):
    try:return str(x.get_editor_property(k))
    except Exception as e:return str(e)
report={'widgets':[],'materials':[],'lights':[]}
for w in u.ObjectIterator(u.M4GunsmithWidget):
    row={'widget':path(w)}
    for k in ['capture','preview_coverage_capture','preview_target','preview_material','standalone_melee']:
        try:
            x=w.get_editor_property(k);row[k]=path(x)
            if k=='capture' and x:
                row['capture_settings']={a:prop(x,a) for a in ['capture_source','show_flag_settings','post_process_settings','post_process_blend_weight']}
                row['components']=[]
                for c in x.get_editor_property('show_only_components'):
                    row['components'].append({'path':path(c),'mesh':path(c.static_mesh) if isinstance(c,u.StaticMeshComponent) else None,'materials':[path(c.get_material(i)) for i in range(c.get_num_materials())]})
                rt=x.texture_target
                if rt:
                    u.RenderingLibrary.export_render_target(x,rt,str(P),'live_preview_before')
            if k=='preview_material' and x:
                row['preview_parent']=path(x.parent)
        except Exception as e:row[k+'_error']=str(e)
    report['widgets'].append(row)
for x in u.ObjectIterator(u.LightComponent):
    if x.get_path_name().startswith('/Engine/Transient'):
        report['lights'].append({'path':path(x),'class':x.get_class().get_name(),'intensity':prop(x,'intensity'),'color':prop(x,'light_color')})
for a in ['/Game/UI/GunsmithWorkbench/M_WeaponPreviewResolved','/Game/Weapons/XuanChiZhenYue20261004/SurfaceV2/Materials/M_XuanChi_Hilt_V2','/Game/Weapons/XuanChiZhenYue20261004/SurfaceV2/Materials/M_XuanChi_Tassel_V2','/Game/Weapons/XuanChiZhenYue20261004/BladeV3/Materials/M_XuanChi_SteelRelief_V3']:
    m=u.load_asset(a);row={'path':path(m),'nodes':[],'outputs':{}}
    for k in ['material_domain','blend_mode','shading_model','tangent_space_normal','use_material_attributes']:row[k]=prop(m,k)
    for k in ['MP_BASE_COLOR','MP_EMISSIVE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_METALLIC','MP_FRONT_MATERIAL','MP_OPACITY']:
        en=getattr(u.MaterialProperty,k);row['outputs'][k]={'node':path(E.get_material_property_input_node(m,en)),'pin':E.get_material_property_input_node_output_name(m,en)}
    for n in E.get_material_expressions(m):
        nr={'path':path(n),'class':n.get_class().get_name(),'inputs':list(E.get_material_expression_input_names(n)),'sources':[path(x) for x in E.get_inputs_for_material_expression(m,n)]}
        if isinstance(n,u.MaterialExpressionTextureSample):
            t=n.texture;nr['texture']=path(t);nr['sampler']=prop(n,'sampler_type');nr['texture_settings']={k:prop(t,k) for k in ['srgb','compression_settings','adjust_brightness','adjust_brightness_curve','adjust_saturation','lod_group','never_stream']}
        if isinstance(n,u.MaterialExpressionCustom):nr['code']=n.get_editor_property('code')
        row['nodes'].append(nr)
    report['materials'].append(row)
(P/'white_surface_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'widgets':report['widgets'],'lights':report['lights']},default=str))
