"""Ward-specific waiting seats on the solid wall spans beside each doorway."""
def build_layout(cfg):
    entries=[]
    for door in cfg['glass_doors']:
        side='N' if door['position'][1]>0 else 'S'
        for suffix,offset in (('L',-3.7),('R',3.7)):
            entries.append(dict(id=door['id']+'_'+suffix,door=door['id'],side=side,
                                center_x_m=round(door['position'][0]+offset,3)))
    entries.append(dict(id='South_Service',side='S',center_x_m=13.5))
    return dict(mesh='/Game/Props/HospitalWaitingBench20260929/SM_Hospital_Waiting_Bench',
                recipe='Scripts/build_pool_module.py',
                center_abs_y_m=3.8,floor_top_cm=4.2,floor_gap_cm=.2,
                center_aisle_half_width_m=3.35,door_half_keep_clear_m=2.45,
                window_side_clearance_m=.2,entries=entries,
                source_credit='Hospital Waiting Bench - AshenCut (fab.com), CC-BY-4.0',
                source_url='https://www.fab.com/listings/05f7dccc-ecee-4bd4-9cc1-189ab2f42cc5')
