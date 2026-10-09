"""Reception-only geometry revision. Retains stock furniture scale and placement."""
import bpy,bmesh,json,math,sys,hashlib,random
from pathlib import Path
from mathutils import Vector
TASK=Path(__file__).resolve().parent;PARENT=TASK.parent
# Re-evaluate the maintained hall recipe, then export only the three changed groups.
src=(PARENT/'author.py').read_text('utf8')
ctx={'__file__':str(PARENT/'author.py'),'__name__':'reception_source'}
exec(compile(src[:src.index('# Meshes are spatially split')],str(PARENT/'author.py'),'exec'),ctx)
g=ctx['g'];ROLES=ctx['ROLES'];materials=ctx['materials'];ROOT=TASK;OUT=TASK/'Authored';BASE='/Game/Dungeons/ReceptionHall20261006/Refine20261007'
g.G={k:v for k,v in g.G.items() if k[1] in ('Signs','Hardware','ReceptionCounter')}
g.C={k:v for k,v in g.C.items() if k[1] in ('Signs','Hardware','ReceptionCounter')}
from collections import defaultdict
g.C=defaultdict(list,g.C)
def role(key,col,rough=.6,metal=0,uv=1):
    ROLES[key]=dict(basecolor_linear=col,roughness=rough,metallic=metal,uv_meters=uv,existing_ue_path=BASE+'/Materials/M_RH2_'+key)
    m=bpy.data.materials.new('RH_'+key);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;materials[key]=m
