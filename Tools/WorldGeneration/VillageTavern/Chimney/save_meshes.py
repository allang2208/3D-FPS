"""Build the three fitted tavern chimney pieces using the existing village PBR materials."""
import json
from pathlib import Path
import sys

import unreal as u

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from chimney_head import head, flashing

source = here.parents[3] / 'SourceAssets/HillsVillageTavern/KitchenRoof'
dest = '/Game/WorldGeneration/VillageTavern/KitchenRoof'
materials = {
    'Mortar': '/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A',
    'YardCap': '/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelYardCap',
    'YardField': '/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelYardField',
    'Lead': '/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelLead',
    'Soot': '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ChimneyR8/Materials/M_ChimneyFlueSoot',
    'HearthStone': '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_HearthStone',
}
seats = json.loads((source/'slate-seats.json').read_text(encoding='utf-8'))
def seat(x,y):
    return seats['%.2f,%.2f'%(x,y)]


def save(name, form, solid):
    lib = u.EditorAssetLibrary
    path = dest+'/SM_TavernChimney'+name
    loaded = lib.load_asset(path) if lib.does_asset_exist(path) else None
    dynamic = u.DynamicMesh()
    slots, bindings = [], []
    for slot,g in form.groups.items():
        if not g['triangles']:
            continue
        material = u.load_asset(materials[slot])
        if not material:
            raise RuntimeError('Missing chimney material '+materials[slot])
        buffers = u.GeometryScriptSimpleMeshBuffers(
            vertices=[u.Vector(*p) for p in g['vertices']],
            normals=[u.Vector(*p) for p in g['normals']], uv0=[u.Vector2D(*p) for p in g['uv0']],
            triangles=[u.IntVector(*t) for t in g['triangles']])
        u.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic,buffers,material_id=len(slots))
        slots.append(slot)
        bindings.append(material)
    if not loaded:
        loaded,status = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,path,
            u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=solid,enable_nanite=solid,
                enable_recompute_normals=False,enable_recompute_tangents=True))
        if not loaded or status != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Could not create '+path)
    nanite = loaded.get_editor_property('nanite_settings')
    nanite.enabled = solid
    nanite.fallback_percent_triangles = 1.
    nanite.fallback_relative_error = 0.
    options = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False, enable_recompute_tangents=True,
        replace_materials=True,new_materials=bindings,new_material_slot_names=slots,
        apply_nanite_settings=True,new_nanite_settings=nanite)
    _,status = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,loaded,options,u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not write '+path)
    if solid:
        loaded.get_editor_property('body_setup').set_editor_property(
            'collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not lib.save_loaded_asset(loaded,False):
        raise RuntimeError('Could not save '+path)
    u.log('TAVERN_CHIMNEY_SAVED '+path)
    return dict(path=path,triangles=form.data()['triangles'],materials=slots)


results = [save('Crown',head(False),True),save('BrokenCrown',head(True),True),
           save('Flashing',flashing(seat),False)]
(source/'chimney-saved.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
