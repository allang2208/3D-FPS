"""Read only the Super90 mesh, material graph and source texture settings."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;R='/Game/Weapons/Super90/Cransh20261006'
out={'textures':{},'materials':{},'mesh':{}}
def read(obj,keys):
    result={}
    for key in keys:
        try:
            value=obj.get_editor_property(key)
            result[key]=value if isinstance(value,(float,bool,int,str)) else str(value)
        except Exception as error:result[key]=str(error)
    return result
for role in ('TTI_Benelli_M4','12gauge','matchsaverz'):
    material=u.load_asset(R+'/Materials/M_S90_'+role)
    info=read(material,['tangent_space_normal','two_sided','blend_mode'])
    info['expressions']=[]
    for node in u.MaterialEditingLibrary.get_material_expressions(material):
        entry={'class':node.get_class().get_name()}
        if isinstance(node,u.MaterialExpressionTextureSample):
            tex=node.texture;entry.update(read(node,['sampler_type','const_coordinate']))
            entry['texture']=tex.get_path_name()
            out['textures'][tex.get_path_name()]=read(tex,['srgb','compression_settings','flip_green_channel','lod_group','lod_bias','max_texture_size','filter','never_stream','virtual_texture_streaming','mip_gen_settings'])
        info['expressions'].append(entry)
    out['materials'][role]=info
mesh=u.load_asset(R+'/SK_Super90_V7')
out['mesh']['slots']=[{'slot':str(m.material_slot_name),'material':m.material_interface.get_path_name() if m.material_interface else None} for m in mesh.materials]
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
out['mesh']['lod_info']=[read(editor.get_lod_build_settings(mesh,i),['recompute_normals','recompute_tangents','use_mikk_t_space','use_full_precision_u_vs','use_high_precision_tangent_basis']) for i in range(editor.get_lod_count(mesh))]
(O/'material_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('SUPER90_MATERIAL_INPUTS_READ',len(out['textures']),len(out['mesh']['slots']))
