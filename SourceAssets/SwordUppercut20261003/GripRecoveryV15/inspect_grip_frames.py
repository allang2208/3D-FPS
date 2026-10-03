from pathlib import Path
P=Path(__file__).resolve().parent
exec(compile((P/'author_common.py').read_text('utf-8'),str(P/'author_common.py'),'exec'))
def rigid(m):return mat(m.translation,m.to_quaternion())
d=json.loads((P/'SourceV14/Standard/editable_keys.json').read_text('utf-8'))
for i in (0,120,135,200,220,246):
    w={n:canonical(m) for n,m in globalize({n:native(k) for n,k in d['samples'][i]['bones'].items()}).items()}
    inv=rigid(w['WPN_root']).inverted()
    print('FRAME',i,'weapon',list(w['WPN_root'].translation),'blade_local',list(inv@w['Blade_Base'].translation))
    for s in ('l','r'):
        h=inv@rigid(w['hand_'+s]); center=sum((inv@w[n+'_'+s].translation for n in ('index_01','middle_01','ring_01','pinky_01')),Vector())/4
        print(s,'hand_local',list(h.translation),'knuckles',list(center),'rotation',list(h.to_quaternion()))
