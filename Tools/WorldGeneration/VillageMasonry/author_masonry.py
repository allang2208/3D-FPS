"""Build fitted masonry in new asset packages while retaining the donors' BodySetups."""
import gc
import json
import math
import os
from collections import defaultdict
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0,str(Path(__file__).resolve().parent))
from stone_reference import MI, L, StoneReference, islands, limits, mesh_data, normal, read_mesh, require

HILLS='/Game/WorldGeneration/TemperateHills/'
DEST=HILLS+'VillageMasonry'
E=u.EditorAssetLibrary


def replacement(slot,broken):
    if slot=='Mortar':
        return 'MI_Main_Mortar_00A'
    if slot in ('YardField','YardSlate','YardCap','HighWallStone','PortalStone') or slot.startswith(('HighWallStone','PortalStone')):
        if broken:
            return 'MI_StoneWall_Pieces_00A'
        if slot in ('YardCap','YardSlate'):
            return 'MI_Main_StoneWall_00B_Gray'
        return 'MI_Main_StoneWall_00A'
    return None


def copy_to_asset(dm,asset):
    opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
                                               replace_materials=False)
    _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not install geometry: '+asset.get_path_name())


def paint_existing(dm,reference,paints):
    # The upper carved facade, fracture seam pairs and deliberate portal
    # clearances must retain every original position, normal and UV seam.
    points,triangles,ids=mesh_data(dm)
    colors_by_vertex=[None]*len(points)
    for triangle,slot in zip(triangles,ids):
        for vi in triangle:
            colors_by_vertex[vi]=paints[slot]
    _,old,have_old,_=u.GeometryScript_VertexColors.get_mesh_per_vertex_colors(dm,True)
    colors=list(L.convert_color_list_to_array(old)) if have_old else [u.LinearColor(1,1,1,1)]*len(points)
    for i,mat in enumerate(colors_by_vertex):
        if mat:
            colors[i]=u.LinearColor(*reference.sample(mat,points[i]))
    u.GeometryScript_VertexColors.set_mesh_per_vertex_colors(dm,L.convert_array_to_color_list(colors))
    return dm


def fitted_blocks(dm,reference,paints):
    points,triangles,ids=mesh_data(dm)
    # Fit the *whole* scanned stone into the bounds of its old block. The top
    # course, ruins and corners retain their chipped outline in both elevations.
    output=defaultdict(lambda:[[],[],[],[]])
    used=0
    for group in islands(points,triangles,ids):
        slot=ids[group[0]]
        indices=sorted({v for ti in group for v in triangles[ti]})
        lo,span=limits(points[v] for v in indices)
        surfaces,faces,colors,normals=output[slot]
        start=len(surfaces)
        if paints[slot]!='MI_Main_Mortar_00A' and min(span)>3. and max(span)<152. and len(group)>=10:
            # Prefer a block with the same stretcher/header aspect ratio. Cycle
            # amongst close matches so neighbouring bays do not stamp one stone.
            dx,dy,dz=span
            quarter=dy>dx
            width,depth=(dy,dx) if quarter else (dx,dy)
            def distance(entry):
                sx,sy,sz=entry[2]
                return abs(math.log((width/dz)/(sx/sz)))+.55*abs(math.log((depth/dz)/(sy/sz)))
            options=sorted(reference.blocks,key=distance)[:6]
            source,local_tris,_=options[(group[0]+len(group))%len(options)]
            vertices=[]
            for (x,y,z),c in source:
                coords=(1.-y,x,z) if quarter else (x,y,z)
                vertices.append(tuple(k+v*size for k,v,size in zip(lo,coords,span)))
                colors.append(c)
            used+=1
        else:
            vertices=[points[v] for v in indices]
            colors.extend(reference.sample(paints[slot],p) for p in vertices)
            remap={v:i for i,v in enumerate(indices)}
            local_tris=[tuple(remap[v] for v in triangles[ti]) for ti in group]
        surfaces.extend(vertices)
        sums=[[0.,0.,0.] for _ in vertices]
        for tri in local_tris:
            n=normal(*(vertices[v] for v in tri))
            for v in tri:
                for k in range(3):
                    sums[v][k]+=n[k]
            faces.append(tuple(start+v for v in tri))
        for vector in sums:
            mag=math.sqrt(sum(k*k for k in vector))
            normals.append(tuple(v/mag for v in vector) if mag else (0,0,1))
    result=u.DynamicMesh()
    for slot,(verts,faces,colors,normals) in output.items():
        buf=u.GeometryScriptSimpleMeshBuffers()
        buf.vertices=[u.Vector(*p) for p in verts]
        buf.triangles=[u.IntVector(*t) for t in faces]
        buf.normals=[u.Vector(*n) for n in normals]
        buf.vertex_colors=[u.LinearColor(*c) for c in colors]
        # The donor PBR projects its own triplanar colour/normal. Provide a
        # centimetre-scaled tangent basis and keep the original wall foot mask.
        buf.uv0=[u.Vector2D((p[1] if abs(n[0])>abs(n[1]) else p[0])/100.,
                             (p[1] if abs(n[2])>.7 else p[2])/100.) for p,n in zip(verts,normals)]
        buf.uv1=[u.Vector2D(max(p[2],0.)/170.,0.) for p in verts]
        u.GeometryScript_MeshEdits.append_buffers_to_mesh(result,buf,material_id=slot)
    return result,used


