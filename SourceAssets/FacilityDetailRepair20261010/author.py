"""Export the five requested scene corrections without changing approved lighting."""
from pathlib import Path
import bpy,bmesh,sys,json,math,hashlib,runpy
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];PARENT=PROJECT/'SourceAssets/DungeonFacilityTransit20261007'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True);BASE='/Game/Dungeons/FacilityDetailRepair20261010'
sys.path.insert(0,str(ROOT));from detail_geometry import build
from fbx_tangent_finish import install as finish_fbx_tangents
finish_fbx_tangents()
src=(PARENT/'author.py').read_text('utf-8-sig');src=src[:src.index('records=[]')]
# Make an actual rebate in both wall constructions for the 4 cm steel return.
src=src.replace('for lo,hi in [(-18,-1.5),(1.5,18)]','for lo,hi in [(-18,-1.54),(1.54,18)]')
src=src.replace("B('Walls',(-24.16,0,5.7),(.32,3,5.4)","B('Walls',(-24.16,0,5.72),(.32,3.08,5.36)")
src=src.replace("B('Approach',(-28,sy*1.64,1.5),(8,.28,3)","B('Approach',(-28.18,sy*1.64,1.5),(7.64,.28,3)")
src=src.replace("B('ApproachTrim',(-28,sy*1.485,.96),(8,.035,.085)","B('ApproachTrim',(-28.19,sy*1.485,.96),(7.62,.035,.085)")
src=src.replace("B('Approach',(-28,0,3.14),(8,3.56,.28)","B('Approach',(-28.18,0,3.14),(7.64,3.56,.28)")
src=src.replace("sign('service',(-1,-17.974,2.7),3.3)","sign('service',(-3.9,-17.974,3.16),3.3)")
src=src.replace("sign('balcony',(-4.6,side*17.97,2.1),2.6", "sign('balcony',(-10.4,side*17.97,2.35),2.6")
ctx={'__file__':str(PARENT/'author.py'),'__name__':'detail_hall_source'};exec(compile(src,'detail_hall_source','exec'),ctx)
g=ctx['g'];g.ROOM='Hall'
for s in (-1,1):g.box('Approach',(-24.18,s*1.66,1.5),(.36,.24,3),'Concrete',collision=True)
g.box('Approach',(-24.18,0,3.16),(.36,3.56,.24),'Concrete',collision=True)
hall_kinds={'Walls','Approach','ApproachTrim','Signs'}
hall_g={k:v for k,v in g.G.items() if k[0]=='Hall' and k[1] in hall_kinds}
hall_c={k:v for k,v in g.C.items() if k in hall_g}
g.G.clear();g.C.clear()
roles=json.loads((PARENT/'RefineV2/materials.json').read_text('utf8'))
# Retain each theme's small asset-identification plate, not the overlapping old mail label.
ref=(PARENT/'RefineV2/author.py').read_text('utf-8-sig')
defs=ref[ref.index('def tech('):ref.index('for theme in CFG')]
dc={'g':g,'TECH':json.loads((PARENT/'RefineV2/atlas.json').read_text('utf8'))}
exec(compile(defs[:defs.index('def dial(')],'equipment_label_helper','exec'),dc)
for room in ('staff_living','power'):
    g.ROOM=room;dc['tech']('serial',(-2.72,-.142,.38),.55)
g.G.update(hall_g);g.C.update(hall_c)
g.ROOM='Hall'
for s in (-1,1):
    g.box('ArrivalFrame',(-23.94,s*1.58,1.5),(.12,.16,3),'Teal')
    g.box('ArrivalFrame',(-24.15,s*1.52,1.5),(.42,.04,3),'Brushed')
    for z in (.22,1.50,2.78):g.bolt('ArrivalFrame',(-23.874,s*1.60,z),(1,0,0),.009)
g.box('ArrivalFrame',(-23.94,0,3.08),(.12,3.32,.16),'Teal')
g.box('ArrivalFrame',(-24.15,0,3.02),(.42,3,.04),'Brushed')
g.box('ArrivalFrame',(-24.02,0,.006),(.54,2.98,.012),'Brushed')
atlas=json.loads((ROOT/'atlas.json').read_text('utf8'));build(g,roles,atlas)
roles['DetailPrint']=dict(existing_ue_path=BASE+'/Materials/M_FacilityDetail_Plates',uv_meters=1,basecolor_linear=[.6,.65,.55])
roles['Glow']['existing_ue_path']='/Game/Dungeons/HallLighting20261007/Materials/M_SteadyDiffuser'
OLD='/Game/Dungeons/FacilityTransit20261007'
removed={
 'Hall':['PanelIndicators'],
 'staff_living':['SconceArms','SconceCaps','CaseRims','HingeMounts','HingePins','QuarterTurns','QuarterTurnSlots','MailSlotRecess','MailSlotBrow','MailLock','KeyHooks','KeyRings','KeyTags'],
 'power':['CaseRims','HingeMounts','HingePins','QuarterTurns','QuarterTurnSlots','InstrumentFaces','HandleHub','MouldedGrip','GripInset','BushingFoot','CableGlands','GlandBoot','TerminalClamp','TerminalBolts']}
