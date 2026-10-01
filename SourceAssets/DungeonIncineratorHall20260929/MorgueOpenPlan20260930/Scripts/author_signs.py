"""Relocate only signs and numbers; retain the previously authored equipment meshes."""
import json,sys
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
sys.path.insert(0,str(HALL/'SceneFix20260930/Scripts'))
import author_fixes as fx
eq=fx.equipment;g=fx.g
C=json.loads((ROOT/'Config/layout.json').read_text(encoding='utf-8'));atlas=json.loads((ROOT/'Authored/sign_atlas.json').read_text(encoding='utf-8'))
def tex(surface,u,v):
    x0,y0,x1,y1=atlas['rects'].get(surface,atlas['rects']['steel']);return ((x0+u*(x1-x0))/2048,1-(y0+v*(y1-y0))/2048)
def signs():
    eq.part('01_Open_hall_directions_and_retained_rooms')
    for key,p,w,h,n in [
        ('stairs',(-9.2125,-2.43,.79),.94,.305,(0,1,0)),
        ('wash',(-1.5,5.091,-.78),1.1,.355,(0,-1,0)),
        ('service',(5.4,5.091,-.78),1.1,.355,(0,-1,0)),
        ('cold',(13.851,-2.6,-.68),1.45,.468,(-1,0,0)),
        ('transfer',(-13.851,4.0,-.73),1.2,.387,(1,0,0)),
        ('ash',(12.1,-7.12,1.30),1.,.323,(0,1,0))]:fx.solid_nameplate(p,w,h,key,n,.007)
    for x in (-9.57,-8.86):
        g.box((x,-2.5,.63),(.03,.05,.36),'steel',.002);g.box((x,-2.467,.79),(.03,.025,.03),'steel',.001)
    for x in (11.72,12.48):
        g.box((x,-7.155,.72),(.04,.04,1.44),'steel',.002);g.box((x,-7.155,.013),(.14,.14,.026),'steel',.002)
    # Small upright desk sign replaces the former foyer lintel signs.
    fx.solid_nameplate((-10,1.45,-2.58),.50,.162,'foyer',(0,-1,0),.005)
    for x in (-10.19,-9.81):g.box((x,1.49,-2.72),(.018,.06,.16),'steel',.001)
    eq.part('02_Relocated_cold_storage_numbers')
    for spec in C['freezer_modules']:
        origin=Vector(spec['origin']);rotation=Matrix.Rotation(1.5707963267948966,3,'Z')
        for row in range(3):
            if spec['key']=='ColdBankOpen' and row==1:continue
            local=Vector((-.08,.168,.17+row*.72+.465))
            fx.solid_nameplate(origin+rotation@local,.19,.13,'slot%02d'%(spec['first_slot']+row),(-1,0,0),.002)
    fx.solid_nameplate((11.10,-1.46,-2.58),.12,.17,'slot08',(-1,0,0),.002)
    eq.part('03_Retained_ash_receiver_identification')
    o=Vector(C['ash_station']['origin']);fx.solid_nameplate(o+Vector((0,.427,1.57)),.59,.162,'machine',(0,1,0),.003)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
fx.ROOT=ROOT;fx.BASE=C['ue_base']
previous_manifest=json.loads((HALL/'MorgueB120260930/Authored/manifest.json').read_text(encoding='utf-8'))
rail_runs=previous_manifest['rail_runs']+[
    {'a':[-12.91,-7.57,-1.8],'b':[-8.75,-7.57,-1.8],'height':.95},
    {'a':[-12.91,-7.57,-1.8],'b':[-12.91,-5.95,-1.8],'height':.95},
    {'a':[-8.75,-7.57,-1.8],'b':[-8.75,-5.95,-1.8],'height':.95}]
fx.rails_layout=lambda:rail_runs
rail_record=fx.export('Railings',fx.author_rails,[fx.rail_prism(s['a'],s['b'],-.025,s['height']+.04,.08) for s in rail_runs],eq.material(),'_OpenB1V2')
mat=bpy.data.materials.new('MorgueSignsV2');mat.use_nodes=True
image=bpy.data.images.load(str(ROOT/'Authored/Textures/T_MorgueSigns_BaseColor.png'));image.pack();node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
g.tex=tex;g.MATERIAL=C['ue_base']+'/Materials/M_MorgueSigns';fx.ROOT=ROOT;fx.BASE=C['ue_base']
record=fx.export('MorgueSigns',signs,[],mat,'_OpenB1V2');record['collision_policy']='none'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/Morgue_OpenPlan_SignsV2.blend'))
previous=previous_manifest['objects']
reuse=[dict(item,reuse_saved_asset=True) for item in previous if item['key'] not in ('MorgueSigns','Railings')]
(ROOT/'Authored/manifest.json').write_text(json.dumps({'objects':reuse+[rail_record,record],'rail_runs':rail_runs,'tests_run':False,'rendered':False},indent=2),encoding='utf-8')
print('MORGUE_OPEN_PLAN_SIGNS_AUTHORED',flush=True)
