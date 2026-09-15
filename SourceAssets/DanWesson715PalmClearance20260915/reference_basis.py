"""Adapt the GitHub donor's hand and forearm relationship to the 715 extractor.

Retained reference preparation from the archived DonorPress author; starts from LeftRecovery. The donor supplies
finger directions and the wrist/forearm relationship; the 715 owns contact
locations, arm lengths, mechanics and gameplay timing.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

_basis_dir=Path(__file__).resolve().parent
_base_file=_basis_dir.parent/'DanWesson715LeftRecovery20260914/author_actions.py'
__file__=str(_base_file)
exec(compile(_base_file.read_text(encoding='utf-8').split("\nif __name__ == '__main__':")[0],str(_base_file),'exec'),globals())
O=_basis_dir;__file__=str(O/'author_actions.py');(O/'Animations').mkdir(exist_ok=True)
_base_single=pose_single;_base_speed=pose_speed

donor_data=reference['RevolverReloadInit'];src_rest=donor_data['rest']
donor_index=19;src_pose=donor_data['poses'][donor_index]
maps={}
for side,label in [('l','L'),('r','R')]:
    target_frame=rest['hand_'+side].to_quaternion().inverted()@anatomy(rest,'hand_'+side,'index_01_'+side,'pinky_01_'+side,'middle_01_'+side)
    source_frame=src_rest[label+'_Hand'].to_quaternion().inverted()@anatomy(src_rest,label+'_Hand',label+'_Index1',label+'_Pinky1',label+'_Middle1')
    maps[side]=target_frame@source_frame.inverted()
source_hand_inv=src_pose['L_Hand'].to_quaternion().inverted()
rest_world_map=rest['hand_l'].to_quaternion()@maps['l']@src_rest['L_Hand'].to_quaternion().inverted()
lower_map=rest['lowerarm_l'].to_quaternion().inverted()@rest_world_map@src_rest['L_Forearm'].to_quaternion()
donor_lower_in_hand=maps['l']@source_hand_inv@src_pose['L_Forearm'].to_quaternion()@lower_map.inverted()
donor_forward_in_hand=(maps['l']@(source_hand_inv@(src_pose['L_Hand'].translation-src_pose['L_Forearm'].translation))).normalized()
world_map=idle['hand_r'].to_quaternion()@maps['r']@src_pose['R_Hand'].to_quaternion().inverted()
preferred_hand=world_map@src_pose['L_Hand'].to_quaternion()@maps['l'].inverted()

# Transfer the donor's actual phalanx directions into Manny palm space. Build
# the chain with Manny offsets; no joint translations, adduction fit or scale.
donor_shape={n:m.copy() for n,m in rest_hand.items()}
for family,label in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('pinky','Pinky')]:
    for j in range(1,4):
        n=f'{family}_{j:02}_l';sn=f'L_{label}{j}';pn=parent[n]
        if j<3:
            source_direction=src_pose[f'L_{label}{j+1}'].translation-src_pose[sn].translation
            target_rest_direction=rest_hand[f'{family}_{j+1:02}_l'].translation-rest_hand[n].translation
        else:
            source_rest_direction=src_rest[sn].translation-src_rest[f'L_{label}{j-1}'].translation
            source_direction=src_pose[sn].to_quaternion()@src_rest[sn].to_quaternion().inverted()@source_rest_direction
            target_rest_direction=rest_hand[n].to_3x3()@tip_local[family]
        desired=(maps['l']@(source_hand_inv@source_direction)).normalized()
        rotation=target_rest_direction.normalized().rotation_difference(desired)@rest_hand[n].to_quaternion()
        local=rest_hand[pn].inverted()@rest_hand[n] if pn in rest_hand else rest_hand[n]
        position=donor_shape[pn]@local.translation if pn in donor_shape else local.translation
        donor_shape[n]=Matrix.LocRotScale(position,rotation,rest_hand[n].to_scale())

hand_forward=(forward-palm*forward.dot(palm)).normalized()
hand_frame=Matrix((hand_forward.cross(palm),hand_forward,palm)).transposed().to_quaternion()
radial=(rest_hand['index_01_l'].translation-rest_hand['pinky_01_l'].translation).normalized()
radial=(radial-palm*radial.dot(palm)).normalized()
rod=min((part for part in geometry['parts'] if 'WPN_Extractor' in part['bones']),key=lambda part:part['min'][1])
cap=Vector(((rod['min'][0]+rod['max'][0])*.5,rod['min'][1],(rod['min'][2]+rod['max'][2])*.5))
upper_length=(idle['lowerarm_l'].translation-idle['upperarm_l'].translation).length
lower_length=(idle['hand_l'].translation-idle['lowerarm_l'].translation).length
source_shoulder=idle['upperarm_l'].translation.copy()
peak=_base_single(0,6,1.03)
peak_GD=peak['WPN_Crane']@gunlocal['WPN_Crane'].inverted()
reference_normal=(peak_GD.to_3x3()@Vector((0,1,0))).normalized()
reference_forward=preferred_hand@hand_forward
reference_forward=(reference_forward-reference_normal*reference_forward.dot(reference_normal)).normalized()
