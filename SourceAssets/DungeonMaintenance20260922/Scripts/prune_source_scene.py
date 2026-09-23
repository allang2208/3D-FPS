"""Remove only rejected generated objects/data from an archived mixed source."""
import bpy,json,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
plan=json.loads((ROOT/'Config/retirement.json').read_text())
args=sys.argv[sys.argv.index('--')+1:];relative=args[0]
archive=PROJECT/plan['archive']/relative;output=PROJECT/relative
if not archive.resolve().is_relative_to((PROJECT/plan['archive']).resolve()):raise RuntimeError('Unexpected archive input')
if not output.resolve().is_relative_to(PROJECT/'SourceAssets'):raise RuntimeError('Unexpected output')
bpy.ops.wm.open_mainfile(filepath=str(archive))
ids=[r['id'].lower() for r in plan['retired']]
labels=set(plan['actor_labels'])|{s.removeprefix('DGN_AV2_') for s in plan['actor_labels']}
removed=[]
for ob in list(bpy.data.objects):
    name=re.sub(r'\.\d{3}$','',ob.name)
    reject=name in labels or any(ident in name.lower() for ident in ids) or name=='Existing Goddess UE asset - anchor'
    if reject:
        removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
# Purge unused packed generated maps/meshes as well as their disconnected objects.
bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(output))
receipts=ROOT/'Receipts/source-pruning';receipts.mkdir(parents=True,exist_ok=True)
(receipts/(output.stem+'.json')).write_text(json.dumps(dict(source=str(archive),output=str(output),removed=removed,tests_run=False),indent=2),encoding='utf-8')
print('REJECTED_GEOMETRY_REMOVED',output.name,len(removed))
