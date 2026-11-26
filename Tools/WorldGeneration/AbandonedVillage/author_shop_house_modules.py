"""Fit the original stone jambs and timber deck borders, retaining their scan UVs and paint."""
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shop_house_modules import BAKERY_BAYS, BOARDS, GUNSHOP_EDGES, HILLS, KIT, floor_tiles, wall_layout

ED = u.EditorAssetLibrary
ASSET = u.GeometryScript_AssetUtils
EDIT = u.GeometryScript_MeshEdits
MATS = u.GeometryScript_Materials
IDENTITY = u.Transform()


def read(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing donor '+path)
    mesh, outcome = ASSET.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read geometry '+path)
    return mesh, [s.material_interface for s in asset.static_materials]


def clip(dm, axis, edge, direction):
    point, normal = [0.,0.,0.], [0.,0.,0.]
    point[axis], normal[axis] = edge, direction
    plane = u.Transform(location=point,rotation=u.MathLibrary.make_rot_from_z(u.Vector(*normal)))
    u.GeometryScript_MeshBooleans.apply_mesh_plane_cut(dm,plane,
        u.GeometryScriptMeshPlaneCutOptions(fill_holes=False,fill_spans=False))


def register_slots(dm, source, materials):
    for i in range(len(source)):
        MATS.remap_material_i_ds(dm,i,128+i)
    for i,mat in enumerate(source):
        if mat not in materials:
            materials.append(mat)
        MATS.remap_material_i_ds(dm,128+i,materials.index(mat))


def save_piece(path, dm, materials, collision):
    original = u.load_asset(collision)
    asset = ED.load_asset(path) if ED.does_asset_exist(path) else ED.duplicate_asset(collision,path)
    if not original or not asset:
        raise RuntimeError('Cannot prepare '+path)
    asset.modify()
    # This reference supplies the original continuous walking/doorway envelope
    # for all the visual modules, including the uncovered tile edges.
    asset.set_editor_property('complex_collision_mesh',original)
    settings = asset.get_editor_property('nanite_settings')
    settings.enabled = True
    settings.fallback_percent_triangles = .32
    settings.fallback_relative_error = .5
    opts = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,
        new_material_slot_names=[m.get_name() for m in materials],enable_recompute_normals=False,
        enable_recompute_tangents=True,apply_nanite_settings=True,new_nanite_settings=settings)
    _, outcome = ASSET.copy_mesh_to_static_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not author '+path)
    asset.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
                                                               u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not ED.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+path)
    return dict(asset=path,triangles=dm.get_triangle_count(),materials=[m.get_path_name() for m in materials],collision=collision)


def opening_template(door, materials, placed_materials=None):
    # Measured extents of the whole clear opening on the original meshes. Each
    # corner and each lintel retains its native surface instead of stamping a flat reveal.
    xs = (-146.,-75.,79.,146.) if door else (-146.,-45.,50.,146.)
    zs = (-147.,-132.,93.,147.) if door else (-147.,-32.,91.,147.)
    mesh, mats = read(KIT + ('SM_H_OldWall_Door_00A' if door else 'SM_H_OldWall_Window_00A'))
    register_slots(mesh,placed_materials if placed_materials is not None else mats,materials)
    cells = []
    for i in range(3):
        for j in range(3):
            if i==1 and (j==1 or (door and j==0)):
                continue
            piece = u.DynamicMesh()
            EDIT.append_mesh(piece,mesh,IDENTITY)
            for index, axis, limits in ((i,0,xs),(j,2,zs)):
                if index>0:
                    clip(piece,axis,limits[index],-1)
                if index<2:
                    clip(piece,axis,limits[index+1],1)
            cells.append((i,j,piece))
    return xs,zs,cells


def bakery_bays():
    dm, materials = u.DynamicMesh(), []
    templates = {door: opening_template(door,materials) for door in (False,True)}
    for frame,left,right,low,high,hole in wall_layout():
        if not hole:
            continue
        a,b,sill,head = hole
        door = sill==0
        xs,zs,cells = templates[door]
        dx = (left,a-3.,b+3.,right)
        dz = (low,sill-2.,head+3.,high)
        for i,j,piece in cells:
            sx=(dx[i+1]-dx[i])/(xs[i+1]-xs[i])
            sz=(dz[j+1]-dz[j])/(zs[j+1]-zs[j])
            x_offset=dx[i]-xs[i]*sx
            if i != 1 and sx < .85:
                # Keep the original stones at the reveal. Trim the far side of
                # a narrow pier instead of squeezing an entire row into it.
                jamb=u.DynamicMesh()
                EDIT.append_mesh(jamb,piece,IDENTITY)
                anchor=i+1 if i==0 else i
                sx=1.
                x_offset=dx[anchor]-xs[anchor]
                clip(jamb,0,dx[i if i==0 else i+1]-x_offset,-1 if i==0 else 1)
                piece=jamb
            fit=u.Transform(location=(x_offset,0,dz[j]-zs[j]*sz),scale=(sx,.72,sz))
            EDIT.append_mesh(dm,piece,u.MathLibrary.compose_transforms(fit,frame))
    return save_piece(BAKERY_BAYS,dm,materials,HILLS+'VillageBakery/Architecture/SM_Bakery_HouseShell')


def gunshop_edges():
    old = HILLS+'VillageGunshop/Architecture/SM_Gunshop_Floors'
    # Keep just the original sloping stone doorstep outside the entrance.
    dm, old_mats = read(old)
    clip(dm,1,-13.01,1)
    flags = next(m for m in old_mats if m.get_name()=='M_ChapelFlagstone')
    MATS.clear_material_i_ds(dm,0)
    materials = [flags]
    tile, native = read(BOARDS)
    register_slots(tile,native,materials)
    for frame, rectangles in floor_tiles():
        for l,r,b,t in rectangles or ():
            piece=u.DynamicMesh()
            EDIT.append_mesh(piece,tile,frame)
            for axis,lo,hi in ((0,l,r),(1,b,t)):
                clip(piece,axis,lo,-1)
                clip(piece,axis,hi,1)
            EDIT.append_mesh(dm,piece,IDENTITY)
    # Reuse the solid substrates of the original sales floor and loft. The
    # loft substrate already wraps around the exact three sides of the stairs.
    backing, slots = read(old)
    timber = next(m for m in slots if m.get_name()=='M_ChapelTimber')
    for index, material in enumerate(slots):
        if material.get_name() not in ('M_ChapelTimber','M_ChapelLimewash'):
            MATS.delete_triangles_by_material_id(backing,index)
    materials.append(timber)
    MATS.clear_material_i_ds(backing,materials.index(timber))
    EDIT.append_mesh(dm,backing,u.Transform(location=(0,0,-4.5)))
    return save_piece(GUNSHOP_EDGES,dm,materials,old)