role('Fabric',[.12,.17,.135],.83,uv=.25);role('Seam',[.065,.085,.073],.86,uv=.25)
role('Wood',[.14,.083,.046],.62,uv=1.2);role('Boards',[.7,.69,.59],.85)
role('Paper',[.72,.70,.61],.85);role('ABS',[.025,.033,.035],.48)
role('Blue',[.028,.055,.073],.72);role('Leather',[.05,.077,.07],.7)
def box(k,c,s,m='Teal',col=False):g.box(k,c,s,m,collision=col)
def rounded(k,c,s,mat,r=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.scale=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('Upholstery edge','BEVEL');mod.width=min(r,min(s)*.44);mod.segments=6;bpy.ops.object.modifier_apply(modifier=mod.name)
    vs=[o.matrix_world@v.co for v in o.data.vertices];g.poly(k,vs,[tuple(p.vertices) for p in o.data.polygons],mat,smooth=[len(p.vertices)==4 and p.area<.015 for p in o.data.polygons]);bpy.data.objects.remove(o,do_unlink=True)
def rounded_loop(cx,cy,z,w,d,r=.05):
    points=[]
    for x,y,start in [(cx+w/2-r,cy+d/2-r,0),(cx-w/2+r,cy+d/2-r,90),(cx-w/2+r,cy-d/2+r,180),(cx+w/2-r,cy-d/2+r,270)]:
        for i in range(10):a=math.radians(start+i*90/9);points.append((x+r*math.cos(a),y+r*math.sin(a),z))
    return points+[points[0]]
# Three-seat upholstered sofa: retain footprint, add seams, welt cords and separate cushion gaps.
rounded('Sofa',(0,0,.31),(2.5,.90,.46),'Fabric',.055)
for x in (-1.13,1.13):
    rounded('Sofa',(x,0,.57),(.21,.95,.61),'Fabric',.055)
    g.tube('Sofa',rounded_loop(x,0,.85,.15,.87,.055),.003,'Seam',8)
for x in (-.75,0,.75):
    rounded('Sofa',(x,-.035,.575),(.70,.66,.15),'Fabric',.045)
    rounded('Sofa',(x,.30,.85),(.72,.23,.67),'Fabric',.050)
    for z in (.536,.624):g.tube('Sofa',rounded_loop(x,-.035,z,.67,.63,.043),.0028,'Seam',8)
    # Vertical back cushion welt, recessed from the foremost upholstered surface.
    ps=rounded_loop(x,.85,0,.68,.62,.04);g.tube('Sofa',[(a,.194,b) for a,b,_ in ps],.0028,'Seam',8)
    for sign in (-1,1):g.tube('Sofa',[(x+sign*.24,.177,.76),(x+sign*.242,.175,.85),(x+sign*.238,.178,.98)],.0015,'Seam',8)
for x in (-.96,.96):
    for y in (-.27,.27):g.lathe('Sofa',(x,y,0),(0,0,1),[(0,.030),(.025,.034),(.10,.027),(.18,.027)],'Steel',24)
g.tube('Sofa',rounded_loop(0,0,.13,2.44,.84,.05),.0035,'Seam',8)
g.box(None,(0,0,.34),(2.5,.95,.68),collision='Sofa');g.box(None,(0,.33,.86),(2.5,.3,.68),collision='Sofa')
# Both outer sides of security checkpoint: full connected belt runs, posts and return leads.
for side in (-1,1):
    ys=[side*v for v in (3.72,6.18,8.64,11.10,13.56,16.20)]
    for y in ys:
        g.lathe('SecurityBarriers',(14,y,0),(0,0,1),[(0,.17),(.025,.17),(.05,.11),(.075,.027),(.91,.027),(.92,.055),(1.035,.055)],'Steel',32,True)
        g.ring('SecurityBarriers',(14,y,.975),(0,0,1),.056,.052,.075,'Teal',24)
    for a,b in zip(ys,ys[1:]):
        box('SecurityBelts',(14,(a+b)/2,.966),(.018,abs(b-a)-.09,.064),'Teal')
        g.box(None,(14,(a+b)/2,.515),(.055,abs(b-a)-.05,1.03),collision='SecurityBarriers')
        for y in (a+side*.058,b-side*.058):box('SecurityBarriers',(14,y,.966),(.027,.024,.078),'Steel')
    # Curved cloth sag is restrained; this is a retractable tensioned belt, not a rigid handrail.
    for x in (10.8,12.4):
        g.lathe('SecurityBarriers',(x,side*3.72,0),(0,0,1),[(0,.17),(.035,.17),(.07,.028),(1.0,.028),(1.035,.055)],'Steel',28,True)
    for a,b in ((10.8,12.4),(12.4,14)):
        box('SecurityBelts',((a+b)/2,side*3.72,.966),(b-a-.06,.018,.064),'Teal')
        g.box(None,((a+b)/2,side*3.72,.515),(b-a-.04,.055,1.03),collision='SecurityBarriers')
# Actual printed board faces have one front surface, true pixel ratio and backed mounting.
atlas=json.loads((TASK/'atlas.json').read_text('utf8'))
def board(key,c,w,normal):
    before=len(g.group('OfficeBoards')['m']);g.printed_plate('OfficeBoards',c,w,w*944/1984,key,normal,atlas,depth=.021)
    data=g.group('OfficeBoards');data['m'][before:]=['Boards' if m=='Labels' else m for m in data['m'][before:]]
    n,u,v=g.basis(normal)
    for a in (-1,1):
        for b in (-1,1):g.bolt('OfficeBoardMounts',Vector(c)+u*a*(w/2-.035)+v*b*(w*944/1984/2-.035),n,.004)
for side in (-1,1):
    board('roster' if side>0 else 'visitors',(23.80,side*8,6.85),2.70,(-1,0,0))
    board('handover' if side>0 else 'rules',(21.7,side*14.69,6.62),2.50,(0,-side,0))
    # Wall-side credenza: never intersects desks, pillars, cabinet or the central door approach.
    rounded('OfficeStorage',(23.36,side*8,4.96),(.66,2.28,.84),'Wood',.015)
    box('OfficeStorage',(23.36,side*8,5.40),(.70,2.34,.04),'Wood',True)
    box('OfficeStorage',(23.04,side*8,4.96),(.027,2.20,.69),'Dark')
    for y in (side*8-.56,side*8+.56):
        rounded('OfficeStorage',(23.016,y,4.96),(.035,1.08,.68),'Teal',.008)
        g.cylinder('OfficeStorage',(22.97,y-.08,5.12),(22.97,y+.08,5.12),.007,'Steel',20)
    for y in (side*8-.95,side*8+.95):
        for x in (23.14,23.58):box('OfficeStorage',(x,y,4.56),(.06,.06,.12),'Steel')
    g.box(None,(23.36,side*8,4.96),(.66,2.28,.84),collision='OfficeStorage')
    # Binder stack with leaf blocks, rounded spines, labels and finger rings.
    for i in range(9):
        y=side*8-.91+i*.068;z=5.57
        rounded('OfficeSupplies',(23.36,y,z),(.285,.062,.33),'Blue' if i%3 else 'Teal',.004)
        box('OfficeSupplies',(23.206,y,5.62),(.005,.043,.093),'Paper')
        g.ring('OfficeSupplies',(23.197,y,5.47),(-1,0,0),.009,.006,.004,'Steel',20)
        box('OfficeSupplies',(23.354,y+.026,5.569),(.256,.005,.29),'Paper')
    # Two-tier document trays, paper stack, closed document box.
    for z in (5.44,5.51):
        rounded('OfficeSupplies',(23.37,side*8+.52,z),(.31,.39,.018),'ABS',.009)
        for y in (side*8+.32,side*8+.72):box('OfficeSupplies',(23.38,y,z+.026),(.32,.014,.06),'ABS')
        for j in range(5):box('OfficeSupplies',(23.37,side*8+.52,z+.012+j*.0015),(.278,.348,.0012),'Paper')
    for y in (side*8+.335,side*8+.705):box('OfficeSupplies',(23.5,y,5.48),(.025,.025,.12),'Steel')
    rounded('OfficeSupplies',(23.4,side*8+.96,5.51),(.33,.30,.20),'Teal',.014)
    box('OfficeSupplies',(23.225,side*8+.96,5.53),(.007,.20,.065),'Paper')
    # Side desk details fit spare tabletop corners, avoiding monitor/keyboard footprints.
    for y in (side*4.4,side*11.8):
        g.lathe('DeskSupplies',(23.38,y-.89,5.282),(0,0,1),[(0,.039),(.007,.042),(.095,.043),(.102,.043),(.102,.037),(.013,.034)],'ABS',32)
        for i in range(5):
            x=23.38+(i%2-.5)*.02;yy=y-.91+(i//2)*.015
            g.cylinder('DeskSupplies',(x,yy,5.30),(x+.008,yy+.006,5.45+i*.004),.003,'Teal' if i%2 else 'Brass',12)
        rounded('DeskSupplies',(23.05,y+.91,5.288),(.23,.15,.02),'Blue',.004)
        box('DeskSupplies',(23.044,y+.908,5.301),(.205,.127,.004),'Paper')
        g.cylinder('DeskSupplies',(22.95,y+.97,5.308),(23.13,y+.95,5.308),.003,'ABS',12)
    # Wall coat pegs adjacent to the entrance, not behind open door leaves.
    box('OfficeCoatHooks',(20.35,side*1.292,6.23),(1.0,.032,.14),'Wood')
    for x in (20.0,20.23,20.46,20.69):g.rounded_pipe('OfficeCoatHooks',[(x,side*1.31,6.24),(x,side*1.40,6.22),(x,side*1.44,6.29)],.008,'Steel',16)
# Small tabletop trays and magazines on existing lounge coffee tables.
for side in (-1,1):
    for x in (-20.7,-16.9):
        y=side*13.55
        rounded('LoungeDetails',(x-.37,y,.472),(.32,.22,.030),'Teal',.010)
        for i in range(4):box('LoungeDetails',(x-.37+i*.002,y,.491+i*.002),(.27,.19,.0016),'Paper')
        g.lathe('LoungeDetails',(x+.05,y+.1,.455),(0,0,1),[(0,.033),(.065,.035),(.072,.035),(.072,.031),(.010,.028)],'White',32)
        g.torus('LoungeDetails',(x+.094,y+.10,.494),(0,1,0),.025,.006,'White',28,8)
# Reuse source export policy and actual UCX, with new owned paths only.
records=[]
exec(compile(src[src.index('def export(obj,kind'):src.index('for (room,kind),data')],'reception_export','exec'))
for (room,kind),data in g.G.items():
    name='SM_RH2_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update();obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    order=list(dict.fromkeys(data['m']))
    for r in order:mesh.materials.append(materials[r])
    mesh.uv_layers.new(name='UVMap');color=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER');uv=mesh.uv_layers['UVMap']
    for face,r,coords,sm in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
        face.material_index=order.index(r);face.use_smooth=sm;axes=[a for a in range(3) if a!=max(range(3),key=lambda k:abs(face.normal[k]))];scale=ROLES[r].get('uv_meters',1)
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=coords[j] if coords else (p[axes[0]]/scale,p[axes[1]]/scale);color.data[li].color=(.03,0,0,1)
    export(obj,kind,g.C.get((room,kind),[]),{'RH_'+r:ROLES[r]['existing_ue_path'] for r in order},nanite=kind not in ('Signs','OfficeBoards'))
for o in bpy.context.scene.objects:o.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ReceptionRefine.blend'))
(TASK/'geometry.json').write_text(json.dumps(dict(meshes=records,roles=ROLES),indent=2),encoding='utf8')
print('RECEPTION_REFINED_GEOMETRY_SAVED',len(records),flush=True)
