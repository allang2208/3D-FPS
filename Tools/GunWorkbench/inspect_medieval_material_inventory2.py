"""Second read-only pass: parent material texture tables, casting-station
survey, Normandy wood family, plus PNG/TGA export of key textures for offline
Blender previews. Exports land in Saved/GunWorkbench20260927/texexport/.
"""
import json, os
from pathlib import Path
import unreal as u

SAVED = Path('D:/FPS3D/FPSGAME/Saved/GunWorkbench20260927')
TEXDIR = SAVED / 'texexport'
TEXDIR.mkdir(parents=True, exist_ok=True)
OUT = SAVED / 'material-inventory2.json'

PARENTS = [
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/M_WBK_Wood',
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/M_WBK_Surface',
    '/Game/Dungeons/ArtPass20260922/Materials/M_Prop_Bucket_Wood',
    '/Game/Dungeons/ArtPass20260922/Materials/M_Prop_Bucket_Metal',
    '/Game/Dungeons/ArtPass20260922/Materials/M_Prop_Rope_All',
    '/Game/Dungeons/ArtPass20260922/Materials/M_Prop_StepLadder_All',
    '/Game/Props/CastingStation20260926/AnvilReferenceV3/Materials/M_AnvilReferenceSteel',
    '/Game/UnrealNormandy/MaterialInstances/MI_Wood_00A',
]


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
    if cls == 'Material':
        texs = []
        try:
            exprs = None
            for ep in ('expression_collection', 'expressions'):
                try:
                    ec = a.get_editor_property(ep)
                    exprs = ec.expressions if hasattr(ec, 'expressions') else ec
                    if exprs is not None:
                        break
                except Exception:
                    continue
            if exprs is None:
                raise RuntimeError('no expression property')
            for e in exprs:
                cn = e.get_class().get_name()
                if 'Texture' in cn:
                    for pr in ('texture', 'mask'):
                        try:
                            t = e.get_editor_property(pr)
                            if t and hasattr(t, 'get_path_name'):
                                rec = {'path': t.get_path_name()}
                                for sp in ('size_x', 'size_y'):
                                    try:
                                        rec[sp] = int(t.get_editor_property(sp))
                                    except Exception:
                                        pass
                                if rec not in texs:
                                    texs.append(rec)
                        except Exception:
                            pass
        except Exception as ex:
            d['expressions_error'] = str(ex)
        d['textures'] = texs
    else:
        for prop in ('texture_parameter_values', 'scalar_parameter_values',
                     'vector_parameter_values'):
            vals = []
            try:
                for it in a.get_editor_property(prop):
                    ent = {'raw': str(it)}
                    try:
                        v = it.get_editor_property('parameter_value')
                        ent['value'] = (v.get_path_name()
                                        if hasattr(v, 'get_path_name') else str(v))
                    except Exception:
                        pass
                    vals.append(ent)
            except Exception:
                pass
            d[prop] = vals
    return d


def dump_dir(dir_path, classes=('StaticMesh', 'Material', 'MaterialInstanceConstant',
                                'Texture2D')):
    rows = []
    try:
        assets = u.EditorAssetLibrary.list_assets(dir_path, recursive=True)
    except Exception as ex:
        return [{'error': str(ex)}]
    for a in assets:
        obj = u.EditorAssetLibrary.load_asset(a)
        if not obj:
            continue
        cn = obj.get_class().get_name()
        if cn not in classes:
            continue
        row = {'path': a, 'class': cn}
        if cn == 'StaticMesh':
            row['slots'] = [
                {'slot': str(s.material_slot_name),
                 'material': s.material_interface.get_path_name()
                 if s.material_interface else None}
                for s in obj.get_editor_property('static_materials')]
        rows.append(row)
    return rows


EXPORT = [
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopBenchPolish/Textures/T_WSBench_BenchWood_BaseColor',
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopBenchPolish/Textures/T_WSBench_BenchWood_Normal',
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopBenchPolish/Textures/T_WSBench_BenchWood_Roughness',
    '/Game/Dungeons/ArtPass20260922/Textures/T_Prop_Bucket_Wood_basecolor',
    '/Game/Dungeons/ArtPass20260922/Textures/T_Prop_Bucket_Wood_normal',
    '/Game/Dungeons/ArtPass20260922/Textures/T_Prop_Bucket_Wood_roughness',
    '/Game/Dungeons/ArtPass20260922/Textures/T_Prop_StepLadder_All_basecolor',
    '/Game/Dungeons/ArtPass20260922/Textures/T_Prop_StepLadder_All_ao',
]


def export_textures(paths):
    exported = []
    tools = u.AssetToolsHelpers.get_asset_tools()
    for p in paths:
        t = u.load_asset(p)
        if not t:
            continue
        name = p.rsplit('/', 1)[-1]
        dest = str(TEXDIR / (name + '.png'))
        task = u.AssetExportTask()
        task.object = t
        task.filename = dest
        task.automated = True
        task.selected = False
        task.replace_identical = True
        task.prompt = False
        ok = tools.export_asset_task(task)
        exported.append({'path': p, 'dest': dest, 'ok': bool(ok),
                         'exists': os.path.exists(dest)})
    return exported


result = {
    'parents': {p: dump_material(p) for p in PARENTS},
    'casting_station': dump_dir('/Game/Props/CastingStation20260926'),
    'normandy_wood_instances': dump_dir(
        '/Game/UnrealNormandy/MaterialInstances',
        classes=('MaterialInstanceConstant',)),
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
print('INVENTORY2_WRITTEN')
