"""Read-only compressed-pose inventory for the requested cross-firearm review.

Known runtime folders plus prior reload branches; this is a bounded asset sweep,
not a claim that every runtime combination or procedural layer is covered.
"""
import ast
import json
import math
import sys
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/FirearmChainmailReview20260930'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,write,digest,asset_file
from garment_ue import transform


def group(name):
    name=name.lower()
    if any(x in name for x in ('reload','single_','speed_')):return 'reload'
    if 'sprint' in name:return 'sprint'
    if 'inspect' in name:return 'inspect'
    if 'equip' in name:return 'equip'
    if 'quick' in name or 'melee' in name:return 'melee'
    if 'aim' in name:return 'ads'
    if 'fire' in name:return 'fire'
    if 'idle' in name:return 'idle'
    return None


def main(only=None):
    # Reuse the historical folder inventory, not its poses or old asset refs.
    tree=ast.parse((P/'SourceAssets/ChainmailReloadFit20260929/collect.py').read_text())
    roots=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='roots' for t in n.targets))
    additions={
        'M4':['M4ContactImpactFinal','M4WrapGripFinal','M4TacticalSprint20260915'],
        'AKM':['AKMIntegration/SourceMatched','AKMIntegration/EquipCharge','RifleTacticalSprint20260915/AKM'],
        'QBZ191':['QBZ191/Refined20260913/Animations','RifleTacticalSprint20260915/QBZ191'],
        'ASH12':['ASH12/Integrated20260917/Animations','ASH12/TacticalSprint20260919'],
        'M1911':['M1911/Contact20260913/Animations','M1911/RevolverInspect20260927/Animations',
            'M1911/QuickCombat20260919/Animations','PistolLocomotion20260914/M1911'],
        'DW715':['DanWesson715/Upgrade20260914/Animations','DanWesson715/QuickCombat20260918/Animations',
            'PistolLocomotion20260914/DW715'],
        'LMG201':['LMG201/BeltFeed08/Animations','LMG201/Accessories22/Animations']}
    for name,folders in additions.items():roots[name]+=folders
    for weapon in ['M1911','DW715']:
        for side in ['l','r']:
            folder=f'PistolDualWield20260914/{weapon}/{side}'
            roots[weapon+'_'+side]=[folder+'/NaturalAimV3/Animations',folder+'/SprintSmoothV5/Animations',
                f'DualPistolQuickCombat20260920/SpinRecoveryV5/{weapon}/{side}/Animations']
            if weapon=='DW715':roots[weapon+'_'+side].append(folder+'/RevolverReloadFlickV6/Animations')
    config=read(P/'Content/ColdSteelData/modular_outfits.json')
    bones=[stem+'_'+side for side in ['l','r'] for stem in
        ['clavicle','upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand']]
    bones+=['WPN_root','WPN_RearSight','WPN_FrontSight']
    manifest=read(R/'inventory.json') if only else {}
    for rig,folders in roots.items():
        if only and rig not in only:continue
        native,profile=next((k,v) for k,v in config['profiles'].items() if v['rig_profile']==rig)
        mesh=u.load_asset(native)
        if not mesh:raise RuntimeError('Missing native '+native)
        paths=set()
        for folder in folders:
            for file in (P/'Content/Weapons'/folder).rglob('A_*.uasset'):
                if not group(file.stem):continue
                if rig=='M4' and 'ExtMagContact' in folder and file.stem.startswith('A_AKM_'):continue
                if rig=='DW715' and 'LeftRecovery' in folder and ('single_0_' in file.stem or 'speed_' in file.stem):continue
                paths.add('/Game/'+file.relative_to(P/'Content').with_suffix('').as_posix())
        options=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.COMPRESSED)
        clips=[]
        for path in sorted(paths):
            asset=u.load_asset(path)
            if not isinstance(asset,u.AnimSequence):continue
            duration=asset.get_play_length()
            # Full motion at 10 Hz plus endpoints; idle/aim pose still sampled
            # over the authored cycle. No playback or persistent engine edits.
            count=max(2,math.ceil(duration*10)+1)
            samples=[]
            available=None
            for i in range(count):
                time=duration*i/(count-1)
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,time,options)
                if available is None:
                    available=set(map(str,u.AnimPoseExtensions.get_bone_names(pose)))
                samples.append(dict(time=time,bones={n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))
                    for n in bones if n in available}))
            clips.append(dict(asset=path,sha256=digest(asset_file(path)),group=group(asset.get_name()),samples=samples))
        shirt=config['items']['ue_chainmail_shirt']['rig_meshes'][rig]
        result=dict(profile=rig,native=native,native_sha256=digest(asset_file(native)),
            shirt=shirt,shirt_sha256=digest(asset_file(shirt)),roots=folders,rate_hz=10,clips=clips)
        output=R/'poses'/f'{rig}.json';output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
        counts={g:sum(c['group']==g for c in clips) for g in sorted({c['group'] for c in clips})}
        manifest[rig]=dict(path=str(output),native=native,shirt=shirt,clips=len(clips),
            samples=sum(len(c['samples']) for c in clips),groups=counts)
        write(R/'inventory.json',manifest)
        print('FIREARM_CHAINMAIL_READ',rig,manifest[rig]['clips'],manifest[rig]['samples'],counts,flush=True)


if __name__=='__main__':main()
