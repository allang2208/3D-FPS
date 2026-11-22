"""Author the shop's shelf goods display hardware into dedicated village packages."""
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
import sys
import unreal as u

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE),str(HERE.parent/'VillageBlacksmith'),str(HERE.parent/'VillageBakery')]
from forge_weapon_display import _layout
from gunshop_furnish import FIX, HILLS, RACK_MODELS, assembly, catalogue
from gunshop_furnish_geometry import board, counter_tray, drawers, fitting_mesh, panels, rifle_support, sample_case, stamped_label

EDITOR = u.EditorAssetLibrary
ASSETS = u.GeometryScript_AssetUtils
EDITS = u.GeometryScript_MeshEdits
SURF = HILLS + 'VillageCarpenter/Props/Surfaces/M_Carpenter'
SMITH = HILLS + 'VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_'
WBU = '/Game/Building/WorkbenchSurfaces20261108/M_WBU_'
SURFACES = {
    'Enamel':WBU+'RackPaint', 'Oak':SMITH+'Oak', 'Sawn':SURF+'Sawn',
    'DarkWood':'/Game/WorldGeneration/VillageTavern/Furniture/M_TavernOiledOak',
    'Iron':SURF+'Iron', 'Steel':SURF+'Steel','Rubber':WBU+'RubberGrip','Brass':SURF+'Brass',
    'Baize':SMITH+'Blanket','Linen':SMITH+'Linen',
    'Glass':'/Game/Building/GunWorkbenchApproved20261006/Materials/M_GWDesign_ClearGlass',
}


@lru_cache(None)
def asset(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing gunshop source '+path)
    return obj


def read_mesh(path):
    dm, ok = ASSETS.copy_mesh_from_static_mesh(asset(path),u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if ok != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not read '+path)
    return dm


def append_model(dm, model, materials):
    for key,(v,n,uv,t) in model.slots.items():
        mat = asset(SURFACES[key])
        if mat not in materials:
            materials.append(mat)
        buf = u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*p) for p in v],
            normals=[u.Vector(*p) for p in n],uv0=[u.Vector2D(*p) for p in uv],
            triangles=[u.IntVector(*f) for f in t])
        EDITS.append_buffers_to_mesh(dm,buf,material_id=materials.index(mat))


def contact_sections(poses, fractions):
    # Intersect the original display triangles with two rack stations. The supporting
    # pins meet solid surfaces even when grips and magazines hang below both pins.
    points, triangles = [], []
    for path, frame in poses:
        dm = read_mesh(path)
        q = u.GeometryScript_MeshQueries
        conv = u.GeometryScript_List
        _,verts,_ = q.get_all_vertex_positions(dm,False)
        _,faces,_ = q.get_all_triangle_indices(dm,False)
        rows = []
        for v in conv.convert_vector_list_to_array(verts):
            p = u.MathLibrary.transform_location(frame,v)
            rows.append((p.x,p.y,p.z))
        points.extend(rows)
        triangles.extend((rows[t.x],rows[t.y],rows[t.z]) for t in conv.convert_triangle_list_to_array(faces))
    result = []
    lo,hi=min(p[0] for p in points),max(p[0] for p in points)
    for fraction in fractions:
        x = lo+(hi-lo)*fraction
        ends = []
        for a,b,c in triangles:
            if min(a[0],b[0],c[0])>x or max(a[0],b[0],c[0])<x:
                continue
            for p,q in ((a,b),(b,c),(c,a)):
                if (p[0]-x)*(q[0]-x)>0 or abs(q[0]-p[0])<1e-6:
                    continue
                f=(x-p[0])/(q[0]-p[0])
                ends.append((p[1]+(q[1]-p[1])*f,p[2]+(q[2]-p[2])*f))
        z=min(p[1] for p in ends)
        near=[p[0] for p in ends if p[1]<=z+.45]
        result.append((x,sum(near)/len(near),z))
    return result


