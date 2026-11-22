"""Fit the original Normandy rubble masonry to the bakery's existing wall openings."""
import json
import os
import sys
from math import floor
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bakery_shell import SOURCE_MASONRY_SHELL, PACK
from shell_geometry import EAVE, WALLS, Mesh, wall

DONOR = '/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_00A'
ORIGINAL = PACK+'/SM_Bakery_HouseShell'
STONE = '/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00A'
MORTAR = '/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A'
EDITS = u.GeometryScript_MeshEdits
ASSETS = u.GeometryScript_AssetUtils
IDENTITY = u.Transform()


class Lining(Mesh):
    """Keep the existing inner limewash and footing; recede just the outside behind the stones."""
    def begin(self,axis,pos):
        self.depth_axis = 1 if axis == 'X' else 0
        self.line = pos
        self.outward = -1 if (axis == 'X' and pos == 0) or (axis == 'Y' and pos < 0) else 1

    def face(self,mat,points,center,grain=None):
        def recess(v):
            p = list(v)
            d = (p[self.depth_axis]-self.line)*self.outward
            if d > 0:
                p[self.depth_axis] = self.line+self.outward*(d*.055)
            return tuple(p)
        if all((p[self.depth_axis]-self.line)*self.outward > 0 for p in points):
            mat = 'NativeMortar'
        super().face(mat,[recess(p) for p in points],recess(center),grain)


def trim(mesh,point,normal):
    frame = u.Transform(location=point,rotation=u.MathLibrary.make_rot_from_z(u.Vector(*normal)))
    u.GeometryScript_MeshBooleans.apply_mesh_plane_cut(mesh,frame,
        u.GeometryScriptMeshPlaneCutOptions(fill_holes=False,fill_spans=False))


def wall_panels(openings,start,end):
    rough = [(a-9,b+9,z-7 if z else z,h+11) for a,b,z,h in openings]
    levels = sorted({-12.,64.,EAVE,*[v for _,_,z,h in rough for v in (z,h)]})
    for low,high in zip(levels,levels[1:]):
        cursor = start
        for a,b in sorted((a,b) for a,b,z,h in rough if z < high and h > low)+[(end,end)]:
            if a > cursor:
                yield cursor,a,low,high,15.4 if high <= 64. else 12.
            cursor = max(cursor,b)


def build_facade(result,tile,axis,pos,start,end,openings,donor_depth):
    # The negative Y face is outside on the original house wall. Work in that
    # frame for each facade, with +X along the wall and +Z up.
    if axis == 'X':
        origin, yaw = (0,pos,0), (0 if pos == 0 else 180)
    else:
        origin, yaw = (pos,0,0), (-90 if pos < 0 else 90)
    along = 1 if yaw in (0,90) else -1
    attach = u.Transform(location=origin,rotation=u.Rotator(yaw=yaw))
    sections = list(wall_panels(openings,start,end))
    if axis == 'X':
        sections.append((-391,391,EAVE,790.,9.))
    # The donor's 2.72 m uninterrupted centre is sampled at the same scale
    # as the inherited longhouse (horizontal width adjustment, 1.20 house scale).
    pitch_x,pitch_z = 272*1.118034*1.2,272*1.2
    for a,b,lo,hi,depth in sections:
        l,r = sorted((along*a,along*b))
        for col in range(floor(l/pitch_x),floor((r-1.e-6)/pitch_x)+1):
            for row in range(floor(lo/pitch_z),floor((hi-1.e-6)/pitch_z)+1):
                x0,x1 = max(l,col*pitch_x),min(r,(col+1)*pitch_x)
                z0,z1 = max(lo,row*pitch_z),min(hi,(row+1)*pitch_z)
                block = u.DynamicMesh()
                EDITS.append_mesh(block,tile,IDENTITY)
                # Alternating cuts meet at the exact same native edge profile,
                # including the normal map, rather than exposing rectangular seams.
                fit = u.Transform(location=((col+.5)*pitch_x,-1.6,(row+.5)*pitch_z),
                    scale=(((-1)**col)*pitch_x/272,(depth-1.6)/donor_depth,((-1)**row)*pitch_z/272))
                u.GeometryScript_MeshTransforms.transform_mesh(block,fit)
                trim(block,(x0,0,0),(-1,0,0))
                trim(block,(x1,0,0),(1,0,0))
                trim(block,(0,0,z0),(0,0,-1))
                trim(block,(0,0,z1),(0,0,1))
                if lo == EAVE:
                    slope = (790.-EAVE)/391.
                    trim(block,(0,0,790),(slope,0,1))
                    trim(block,(0,0,790),(-slope,0,1))
                EDITS.append_mesh(result,block,attach)


