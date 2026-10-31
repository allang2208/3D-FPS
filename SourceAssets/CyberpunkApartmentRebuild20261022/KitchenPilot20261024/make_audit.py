"""Build read-only semantic audit parts from the current V2 kitchen source.
No production FBX selection includes these objects.
"""
from pathlib import Path
import bpy,json,math
from mathutils import Vector
R=Path(__file__).resolve().parent
# Remove only previous local audit objects, never production/source components.
for o in list(bpy.data.objects):
    if o.name.startswith('AUD_'):bpy.data.objects.remove(o,do_unlink=True)
records=[]
def bounds(o):
    pts=[o.matrix_world@v.co for v in o.data.vertices]
    return [[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]]
def audit(name,label,source,kind='prop'):
    unique='AUD_'+name
    if unique in bpy.data.objects:
        serial=source.get('AuditSource',source.name).rsplit('_',1)[-1]
        if serial.isdigit():unique+='.'+str(int(serial)+1).zfill(3)
    o=bpy.data.objects.new(unique,source.data.copy());bpy.context.scene.collection.objects.link(o)
    o.matrix_world=source.matrix_world.copy();o['AuditOnly']=True;o['SemanticLabel']=label
    source_id=source.get('AuditSource',source.name)
    o['SourceComponent']=source_id
    records.append(dict(id=o.name,label=label,source=source_id,kind=kind,bounds_m=bounds(o)))
    return o
for name in ['Dishes','Prep','DiningDressing','Sink','FridgeLowerDoor','FridgeUpperDoor']:
    source=bpy.data.objects['KIT_'+name]
    vs=[v.co.copy() for v in source.data.vertices]
    specs=[]
    for entry in source.get('AuditPrimitives','').split(';'):
        if not entry:continue
        start,count,primitive,serial,*label=entry.split(':')
        specs.append((int(serial),int(start),int(count),label[0] if label else primitive))
    if not specs or any(not row[3] for row in specs):raise RuntimeError('Missing original primitive provenance '+source.name)
    for serial,start,count,primitive in sorted(specs):
        polys=list(source.data.polygons[start:start+count])
        used=sorted({vi for p in polys for vi in p.vertices});remap={a:b for b,a in enumerate(used)}
        me=bpy.data.meshes.new(source.name+'_audit')
        world_matrix=source.matrix_world.copy()
        world_matrix.translation=(8.075,8.69,.7825) if name=='DiningDressing' else source.location
        me.from_pydata([world_matrix@vs[j] for j in used],[],[[remap[j] for j in p.vertices] for p in polys]);me.update()
        shell=bpy.data.objects.new('_TMP_shell',me);bpy.context.scene.collection.objects.link(shell);shell['AuditSource']=source.name
        for old in source.data.materials:me.materials.append(old)
        for p,old in zip(me.polygons,polys):p.material_index=old.material_index;p.use_smooth=old.use_smooth
        o=audit(name+'_%03d'%serial,name,shell,primitive)
        o['Primitive']=primitive;o['SupportBottom_m']=bounds(o)[0][2]
        bpy.data.objects.remove(shell,do_unlink=True)
# Split the unchanged refrigerator shell by existing material, not by approximate
# bounding volumes. Native RS_PoolIvory/RS_FreshPlastic are interiors/bins.
for part in ['Lower','Upper']:
    for kind in ['Door','Body']:
        src=bpy.data.objects['KIT_SM_Staff_Fridge'+part+kind+'_V5']
        slots={}
        for p in src.data.polygons:slots.setdefault(p.material_index,[]).append(p)
        for idx,polys in slots.items():
            mat=src.data.materials[idx]
            name=mat.name if mat else 'Unknown'
            me=bpy.data.meshes.new('FridgeAudit');me.from_pydata([v.co for v in src.data.vertices],[],[tuple(p.vertices) for p in polys]);me.update()
            for m in src.data.materials:me.materials.append(m)
            shell=bpy.data.objects.new('_TMP_fridge',me);bpy.context.scene.collection.objects.link(shell);shell.location=src.location
            o=audit('Fridge'+part+kind+'_'+name,'fridge_'+name,shell,'fridge_'+('door_panel' if ('Ceramic' in name and kind=='Door') else 'interior' if any(x in name for x in ['FreshPlastic','PoolIvory']) else 'handle' if 'Steel' in name and kind=='Door' else 'shell'))
            for v in o.data.vertices:v.co.y=-v.co.y
            for p in o.data.polygons:p.flip()
            o.data.update()
            bpy.data.objects.remove(shell,do_unlink=True)
# Basin supports use the actual four countertop solids below; no synthetic
# duplicate counter plane or ring is introduced into clearance checks.

# Actual formal table support, local audit-only duplicate. Source desk mesh is
# already in UE axes, so only its Y sign is reversed for this Blender scene.
current=json.loads((R/'current-interfaces-v2.json').read_text(encoding='utf8'))
support=current['targets']['AP_Kitchen_Dining']['components'][0]
# Do not invent a missing source table. Use the actual saved UE mesh's exact
# support rectangle/top level; this is a local clearance reference, not a prop.
b=support['bounds'];table_top=b[1][2]/100
center=(support['world']['location'][0]-445)/100
source_y=-(support['world']['location'][1]+673)/100
vs=[(center+b[i][0]/100,source_y-b[j][1]/100,z) for z in [table_top-.020,table_top] for i,j in [(0,0),(1,0),(1,1),(0,1)]]
me=bpy.data.meshes.new('MeasuredTableSupport');me.from_pydata(vs,[],[(0,1,2,3),(7,6,5,4),(4,5,1,0),(5,6,2,1),(6,7,3,2),(7,4,0,3)]);me.update()
table=bpy.data.objects.new('_TMP_table',me);bpy.context.scene.collection.objects.link(table)
audit('FormalDining','table',table,'support')
bpy.data.objects.remove(table,do_unlink=True)
(R/'formal-table-support.json').write_text(json.dumps(support,indent=2),encoding='utf8')
# Counter's actual closed structural worktop with a rounded sink aperture.
for i in range(1):
    source=bpy.data.objects['KIT_Counter'];entries=source.get('AuditPrimitives','').split(';')
    start,count,*_=entries[i].split(':');start,count=int(start),int(count);polys=list(source.data.polygons[start:start+count])
    used=sorted({vi for p in polys for vi in p.vertices});remap={a:b for b,a in enumerate(used)}
    me=bpy.data.meshes.new('CounterSupport');me.from_pydata([source.matrix_world@source.data.vertices[j].co for j in used],[],[[remap[j] for j in p.vertices] for p in polys]);me.update()
    tmp=bpy.data.objects.new('_TMP_counter',me);bpy.context.scene.collection.objects.link(tmp)
    audit('CounterSupport'+str(i),'counter_support',tmp,'support');bpy.data.objects.remove(tmp,do_unlink=True)
(R/'audit-parts.json').write_text(json.dumps(records,indent=2),encoding='utf8')
parts=[dict(id=o.name,objects=[o.name]) for o in bpy.data.objects if o.get('AuditOnly')]
(R/'local-assembly-v2.json').write_text(json.dumps(dict(schema='dsh-assembly-manifest/1',units='mm',coord=dict(up='Z',forward='-Y'),parts=parts,interfaces=[],allow_pairs=[]),indent=2),encoding='utf8')
print('V2_AUDIT_PARTS',len(records))
