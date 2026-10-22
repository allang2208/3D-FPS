"""Close the open scanned meteor and build a fuller underside, preserving PBR UVs."""
import json
import math
from collections import Counter
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'SourceAssets/MeteorClosedVolume20261019'
DEST='/Game/Skills/FireMagic20260921/MeteorClosedVolumeV1'
SOURCE='/Game/Skills/FireMagic20260921/RealisticV3'
MODEL=u.ModelingService
QUERY=u.GeometryScript_MeshQueries
EDIT=u.GeometryScript_MeshEdits
EAL=u.EditorAssetLibrary


def done(result):
    if not result.get_editor_property('success'):
        raise RuntimeError(str(result.get_editor_property('message')))
    return result


def info(handle):
    data=MODEL.get_mesh_info(handle)
    result={key:data.get_editor_property(key) for key in
            ['triangle_count','vertex_count','is_closed','open_border_edges','connected_components','num_uv_layers','volume']}
    for key in ['bounds_min','bounds_max']:
        v=data.get_editor_property(key);result[key]=[v.x,v.y,v.z]
    return result


def run():
    names=['SM_MeteorClosedRock','MI_MeteorClosedRock']
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(DEST+'/'+n for n in names):raise RuntimeError('Preserve unsaved meteor model edits')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Do not author the meteor during PIE')
    EAL.make_directory(DEST)
    handle=done(MODEL.load_mesh_from_static_mesh(SOURCE+'/SM_MeteorNaturalRock',0)).get_editor_property('handle')
    try:
        before=info(handle)
        mesh=MODEL.get_dynamic_mesh(handle)
        edges=Counter()
        for tid in range(QUERY.get_num_triangle_i_ds(mesh)):
            tri,valid=QUERY.get_triangle_indices(mesh,tid)
            if not valid:continue
            a,b,c=tri.x,tri.y,tri.z
            for x,y in [(a,b),(b,c),(c,a)]:edges[tuple(sorted((x,y)))]+=1
        boundary={v for edge,count in edges.items() if count==1 for v in edge}
        if not boundary:raise RuntimeError('Source no longer has the diagnosed opening; preserve it for reassessment')
        points=[QUERY.get_vertex_position(mesh,vid)[0] for vid in boundary]
        # Remove the ragged open lip, retain the scanned upper surface, then
        # mirror and weld only that cut rim into a continuous lower surface.
        cut_z=max(p.z for p in points)+.3
        top=before['bounds_max'][2]
        if top-cut_z<8:raise RuntimeError('Opening reaches too high for the planned local underside repair')
        frame=u.Transform(location=u.Vector(0,0,cut_z))
        done(MODEL.mirror(handle,frame,True,True,True))
        mesh=MODEL.get_dynamic_mesh(handle)
        # Break the mirrored silhouette below the welded seam. The weight is
        # exactly zero at the seam, so topology and the scanned top stay intact.
        for vid in range(QUERY.get_num_vertex_i_ds(mesh)):
            p,valid=QUERY.get_vertex_position(mesh,vid)
            if not valid or p.z>=cut_z:continue
            w=min(1.,(cut_z-p.z)/(top-cut_z))
            q=u.Vector(p.x+1.2*w*math.sin(p.y*.19+.3),
                       p.y+1.0*w*math.cos(p.x*.17),
                       p.z-.7*w*math.sin(p.x*.21)*math.cos(p.y*.19))
            EDIT.set_vertex_position(mesh,vid,q,True)
        shape=info(handle)
        width=max(shape['bounds_max'][i]-shape['bounds_min'][i] for i in [0,1])
        height=shape['bounds_max'][2]-shape['bounds_min'][2]
        done(MODEL.scale_mesh(handle,u.Vector(1,1,width*.82/height),u.Vector(0,0,cut_z)))
        done(MODEL.recenter_mesh(handle,'Bounds'))
        done(MODEL.recompute_normals(handle,60.))
        after=info(handle)
        if not after['is_closed'] or after['open_border_edges'] or after['connected_components']!=1:
            raise RuntimeError('Closed one-piece rock not achieved: '+json.dumps(after))
        material=EAL.duplicate_asset(SOURCE+'/MI_MeteorNaturalRock',DEST+'/MI_MeteorClosedRock') if not EAL.does_asset_exist(DEST+'/MI_MeteorClosedRock') else u.load_asset(DEST+'/MI_MeteorClosedRock')
        if not material:raise RuntimeError('Cannot create the meteor PBR instance')
        for axis in ['U','V']:
            u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(material,'Detail Texture Tiling - '+axis,54.)
        u.MaterialEditingLibrary.update_material_instance(material)
        if not EAL.save_loaded_asset(material,False):raise RuntimeError('PBR instance save failed')
        done(MODEL.save_mesh_to_static_mesh(handle,DEST+'/SM_MeteorClosedRock',True,False,False,True))
        asset=u.load_asset(DEST+'/SM_MeteorClosedRock')
        for i in range(len(asset.get_editor_property('static_materials'))):asset.set_material(i,material)
        if not EAL.save_loaded_asset(asset,False):raise RuntimeError('Closed mesh save failed')
        # Requested topology diagnosis includes the saved mesh, not only the
        # temporary modeling handle. No scene, game, rendering or physics run.
        saved_handle=done(MODEL.load_mesh_from_static_mesh(asset.get_path_name(),0)).get_editor_property('handle')
        try:saved=info(saved_handle)
        finally:MODEL.release_mesh(saved_handle)
        if not saved['is_closed'] or saved['open_border_edges']:
            raise RuntimeError('Saved mesh has an open boundary')
        receipt={'complete':True,'source':SOURCE+'/SM_MeteorNaturalRock','cut_z_cm':cut_z,
                 'before':before,'after':after,'saved_mesh':saved,
                 'saved_assets':[asset.get_path_name(),material.get_path_name()],
                 'topology_checked':True,'gameplay_tested':False,'rendered':False,
                 'runtime_size':'80 * (explosion_radius_cm / 217.5) cm longest side; 240 cm at level 1'}
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'mesh-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        print('METEOR_CLOSED_ROCK_SAVED '+json.dumps(receipt))
    finally:MODEL.release_mesh(handle)


if __name__=='__main__':run()
