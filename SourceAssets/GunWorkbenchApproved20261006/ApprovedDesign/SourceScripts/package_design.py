import bpy,pathlib,json,zipfile
R=pathlib.Path(__file__).resolve().parents[1];D=R/'output/Delivery';D.mkdir(exist_ok=True);F=D/'GunWorkbenchDesign';F.mkdir(exist_ok=True)
sets={'TableAndMat':[],'Lamp':[],'RetainedTools':[],'NewProps':[],'NewAmmo':[],'SceneSetup':[]}
for o in bpy.context.scene.objects:
 g=o.get('layout_group','')
 if g=='OriginalTableMat':key='TableAndMat'
 elif g=='Lamp':key='Lamp'
 elif g in ['Screwdriver','Wrench','Pliers','OilCan']:key='RetainedTools'
 elif g.startswith('ammo_'):key='NewAmmo'
 elif g in ['Printer','AmmoPress','ComponentsTray','ToolOrganizer']:key='NewProps'
 else:key='SceneSetup'
 sets[key].append(o)
manifest={}
for k,obs in sets.items():
 p=F/(k+'.blend');bpy.data.libraries.write(str(p),set(obs),fake_user=True,compress=True);manifest[k]={'file':p.name,'objects':len(obs),'bytes':p.stat().st_size}
(F/'libraries.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
