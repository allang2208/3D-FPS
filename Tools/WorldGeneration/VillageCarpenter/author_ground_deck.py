"""Bake the original scanned floor into staggered west/east sections for plot 04."""
import json
import sys
from pathlib import Path

import unreal as u

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from carpenter_floor_repairs import DECK, INFILL_ROW, JOINTS

E = u.EditorAssetLibrary
Q = u.GeometryScript_MeshQueries
G = u.GeometryScript_AssetUtils
L = u.GeometryScript_List
edit = u.GeometryScript_MeshEdits
source = u.load_asset('/Game/UnrealNormandy/StaticMeshes/SM_WoodenFloor_00A')
source_slots = list(source.static_materials)
wood = u.load_asset('/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterSawn')
iron = u.load_asset('/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron')
owner = 'Carpenter04StaggeredDeck'
identity = u.Transform()
if not (wood and iron):
    raise RuntimeError('The carpenter surfaces are required for the repair plank')


def positions(mesh):
    _, points, _ = Q.get_all_vertex_positions(mesh, False)
    return list(L.convert_vector_list_to_array(points))


def reshape(plank, east, shift, worn=False):
    pts = positions(plank)
    edge = min(v.x for v in pts) if east else max(v.x for v in pts)
    target = (-150 if east else 150) + shift + (.12 if east else -.12)
    # Leave the outer half of the board untouched. All support slats keep their
    # original dimensions and longitudinal grain stays aligned with the splice.
    for p in pts:
        weight = max(0., (-p.x if east else p.x) - 8.) / (abs(edge) - 8.)
        inset = (1.4 + .02*(p.y+100)) if worn and east else 0.
        p.x += weight * (target + inset - edge)
    edit.set_all_mesh_vertex_positions(plank, L.convert_array_to_vector_list(pts))


def top_at(mesh, points, x, y):
    _, face_list, _ = Q.get_all_triangle_indices(mesh, False)
    z_hits = []
    for f in L.convert_triangle_list_to_array(face_list):
        a,b,c = (points[i] for i in (f.x, f.y, f.z))
        dx1,dy1,dx2,dy2 = b.x-a.x,b.y-a.y,c.x-a.x,c.y-a.y
        det = dx1*dy2-dy1*dx2
        if abs(det) < 1.e-8:
            continue
        s = ((x-a.x)*dy2-(y-a.y)*dx2)/det
        t = (dx1*(y-a.y)-dy1*(x-a.x))/det
        if s >= -1.e-6 and t >= -1.e-6 and s+t <= 1.000001:
            z_hits.append(a.z+s*(b.z-a.z)+t*(c.z-a.z))
    return max(z_hits)


def fixings(mesh):
    points = positions(mesh)
    middle_y = (max(v.y for v in points) + min(v.y for v in points))*.5
    heads = u.DynamicMesh()
    # Joist centres in the actual donor tile, with two flush forged clouts per
    # bearing. Their heads sit on the scanned board's surface at each nail.
    for x in (-85., 29., 89., 142.):
        for dy in (-6.4, 6.4):
            y = middle_y + dy
            z = top_at(mesh, points, x, y)
            t = u.Transform(location=[x,y,z-.16], rotation=u.Rotator(yaw=x+dy),
                            scale=[1.,.87,1.])
            u.GeometryScript_Primitives.append_cylinder(heads,u.GeometryScriptPrimitiveOptions(),
                                                         t,.48,.28,7,0,True)
    u.GeometryScript_Materials.clear_material_i_ds(heads,1)
    edit.append_mesh(mesh,heads,identity)


def save(suffix, mesh, materials, names, collide):
    path = DECK + suffix
    asset = E.load_asset(path) if E.does_asset_exist(path) else None
    if asset and E.get_metadata_tag(asset, 'CarpenterDeckOwner') != owner:
        raise RuntimeError('Existing asset has different owner: '+path)
    if not asset:
        opts = u.GeometryScriptCreateNewStaticMeshAssetOptions(
            enable_collision=collide, enable_nanite=False,
            enable_recompute_normals=False, enable_recompute_tangents=True)
        asset,outcome = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh,path,opts)
        if not asset or outcome != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot create '+path)
    nanite = source.get_editor_property('nanite_settings')
    nanite.enabled = True
    nanite.fallback_percent_triangles = 1.
    nanite.fallback_relative_error = 0.
    opts = u.GeometryScriptCopyMeshToAssetOptions(
        replace_materials=True, new_materials=materials, new_material_slot_names=names,
        enable_recompute_normals=False, enable_recompute_tangents=True,
        apply_nanite_settings=True,new_nanite_settings=nanite)
    _,outcome = G.copy_mesh_to_static_mesh(mesh,asset,opts,u.GeometryScriptMeshWriteLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot write '+path)
    if collide:
        # Measured original walking plane is 0.12 cm above the finished floor
        # after the 1.2 vertical scale. Keep it under the removable insert too.
        body = asset.get_editor_property('body_setup')
        aggregate = body.get_editor_property('agg_geom')
        box = u.KBoxElem()
        box.set_editor_property('center',u.Vector(0,0,10.05))
        for prop,size in (('x',300.),('y',300.),('z',20.1)):
            box.set_editor_property(prop,size)
        aggregate.set_editor_property('box_elems',[box])
        aggregate.set_editor_property('convex_elems',[])
        body.set_editor_property('agg_geom',aggregate)
        body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    E.set_metadata_tag(asset,'CarpenterDeckOwner',owner)
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Cannot save '+path)
    return path


def components():
    mesh,outcome = G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read floor boards')
    _,pieces = u.GeometryScript_MeshDecomposition.split_mesh_by_components(mesh,None)
    boards, below = [], []
    for piece in pieces:
        b = Q.get_mesh_bounding_box(piece)
        if b.min.z > 11 and b.max.x-b.min.x > 280:
            boards.append(((b.min.y+b.max.y)*.5,piece))
        else:
            below.append(piece)
    boards.sort(key=lambda item:item[0])
    if len(boards) != len(JOINTS):
        raise RuntimeError('The floor donor needs ten separate surface boards')
    return [p for _,p in boards],below


def bake():
    E.make_directory(DECK.rsplit('/',1)[0])
    materials = [s.material_interface for s in source_slots]
    names = [str(s.material_slot_name) for s in source_slots]
    receipt = []
    for east in (False,True):
        boards,below = components()
        tile = u.DynamicMesh()
        for part in below:
            edit.append_mesh(tile,part,identity)
        for i,plank in enumerate(boards):
            if east and i == INFILL_ROW:
                continue
            reshape(plank,east,JOINTS[i])
            edit.append_mesh(tile,plank,identity)
        receipt.append(save('East' if east else 'West',tile,materials,names,True))
    for worn in (True,False):
        boards,_ = components()
        plank = boards[INFILL_ROW]
        reshape(plank,True,JOINTS[INFILL_ROW],worn)
        if worn:
            receipt.append(save('WornPlank',plank,materials,names,False))
        else:
            u.GeometryScript_Materials.clear_material_i_ds(plank,0)
            fixings(plank)
            receipt.append(save('SplicedPlank',plank,[wood,iron],['Sawn','Iron'],False))
    out = here.parents[2]/'SourceAssets/HillsVillageCarpenter'
    (out/'ground-deck-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    u.log('CARPENTER_GROUND_DECK_SAVED '+str(len(receipt)))


bake()
