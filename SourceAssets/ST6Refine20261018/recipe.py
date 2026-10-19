"""Merge the ST6 refinement without changing other equipment or body profiles."""
DEST='/Game/Characters/ModularOutfit20260924/Super90Source20261006/ST6Refine20261018'
def apply(config):
    item=config['items']['ue_st6_sleeves']
    item['appearance_family']='ST6Refine20261018'
    for profile,slots in item['base_material_overrides'].items():
        for section in slots:
            name='MI_ST6Torso_'+profile if profile in ('Body','Jason') and section in ('3','8','9') else 'M_ST6Fabric'
            slots[section]=DEST+'/Materials/'+name+'.'+name
    item['rig_meshes']['Jason']=DEST+'/Jason/SK_Jason_ST6Refined.SK_Jason_ST6Refined'
    item['owner_body_meshes']={'Jason':DEST+'/Jason/SK_Jason_ST6Trims.SK_Jason_ST6Trims'}
    item.pop('owner_body_hidden_materials',None)
    return config
