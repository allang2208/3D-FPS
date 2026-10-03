"""Amend only RSH12 catalog objects after its animation assets are saved."""
from pathlib import Path
import json
O=Path(__file__).parent;P=O.parents[1];D=P/'Content/ColdSteelData'
def apply_item(item):
    item['desc']='俄罗斯大口径单动左轮，使用12.7毫米弹药，五发弹巢。每次击发后由右手拇指拨回击锤，完成拨锤与回握后才能再次射击。下置枪管，逐发装填；非空仓保留余弹，空仓先退壳再补弹。'
def apply_weapon(w):
    w['base']['fire_interval']=1.0
    for option in w['options']['trigger']:
        if option['id']=='false':
            option.update(name='原厂单动扳机',description='一次扣动发射一发；射后拇指拨回击锤，完成拨锤回握才解锁下一枪。')
        elif option['id']=='rsh12_lightweight_fast':
            option.update(description='保持单动击发；开火、拨锤和回握循环同步加速20%。')
    for trait in w.get('traits',[]):
        if '双动左轮' in trait.get('text',''):trait['text']=trait['text'].replace('双动左轮','单动左轮；射后拇指拨锤')
def write_object(path,identity,transform,list_key=None):
    raw=path.read_bytes();text=raw.decode('utf-8-sig');data=json.loads(text)
    needle=json.dumps(identity);at=text.index(needle,text.index(json.dumps(list_key)) if list_key else 0)
    if list_key:
        start=text.rfind('{',0,at);value,length=json.JSONDecoder().raw_decode(text[start:]);end=start+length
    else:
        start=text.index(':',at)+1
        while text[start].isspace():start+=1
        value,length=json.JSONDecoder().raw_decode(text[start:]);end=start+length
    transform(value);new=text[:start]+json.dumps(value,ensure_ascii=False,indent=2)+text[end:]
    backup=O/'BeforeCatalog'/path.name;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent catalog edit '+str(path))
    path.write_text(new,encoding='utf8');return value
if __name__=='__main__':
    if not json.loads((O/'import_receipt.json').read_text(encoding='utf8'))['complete']:raise RuntimeError('Animation import is incomplete')
    item=write_object(D/'items.json','ue_rsh12',apply_item)
    weapon=write_object(D/'gunsmith.json','ue_rsh12',apply_weapon,'weapons')
    (O/'catalog.json').write_text(json.dumps(dict(item=item,weapon=weapon,action='single_action',source_fire_duration=1.,cock_latch=.60),ensure_ascii=False,indent=2),encoding='utf8')
    print('RSH12_SINGLE_ACTION_CATALOG_SAVED')
