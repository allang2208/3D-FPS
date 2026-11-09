"""Register the M249 in the existing firearm, workshop, clothing and inventory catalogues."""
from pathlib import Path
import json
import os
import tempfile

ROOT=Path(__file__).resolve().parent
DATA=ROOT.parents[1]/"Content/ColdSteelData"
def insert(file,kind,anchor,key,value):
    p=DATA/file
    original=p.read_bytes()
    document=original.decode("utf-8-sig")
    newline="\r\n" if "\r\n" in document else "\n"
    document=document.replace("\r\n","\n")
    spaces={"root":"  ","nested":"    ","variant":"        ","array":"    "}[kind]
    if kind=="array":
        token=spaces+'{\n'+spaces+'  "id": "'+anchor+'",'
        begin=spaces+json.dumps(value,ensure_ascii=False,indent=2).replace("\n","\n"+spaces)
        present=spaces+'  "id": "'+key+'",'
    else:
        token=spaces+json.dumps(anchor,ensure_ascii=False)+": {"
        begin=spaces+json.dumps(key,ensure_ascii=False)+": "+json.dumps(value,ensure_ascii=False,indent=2).replace("\n","\n"+spaces)
        present=spaces+json.dumps(key,ensure_ascii=False)+": {"
    if "\n"+present in document:return
    if document.count("\n"+token)!=1:raise RuntimeError("Cannot place "+file+" "+anchor)
    out=document.replace("\n"+token,"\n"+begin+",\n"+token,1)
    encoded=out.replace("\n",newline).encode("utf-8-sig" if original.startswith(b"\xef\xbb\xbf") else "utf8")
    with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as tmp:
        tmp.write(encoded)
    try:
        if p.read_bytes()!=original:raise RuntimeError("Concurrent edit to "+str(p))
        os.replace(tmp.name,p)
    finally:Path(tmp.name).unlink(missing_ok=True)

item={"category":"weapon","desc":"M249 是一款班用轻机枪。这个改装版本配有前握把、光学瞄具和折叠脚架，使用 5.56 毫米弹药。弹箱支持持续射击，更换时需要留出较长的空当。","equipSlot":"weapon","icon":"Icons/ue_m249.png","ue_icon":"Icons/ue_m249.png","icon_fallback":"M249","id":"ue_m249","isTwoHanded":True,"name":"M249 轻机枪","stack_max":1,"stats":[{"name":"物理攻击","value":"30"},{"name":"弹匣容量","value":"100"}],"type":"武器","weaponType":"machineGun","weaponTypeTag":"轻机枪","grid_w":5,"grid_h":2}
insert("items.json","root","ue_pkm_lowpoly","ue_m249",item)
gun={"id":"ue_m249","model":"M249","name":"M249 轻机枪","inherit_common_options":False,"allowed":["bipod"],
     "base":{"spread_mult":2.25,"ammo_item_id":"ammo_556","ads_smooth":7.133,"mag_size":100,"recoil":92,"camera_shake":94,"fire_interval":.08,"reload_time":8.8,"empty_reload_time":9.6,"damage":30,"bullet_speed":350,"effective_range":120,"stability_mult":1.1},
     "traits":[{"icon":"drawback","text":"持握机枪时，移动速度−33%；收起武器或切换至非机枪武器后恢复。"}],
     "options":{"bipod":[{"id":"false","name":"原厂折叠脚架","description":"两条支腿收在护木下方。","effects":[],"stats":{},"special_effects":[]},{"id":"m249_no_bipod","name":"卸下脚架","description":"移除支腿和下方支架。","effects":[{"text":"开镜耗时-5%","benefit":1}],"stats":{"ads_percent":-.05},"special_effects":[]}]}}
import sys
sys.path.insert(0,str(ROOT/"Repair04"))
from publish_factory import factory
gun=factory(gun)
insert("gunsmith.json","array","ue_pkm_lowpoly","ue_m249",gun)
formula={"source":"M249_LMG","base":7,"enhanceFlat":.60,"attrs":[{"key":"str","base":.30,"perEnhance":.068},{"key":"wis","base":.25,"perEnhance":.056}]}
insert("combat-weapon-formulas.json","root","ue_pkm_lowpoly","ue_m249",formula)
recipe=json.loads((ROOT/"assembly.json").read_text(encoding="utf8"))
insert("gun-assembly.json","array","assemble_pkm_lowpoly","assemble_m249",recipe)
assets=json.loads((ROOT/"assets_saved.json").read_text())
clothes=json.loads((DATA/"modular_outfits.json").read_text(encoding="utf-8-sig"))["profiles"]
donor=next(k for k in clothes if k.endswith("SK_PKM_Manny_Modular.SK_PKM_Manny_Modular"))
profile=clothes[donor].copy()
profile["hide_source_materials"]=assets["skin_slots"]
insert("modular_outfits.json","nested",donor,assets["mesh"],profile)
catalog=json.loads((DATA/"modular_outfits.json").read_text(encoding="utf-8-sig"))
for variant in catalog.get("body_variants",{}).values():
    if donor in variant.get("profiles",{}):
        other=variant["profiles"][donor].copy()
        other["hide_source_materials"]=assets["skin_slots"]
        insert("modular_outfits.json","variant",donor,assets["mesh"],other)
