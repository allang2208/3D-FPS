"""Keep the published feed finish when earlier M249 assets are rebuilt."""
def restore():
    import unreal as u,hashlib
    from pathlib import Path
    E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
    D='/Game/Weapons/M249/Surface20261108'
    rows={
        '/Game/Weapons/M249/SideMagazine20261108/Meshes/SM_m249_side_mag_30':D+'/Materials/MI_M249_SideMagazine30_29',
        '/Game/Weapons/M249/SideMagazine20261108/Meshes/SM_m249_side_mag_45':D+'/Materials/MI_M249_SideMagazine45_29',
        '/Game/Weapons/M249/SideMagazine20261108/Meshes/SM_M249_SidePort':D+'/Materials/MI_M249_SidePort29'}
    if not all(E.does_asset_exist(p) for p in rows.values()):return {}
    if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE retained; cannot restore feed bindings')
    changed={}
    def save(a):
        if not E.save_loaded_asset(a,False):raise RuntimeError('Feed finish save '+a.get_path_name())
        p=a.get_path_name().split('.')[0]
        changed[p]=hashlib.sha256((Path(u.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
    for p,q in rows.items():
        mesh=u.load_asset(p);mi=u.load_asset(q)
        if not mesh:continue
        if any(s.material_interface!=mi for s in mesh.static_materials):
            for i in range(len(mesh.static_materials)):mesh.set_material(i,mi)
            save(mesh)
    receiver=u.load_asset(D+'/Materials/MI_M249_Factory_Receiver')
    for suffix in ('OldBox','NewBox'):
        mi=u.load_asset(D+'/Materials/MI_M249_Surface__'+suffix)
        if not mi:continue
        values={k:L.get_material_instance_scalar_parameter_value(receiver,k) for k in ('GrainTileCm','GrainRoughness','MottleRoughness')}
        values['RainSurfaceResponse']=0.
        if any(abs(L.get_material_instance_scalar_parameter_value(mi,k)-v)>1e-6 for k,v in values.items()):
            for k,v in values.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
            L.update_material_instance(mi);save(mi)
    return changed
