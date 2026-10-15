"""Prepare a scoped refinement of the stabilizer and two crystal packages."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;PROJECT=BASE.parents[1]
for name in ('Scripts','Authored','Export','Textures','Icons','Receipts','Before','UEImportHost/Config'):(ROOT/name).mkdir(parents=True,exist_ok=True)
def source(name):return (BASE/'Scripts'/name).read_text('utf8').replace("PROJECT=ROOT.parents[1]","PROJECT=ROOT.parents[2]")
shutil.copy2(BASE/'Scripts/geometry.py',ROOT/'Scripts/geometry.py')
texture=source('prepare_textures.py')
texture=texture.replace('SURFACES={',"ASSETS={k:v for k,v in ASSETS.items() if k in ('Stabilizer','Catalyst','BlueFungus')}\nSURFACES={")
texture=texture.replace("'crystal':((.34,.17,.48),.18,.12),'bluecrystal':((.08,.28,.44),.22,.08)","'crystal':((.32,.075,.49),.16,0),'bluecrystal':((.025,.20,.39),.17,0)")
start=texture.index('for (key,spec),accent in zip(ASSETS.items(),accents):')
end=texture.index('textures={}',start)
texture=texture[:start]+'''accents={'Stabilizer':(36,94,100),'Catalyst':(83,42,111),'BlueFungus':(32,83,124)}
for key,spec in ASSETS.items():
 x,y,x1,_=REGIONS[key];w=x1-x;h=360;REGIONS[key]=[x,y,x1,y+h]
 im=Image.new('RGB',(w,h),(226,231,219));d=ImageDraw.Draw(im);accent=accents[key]
 d.rectangle((12,12,w-12,h-12),outline=accent,width=6)
 d.rectangle((24,24,205,h-24),fill=accent);text(d,(114,h/2),'CS',99,(245,246,234),'mm')
 text(d,(255,45),spec['code'],115)
 text(d,(255,205),spec['name'],77)
 text(d,(w-50,110),'SEALED',40,accent,'rm');text(d,(w-50,195),'REAGENT',40,accent,'rm')
 text(d,(w-50,279),'26-1015',37,accent,'rm')
 base.paste(im,(x,y));orm.paste(Image.new('RGB',(w,h),(255,155,0)),(x,y))
''' +texture[end:]
(ROOT/'Scripts/prepare_textures.py').write_text(texture,'utf8')
author=source('author_models.py')
author=author.replace("'GlassClear':([.91,.965,.98],.10,[.94,.98,.99])","'GlassClear':([.99,.995,.998],.025,[.995,.998,1.0])")
author=author.replace("default_value=.96 if name.startswith('Glass') else .82","default_value=1.0 if name.startswith('Glass') else .92")
author=author.replace("return H.bevel(o,.018,2)","H.bevel(o,.012,2)\n for face in o.data.polygons:face.use_smooth=False\n return o")
author=author.replace("H.panel('specimen top printed label',(0,0,6.345),3.8,3.8,'BlueFungus')","H.panel('specimen top printed label',(0,0,6.345),4.3,1.25,'BlueFungus')")
author=author.replace("label('BlueFungus',3.27,3.0,2.3,1.04)","label('BlueFungus',3.27,1.05,.85,1.04)")
author=author.replace("BUILDERS={'BaseFluid':basefluid,'Stabilizer':stabilizer,'Catalyst':catalyst,'RedRoot':redroot,'BlueFungus':bluefungus,'Silverleaf':silverleaf}","BUILDERS={'Stabilizer':stabilizer,'Catalyst':catalyst,'BlueFungus':bluefungus}")
(ROOT/'Scripts/author_models.py').write_text(author,'utf8')
render=source('render_icons.py')
render=render.replace("ICONS=PROJECT/'Content/ColdSteelData/Icons/AlchemyMaterials20261015'","ICONS=ROOT/'Icons'")
render=render.replace("'ue_icon':str(path.relative_to(PROJECT/'Content/ColdSteelData')).replace('\\\\','/')","'ue_icon':'Icons/AlchemyMaterials20261015/'+path.name")
# Render candidates separately; the installer publishes their registered paths.
for identity in ('alchemy_compound_stabilizer','alchemy_active_catalyst','alchemy_bluemarrow_crystals'):
 p=PROJECT/'Content/ColdSteelData/Icons/AlchemyMaterials20261015'/(identity+'.png')
 if not (ROOT/'Before'/p.name).exists():shutil.copy2(p,ROOT/'Before'/p.name)
render=render.replace("direction=(5,-13,11) if key=='Stabilizer' else VIEWS[key][0][0]","direction=(5,-13,11) if key=='Stabilizer' else (3,-14,6)")
render=render.replace("default_value=.42","default_value=.28")
render=render.replace("700,4)","450,2.2)").replace("450,3.5)","180,2)").replace("900,3)","650,2)")
(ROOT/'Scripts/render_icons.py').write_text(render,'utf8')
imp=source('import_assets.py')
imp=imp.replace("DEST='/Game/Items/AlchemyMaterials20261015/V3'","DEST='/Game/Items/AlchemyMaterials20261015/V4'")
imp=imp.replace("if not STAGED:raise RuntimeError('This importer requires the isolated content-only host')","if not STAGED and HOST!=PROJECT.resolve():raise RuntimeError('Wrong project')\nif not STAGED:\n level=u.get_editor_subsystem(u.LevelEditorSubsystem)\n if level and level.is_in_play_in_editor():raise RuntimeError('Preserve active PIE before replacing loaded meshes')\n for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():\n  if package.get_name().startswith('/Game/Items/AlchemyMaterials20261015/'):\n   raise RuntimeError('Preserve unsaved task asset '+package.get_name())")
imp=imp.replace('  return obj\n t=u.AssetImportTask()', '  if not options:return obj\n t=u.AssetImportTask()')
imp=imp.replace('t.automated=True;t.save=False','t.automated=True;t.save=False;t.replace_existing=options is not None;t.replace_existing_settings=options is not None')
imp=imp.replace("mesh=imp(spec['fbx'],spec['mesh'],DEST+'/Meshes',options)","mesh=imp(spec['fbx'],spec['mesh'],'/Game/Items/AlchemyMaterials20261015/V3/Meshes',options)")
imp=imp.replace("report['stage']='staged_assets_saved'","report['stage']='staged_assets_saved' if STAGED else 'assets_saved'")
imp=imp.replace("if not STAGED:\n level=", "if not STAGED and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():\n level=")
(ROOT/'Scripts/import_assets.py').write_text(imp,'utf8')
host=json.loads((BASE/'UEImportHost/AlchemyMaterialsImport.uproject').read_text('utf8'))
(ROOT/'UEImportHost/AlchemyMaterialsImport.uproject').write_text(json.dumps(host,indent=2),'utf8')
shutil.copy2(BASE/'UEImportHost/Config/DefaultEngine.ini',ROOT/'UEImportHost/Config/DefaultEngine.ini')
print('VISUAL_REFINEMENT_PREPARED')
