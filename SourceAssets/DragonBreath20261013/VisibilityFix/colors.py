import sys,json
from pathlib import Path
import unreal as u
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
import build_dragon_breath as a
out={}
for path in [a.DEST+'/NS_DragonBreath',a.SOURCE+'/VFX/Niagara/N_FlameAttack']:
    s=u.load_asset(path); rows={}
    for e in a.emitters(s):
        rows[e]={}
        for script,module,keys in [('ParticleSpawnScript','InitializeParticle',['Color Mode','Color','Color Minimum','Color Maximum']),('ParticleUpdateScript','ScaleColor',['Scale Mode','Scale RGB','Scale Alpha','Color Value To Scale'])]:
            for k in keys:
                rows[e][module+'/'+k]=u.RainAssetEditor.read_input(s,e,script,module,k)
    out[path]=rows
Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/VisibilityFix/colors.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('DRAGON_COLORS '+json.dumps(out))
