"""Import only the versioned castle kit. Read the actual chapel lancet-bay binding."""
import json
import os
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
import import_kit as kit

E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
DEST=kit.PACK+'/ChapelGatehouse'
CHAPEL='/Game/WorldGeneration/TemperateHills/OldChapel'
RUN=Path(os.environ['GATEHOUSE_RUN'])


def connect(src,dst,pin):
    if not L.connect_material_expressions(src,'',dst,pin):
        raise RuntimeError('Cannot connect '+dst.get_name()+' '+pin)


def wall_material():
    window=kit.require(CHAPEL+'/Meshes/SM_ChapelWindowBay')
    donor=window.get_material(0)
    if not donor or donor.get_name()!='M_ChapelWall':
        raise RuntimeError('Chapel window bay exterior material changed')
    path=DEST+'/M_GatehouseChapelWall'
    mat=E.duplicate_asset(donor.get_path_name().split('.')[0],path)
    if not mat:raise RuntimeError('Could not copy chapel wall graph')
    normal=L.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL)
    inputs=L.get_inputs_for_material_expression(mat,normal)
    bump=next(n for n in inputs if isinstance(n,u.MaterialExpressionBumpOffset))
    inputs=L.get_inputs_for_material_expression(mat,bump)
    uv=next(n for n in inputs if isinstance(n,u.MaterialExpressionTextureCoordinate))
    height=next(n for n in inputs if isinstance(n,u.MaterialExpressionTextureSample))
    phase=L.create_material_expression(mat,u.MaterialExpressionAppendVector,-720,50)
    for index,axis in enumerate(('U','V')):
        p=L.create_material_expression(mat,u.MaterialExpressionScalarParameter,-940,index*92)
        p.set_editor_property('parameter_name','Wall phase '+axis)
        p.set_editor_property('use_custom_primitive_data',True)
        # Chapel patina reserves 0..4 for its site transform on the paving.
        p.set_editor_property('primitive_data_index',8+index)
        connect(p,phase,('A','B')[index])
    shifted=L.create_material_expression(mat,u.MaterialExpressionAdd,-460,45)
    connect(uv,shifted,'A')
    connect(phase,shifted,'B')
    connect(shifted,bump,'Coordinate')
    connect(shifted,height,'UVs')
    L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_NANITE,True)
    L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    L.recompile_material(mat)
    kit.save(mat)
    return mat,donor


def dress_existing_wall(role,wall):
    # Preserve the deployed mesh's crest, footing rubble, individual fractures,
    # simple hulls and complex collision donor. Only remap the stone sections.
    source='/Game/WorldGeneration/TemperateHills/VillageMasonry/ReliefMeshes/'+role
    asset=E.duplicate_asset(source,DEST+'/'+role)
    if not asset:raise RuntimeError('Cannot stage existing wall '+source)
    dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+source)
    slots=asset.get_editor_property('static_materials')
    project_uv=next(getattr(u.GeometryScript_UVs,n) for n in dir(u.GeometryScript_UVs)
                    if n.replace('_','')=='setmeshuvsfromboxprojection')
    projected=[]
    for i,slot in enumerate(slots):
        name=str(slot.material_slot_name)
        if name not in ('YardField','YardSlate') and not name.startswith('HighWallStone'):
            continue
        _,selection=u.GeometryScript_MeshSelection.select_mesh_elements_by_material_id(dm,i)
        _,count=u.GeometryScript_MeshSelection.get_mesh_selection_info(selection)
        if count:
            project_uv(dm,0,
                u.Transform(scale=(200.,200.,200.)),selection,0)
        asset.set_material(i,wall)
        projected.append(name)
    if not projected:raise RuntimeError('No exposed stone slot on '+source)
    opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,
        enable_recompute_tangents=True,replace_materials=False)
    _,result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+role)
    kit.save(asset)
    return dict(path=asset.get_path_name(),source=source,chapel_slots=projected,triangles=dm.get_triangle_count())


