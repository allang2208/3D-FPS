"""Read both shotgun viewmodel binds, the equipped glove and saved sequence poses."""
import ast
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
from native_glove_profile import P, R, RIG
OUT = R / 'Read'
OUT.mkdir(parents=True,exist_ok=True)
G, Q, B, L = (u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries,
              u.GeometryScript_BoneWeights, u.GeometryScript_List)
capture = ast.parse((P / 'Tools/ST6SleeveRepair/capture.py').read_text('utf-8'))
exec(compile(ast.Module([n for n in capture.body if isinstance(n, ast.FunctionDef)], []),
             'outfit-native-mesh-reader', 'exec'))
if os.environ.get('TS01_READ_INSTALLED_SHOTGUN_GLOVE')=='1':
    installed = json.loads((R/'published.json').read_text())
    read(installed['asset'], 'Installed')
    print('TS01_INSTALLED_GLOVE_READ')
else:
    cfg = json.loads((P / 'Content/ColdSteelData/modular_outfits.json').read_text('utf-8-sig'))
    profiles = {key: row for key, row in cfg['profiles'].items() if row['rig_profile'] == RIG}
    original='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR4/Wear/'+RIG+'/SK_TS01_'+RIG+'_CuffFitGloves'
    read(original+'.'+original.split('/')[-1], 'R4')

    def packed(transform):
        p, q, s = transform.translation, transform.rotation, transform.scale3d
        return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]

    for path, row in profiles.items():
        gun = 'M870' if '/M870/' in path else RIG
        for body, section in [('Jason', cfg), ('Kaitlin', cfg['body_variants']['kaitlin'])]:
            read(section['profiles'][path]['native_bare_skin'], gun+'_'+body)
        mesh = u.load_asset(path)
        mod = u.SkeletonModifier()
        if not mod.set_skeletal_mesh(mesh):
            raise RuntimeError('Missing reference mesh '+path)
        names = [str(n) for n in mod.get_all_bone_names()]
        parents = [str(mod.get_parent_name(n)) for n in names]
        data = dict(names=names, parents=parents, ref=[packed(mod.get_bone_transform(n,True)) for n in names], clips={})
        folder = path.rsplit('/',1)[0] + '/Animations/'
        for clipname in sorted((P/'Content'/folder[6:]).glob('A_'+gun+'_*.uasset')):
            clip = u.load_asset(folder+clipname.stem)
            if not isinstance(clip, u.AnimSequence):
                continue
            end = clip.get_play_length()
            frame_count = max(1, round(12*end))
            times = [end*i/frame_count for i in range(frame_count+1)]
            data['clips'][clipname.stem] = dict(times=times, path=clip.get_path_name(), local=[
                [packed(v) for v in u.AnimationLibrary.get_bone_poses_for_time(clip,names,t,False,mesh)] for t in times])
        with gzip.open(OUT/(gun+'_poses.json.gz'), 'wt', encoding='utf8') as f:
            json.dump(data,f,separators=(',',':'))
        print('NATIVE_GLOVE_POSES',gun,len(data['clips']),flush=True)