def apply_house_masonry(asset,reference,fit_stones=False,broken=False):
    slots=list(asset.static_materials)
    paints=[replacement(str(s.material_slot_name),broken) for s in slots]
    if not any(paints):
        raise RuntimeError('No named masonry section on '+asset.get_path_name()+': '+str([str(s.material_slot_name) for s in slots]))
    dm=read_mesh(asset)
    fitted=0
    if fit_stones:
        dm,fitted=fitted_blocks(dm,reference,paints)
    else:
        paint_existing(dm,reference,paints)
    copy_to_asset(dm,asset)
    for i,material in enumerate(paints):
        if material:
            asset.set_material(i,require(MI+material))
    return fitted


def rebind_gate_masonry(asset,reference=None):
    """Apply to the completed gate shell before its owning importer saves it."""
    return apply_house_masonry(asset,reference or StoneReference())


def inputs():
    for role in ('RepairedA','RepairedB','RuinedA','RuinedB','RuinedC','RuinedD','PierRepaired','PierRuined','RubbleA','RubbleB'):
        yield HILLS+'VillagePerimeter/SM_VillageWall'+role,True,('Ruin' in role or 'Rubble' in role)
    for role in ('YardWallA','YardWallB','YardPier'):
        yield HILLS+'OldChapel/Meshes/SM_Chapel'+role,True,False
    for role in ('StoneChunkA','StoneChunkB'):
        yield HILLS+'VillageDefenses/SM_'+role,True,True
    yield HILLS+'HighVillageDefense/SM_HighWall',False,False
    for index in range(9):
        yield HILLS+'HighVillageDefense/Fracture/SM_HighWallShard_%02d'%index,False,False


def main():
    ref=StoneReference()
    if not ref.blocks:
        raise RuntimeError('No suitable three-dimensional stone islands in the surveyed house')
    E.make_directory(DEST)
    gate=os.environ.get('VILLAGE_MASONRY_GATE','')
    selected=[(path,False,False) for path in gate.split(';') if path] if gate else list(inputs())
    receipt={'stone_source':SOURCE_WALL,'fitting_candidates':len(ref.blocks),'meshes':[]}
    work=Path(os.environ['VILLAGE_MASONRY_WORK'])
    for path,fit,broken in selected:
        parent=require(path)
        dst=DEST+'/'+parent.get_name()
        asset=E.duplicate_asset(path,dst)
        if not asset:
            raise RuntimeError('Cannot duplicate '+path)
        fitted=apply_house_masonry(asset,ref,fit,broken)
        if fit:
            # Keep custom aggregate and per-poly traces independent of the
            # newly carved stones, including the original Nanite fallback.
            asset.set_editor_property('complex_collision_mesh',parent.get_editor_property('complex_collision_mesh') or parent)
        if not E.save_loaded_asset(asset,False):
            raise RuntimeError('Cannot save '+dst)
        receipt['meshes'].append(dict(asset=dst,source=path,fitted_blocks=fitted))
        u.log('VILLAGE_MASONRY_SAVED %s %d'%(dst,fitted))
        (work/'progress.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        del asset,parent
        gc.collect()
        u.SystemLibrary.collect_garbage()
    (work/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')


SOURCE_WALL='/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_00A'
if __name__=='__main__':
    main()
