"""Save corrected mount metadata and check the requested left fit / size scope."""
import json,math
from pathlib import Path
import unreal as u
O=Path(__file__).parent;E=u.EditorAssetLibrary
mount=[29.5,-3.19,-8.25]
report={'mount_sight_cm':mount,'roll_degrees':180,'scale_changed':False,'parts':{},
        'scope':'Imported asset dimensions, sampled compressed pose scale and left mount/socket coordinates; no gameplay run.'}
def v(p):return [p.x,p.y,p.z]
def left(p):return [mount[0]+p.x,mount[1]-p.y,mount[2]-p.z]
for kind in ('laser','flashlight'):
    donor=u.load_asset('/Game/Weapons/TacticalDevices20260913'+('/HunyuanV3' if kind=='flashlight' else '')+'/M4/'+kind+'/SM_TacticalDevice')
    asset=u.load_asset('/Game/Weapons/ASH12/TacticalDevices20260920/'+kind+'/SM_ASH12_'+kind)
    original=donor.get_bounding_box();b=asset.get_bounding_box()
    donor_length=original.max.y-original.min.y;length=b.max.x-b.min.x
    if abs(length-donor_length)>.001:raise RuntimeError('Unexpected size difference '+kind)
    emitter=left(asset.find_socket('Emitter').relative_location)
    guide=left(asset.find_socket('AimGuide').relative_location)
    direction=[guide[i]-emitter[i] for i in range(3)]
    if emitter[1]>=-3.19 or direction[0]<=0 or math.hypot(direction[1],direction[2])>.001:
        raise RuntimeError('Incorrect left emitter placement / direction '+kind)
    E.set_metadata_tag(asset,'ASHMount','Sight frame (29.5,-3.19,-8.25) cm; left side; local X roll 180 degrees; unit body scale')
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):raise RuntimeError('Metadata save failed '+kind)
    report['parts'][kind]={'length_cm':length,'donor_length_cm':donor_length,
        'size_ratio':length/donor_length,'emitter_sight_cm':emitter,'guide_sight_cm':guide,'saved':True}
poses=json.loads((O/'bone_scale.json').read_text())
error=max(abs(scale-1) for row in poses['poses'] for scale in row['effective_mesh_scale'])
if error>1e-5:raise RuntimeError('Effective mount scale is not one')
report['max_effective_scale_error']=error
(O/'left_mount_receipt.json').write_text(json.dumps(report,indent=2))
print('ASH_LEFT_MOUNT_CHECK '+json.dumps(report))
