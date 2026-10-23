"""Install Final Toll's option, module, body roles and model-derived framed icon."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,runpy,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
ID='final_toll_soul_bell';WEAPON='ue_runebound_warhammer';D='/Game/Weapons/RuneboundWarhammer20261022/FinalTollV1/'
MESH='SM_RuneboundWarhammer_FinalTollHammerHeads_V1';ICON=WEAPON+'_hammer_heads_'+ID+'.png'
OPTION={
 'id':ID,'name':'终律·镇魂钟','tier':'legendary','weapons':[WEAPON],
 'description':'符文战锤专属。古老钟室以暗青铜拱肋锁住符文音柱，黑铁平砧承接落锤的重量，让镇魂回响沿长柄传递。',
 'appearance':'镂空钟室 · 苍金音柱 · 黑铁平砧与风化青铜拱肋',
 'stats':{'heavy_damage_mult':1.15,'heavy_release_stamina_mult':2.},
 'effects':[{'text':'重击伤害 +15%','benefit':1},{'text':'重击出手体力消耗 +100%','benefit':-1}],
 'special_effects':[
  '双重重击｜蓄满后的重击改为先下砸、再从落点向右上回击，两段分别造成完整重击伤害并独立命中；释放动作不受普通攻击速度影响。出手体力消耗翻倍，蓄力期间消耗不变。',
  '镇魂刻印｜符文苏醒期间，重击有效命中为该目标叠加一层刻印，持续6秒；同一目标达到两层时消耗刻印，附加350%魔法攻击力的单体魔法伤害，且触发重击的削韧效果翻倍。每段对同一目标只叠一层，双重重击两段均命中即可触发。',
  '符文共鸣｜搭配破坏魔力符文，终律附加魔法伤害提高至700%魔法攻击力，声纹与光尘转红；迅捷魔力符文保留5次命中苏醒与普通攻击速度+10%。',
  '终律回响｜内部符文音柱闪亮，目标上的竖向刻印合拢，细长声纹与苍金光尘上浮消散。苏醒结束、切换武器、卸下锤头或目标死亡时清除刻印。'
 ]}
SPEC={'mesh':D+MESH+'.'+MESH,'location_cm':[0.,0.,91.6],
 'appearance':OPTION['appearance'],'interface':'runebound_warhammer_modular_v1',
 'model_revision':'FinalTollHammerHeadV1','exclusive_to':WEAPON,'heavy_attack':'final_toll_double_heavy',
 'materials':{n:D+n+'.'+n for n in ('M_FinalToll_PBR_Surface','M_FinalToll_FineInlay_Brass','M_FinalToll_Rune_Energy')}}

def publish():
 imported=json.loads((P/'import_receipt.json').read_text('utf-8-sig'))
 builds=json.loads((P/'build_receipt.json').read_text('utf-8-sig'))
 if not imported.get('complete') or not imported.get('installed_to_main_project'):raise RuntimeError('Finish actual asset saves and installation first')
 if not {'FPSGAME','FPSGAMEEditor'}<={r['target'] for r in builds['targets'] if r['exit_code']==0}:raise RuntimeError('Finish necessary native builds first')
 image=P/'Icons'/ICON
 if not image.is_file():raise RuntimeError('Finish actual-model modification icon first')
 changes=[]
 for relative,kind in [('Content/ColdSteelData/runebound-warhammer-gunsmith.json','bench'),('Content/ColdSteelData/runebound-warhammer-modules.json','modules'),('SourceAssets/RuneboundWarhammer20261022/ModulesV1/workbench.json','bench'),('SourceAssets/RuneboundWarhammer20261022/ModulesV1/catalog_base.json','modules')]:
  path=ROOT/relative;before=path.read_bytes();value=json.loads(before.decode('utf-8-sig'))
  if kind=='bench':
   options=next(c for c in value['columns'] if c['key']=='hammer_heads').setdefault('options',[])
   i=next((i for i,v in enumerate(options) if v.get('id')==ID),None)
   if i is None:options.append(OPTION)
   else:options[i]=OPTION
  else:value['slots']['hammer_heads'][ID]=SPEC
  backup=P/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(before)
  if path.read_bytes()!=before:raise RuntimeError('Concurrent change '+relative)
  tmp=path.with_name(path.name+'.final-toll.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,path);changes.append(relative)
 # This shared file is published strictly by owned leaf paths, never replaced.
 body=ROOT/'Content/ColdSteelData/player_body.json';before=body.read_bytes();candidate=json.loads(before.decode('utf-8-sig'));owned=[]
 for row in imported['body_animations']:
  cursor=candidate
  for part in row['scope']:cursor=cursor[part]
  role='Warhammer.FullBody.FinalTollHeavy';cursor[role]=row['asset'];owned.append(tuple(row['scope']+[role]))
 commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
 body_receipt=commit(body,before,candidate,owned_paths=owned,producer=__file__)
 icon_target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/ICON;shutil.copy2(image,icon_target)
 receipt={'complete':True,'saved_at_utc':datetime.now(timezone.utc).isoformat(),'weapon':WEAPON,'part':ID,'catalogs':changes,
  'saved_assets':imported['assets'],'native_builds':builds['targets'],'body_roles':[list(p) for p in owned],'body_config_receipt':str(body_receipt),
  'icon':str(icon_target.relative_to(ROOT)),'icon_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
  'model_triangles':111240,'textures':{'resolution':4096,'maps':['BaseColor','ORM','Normal']},
  'double_heavy':{'seconds':1.25,'contacts':[.10,.42],'damage_each':'full heavy, including the +15% modifier','release_stamina_multiplier':2.,'ordinary_attack_speed_applies':False},
  'soul_seal':{'target_scope':'per enemy, per weapon instance','heavy_hits':2,'seconds':6.,'magic_attack_coefficient':3.5,'destruction_coefficient':7.,'triggering_heavy_toughness_multiplier':2.},
  'particles':'one shared bounded DynamicMesh, 64 additional seal quads, pale-gold/red emission and upward final-toll dust; no additional area detonation',
  'save_schema':'existing gunsmith_parts.hammer_heads; no schema change',
  'tests_run':False,'game_started':False,'editor_ui_started':False}
 (P/'delivery_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
 print('FINAL_TOLL_PUBLISHED',json.dumps({'assets':len(imported['assets']),'roles':len(owned),'catalogs':changes},ensure_ascii=False))
if __name__=='__main__':publish()
