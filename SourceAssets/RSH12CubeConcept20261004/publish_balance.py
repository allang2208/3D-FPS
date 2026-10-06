"""Publish the requested RSH base tuning only; the cuboid remains concept art."""
import json, math, re
from pathlib import Path

O=Path(__file__).resolve().parent
P=O.parents[1]
# Frozen pre-change baseline. Reruns do not compound the user's 25 percent / 25 points.
ORIGINAL_RECOIL=180.
ORIGINAL_SHAKE=140.
ORIGINAL_STABILITY=100./(1.+.5*ORIGINAL_SHAKE/100.+.5*math.sqrt(ORIGINAL_SHAKE/100.))
TARGET_RECOIL=ORIGINAL_RECOIL*1.25
TARGET_STABILITY=ORIGINAL_STABILITY-25.
STABILITY_MULT=TARGET_STABILITY/ORIGINAL_STABILITY

def apply_weapon(weapon):
    weapon['base']['recoil']=TARGET_RECOIL
    weapon['base']['stability_mult']=STABILITY_MULT

if __name__=='__main__':
    path=P/'Content/ColdSteelData/gunsmith.json'
    raw=path.read_bytes()
    text=raw.decode('utf-8-sig')
    decoder=json.JSONDecoder()
    pos=text.index('[',text.index('"weapons"'))+1
    while True:
        while text[pos].isspace() or text[pos]==',':pos+=1
        weapon,end=decoder.raw_decode(text,pos)
        if weapon['id']=='ue_rsh12':break
        pos=end
    before=dict(weapon['base'])
    apply_weapon(weapon)
    indent=re.search(r'[^\S\n]*$',text[:pos]).group()
    replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
    backup=O/'Before/gunsmith.json'
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during RSH tuning')
    path.write_text(text[:pos]+replacement+text[end:],encoding='utf8')
    receipt=dict(weapon='ue_rsh12',before=before,after=weapon['base'],
        recoil_change_percent=25,stability_change_points=-25,
        base_stability_before=ORIGINAL_STABILITY,base_stability_after=TARGET_STABILITY,
        suppressor_model_replaced=False,runtime_tested=False)
    (O/'balance_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print(json.dumps(dict(recoil=TARGET_RECOIL,stability_before=ORIGINAL_STABILITY,stability_after=TARGET_STABILITY,stability_mult=STABILITY_MULT)))
