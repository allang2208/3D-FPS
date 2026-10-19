"""ST6 keeps native body geometry and restores its original separate sleeves."""
DEST='/Game/Characters/ModularOutfit20260924/Super90Source20261006/ST6NativeBody20261017'
def apply(config):
    item=config['items']['ue_st6_sleeves']
    item.update(part='shirt',covers=[],world_covers=[],appearance_family='ST6NativeBody20261017')
    for key in ('rig_world_covers','owner_body_meshes','owner_body_hidden_materials'):
        item.pop(key,None)
    cloth=DEST+'/Materials/M_ST6NativeFabric.M_ST6NativeFabric'
    overrides={profile:{'0':cloth,'1':cloth} for profile in item['rig_meshes']}
    for profile in ('Body','Jason'):
        torso=DEST+'/Materials/MI_ST6Torso_'+profile+'.MI_ST6Torso_'+profile
        overrides[profile]['3']=torso
        if profile=='Jason':
            for section in ('8','9'):overrides[profile][section]=torso
    item['base_material_overrides']=overrides
    # ST6Refine20261018: retain the native neck and hem refinement.
    from pathlib import Path
    import runpy
    refinement=runpy.run_path(str(Path(__file__).parent.parent/'ST6Refine20261018/recipe.py'))
    refinement['apply'](config)
    return config
