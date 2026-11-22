"""Publish the south longhouse to separate packages in the background authoring host."""
import hashlib
import json
import os
from math import floor
from pathlib import Path
import sys

import unreal as u

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from gunshop_shell import PACK
from gunshop_shell_geometry import BELT, WALLS, models, regions

HILLS='/Game/WorldGeneration/TemperateHills/'
CHAPEL=HILLS+'OldChapel/Materials/M_Chapel'
SURFACES={
    'Plaster':CHAPEL+'Limewash', 'Mortar':CHAPEL+'Limewash', 'Flags':CHAPEL+'Flagstone',
    'BedMortar':HILLS+'VillageMasonry/Relief/MI_Main_Mortar_00A',
    'Oak':HILLS+'VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak',
    'Sawn':HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterSawn',
    'Iron':HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterIron',
    'DarkWood':CHAPEL+'Timber','Slate':CHAPEL+'Slate','Lead':CHAPEL+'Lead',
}
DONOR=HILLS+'VillageMasonry/ReliefMeshes/SM_Bakery_AbandonedHouseMasonry'
LIB=u.EditorAssetLibrary
EDITS=u.GeometryScript_MeshEdits
CONVERT=u.GeometryScript_AssetUtils
IDENTITY=u.Transform()


def trim(mesh, point, normal):
    cutting=u.Transform(location=point,rotation=u.MathLibrary.make_rot_from_z(u.Vector(*normal)))
    u.GeometryScript_MeshBooleans.apply_mesh_plane_cut(mesh,cutting,
        u.GeometryScriptMeshPlaneCutOptions(fill_holes=False,fill_spans=False))


def apron():
    donor=LIB.load_asset(DONOR)
    if not donor:
        raise RuntimeError('Missing restored village stonework '+DONOR)
    tile,status=CONVERT.copy_mesh_from_static_mesh(donor,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read original displaced masonry')
    # Surveyed uninterrupted panel in the bakery's western wall. Take the
    # baked relief, original painted stone joints and shader slots together.
    for point,normal in [((-393,0,0),(1,0,0)),((0,312,0),(0,-1,0)),((0,584,0),(0,1,0)),
                         ((0,0,80),(0,0,-1)),((0,0,312),(0,0,1))]:
        trim(tile,point,normal)
    u.GeometryScript_MeshTransforms.translate_mesh(tile,u.Vector(392,-448,-196))
    u.GeometryScript_MeshTransforms.transform_mesh(tile,u.Transform(rotation=u.Rotator(yaw=90)))
    if not tile.get_triangle_count():
        raise RuntimeError('There was no exterior relief in the donor panel')
    out=u.DynamicMesh()
    for axis,line,start,end,openings in WALLS:
        yaw=(0 if line==0 else 180) if axis=='X' else (-90 if line<0 else 90)
        sign=1 if yaw in (0,90) else -1
        origin=(0,line,0) if axis=='X' else (line,0,0)
        frame=u.Transform(location=origin,rotation=u.Rotator(yaw=yaw))
        for begin,end_,z,h in regions(start,end,openings,-17,BELT-6):
            a,b=sorted((sign*begin,sign*end_))
            for col in range(floor(a/272),floor((b-.0001)/272)+1):
                l,r=max(a,col*272),min(b,(col+1)*272)
                for row in range(floor(z/232),floor((h-.0001)/232)+1):
                    low,high=max(z,row*232),min(h,(row+1)*232)
                    if r-l<.01 or high-low<.01:
                        continue
                    piece=u.DynamicMesh()
                    xf=u.Transform(location=((col+.5)*272,-11.9,(row+.5)*232),
                                   scale=((-1)**col,1,(-1)**row))
                    EDITS.append_mesh(piece,tile,xf)
                    for at,direction in [((l,0,0),(-1,0,0)),((r,0,0),(1,0,0)),
                                         ((0,0,low),(0,0,-1)),((0,0,high),(0,0,1))]:
                        trim(piece,at,direction)
                    EDITS.append_mesh(out,piece,frame)
    surfaces=[s.material_interface for s in donor.static_materials]
    names=[str(s.material_slot_name) for s in donor.static_materials]
    return out,names,surfaces


def build_mesh(model):
    dm=u.DynamicMesh()
    names=list(model.slots)
    surfaces=[LIB.load_asset(SURFACES[name]) for name in names]
    if not all(surfaces):
        raise RuntimeError('Missing architectural material '+repr(names))
    for index,name in enumerate(names):
        vertices,normals,uvs,indices=model.slots[name]
        buf=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*p) for p in vertices],
            normals=[u.Vector(*p) for p in normals],uv0=[u.Vector2D(*p) for p in uvs],
            triangles=[u.IntVector(*p) for p in indices])
        EDITS.append_buffers_to_mesh(dm,buf,material_id=index)
    return dm,names,surfaces


def publish():
    results={}
    digest=hashlib.sha256((HERE/'gunshop_shell_geometry.py').read_bytes()+Path(__file__).read_bytes()).hexdigest()
    LIB.make_directory(PACK.rsplit('/',1)[0])
    parts=models()
    for key in [*parts,'StoneApron']:
        path=PACK+key
        asset=LIB.load_asset(path) if LIB.does_asset_exist(path) else None
        if asset and LIB.get_metadata_tag(asset,'GunshopArchitectureSource')==digest:
            results[key]=dict(asset=path)
            continue
        dm,names,surfaces=apron() if key=='StoneApron' else build_mesh(parts[key])
        collision=key!='StoneApron'
        nanite=key in ('Roof','StoneApron','Floors','Timber')
        if not asset:
            options=u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=True,enable_collision=collision,enable_nanite=False)
            asset,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,options)
            if not asset or status!=u.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError('Could not create '+path)
        settings=asset.get_editor_property('nanite_settings')
        settings.enabled=nanite
        settings.fallback_percent_triangles=.32 if key=='StoneApron' else 1.
        settings.fallback_relative_error=.7 if key=='StoneApron' else 0.
        options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
            replace_materials=True,new_materials=surfaces,new_material_slot_names=names,
            apply_nanite_settings=True,new_nanite_settings=settings)
        _,status=CONVERT.copy_mesh_to_static_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Could not fit '+path)
        if collision:
            asset.get_editor_property('body_setup').set_editor_property(
                'collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        LIB.set_metadata_tag(asset,'GunshopArchitectureSource',digest)
        if not LIB.save_loaded_asset(asset,False):
            raise RuntimeError('Could not write '+path)
        results[key]=dict(asset=path,triangles=dm.get_triangle_count())
        u.log('GUNSHOP_ARCHITECTURE_SAVED '+path)
    receipt=Path(os.environ['BAKERY_LEVEL_RUN'])/'level-saved.json'
    receipt.write_text(json.dumps(results,indent=2),encoding='utf-8')


if __name__ == '__main__':
    publish()