def publish():
    donor, original = u.load_asset(DONOR), u.load_asset(ORIGINAL)
    if not donor or not original:
        raise RuntimeError('Missing the abandoned village wall or the original bakery shell')
    native = [slot.material_interface for slot in donor.static_materials]
    native_paths = [m.get_path_name().split('.')[0] for m in native]
    if STONE not in native_paths or MORTAR not in native_paths:
        raise RuntimeError('The original wall material bindings have changed: '+repr(native_paths))
    base = Lining()
    wall(base,Mesh(),Mesh(),base.begin)
    mats = {str(s.material_slot_name): s.material_interface for s in original.static_materials}
    mats['NativeMortar'] = native[native_paths.index(MORTAR)]
    names = list(base.slots)
    surfaces = [mats[n] for n in names]
    result = u.DynamicMesh()
    for index,name in enumerate(names):
        vertices,normals,uvs,triangles = base.slots[name]
        buf = u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*v) for v in vertices],
            normals=[u.Vector(*v) for v in normals],uv0=[u.Vector2D(*v) for v in uvs],
            triangles=[u.IntVector(*v) for v in triangles])
        EDITS.append_buffers_to_mesh(result,buf,material_id=index)
    tile,status = ASSETS.copy_mesh_from_static_mesh(donor,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not read the donor masonry')
    for index,material in enumerate(native):
        # Temporary IDs are outside both the source and destination slot ranges.
        u.GeometryScript_Materials.remap_material_i_ds(tile,index,100+index)
        if material not in surfaces:
            names.append('AbandonedHouseStone')
            surfaces.append(material)
    for index,material in enumerate(native):
        u.GeometryScript_Materials.remap_material_i_ds(tile,100+index,surfaces.index(material))
    trim(tile,(0,0,0),(0,1,0))
    for edge,normal in [((-136,0,0),(-1,0,0)),((136,0,0),(1,0,0)),
                        ((0,0,-136),(0,0,-1)),((0,0,136),(0,0,1))]:
        trim(tile,edge,normal)
    # Simplify the source once, before it is repeated around the building. The
    # bound is four millimetres at the original scale and keeps mortar/UV seams.
    u.GeometryScript_MeshSimplification.apply_simplify_to_tolerance(tile,.4,u.GeometryScriptSimplifyMeshOptions())
    for axis,pos,start,end,openings in WALLS:
        build_facade(result,tile,axis,pos,start,end,openings,-donor.get_bounding_box().min.y)
    editor = u.EditorAssetLibrary
    out = u.load_asset(SOURCE_MASONRY_SHELL) if editor.does_asset_exist(SOURCE_MASONRY_SHELL) else editor.duplicate_asset(ORIGINAL,SOURCE_MASONRY_SHELL)
    if not out:
        raise RuntimeError('Could not allocate bakery masonry')
    out.modify()
    out.set_editor_property('complex_collision_mesh',original)
    nanite = out.get_editor_property('nanite_settings')
    nanite.enabled = True
    nanite.fallback_percent_triangles = .28
    nanite.fallback_relative_error = .65
    opts = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
        replace_materials=True,new_materials=surfaces,new_material_slot_names=names,
        apply_nanite_settings=True,new_nanite_settings=nanite)
    _,status = ASSETS.copy_mesh_to_static_mesh(result,out,opts,u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS or not editor.save_loaded_asset(out,False):
        raise RuntimeError('Could not save the repaired bakery masonry')
    return dict(mesh=SOURCE_MASONRY_SHELL,geometry_donor=DONOR,donor_materials=native_paths,
                collision=ORIGINAL,surface_triangles=result.get_triangle_count())


if __name__ == '__main__':
    Path(os.environ['BAKERY_ARCHITECTURE_RECEIPT']).write_text(json.dumps(publish(),indent=2),encoding='utf8')
