"""Requested icon audit and scoped PNG deployment. Does not run the game."""
import json,hashlib,shutil,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;R=P.parents[1];D=R/'Content/ColdSteelData/AttachmentIcons20260913';O=P/'Icons';B=R/'trash/AttachmentIconAudit20260914/Before/Icons';B.mkdir(parents=True,exist_ok=True)
M=json.loads((P/'render_manifest.json').read_text());before=json.loads((P/'inventory.json').read_text());catalog=json.loads((R/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
renderkeys={r['key'] for r in M['renders']};preserve=set(M['preserve']);aliases=M['aliases']
for key in preserve:
 source=D/(key+'.png');old=next(x for x in before['icons'] if x['key']==key)
 if digest(source)!=old['sha256']:raise RuntimeError('Accepted stock changed concurrently: '+key)
 shutil.copy2(source,O/source.name)
for key in renderkeys:
 if not (O/(key+'.json')).exists() or not (O/(key+'.png')).exists():raise RuntimeError('Incomplete render '+key)
pending=dict(aliases)
while pending:
 progressed=False
 for key,data in list(pending.items()):
  target=O/(data['target']+'.png')
  if target.exists():shutil.copy2(target,O/(key+'.png'));pending.pop(key);progressed=True
 if not progressed:raise RuntimeError('Unresolved alias graph '+str(pending))
keys=renderkeys|preserve|set(aliases);files=[]
for key in sorted(keys):
 path=O/(key+'.png');im=Image.open(path).convert('RGBA');a=im.getchannel('A');bbox=a.getbbox();hist=a.histogram()
 if im.size!=(1024,1024) or not bbox or not hist[0] or min(bbox[0],bbox[1],1024-bbox[2],1024-bbox[3])<50:raise RuntimeError('Framing/alpha failure '+key+': '+str(bbox))
 files.append({'key':key,'size':list(im.size),'alpha_bbox':bbox,'opaque_fraction':hist[255]/1048576,'sha256':digest(path),'kind':'accepted_stock' if key in preserve else 'intentional_alias' if key in aliases else 'new_actual_model_render'})
options=[];missing_before=[];oldkeys={i['key'] for i in before['icons']}
for w in catalog['weapons']:
 effective={slot:{o['id']:o for o in opts} for slot,opts in w['options'].items()}
 for slot,opts in catalog.get('common_options',{}).items():
  effective.setdefault(slot,{})
  for option in opts:effective[slot].setdefault(option['id'],option)
 allowed=list(w['allowed'])+ [s for s in catalog.get('common_options',{}) if s not in w['allowed']]
 for slot in allowed:
  for ident,option in effective[slot].items():
   common=slot+'_'+ident;override=w['id']+'_'+common;resolved=override if override in keys else common
   if resolved not in keys:raise RuntimeError('Uncovered catalog option '+w['id']+'/'+common)
   row={'weapon':w['id'],'weapon_name':w['name'],'slot':slot,'id':ident,'name':option['name'],'icon':resolved,'weapon_override':resolved==override}
   options.append(row)
   if common not in oldkeys and override not in oldkeys:missing_before.append(row)
changes=[]
for entry in files:
 key=entry['key'];src=O/(key+'.png');dst=D/src.name
 if dst.exists() and digest(src)==digest(dst):continue
 for suffix in ['.png','.uasset']:
  old=D/(key+suffix)
  if old.exists() and not (B/old.name).exists():shutil.copy2(old,B/old.name)
 state='replaced' if dst.exists() else 'added';shutil.copy2(src,dst);changes.append({'key':key,'action':state})
report={'scope':'Requested complete gunsmith option and category icon audit; no gameplay tests.',
 'weapons':len(catalog['weapons']),'effective_option_rows':len(options),'unique_current_option_images':len({x['icon'] for x in options}),
 'before_png_count':len(oldkeys),'missing_before_option_rows':len(missing_before),'missing_before_unique_common_keys':sorted({x['slot']+'_'+x['id'] for x in missing_before}),
 'actual_model_renders':len(renderkeys)-1,'neutral_state_renders':1,'preserved_accepted_stocks':len(preserve),'intentional_aliases':len(aliases),'after_png_count':len(keys),
 'replaced_pngs':sum(x['action']=='replaced' for x in changes),'added_pngs':sum(x['action']=='added' for x in changes),
 'missing_after':0,'options':options,'files':files,'changes':changes,'alias_policy':aliases,
 'findings':['Original iron sight showed front and rear together; now one rear assembly per weapon, with its fixed mount where split from the receiver.',
 'Old attachment images used angled concepts and baked black backgrounds; regenerated actual current models at level orthographic front-left.',
 'M1911 and DW715 trigger images were identical concepts; use their different actual triggers.',
 'Missing defaults, balanced rear grip and tactical device images used category fallback; all effective catalog options now resolve explicitly.',
 'Factory parts of different weapon families previously shared M4 images; per-weapon image resolution and cache keys now preserve differences.',
 'Intermediate FBX exports lose some runtime material graphs; icon scenes restore explicit polymer and receiver/mount coating bindings from current import recipes.',
 'Shared numeric-only short/long barrel and fast trigger options have no distinct runtime mesh. Deliberately reuse the current real part image; labels/stats differentiate.',
 'Category navigation images now use the same transparent real-part images; old category material remains a compatibility fallback.'],
 'limits':['Blender lighting differs from in-game lighting. M4 Phong conversion is approximated with the same coating source; game materials are unchanged.',
 'Shared rifle accessory icons use the current M4 body variant. Small rifle-specific mounting adapters and coatings use that representative; differing factory silhouettes and compact pistol variants have dedicated overrides.',
 'No PIE/gameplay or save regression was run. User tests the updated workbench in game.']}
(P/'audit_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k in ['weapons','effective_option_rows','unique_current_option_images','before_png_count','missing_before_option_rows','missing_before_unique_common_keys','actual_model_renders','preserved_accepted_stocks','after_png_count','replaced_pngs','added_pngs','missing_after']},ensure_ascii=False))
