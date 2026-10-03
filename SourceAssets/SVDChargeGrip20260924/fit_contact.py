"""Place the accepted AKM right-hand hook on the SVD handle's outer contact face."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;inputs=json.loads((O/'pose_inputs.json').read_text())
def mats(d):return {n:Matrix(m) for n,m in d.items()}
def center(points):return sum(points,Vector())/len(points)
def outer_handle(raw,width):
 points=[Vector(v) for v in raw];edge=min(v.x for v in points)
 return [v for v in points if v.x<edge+width]
don=inputs['AKM'];target=inputs['SVD'];poses=[mats(p) for p in don['poses']];f=330;p=poses[f]
inv=p['WPN_root'].inverted();closed=poses[0]['WPN_root'].inverted()@poses[0]['WPN_bolt']
travel=(inv@p['WPN_bolt']).translation-closed.translation
H=inv@p['hand_r'];H.translation-=travel
don_tip=outer_handle(don['handle_closed_root'],.008)
svd_tip=outer_handle(target['handle_closed_root'],.008)
# Match the outside edge and the forward pull face. These are the actual
# handle surfaces engaged by the donor hook, not the bolt-bone pivot.
def anchor(points):
 return Vector((min(v.x for v in points),min(v.y for v in points),(min(v.z for v in points)+max(v.z for v in points))*.5))
delta=anchor(svd_tip)-anchor(don_tip);H.translation+=delta
parents=don['parents'];rest=mats(don['rest'])
fingers=[n for n in rest if n.endswith('_r') and n.startswith(('index','middle','ring','pinky','thumb'))]
def basis_at(frame):
 pose=poses[frame];out={}
 for n in fingers:
  local_rest=rest[parents[n]].inverted()@rest[n]
  basis=local_rest.inverted()@pose[parents[n]].inverted()@pose[n]
  out[n]=list(basis.to_quaternion())
 return out
out={'donor':don['blend'],'donor_action':don['action'],'donor_frame':f,'contact_hand_root':[list(v) for v in H],
 'finger_basis':basis_at(330),'approach_basis':basis_at(300),'release_basis':basis_at(355),
 'handle_anchor_AKM_root':list(anchor(don_tip)),'handle_anchor_SVD_root':list(anchor(svd_tip)),
 'handle_translation':list(delta),'method':'Preserve current AKM right-hand hook rotations; match actual outside and forward handle faces in weapon space. Follow the SVD bolt track throughout pull.'}
(O/'contact_fit.json').write_text(json.dumps(out,indent=2))
print('CHARGE_CONTACT_FIT',json.dumps({k:v for k,v in out.items() if not k.endswith('basis')}),flush=True)
