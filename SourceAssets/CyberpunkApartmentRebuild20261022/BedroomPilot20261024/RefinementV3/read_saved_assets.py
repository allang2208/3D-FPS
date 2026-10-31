"""Read the saved mesh/material chain for this revision, without running the game."""
import unreal as u,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;L=u.MaterialEditingLibrary
assets=json.loads((R/'assets_saved.json').read_text('utf8'));manifest=json.loads((R/'assembly.json').read_text('utf8'))
rows=[]
for role,path in assets['materials'].items():
    m=u.load_asset(path);textures=[]
    for n in L.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionTextureSample) and n.texture:
            textures.append(dict(texture=n.texture.get_path_name(),sampler=str(n.sampler_type),srgb=n.texture.srgb,compression=str(n.texture.compression_settings)))
    normal=bool(L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL))
    if not normal or not any('SAMPLERTYPE_NORMAL' in t['sampler'] for t in textures):raise RuntimeError('Missing active normal '+role)
    if m.get_editor_property('two_sided') or m.get_editor_property('blend_mode')!=u.BlendMode.BLEND_OPAQUE:raise RuntimeError('Unexpected shell material '+role)
    rows.append(dict(role=role,path=path,normal_connected=normal,textures=textures))
meshrows=[]
for source in manifest['meshes']:
    row=assets['meshes'][source['key']];mesh=u.load_asset(row['path'])
    if hashlib.sha256(Path(source['fbx']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Final source mismatch '+source['key'])
    if any(not s.material_interface for s in mesh.static_materials):raise RuntimeError('Unbound material '+source['key'])
    meshrows.append(dict(key=source['key'],path=row['path'],slots=[str(s.material_slot_name) for s in mesh.static_materials],triangles=source['triangles']))
result=dict(stage='saved_assets_read_back',materials=rows,meshes=meshrows,game_run=False)
(R/'saved-assets-readback.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('BP3_SAVED_READBACK',len(meshrows),len(rows))
