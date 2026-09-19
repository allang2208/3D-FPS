"""Dense deformed-skin and preservation audit, explicitly requested by user."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent
K=math.tan(math.radians(37.5));ASPECT=16/9;COUNT=697
construction=json.loads((P/'construction.json').read_text())
loops=json.loads((P/'Review_ForwardGroupFlowV40/source_audit.json').read_text())['boundaries']
changed={f'{base}_{side}' for side in ('l','r') for base in ('clavicle','upperarm','upperarm_twist_01','upperarm_twist_02')}

def load(folder):
    bpy.ops.wm.open_mainfile(filepath=str(P.parent/folder/('AzureRunesword_'+folder+'.blend')))
    r=bpy.data.objects['SK_RuneSword_Rig'];s=bpy.context.scene;a=bpy.data.actions['A_RuneSword_Inspect']
    r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    return r,s,bpy.data.objects['SK_Manny_Arms_Export']

def signature(r,arms):
    values={'mesh':[(list(v.co),[(g.group,g.weight) for g in v.groups]) for v in arms.data.vertices],
            'faces':[list(p.vertices) for p in arms.data.polygons],
            'groups':[g.name for g in arms.vertex_groups],
            'rest':{b.name:[list(row) for row in b.matrix_local] for b in r.data.bones}}
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()

def at(s,index):s.frame_set(index//2,subframe=(index%2)*.5)
def error(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
def angle(a,b):
    q=a.to_quaternion().rotation_difference(b.to_quaternion()).normalized()
    return math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w)))
def clearance(vs):
    return max(min(-v.z-K*v.y for v in vs),min(v.x-K*ASPECT*v.y for v in vs),
               min(-v.x-K*ASPECT*v.y for v in vs),min(.005-v.y for v in vs))

r,s,arms=load('ForwardGroupFlowV40');before_signature=signature(r,arms);before=[]
for i in range(COUNT):
    at(s,i);before.append({b.name:b.matrix.copy() for b in r.pose.bones})
r,s,arms=load('AnchoredArmFlowV41');after_signature=signature(r,arms)
report={'samples':COUNT,'sample_rate':240,'duration_seconds':2.9,'camera_vertical_fov':75,'aspect':ASPECT,
        'source_mesh_weights_rest_sha256':before_signature,'result_mesh_weights_rest_sha256':after_signature,
        'unchanged_mesh_weights_rest':before_signature==after_signature,'max_preserved_matrix_error':0.,
        'max_preserved_rotation_error_deg':0.,'max_preserved_position_error_cm':0.,
        'max_key_rotation_error_deg':0.,'max_key_position_error_cm':0.,
        'max_hand_weapon_relative_matrix_error':0.,'max_upperarm_length_error_cm':0.,
        'max_endpoint_matrix_error':0.,'min_actual_cut_clearance_cm':float('inf'),
        'cut_visibility_failures':[],'cut_margin_below_1cm':[],'max_joint_step_deg':{},'source_max_joint_step_deg':{},'joint_step_peaks':{},'common_down_peak_cm':0.,
        'common_down_time_range':[],'max_upperarm_swing_deg':{},'samples_detail':[]}
prev={};moving_down=[]
for i in range(COUNT):
    at(s,i);dg=bpy.context.evaluated_depsgraph_get();ea=arms.evaluated_get(dg);em=ea.to_mesh()
    actual={b.name:b.matrix.copy() for b in r.pose.bones};source=before[i]
    f=i//2;v=construction['samples'];down=(v[f]['common_down_m']+v[min(f+1,348)]['common_down_m'])/2 if i%2 else v[f]['common_down_m']
    report['common_down_peak_cm']=max(report['common_down_peak_cm'],down*100)
    if down>1e-5:moving_down.append(i/240)
    delta=Matrix.Translation(Vector((0,0,-down)))
    for n,m in actual.items():
        if n not in changed:
            expected=delta@source[n]
            report['max_preserved_matrix_error']=max(report['max_preserved_matrix_error'],error(m,expected))
            report['max_preserved_rotation_error_deg']=max(report['max_preserved_rotation_error_deg'],angle(m,expected))
            report['max_preserved_position_error_cm']=max(report['max_preserved_position_error_cm'],(m.translation-expected.translation).length*100)
            if i%2==0:
                report['max_key_rotation_error_deg']=max(report['max_key_rotation_error_deg'],angle(m,expected))
                report['max_key_position_error_cm']=max(report['max_key_position_error_cm'],(m.translation-expected.translation).length*100)
        if i in (0,COUNT-1):report['max_endpoint_matrix_error']=max(report['max_endpoint_matrix_error'],error(m,source[n]))
    for side in ('l','r'):
        h='hand_'+side
        report['max_hand_weapon_relative_matrix_error']=max(report['max_hand_weapon_relative_matrix_error'],
            error(actual[h].inverted()@actual['WPN_root'],source[h].inverted()@source['WPN_root']))
        a='upperarm_'+side;e='lowerarm_'+side
        length=lambda p:(p[a].translation-p[e].translation).length
        report['max_upperarm_length_error_cm']=max(report['max_upperarm_length_error_cm'],abs(length(actual)-length(source))*100)
        report['max_upperarm_swing_deg'][side]=max(report['max_upperarm_swing_deg'].get(side,0),angle(actual[a],source[a]))
        for n in (a,e,h):
            if n in prev:
                step=angle(prev[n],actual[n]);old_step=angle(before[i-1][n],source[n])
                report['source_max_joint_step_deg'][n]=max(report['source_max_joint_step_deg'].get(n,0),old_step)
                if step>report['max_joint_step_deg'].get(n,0):
                    report['max_joint_step_deg'][n]=step
                    report['joint_step_peaks'][n]={'time':i/240,'position_m':list(actual[n].translation),'source_step_deg':old_step}
            prev[n]=actual[n]
    borders=[]
    for bi,g in enumerate(loops):
        points=[ea.matrix_world@em.vertices[j].co for j in g['vertices']];c=clearance(points)*100
        report['min_actual_cut_clearance_cm']=min(report['min_actual_cut_clearance_cm'],c)
        if c<=0:report['cut_visibility_failures'].append({'time':i/240,'boundary':bi,'clearance_cm':c})
        if c<1:report['cut_margin_below_1cm'].append({'time':i/240,'boundary':bi,'clearance_cm':c})
        borders.append(c)
    ea.to_mesh_clear();report['samples_detail'].append({'time':i/240,'cut_clearance_cm':borders})
report['common_down_time_range']=[min(moving_down),max(moving_down)] if moving_down else []
report['interpolation_note']='120 Hz keys preserve targets exactly; interpolating changed parent/local chains at half frames creates submillimeter-to-millimeter differences. Limits: 0.2 cm and 0.2 degree at subframes; 0.01 cm and 0.01 degree at authored keys.'
report['pass']=(report['unchanged_mesh_weights_rest'] and not report['cut_visibility_failures']
    and report['max_key_position_error_cm']<.01 and report['max_key_rotation_error_deg']<.01
    and report['max_preserved_position_error_cm']<.2 and report['max_preserved_rotation_error_deg']<.2
    and report['max_upperarm_length_error_cm']<.01 and report['max_endpoint_matrix_error']<.0001)
(P/'connection_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='samples_detail'},indent=2),flush=True)
if not report['pass']:raise RuntimeError('Connection preservation or deformed cut-loop audit failed')
