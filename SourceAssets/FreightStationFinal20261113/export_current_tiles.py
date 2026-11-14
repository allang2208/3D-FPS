from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
def apply(w,req):
    # Start again from the accepted repaired mesh, never from an obsolete pre-repair source.
    import unreal as u
    a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='StationLine_AbandonedTransitStation_6')
    a.modify();a.static_mesh_component.modify()
    a.static_mesh_component.set_static_mesh(u.load_asset('/Game/SceneTests/FreightOppositePlatform20261113/Meshes/SM_StationTiles_WestRepair'))
    src=(R.parent/'FreightOppositePlatform20261113/tile_source.py').read_text('utf8')
    src=src.replace('copy_mesh_from_static_mesh(m,mesh,u.GeometryScriptCopyMeshFromAssetOptions(),lod)','copy_mesh_from_static_mesh_v2(m,mesh,u.GeometryScriptCopyMeshFromAssetOptions(),lod,False)')
    env={'__file__':str(R/'export_current_tiles.py')};exec(compile(src,'tile_material_ids','exec'),env)
    return env['apply'](w,req)
