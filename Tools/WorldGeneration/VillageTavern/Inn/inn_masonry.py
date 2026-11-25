"""Cut both faces of the taproom's actual Normandy rubble tile, retaining material IDs and UVs."""
import math
import unreal as u

DONOR='/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_00A'
STONE='/Game/WorldGeneration/TemperateHills/VillageMasonry/WallVariants/MI_Main_StoneWall_00A_VillageWall'
QUOIN='/Game/WorldGeneration/TemperateHills/VillageMasonry/WallVariants/MI_StoneWall_Pieces_00B_Gray_VillageWall'
MORTAR='/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A'
EDITS=u.GeometryScript_MeshEdits

def cut(mesh,point,normal):
    plane=u.Transform(location=point,rotation=u.MathLibrary.make_rot_from_z(u.Vector(*normal)))
    u.GeometryScript_MeshBooleans.apply_mesh_plane_cut(mesh,plane,
        u.GeometryScriptMeshPlaneCutOptions(fill_holes=False,fill_spans=False))

def make_tile():
    src=u.load_asset(DONOR)
    tile,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(src,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(DONOR)
    for where,n in [((-136,0,0),(-1,0,0)),((136,0,0),(1,0,0)),((0,0,-136),(0,0,-1)),((0,0,136),(0,0,1))]:
        cut(tile,where,n)
    u.GeometryScript_MeshSimplification.apply_simplify_to_tolerance(tile,.72,u.GeometryScriptSimplifyMeshOptions())
    # The backing mesh occupies slot 0. Copy original mortar into slot 0 and original stone into slot 1.
    mats=u.GeometryScript_Materials
    mats.remap_material_i_ds(tile,0,17);mats.remap_material_i_ds(tile,1,0);mats.remap_material_i_ds(tile,17,1)
    return tile

def dress(mesh,tile,panels):
    px,pz=340.,318.
    for axis,line,left,right,low,high,depth in panels:
        if depth>22.:
            if left in (-724,-426):left-=21.
            if right in (644,828):right+=21.
        for col in range(math.floor(left/px),math.ceil(right/px)):
            for row in range(math.floor(low/pz),math.ceil(high/pz)):
                a,b=max(left,col*px),min(right,(col+1)*px)
                lo,hi=max(low,row*pz),min(high,(row+1)*pz)
                if b-a<.05 or hi-lo<.05:continue
                sx=(-1)**col*px/272.;sz=(-1)**row*pz/272.
                ox,oz=(col+.5)*px,(row+.5)*pz
                block=u.DynamicMesh()
                EDITS.append_mesh(block,tile,u.Transform())
                for v,bound,mid,scale,coord,sign in [(a,col*px,ox,sx,0,-1),(b,(col+1)*px,ox,sx,0,1),
                    (lo,row*pz,oz,sz,2,-1),(hi,(row+1)*pz,oz,sz,2,1)]:
                    if abs(v-bound)<.001:continue
                    p=[0.,0.,0.];n=p.copy();p[coord]=(v-mid)/scale;n[coord]=math.copysign(1,scale)*sign
                    cut(block,p,n)
                if axis=='Y' and low==871 and high==969:
                    # Clip the return gable to the tile underside, maintaining the stone courses.
                    cut(block,((423-ox)/sx,0,(969-oz)/sz),(98./405.*sx,0,sz))
                # The ground-storey donor is 1.46x in plan. Give perimeter rubble the same
                # projection; offset its center outwards so the room and stair clearances stay put.
                exterior=depth>22.
                outside=-1 if line in (-724,-426) else 1
                face=line+(9.*outside if exterior else 0.)
                loc=(ox,face,oz) if axis=='X' else (face,ox,oz)
                pose=u.Transform(location=loc,rotation=u.Rotator(yaw=0 if axis=='X' else 90),
                    scale=(sx,1.42 if exterior else (depth/2+3)/23.,sz))
                EDITS.append_mesh(mesh,block,pose)


def corners(mesh):
    from inn_geometry import WEST,EAST,FRONT,BACK,GUEST,OWNER,EAVES
    asset=u.load_asset('/Game/UnrealNormandy/StaticMeshes/SM_H_WallCorner_00A')
    stone,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Missing taproom corner stones')
    u.GeometryScript_Materials.remap_material_i_ds(stone,0,2)
    for x,y,yaw in [(EAST,FRONT,-90),(WEST,FRONT,180),(EAST,BACK,0),(WEST,BACK,90)]:
        back=y==BACK
        spans=([(-6,GUEST)] if back else [])+[(GUEST,OWNER),(OWNER,872 if back else EAVES)]
        for lo,hi in spans:
            # Native dressed corners bridge the exposed ends of both irregular stone faces.
            dx=7 if x==WEST else -7
            dy=-7 if back else 7
            pose=u.Transform(location=(x+dx,y+dy,(hi+lo)/2),rotation=u.Rotator(yaw=yaw),
                             scale=(1.61,1.61,(hi-lo+3)/302.7))
            EDITS.append_mesh(mesh,stone,pose)
