"""Requested offline catalog and publisher regression review; no live UE access."""
import ast,json,shutil,tempfile
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/EquipmentReview20261006'
D=P/'Content/ColdSteelData'
body=json.loads((D/'player_body.json').read_text(encoding='utf-8-sig'))
outfit=json.loads((D/'modular_outfits.json').read_text(encoding='utf-8-sig'))
catalog=json.loads((D/'items.json').read_text(encoding='utf-8-sig'))
shirts=['ue_field_sweater','ue_field_sweater_charcoal','ue_chainmail_shirt']
items=[key for key,value in outfit['items'].items() if value.get('slot') in (13,15)]+shirts
refs=set();errors=[]
def visit(value):
    if isinstance(value,dict):
        for child in value.values():visit(child)
    elif isinstance(value,list):
        for child in value:visit(child)
    elif isinstance(value,str) and value.startswith('/Game/'):refs.add(value)
for key in items:
    item=catalog[key];recipe=outfit['items'][key]
    if item['equipSlot']!={7:'armor',13:'boots',15:'pants'}[recipe['slot']]:errors.append(key+' slot mismatch')
    if not (D/item['ue_icon']).is_file():errors.append(key+' missing icon')
    visit(recipe);visit(item)
visit(outfit['profiles'][body['body_mesh']]);visit(body['body_mesh'])
for ref in refs:
    if not (P/'Content'/(ref.split('.')[0].removeprefix('/Game/')+'.uasset')).is_file():errors.append('Missing '+ref)

# Exercise the real publisher against an isolated project tree. Changing only
# its project-root literal leaves the publication and JSON-edit logic intact.
with tempfile.TemporaryDirectory(prefix='fps-outfit-publisher-') as folder:
    root=Path(folder)
    relative=[
        'Content/ColdSteelData/player_body.json','Content/ColdSteelData/modular_outfits.json',
        'Tools/BrownLeatherSet/json_entries.py','SourceAssets/OwnerBodyShared20261005/saved_shirts.json',
        'SourceAssets/SleeveSpikeRepair20261006/saved_shoulders.json']
    for rel in relative:
        target=root/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(P/rel,target)
    tuned=json.loads(json.dumps(body));tuned['first_person_body']['camera_forward_cm']=73.
    tuned['first_person_body']['review_preserved_setting']=True
    target=root/'Content/ColdSteelData/player_body.json';target.write_text(json.dumps(tuned),encoding='utf-8')
    script=P/'Tools/FirstPersonLegs/publish_shared_body.py'
    tree=ast.parse(script.read_text(encoding='utf-8-sig'))
    class RootRedirect(ast.NodeTransformer):
        def visit_Constant(self,node):
            return ast.copy_location(ast.Constant(root.as_posix()),node) if node.value==P.as_posix() else node
    tree=ast.fix_missing_locations(RootRedirect().visit(tree))
    exec(compile(tree,str(script),'exec'),{'__name__':'__main__'})
    actual=json.loads(target.read_text(encoding='utf-8-sig'))
    if actual['first_person_body']!=tuned['first_person_body']:errors.append('Publisher reset camera tuning')
    actual_outfit=json.loads((root/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
    if actual_outfit!=outfit:errors.append('Re-publishing changed accepted outfit recipes')
    publisher_passed=not errors
report=dict(items=len(items),asset_references=len(refs),missing_or_invalid=errors,
    publisher_preserves_camera_and_recipes=publisher_passed,live_scene_read=False,runtime_tested=False)
R.mkdir(parents=True,exist_ok=True);(R/'offline-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
if errors:raise RuntimeError('Offline equipment review failed')
