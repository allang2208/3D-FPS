"""Read-only survey of reusable materials and other workbench surfaces.

Dumps parent chains, parameter overrides, texture references and material
slots of the build palette's bench-family entries so the medieval restyle can
reuse inventory materials instead of authoring new ones. Writes JSON only.
"""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/Saved/GunWorkbench20260927/material-inventory.json')

MATERIALS = [
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/InUse/MI_WBK_WSBench_BenchWood_R3',
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/InUse/MI_WBK_WSBench_EndGrain',
    '/Game/Dungeons/ArtPass20260922/Materials/MI_Prop_Bucket_Wood',
    '/Game/Dungeons/ArtPass20260922/Materials/MI_Prop_Bucket_Metal',
    '/Game/Dungeons/ArtPass20260922/Materials/MI_Prop_Rope_All',
    '/Game/Dungeons/ArtPass20260922/Materials/MI_Prop_StepLadder_All',
    '/Game/Dungeons/ArtPass20260922/Materials/MI_Prop_Lantern_All',
    '/Game/Props/RomanColumn20260915/M_Bronze',
    '/Game/Building/Voxels/M_Voxel_Wood',
    '/Game/Building/GunWorkbenchPolish20260928/Materials/M_GW3_Mat',
]


def tex_info(t):
    if not t:
        return None
    d = {'path': t.get_path_name()}
    for prop in ('size_x', 'size_y'):
        try:
            d[prop] = int(t.get_editor_property(prop))
        except Exception:
            pass
    return d


def dump_material(path):
    a = u.load_asset(path)
    if not a:
        return {'missing': True}
    cls = a.get_class().get_name()
    d = {'class': cls}
    try:
        p = a.get_editor_property('parent')
        d['parent'] = p.get_path_name() if p else None
    except Exception:
        d['parent'] = None
    if 'MaterialInstance' in cls:
        for prop in ('scalar_parameter_values', 'vector_parameter_values',
                     'texture_parameter_values'):
            try:
                vals = []
                for it in a.get_editor_property(prop):
                    ent = {'raw': str(it)}
                    for attr in ('parameter_name', 'param_name'):
                        try:
                            ent[attr] = str(it.get_editor_property(attr))
                            break
                        except Exception:
                            pass
                    try:
                        v = it.get_editor_property('parameter_value')
                        if hasattr(v, 'get_path_name'):
                            ent['value'] = v.get_path_name()
                        else:
                            ent['value'] = str(v)
                    except Exception:
                        pass
                    vals.append(ent)
                d[prop] = vals
            except Exception as ex:
                d[prop + '_error'] = str(ex)
        try:
            static_tex = a.static_parameters_override if hasattr(a, 'static_parameters_override') else None
        except Exception:
            static_tex = None
    if cls == 'Material':
        texs, params = [], []
        try:
            for e in a.get_editor_property('expressions'):
                cn = e.get_class().get_name()
                if 'Texture' in cn or 'TextureObject' in cn:
                    for p in ('texture', 'mask'):
                        try:
                            t = e.get_editor_property(p)
                            if t and hasattr(t, 'get_path_name'):
                                info = tex_info(t)
                                if info and info not in texs:
                                    texs.append(info)
                        except Exception:
                            pass
                try:
                    pn = str(e.get_editor_property('parameter_name'))
                    if pn and pn != 'None':
                        params.append({'expr': cn, 'param': pn})
                except Exception:
                    pass
        except Exception as ex:
            d['expressions_error'] = str(ex)
        d['textures'] = texs
        d['named_params'] = params[:60]
    try:
        d['shading_model'] = str(a.get_editor_property('shading_model'))
        d['blend_mode'] = str(a.get_editor_property('blend_mode'))
    except Exception:
        pass
    try:
        d['two_sided'] = bool(a.get_editor_property('two_sided'))
    except Exception:
        pass
    return d


def dump_palette_benches():
    palette = u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
    rows = []
    if not palette:
        return rows
    for e in palette.get_editor_property('components'):
        eid = str(e.get_editor_property('id'))
        low = eid.lower()
        if not any(k in low for k in ('bench', 'forge', 'anvil', 'smelt')):
            continue
        mesh = e.get_editor_property('mesh')
        row = {'id': eid, 'mesh': mesh.get_path_name() if mesh else None}
        if mesh:
            slots = []
            for s in mesh.get_editor_property('static_materials'):
                mi = s.material_interface
                slots.append({
                    'slot': str(s.material_slot_name),
                    'material': mi.get_path_name() if mi else None})
            row['slots'] = slots
        rows.append(row)
    return rows


def dump_mesh_slots(path):
    m = u.load_asset(path)
    if not m:
        return {'missing': True}
    return {'slots': [
        {'slot': str(s.material_slot_name),
         'material': s.material_interface.get_path_name() if s.material_interface else None}
        for s in m.get_editor_property('static_materials')]}


result = {
    'materials': {p: dump_material(p) for p in MATERIALS},
    'palette_benches': dump_palette_benches(),
    'normal_workbench': dump_mesh_slots(
        '/Game/Building/Workbench/Meshes/SM_WBStandalone_Workbench'),
    'forge_props': dump_mesh_slots(
        '/Game/Props/ForgeInteraction20260927/SM_ForgeHammer'),
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
print('MATERIAL_INVENTORY_WRITTEN', OUT)
