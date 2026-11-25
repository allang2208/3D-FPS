"""Author fitted upper-storey modules using the same UV convention as the village bakery."""
from pathlib import Path
import json
import os
import sys
import unreal as u

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'SourceAssets/HillsVillageTavern/Inn'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from inn_geometry import make_models
import inn_masonry

PACKAGE='/Game/WorldGeneration/VillageTavern/Inn'
HILLS='/Game/WorldGeneration/TemperateHills/'
SURFACES={
    'DarkWood':HILLS+'OldChapel/Materials/M_ChapelTimber',
    'Oak':'/Game/WorldGeneration/VillageTavern/Furniture/M_TavernDiningOak',
    'Sawn':HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterSawn',
    'Lime':'/Game/WorldGeneration/VillageTavern/KitchenScreen/MI_TavernKitchenWeatheredLime',
    'Masonry':inn_masonry.MORTAR,
    'NativeStone':inn_masonry.STONE,
    'GroundFloorQuoin':inn_masonry.QUOIN,
    'Stone':HILLS+'VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_HearthStone',
    'Iron':HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterIron',
}

def author(hall_refit=False,joinery=False):
    ed=u.EditorAssetLibrary
    loaded={k:ed.load_asset(v) for k,v in SURFACES.items()}
    if not all(loaded.values()):raise RuntimeError('Missing surfaces '+str([k for k,v in loaded.items() if not v]))
    if joinery:
        from suite_surfaces import finishes
        loaded.update(finishes())
    report={}
    tile=inn_masonry.make_tile()
    for name,model in make_models(hall_refit,joinery).items():
        if joinery and name not in ('TimberFrame','Partitions','KitchenPass','Cupboard','Mirror','Settle','WindowFrame'):continue
        if hall_refit and not joinery and name not in ('Partitions','TimberFrame','KitchenPass'):continue
        mesh=u.DynamicMesh()
        for i,(mat,(verts,normals,uv,tris)) in enumerate(model.slots.items()):
            buf=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*p) for p in verts],
                normals=[u.Vector(*n) for n in normals],uv0=[u.Vector2D(*t) for t in uv],
                triangles=[u.IntVector(*t) for t in tris])
            u.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh,buf,material_id=i)
        names=list(model.slots)
        if hasattr(model,'panels'):
            inn_masonry.dress(mesh,tile,model.panels)
            names.append('NativeStone')
        if name=='Facade':
            inn_masonry.corners(mesh)
            names.append('GroundFloorQuoin')
        path=PACKAGE+'/SM_Inn'+name+('_JoineryR4' if joinery else '_HallRoadR3' if hall_refit else '_StoneCourt')
        asset=ed.load_asset(path) if ed.does_asset_exist(path) else None
        if not asset:
            options=u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=True,
                enable_nanite=False,enable_recompute_normals=False,enable_recompute_tangents=True)
            asset,outcome=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh,path,options)
            if not asset or outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
        opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
            replace_materials=True,new_materials=[loaded[key] for key in names],new_material_slot_names=names)
        if hasattr(model,'panels'):
            settings=asset.get_editor_property('nanite_settings')
            settings.enabled=True
            opts.set_editor_property('apply_nanite_settings',True)
            opts.set_editor_property('new_nanite_settings',settings)
        _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,asset,opts,u.GeometryScriptMeshWriteLOD())
        if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
        body=asset.get_editor_property('body_setup')
        if name=='Stairs':
            asset.set_editor_property('complex_collision_mesh',ed.load_asset(PACKAGE+'/SM_InnWalkRamp_StoneCourt'))
        if name=='RoomDoor':
            rect=u.KBoxElem()
            for key,val in [('center',u.Vector(0,0,108)),('x',5.),('y',104.),('z',216.)]:
                rect.set_editor_property(key,val)
            geom=body.get_editor_property('agg_geom')
            geom.set_editor_property('box_elems',[rect]);geom.set_editor_property('convex_elems',[])
            body.set_editor_property('agg_geom',geom)
            body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        else:body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if not ed.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+path)
        report[name]=dict(package=path,triangles=mesh.get_triangle_count(),surfaces=names)
    return report

if __name__=='__main__':
    plan=json.loads((ROOT/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf8'))
    report=author()
    if plan.get('tavern',{}).get('inn',{}).get('hall_road'):
        report['HallRoadR3']=author(True)
        report['JoineryR4']=author(True,True)
    Path(os.environ['TAVERN_INN_BATCH'],'modules.json').write_text(json.dumps(report,indent=2),encoding='utf8')
