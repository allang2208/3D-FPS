import unreal as u
L = u.MaterialEditingLibrary
mat = u.load_asset('/Game/Props/WarehouseCrateTiers20260924/Materials/M_Crate_Wood')
def srcinfo(p):
    n = L.get_material_property_input_node(mat, getattr(u.MaterialProperty, p))
    if n is None: return p+' = None'
    parts=[n.get_class().get_name()]
    try:
        t=n.get_editor_property('texture')
        if t: parts.append(t.get_path_name().split('.')[0].split('/')[-1]+'='+str(n.get_editor_property('sampler_type')).split('.')[-1])
    except Exception: pass
    return p+' -> '+' '.join(parts)
for p in ('MP_BASE_COLOR','MP_METALLIC','MP_ROUGHNESS','MP_NORMAL'): print(srcinfo(p), flush=True)
print('two_sided', mat.get_editor_property('two_sided'), flush=True)
