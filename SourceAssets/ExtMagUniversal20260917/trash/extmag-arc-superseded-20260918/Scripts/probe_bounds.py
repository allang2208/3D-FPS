import unreal as u, json
out={}
for name,path in {
 "M4_drum":"/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum",
 "AKM_drum":"/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum",
 "QBZ_drum":"/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_drum",
 "ExtMag_M440":"/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_M440",
 "ExtMag_AKM40":"/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_AKM40",
 "ExtMag_QBZ40":"/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_QBZ40",
}.items():
    m=u.load_asset(path)
    if not m: out[name]="MISSING"; continue
    b=m.get_bounds()
    out[name]={"center":[round(b.origin.x,2),round(b.origin.y,2),round(b.origin.z,2)],
               "size":[round(b.box_extent.x*2,2),round(b.box_extent.y*2,2),round(b.box_extent.z*2,2)]}
u.log("ASSET_BOUNDS "+json.dumps(out))