def fitted_rack(dm, materials):
    # Use the actual assembled ironworker's finishing rack. Reuse its feet, rails,
    # braces, wear and bolt placement; the blade-specific hooks belong to that shop.
    yaw = u.Transform(rotation=u.Rotator(yaw=90))
    local = u.MathLibrary.compose_transforms(u.Transform(location=(-326.,36.,0.)),yaw)
    for (state,path,override,collision),poses in _layout(asset).items():
        if state != 'Common':
            continue
        donor = read_mesh(path)
        source_materials = [asset(override) if override else slot.material_interface
                            for slot in asset(path).static_materials]
        for i,mat in enumerate(source_materials):
            u.GeometryScript_Materials.remap_material_i_ds(donor,i,100+i)
            if mat not in materials:
                materials.append(mat)
        for i,mat in enumerate(source_materials):
            u.GeometryScript_Materials.remap_material_i_ds(donor,100+i,materials.index(mat))
        for pose in poses:
            transform=u.MathLibrary.compose_transforms(pose,local)
            EDITS.append_mesh(dm,donor,transform)
    mesh=fitting_mesh()
    # The smith used a diagonal in the repaired rack. Its ends are housed at the
    # rear face of the rails, away from the display bays.
    mesh.timber('Oak',(-105,20,26),(105,20,172),4,6,.55)
    recipes=catalogue()
    for index,(key,target) in enumerate(RACK_MODELS):
        poses=assembly(recipes[key],target,True,asset)
        rail=179. if index<2 else 94.
        for x,y,z in contact_sections(poses,(.2,.72)):
            rifle_support(mesh,x,y,z,rail)
        card_z=target[2]-8.
        mesh.box('DarkWood',target[0]-1.,target[0]+1.,10.5,14.3,card_z+1,rail,.32)
        stamped_label(mesh,('M16A2','AKM','SUPER90')[index],target[0],10.4,card_z,2.15)
    append_model(dm,mesh,materials)


def publish(only=None):
    sources=[Path(__file__),HERE/'gunshop_furnish.py',HERE/'gunshop_furnish_geometry.py',
             HERE.parent/'VillageBlacksmith/forge_weapon_display.py',
             HERE.parents[2]/'Content/ColdSteelData/gun-assembly.json']
    stamp=hashlib.sha256(b''.join(f.read_bytes() for f in sources)).hexdigest()
    EDITOR.make_directory(FIX.rsplit('/',1)[0])
    record={}
    fixtures=[('FinishingRack',None),('PerforatedBoard',board),('OpticsMounts',lambda:panels(True)),
              ('AccessoriesMounts',lambda:panels(False)),('MerchantDrawers',drawers),('CounterCase',sample_case),
              ('CounterTray',counter_tray)]
    for key,model in fixtures:
        if only is not None and key not in only:
            continue
        path=FIX+key
        mesh=EDITOR.load_asset(path) if EDITOR.does_asset_exist(path) else None
        if mesh and EDITOR.get_metadata_tag(mesh,'GunshopFixtureSource')==stamp:
            record[key]=path
            continue
        dm=u.DynamicMesh()
        materials=[]
        if key=='FinishingRack':
            fitted_rack(dm,materials)
        else:
            append_model(dm,model(),materials)
        solid=key in ('FinishingRack','MerchantDrawers')
        if not mesh:
            cfg=u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=True,enable_nanite=False,enable_collision=solid)
            mesh,ok=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,cfg)
            if not mesh or ok!=u.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError('Failed to create '+path)
        opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
              replace_materials=True,new_materials=materials,new_material_slot_names=[m.get_name() for m in materials])
        _,ok=ASSETS.copy_mesh_to_static_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
        if ok!=u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Failed to write '+path)
        if solid:
            mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        EDITOR.set_metadata_tag(mesh,'GunshopFixtureSource',stamp)
        if not EDITOR.save_loaded_asset(mesh,False):
            raise RuntimeError('Could not save '+path)
        record[key]=path
    return record


if __name__=='__main__':
    out=Path(os.environ['BAKERY_LEVEL_RUN'])
    (out/'level-saved.json').write_text(json.dumps({'fixtures':publish()},indent=2),encoding='utf-8')
