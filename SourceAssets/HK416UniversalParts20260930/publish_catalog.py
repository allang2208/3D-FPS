"""Add the two common IDs to the 13 supported firearms without reformatting peers."""
import json,re,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];file=P/'Content/ColdSteelData/gunsmith.json'
parts={
 'optic':{'id':'eoth_holographic','name':'EOTH全息瞄准镜','description':'封闭护罩内置环形分划与透光镜片，配合适配安装座连接枪械。','effects':[{'text':'开镜耗时减少5%','benefit':1}],'stats':{'ads_percent':-.05}},
 'muzzle':{'id':'multi_caliber_suppressor','name':'多口径消音器','description':'通过开放式管口与适配接环连接枪管，减轻开火声与射击扰动。','effects':[{'text':'开镜耗时增加5%','benefit':-1},{'text':'子弹速度降低15%','benefit':-1},{'text':'后坐力降低20%','benefit':1},{'text':'枪械稳定性提高15%','benefit':1},{'text':'腰射随机散布减少10%','benefit':1}],'stats':{'ads_percent':.05,'bullet_speed_mult':.85,'recoil_mult':.8,'stability_mult':1.15,'hip_spread_mult':.9}}}
supported={'ue_m4a1','ue_akm','ue_qbz191','ue_m1911','ue_g18','ue_dan_wesson715','ue_ash12','ue_m16a2','ue_a762','ue_svd','ue_pkm_lowpoly','ue_lmg201','ue_hk416'}
old=file.read_text(encoding='utf-8-sig');decoder=json.JSONDecoder();edits=[];published=[]
pos=old.index('[',old.index('"weapons"'))+1
while True:
    while old[pos].isspace() or old[pos]==',':pos+=1
    if old[pos]==']':break
    weapon,n=decoder.raw_decode(old[pos:]);block=old[pos:pos+n]
    if weapon['id'] in supported:
        opts=block.index('{',block.index('"options"'));_,olen=decoder.raw_decode(block[opts:])
        for slot,part in parts.items():
            match=re.search(r'"'+slot+r'"\s*:\s*\[',block[opts:opts+olen]);start=opts+match.end()-1
            options,length=decoder.raw_decode(block[start:]);end=start+length-1
            if any(x['id']==part['id'] for x in options):continue
            indent=' '*(len(block[:start].rsplit('\n',1)[-1])-len(block[:start].rsplit('\n',1)[-1].lstrip())+2)
            encoded=json.dumps(part,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
            insertion=',' if options else ''
            edits.append((pos+end,pos+end,insertion+'\n'+indent+encoded+'\n'+indent[:-2]))
        published.append(weapon['id'])
    pos+=n
backup=O/'CodeBefore/gunsmith.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(file,backup)
new=old
for start,end,content in sorted(edits,reverse=True):new=new[:start]+content+new[end:]
if file.read_text(encoding='utf-8-sig')!=old:raise RuntimeError('Catalog changed during publication')
file.write_text(new,encoding='utf-8')
(O/'catalog_publication.json').write_text(json.dumps({'parts':parts,'weapons':published,'ADS_convention':'Project ads_percent is the written signed change in opening time. Existing convention retained.','runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('COMMON_PART_CATALOG_PUBLISHED',len(published),'firearms',len(edits),'options')
