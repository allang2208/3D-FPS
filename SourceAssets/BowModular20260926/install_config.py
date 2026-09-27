"""Activate the saved modular recipe and modification catalog."""
from pathlib import Path
import json
P=Path(__file__).parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
receipt=json.loads((P/'import-receipt.json').read_text())
assets=receipt['saved']
for name in ['SM_Bow_BodyModular','SM_Bow_GripWrap','SM_Bow_ArrowRestWood','SM_Bow_ArrowRestLined','M_Bow_GripLinen','M_Bow_FastString']:
    if name not in assets:raise RuntimeError('Required saved asset missing '+name)
path=DATA/'bows.json';catalog=json.loads(path.read_text(encoding='utf-8-sig'));bow=catalog['bow_dark']
if bow.get('bow_presentation_revision',0)<25:
    for k in list(bow):
        if k.startswith('bow_part_arrow_rest_'):bow[k.replace('bow_part_arrow_rest_','bow_part_arrow_')]=bow.pop(k)
bow.update(bow_presentation_revision=25,bow_part_slots='riser,grip,string,arrow_rest,sight,arrow',
           bow_part_riser_mesh=assets['SM_Bow_BodyModular'],bow_part_grip_mesh=assets['SM_Bow_GripWrap'],
           bow_part_grip_material='',bow_part_grip_rods=0,bow_part_grip_scale=1,
           bow_part_arrow_rest_mesh=assets['SM_Bow_ArrowRestWood'],bow_part_arrow_rest_material='',
           bow_part_arrow_rest_rods=0,bow_part_arrow_rest_scale=1)
def visual(slot):return {k:v for k,v in bow.items() if k.startswith('bow_part_'+slot+'_')}
def option(id,name,description,appearance,visual,**stats):return dict(id=id,name=name,description=description,appearance=appearance,visual=visual,stats=stats)
columns=[]
def column(key,name,default,desc,options):columns.append(dict(key=key,name=name,default=default,description=desc,factory_visual=visual(key),options=options))
column('riser','弓体','原装木质弓胎','整根木质弓胎，保留原有弓梢与弦挂点。',[
 option('strong_draw','强拉力弓胎','以更长拉弓时间和更高耐力消耗，换取满弓伤害与箭速。','沿用原装弓胎形状；本项为拉力调校。',{},damage_mult=1.12,draw_mult=1.10,speed_mult=1.06,stamina_mult=1.15)])
column('grip','握把缠带','原装绿色缠带','从原弓分离的中心缠带，保留手掌接触面。',[
 option('waxed_linen','棕色蜡麻缠带','更稳定的握持，降低满弓晃动并延长稳定保持时间。','原有绳圈换为棕色哑光蜡麻。',{'bow_part_grip_material':assets['M_Bow_GripLinen']},sway_mult=.85,hold_mult=1.10)])
column('string','弓弦','原装弓弦','上下两段动态弓弦，沿用右手拉弦接触点。',[
 option('fast_string','轻量快弦','缩短拉弓时间并提高箭速，满弓保持时间略短。','更细的浅棕色弦。',{'bow_part_string_material':assets['M_Bow_FastString'],'bow_part_string_radius_cm':.065},draw_mult=.94,speed_mult=1.04,hold_mult=.92)])
column('arrow_rest','箭台','木制箭台','贴合原弓表面的独立木托，托住箭杆。',[
 option('lined_rest','皮垫箭台','软垫稳定搭箭，缩短搭箭时间并降低腰射扩散。','木托上增加一层深棕色皮垫。',{'bow_part_arrow_rest_mesh':assets['SM_Bow_ArrowRestLined']},nock_mult=.93,spread_mult=.90)])
column('sight','瞄具','木制机械瞄具','沿用当前木制瞄具和 ADS 对位点。',[
 option('no_sight','拆除瞄具','移除木制瞄具，ADS 改为沿箭杆方向瞄准。','移除瞄圈、准星及其底座。',{'bow_part_sight_mesh':'','bow_ads_sight_cm':'','bow_ads_rest_cm':'75,0,0'})])
columns[-1]['factory_visual']['bow_ads_sight_cm']=bow['bow_ads_sight_cm']
gs=dict(version=1,columns=columns,weapons=[dict(id='bow_dark',traits=[dict(icon='neutral',text=s) for s in ['整根弓胎 · 独立缠带','五槽改造 · 箭矢独立','腰射扩散 · ADS 精准']])])
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(DATA/'bow-gunsmith.json').write_text(json.dumps(gs,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
config=ROOT/'Config/DefaultGame.ini';text=config.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/ModularV13")'
if line not in text:text=text.replace('[/Script/UnrealEd.ProjectPackagingSettings]','[/Script/UnrealEd.ProjectPackagingSettings]\n'+line)
config.write_text(text,encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'revision':25,'slots':[c['key'] for c in columns],'assets_saved':True,'runtime_tested':False},indent=2),encoding='utf8')
print('BOW_MODULAR_CATALOG_INSTALLED')
