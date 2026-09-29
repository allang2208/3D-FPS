"""Sparse, upright room dressing; the bed actor owns the shared occupancy order."""
def build_props():
    base='/Game/Dungeons/IsolationWard20260929/Props/'
    return [dict(id='MedicalCart',mesh=base+'SM_Ward_MedicalCart',min_per_room=0,max_per_room=1,clearance=100.,blocking=True),
            dict(id='IVDripCrutch',mesh=base+'SM_Ward_IVDripCrutch',min_per_room=0,max_per_room=1,clearance=80.,blocking=False)]
