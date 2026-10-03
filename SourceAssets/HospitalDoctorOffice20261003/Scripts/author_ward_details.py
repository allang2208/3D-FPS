"""Rebuild only bedside service panels, attached wall handrails and room signs."""
from pathlib import Path
import json, os

TASK=Path(__file__).resolve().parents[1]
PROJECT=TASK.parents[1]
SOURCE=PROJECT/'SourceAssets/DungeonIsolationWard20260929'
entry=SOURCE/'Scripts/author_ward.py'
code=entry.read_text('utf8')
code=code.replace("ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'",
    "ROOT=Path("+repr(str(SOURCE))+");PROJECT=ROOT.parents[1];OUT=Path("+repr(str(TASK/'Authored'))+")")
code=code.replace("G={};GLASS_COLLISION=[]", """
for key,path in {'PanelWhite':'/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_White',
                 'PanelRed':'/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_Red',
                 'PanelBlue':'/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_Blue'}.items():
 MAPPING[key]=path;MATS[key]=bpy.data.materials.new('RS_'+key)
G={};GLASS_COLLISION=[]""")
old="""   fill(lo+.02,hi-.02,.88,.99,'WallRails','PaintedSteel',.042,side*.20)
   fill(lo+.02,hi-.02,.92,.96,'WallRails','Rubber',.012,side*.229)"""
new="""   start,end=lo+.08,hi-.08
   if end-start<.15:continue
   def rail_point(t,off,z=.90):
    p=a+d*t+n*side*off;return (p.x,p.y,z)
   # Round grip with returned ends; each bracket reaches the finished wall.
   detail.tube('WallRails',[rail_point(start,.15),rail_point(start,.205),
       rail_point(start+.035,.225),rail_point(end-.035,.225),
       rail_point(end,.205),rail_point(end,.15)],.022,'PaintedSteel',24)
   detail.tube('WallRails',[rail_point(start+.07,.225),rail_point(end-.07,.225)],.023,'Rubber',24)
   count=max(2,math.ceil((end-start)/1.2)+1)
   for j in range(count):
    t=start+.065+(end-start-.13)*j/(count-1)
    p=a+d*t+n*side*.147
    box('WallRails',(p.x,p.y,.84),(.067,.013,.085),'PaintedSteel',angle)
    detail.tube('WallRails',[rail_point(t,.151,.84),rail_point(t,.207,.84),rail_point(t,.225,.878)],.010,'BareSteel',16)
    for z in (.811,.869):detail.fastener(rail_point(t,.155,z),(n.x*side,n.y*side,0),.004,'WallRails')"""
if old not in code:raise RuntimeError('Preserve changed wall rail source')
code=code.replace(old,new)
old="""  back=y1-.25 if y0>0 else y0+.25
  box('HeadwallServices',(cx,back,1.24),(3.1,.13,.22),'PaintedSteel')
  box('HeadwallServices',(cx,back+( -.075 if y0>0 else .075),1.24),(3.0,.012,.07),'BareSteel')
  for x in (cx-.85,cx+.85):box('HeadwallServices',(x,back,1.47),(.16,.14,.14),'Rubber')"""
new="""  side=-1 if y0>0 else 1
  back=y1-.18 if y0>0 else y0+.18
  box('HeadwallServices',(cx,back,1.28),(3.10,.085,.19),'PaintedSteel')
  front=back+side*.048
  box('HeadwallServices',(cx,front,1.28),(3.01,.012,.146),'PanelWhite')
  for x in (cx-1.45,cx+1.45):
   box('HeadwallServices',(x,front+side*.009,1.28),(.044,.022,.157),'PaintedSteel')
  for x in (cx-.95,cx-.72):
   box('HeadwallServices',(x,front+side*.013,1.28),(.13,.021,.115),'PanelWhite')
   for dx,dz in ((-.025,.018),(.025,.018),(0,-.024)):
    box('HeadwallServices',(x+dx,front+side*.025,1.28+dz),(.012,.003,.019),'Rubber')
  for x,mat in ((cx+.35,'PanelBlue'),(cx+.65,'PanelRed')):
   detail.ring((x,front+side*.018,1.28),(0,side,0),.028,.013,.021,'BareSteel',32,'HeadwallServices')
   detail.ring((x,front+side*.033,1.28),(0,side,0),.022,.013,.006,mat,32,'HeadwallServices')
   detail.tube('HeadwallServices',[(x,front+side*.030,1.28),(x,front+side*.033,1.28)],.011,'Rubber',20)
  box('HeadwallServices',(cx+1.05,front+side*.015,1.28),(.105,.023,.112),'PaintedSteel')
  box('HeadwallServices',(cx+1.05,front+side*.029,1.29),(.045,.006,.045),'PanelRed')
  for x in (cx-1.36,cx+1.36):detail.fastener((x,front+side*.020,1.28),(0,side,0),.004,'HeadwallServices')"""
if old not in code:raise RuntimeError('Preserve changed headwall source')
code=code.replace(old,new).replace("sign('DECON',[23.5,-4.29,3.36],1,.21)",
    "sign('DOCTOR OFFICE',[23.5,-4.29,3.36],1,.16)")
code=code.replace("json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))['objects']",
    "json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))['objects']")
os.environ['WARD_EXPORT_KINDS']='WallRails,HeadwallServices,Wayfinding'
exec(compile(code,str(entry),'exec'))
wanted={'WallRails','HeadwallServices','Wayfinding'}
manifest=json.loads((OUT/'manifest.json').read_text('utf8'))
manifest['objects']=[x for x in manifest['objects'] if x['kind'] in wanted]
for item in manifest['objects']:
 item['asset']='/Game/Dungeons/HospitalDoctorOffice20261003/Meshes/'+item['name']
 item['replaces']='/Game/Dungeons/IsolationWard20260929/Meshes/'+item['name']
manifest.update(revision=1,source='Original ward architecture, scoped panel and handrail rebuild')
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')

