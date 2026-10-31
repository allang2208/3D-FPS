"""Explicit semantic support graph for the scoped kitchen authoring scene."""
from pathlib import Path
import bpy,json,hashlib
R=Path(__file__).resolve().parent
records=json.loads((R/'audit-parts.json').read_text(encoding='utf8'))
rows={r['id']:r for r in records}
def numbered(group,n):return 'AUD_%s_%03d'%(group,n)
def merged(group,serial):return numbered(group,0)+('__part%03d'%serial if group=='Sink' else '.001')

def manifest_for(group):
    e=[]
    def add(a,b,kind='support',tol=.10):e.append(dict(id='IF_%03d'%len(e),a=a,b=b,fit='location',nominal_mm=0,tol_mm=tol,interface=kind))
    root='AUD_FormalDining' if group=='DiningDressing' else 'AUD_CounterSupport0'
    if group=='Dishes':
        add(numbered(group,0),root)
        for serial in [1,2]:add(numbered(group,serial),numbered(group,0),'rack_frame')
        for i in range(4):
            add(numbered(group,4+i*2),numbered(group,3+i*2),'plate_saddle',.10)
            add(numbered(group,3+i*2),numbered(group,0),'saddle_mount')
        add(numbered(group,11),numbered(group,0),'cup_tray_mount')
        add(numbered(group,0)+'.001',numbered(group,11),'cup_on_tray')
        add(numbered(group,13),numbered(group,0),'bowl_tray_mount')
        add(numbered(group,14),numbered(group,13),'bowl_on_tray')
    elif group=='Prep':
        for i in [0,1,16,27,31]:add(numbered(group,i),root)
        for i in [2,3,4,5,6,7]:add(numbered(group,i),numbered(group,1),'rack_frame')
        for i in range(4):
            add(numbered(group,8+i*2),numbered(group,9+i*2),'knife_handle')
            add(numbered(group,8+i*2),numbered(group,[3,5,6,7][i]),'knife_slot',.10)
        add(numbered(group,17),numbered(group,16),'soil_pot')
        for i in range(18,27):add(numbered(group,i),numbered(group,17),'herb_root')
        for jar in [27,31]:
            add(numbered(group,jar+1),numbered(group,jar),'lid',.5)
            add(numbered(group,jar+2),numbered(group,jar),'contents')
            add(numbered(group,jar+3),numbered(group,jar),'label')
    elif group=='DiningDressing':
        left=[r['id'] for r in records if r['source']=='KIT_DiningDressing' and r['kind']=='box_000'][0]
        right=[r['id'] for r in records if r['source']=='KIT_DiningDressing' and r['kind']=='box_006'][0]
        napkin=[r['id'] for r in records if r['source']=='KIT_DiningDressing' and r['kind']=='box_012'][0]
        vase=[r['id'] for r in records if r['source']=='KIT_DiningDressing' and r['kind']=='lathe_013'][0]
        insert=[r['id'] for r in records if r['source']=='KIT_DiningDressing' and r['kind']=='lathe_014'][0]
        for a in [left,right,napkin,vase]:add(a,root)
        for mat,serial,coffee_serial in [(left,1,3),(right,7,9)]:
            add(numbered(group,serial),mat,'plate_linen')
            add(numbered(group,serial+1),mat,'glass_linen')
            add(numbered(group,coffee_serial),numbered(group,serial+1),'glass_contents')
        for utensil,mat in [('UtensilLeft',left),('UtensilRight',right)]:
            for r in records:
                if r['source']=='KIT_DiningDressing' and r['kind']==utensil:add(r['id'],mat,'utensil')
        add(insert,vase,'vase_insert')
        for i in [15,16,17]:add(numbered(group,i),insert,'flower_insert')
    elif group=='Sink':
        root='AUD_CounterSupport0'
        def sink_kind(kind):return [r['id'] for r in records if r['source']=='KIT_Sink' and r['kind']==kind][0]
        basin=sink_kind('BasinShell');rim=sink_kind('DrainAssembly');tap=sink_kind('TapWithGasket')
        strainer=rim
        add(basin,root,'basin_flange')
        # Single structural countertop is the root support for the sink.
        tap_support='AUD_CounterSupport0'
        add(sink_kind('TapGasket'),tap_support,'tap_mount')
        add(tap,sink_kind('TapGasket'),'tap_seal')
        add(sink_kind('SoapDispenser'),tap_support,'soap_mount')
        add(rim,basin,'drain_cut_edge',.10)
        towel_ids=[sink_kind('box_'+str(i).zfill(3)) for i in [5,6,7]]
        add(towel_ids[0],root,'linen_mount')
        for i in [1,2]:add(towel_ids[i],towel_ids[i-1],'folded_linen')
        for kind in ['box_008','box_009']:add(sink_kind(kind),towel_ids[-1],'towel_stripe')
    included={r['id'] for r in records if r['id'].startswith('AUD_'+group+'_') or r['id']==root or (group in ['Sink','Dishes','Prep'] and r['id']=='AUD_CounterSupport0')}
    return dict(schema='dsh-assembly-manifest/1',units='mm',coord=dict(up='Z',forward='-Y'),
        stage='local_support_interface',root_part=root,
        parts=[dict(id=r['id'],objects=[r['id']]) for r in records if r['id'] in included],interfaces=e,allow_pairs=[])

for group in ['Dishes','Prep','DiningDressing','Sink']:
    m=manifest_for(group);path=R/('manifest-'+group.lower()+'.json');path.write_text(json.dumps(m,indent=2),encoding='utf8')
    names=[o.name for o in bpy.data.objects if o.name in {p['objects'][0] for p in m['parts']}]
    result=json.loads(K.dsh_assembly_api['scan'](objects=names,manifest=str(path),max_pairs=40000,summary_only=False))
    result['authoring_sha256']=hashlib.sha256((R/'KitchenDetailV1.blend').read_bytes()).hexdigest()
    (R/('support-'+group.lower()+'.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
    print('SUPPORT',group,result.get('verdict'),result.get('counts'))
    print('FLOAT',[(r.get('part'),r.get('other_part'),r.get('mesh_gap_mm'),r.get('reason')) for r in result.get('floaters',[])])
    print('BAD',[(r['a'],r['b'],r['class'],r.get('depth_mm')) for r in result.get('offenders',[])])
print('SUPPORT_SCANS_WRITTEN')
