"""Create Zhufeng's independent authoring scripts from the fitted blade pipeline."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
D=P.parent/'ChixiaoBladeV1'
for name in ['author_blade.py','author_shader.py','author_icon.py','install_assets.py','prepare_asset_host.py','stage_assets.ps1']:
    s=(D/name).read_text(encoding='utf-8-sig')
    s=s.replace('Chixiao','Zhufeng').replace('CHIXIAO','ZHUFENG').replace('chixiao','zhufeng').replace('赤霄','逐风')
    if name=='author_blade.py':
        s=s.replace('C=np.array([CX,CX,.0005,.004,.004,.000,-.010,-.030,-.060,-.090,-.119,-.139])','C=np.array([CX,CX,.0005,.002,.003,.000,-.007,-.022,-.043,-.070,-.096,-.117])')
        s=s.replace('W=np.array([RW,RW,.073,.084,.092,.094,.091,.078,.059,.037,.014,.00016])','W=np.array([RW,RW,.078,.082,.084,.085,.083,.074,.057,.035,.013,.00016])')
        s=s.replace('col[:]=[.20,.22,.235]','col[:]=[.24,.29,.32]')
        s=s.replace('np.array([.25,.038,.033])','np.array([.055,.16,.185])')
        s=s.replace('np.array([.51,.34,.135])','np.array([.54,.57,.59])')
        s=s.replace('(.35,.19,.052,1)','(.47,.50,.52,1)')
        # Flowing raised dorsal ribbons, all within the narrow spine-side lane.
        a=s.index('    paths=[]');b=s.index('    for side in [-1,1]:',a)
        s=s[:a]+'''    paths=[]
    for lane in range(3):
        path=[]
        for k in range(cloud_steps*3):
            q=k/(cloud_steps*3-1)
            t=.055+q*(.54-lane*.075)
            u0=.045+lane*.063+.09*math.exp(-q*9)*math.sin(q*math.pi*4)
            path.append((t,u0))
        paths.append(path)
'''+s[b:]
        s=s.replace("across*math.cos(a)*.00045+Vector((0,side*math.sin(a)*.00024,0))","across*math.cos(a)*(.00065*(1-j/(len(path)-1))+.00012)+Vector((0,side*math.sin(a)*.00036,0))")
        s=s.replace('new closed loft with recessed spine inlay/fullers and two-sided brass cloud relief','fitted closed curved blade with blue-grey forged steel, silver edge and three tapered silver wind ribbons per face')
    if name=='install_assets.py':
        s=s.replace('u.LinearColor(.35,.19,.052,1)','u.LinearColor(.47,.50,.52,1)')
    (P/name).write_text(s,encoding='utf-8-sig' if name.endswith('.ps1') else 'utf-8')
catalog=json.loads((P.parents[2]/'Content/ColdSteelData/zhanmadao-modules.json').read_text(encoding='utf-8-sig'))
(P/'source_bindings.json').write_text(json.dumps({'factory':catalog['slots']['blade_1']['factory']['materials']},indent=2),encoding='utf-8')
print('ZHUFENG_AUTHORING_SOURCES_READY')