def oldpath(room,kind):
    return OLD+('/Meshes/SM_FT_Hall_' if room=='Hall' else '/RefineV2/Meshes/SM_FT2_'+room+'_')+kind
records=[]
for (room,kind),data in g.G.items():
    g.ROOM=room
    name='SM_FDR_'+room+'_'+kind;me=bpy.data.meshes.new(name);me.from_pydata(data['v'],[],data['f']);me.update()
    order=list(dict.fromkeys(data['m']))
    for role in order:
        key='FDR_'+role;m=bpy.data.materials.get(key)
        if not m:m=bpy.data.materials.new(key);m.diffuse_color=(*roles[role].get('basecolor_linear',[.2,.2,.2]),1)
        me.materials.append(m)
    uv=me.uv_layers.new(name='UVMap');age=me.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for f,role,coords,smooth in zip(me.polygons,data['m'],data['uv'],data['smooth']):
        f.material_index=order.index(role);f.use_smooth=smooth
        axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(f.normal[a]))];s=roles[role].get('uv_meters_override',roles[role].get('uv_meters',1))
        for j,li in enumerate(f.loop_indices):
            p=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=coords[j] if coords and role in ('Labels','TechLabels','DetailPrint') else (coords[j][0]/s,coords[j][1]/s) if coords else (p[axes[0]]/s,p[axes[1]]/s)
            age.data[li].color=(.020,0,0,1)
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    # Short equipment parts receive physical edge radii. Long architectural strips
    # and printed/curved lamps use their authored interfaces, without tiny bevel slivers.
    if kind in ('MailSlots','IsolatorCabinet','HandleBezel','MaintenancePanel','ServiceBench'):
        mod=ob.modifiers.new('Manufactured radii','BEVEL');mod.width=.002;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(40)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY');bm.to_mesh(ob.data);bm.free()
    # Bevel interpolation around small hardware can collapse UV triangles: project
    # equipment faces after final topology, while retaining authored print islands.
    if kind in ('MailSlots','IsolatorCabinet','HandleBezel','MaintenancePanel','ServiceBench'):
        uv=ob.data.uv_layers.active
        for f in ob.data.polygons:
            role=order[f.material_index];s=roles[role].get('uv_meters',1)
            axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(f.normal[a]))]
            for li in f.loop_indices:
                p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/s,p[axes[1]]/s)
        from uv_finish import finish
        finish(ob.data)
    hulls=g.C.get((room,kind),[]);cols=[]
    # Mail/cabinet decorative replacements preserve their old coarse block footprint.
    if kind=='MailSlots':
        for x in (-3.32,-2.72,-2.12):g.box(None,(x,-.325,.91),(.51,.24,.43),collision=kind)
        hulls=g.C[(room,kind)]
    if kind=='IsolatorCabinet':
        g.box(None,(-2.73,-.39,1.79),(1.56,.40,1.72),collision=kind);hulls=g.C[(room,kind)]
    for i,(vs,fs) in enumerate(hulls):
        cm=bpy.data.meshes.new('UCX_'+name+'_%03d'%i);cm.from_pydata(vs,[],fs);cm.update()
        bm=bmesh.new();bm.from_mesh(cm);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cm);bm.free()
        co=bpy.data.objects.new(cm.name,cm);bpy.context.collection.objects.link(co);co.select_set(True);cols.append(co)
    fbx=OUT/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR',add_leaf_bones=False,path_mode='STRIP')
    for co in cols:co.hide_set(True);co.hide_render=True
    old='/Game/Dungeons/TransitFinish20261010/Meshes/SM_TransitFinish_ArrivalFrameV2' if kind=='ArrivalFrame' else None if kind=='DetailPlates' else oldpath(room,kind)
    records.append(dict(room=room,kind=kind,mesh=BASE+'/Meshes/'+name,old=old,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),
        materials={'FDR_'+r:roles[r]['existing_ue_path'] for r in order},triangles=len(ob.data.polygons),collision=bool(hulls),collision_hulls=len(hulls),cast_shadow=kind not in ('DetailPlates','SconceShade','EquipmentLabels','Signs'),nanite=kind not in ('DetailPlates','SconceShade','EquipmentLabels','Signs','KeyRail'),authored_tangents=kind in ('IsolatorCabinet','MaintenancePanel','ServiceBench')))
    print('DETAIL_EXPORTED',room,kind,len(ob.data.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FacilityDetailRepair.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records,remove=[oldpath(r,k) for r,ks in removed.items() for k in ks],rendered=False),indent=2),encoding='utf8')