E.make_directory(DEST)
frame_dest=DEST+'/SquareKeep'
E.make_directory(frame_dest)
portals_only=os.environ.get('GATEHOUSE_PORTALS_ONLY')=='1'
high_walls_only=os.environ.get('GATEHOUSE_HIGH_WALLS_ONLY')=='1'
if portals_only or high_walls_only:
    wall=kit.require(DEST+'/M_GatehouseChapelWall')
    donor=kit.require(CHAPEL+'/Meshes/SM_ChapelWindowBay').get_material(0)
else:
    wall,donor=wall_material()
materials={'ChapelWall':wall,'Coping':kit.require(CHAPEL+'/Materials/M_ChapelYardCap'),
           'Footing':kit.require(CHAPEL+'/Materials/M_ChapelFooting'),
           'Floorboard':kit.require(CHAPEL+'/Materials/M_ChapelTimber'),
           'Paving':kit.require(CHAPEL+'/Materials/M_ChapelFlagstone'),
           'Oak':kit.require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
           'Iron':kit.require('/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron'),
           'Bronze':kit.require('/Game/Props/RomanColumn20260915/M_Bronze'),
           'Embers':kit.require('/Game/WorldGeneration/TemperateHills/ShopLighting/M_StaffHearthEmber')}
source=kit.PROJECT/'SourceAssets/HillsVillageHighWall20261120/ChapelGatehouse'
receipt={'source_wall':donor.get_path_name(),'material':wall.get_path_name(),'saved':{}}
if os.environ.get('GATEHOUSE_FRAMES_ONLY')=='1' or not (portals_only or high_walls_only):
    from ground_wear import make_ground_wear
    receipt['ground_wear']=make_ground_wear(DEST).get_path_name()
if not portals_only:
    wall_uv=next(n for n in L.get_material_expressions(wall) if isinstance(n,u.MaterialExpressionTextureCoordinate))
    receipt['wall_uv_tiling']=[wall_uv.get_editor_property(k) for k in ('UTiling','VTiling')]
roles=['SM_HighPortalGalleryWest','SM_HighPortalGalleryEast']
if os.environ.get('GATEHOUSE_FRAMES_ONLY')!='1':
    roles+=['SM_GateWroughtGrilleWest','SM_GateWroughtGrilleEast','SM_GateReleaseHandle']
tower_only=os.environ.get('GATEHOUSE_TOWER_ONLY')=='1'
if tower_only or not (portals_only or high_walls_only):
    tower_source=source.parent/'HighTower'
    kit.create_role('SM_HighWatchtower',materials,receipt,package_root=frame_dest,source_dir=tower_source,
                    receipt_file=RUN/'importing.json',preserve_silhouette=True)
if not high_walls_only and not tower_only:
    for role in roles:
        kit.create_role(role,materials,receipt,package_root=frame_dest,source_dir=source,receipt_file=RUN/'importing.json',preserve_silhouette=True)
if not portals_only:
    mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.get_default_object(u.StaticMeshEditorSubsystem)
    for role in ['SM_HighWall']+[f'SM_HighWallShard_{i:02d}' for i in range(9)]:
        kit.create_role(role,materials,receipt,package_root=DEST,source_dir=source,receipt_file=RUN/'importing.json',preserve_silhouette=True)
        if role.startswith('SM_HighWallShard_'):
            shard=kit.require(DEST+'/'+role)
            if mesh_editor.add_simple_collisions(shard,u.ScriptCollisionShapeType.NDOP18)<0:
                raise RuntimeError('Could not cook wall fragment collision: '+role)
            kit.save(shard)
            receipt['saved'][role]['convex_collision']='NDOP18'
if not portals_only and not high_walls_only:
    walls=['SM_VillageWall'+suffix for suffix in
            ('RepairedA','RepairedB','RuinedA','RuinedB','RuinedC','RuinedD','PierRepaired','PierRuined')]
    for role in walls:
        receipt['saved'][role]=dress_existing_wall(role,wall)
if not receipt['saved']:raise RuntimeError('No gatehouse meshes')
(RUN/'saved.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')

