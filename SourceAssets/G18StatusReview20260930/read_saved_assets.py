"""Requested read-only G18 asset review; no asset save, import or gameplay."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;S=O.parent;E=u.EditorAssetLibrary
root='/Game/Weapons/G18/Integrated20260929'
receipts=[S/d/'import_receipt.json' for d in ('G18Integration20260929','G18AttachmentRepair20260930','G18TacticalFit20260930')]
expected=sorted({p for r in receipts for p in json.loads(r.read_text())['saved']})
R={'scope':'read-only saved G18 assets; no gameplay, import, or package save','receipt_asset_count':len(expected),'missing_assets':[p for p in expected if not E.does_asset_exist(p)],'attachments':{},'icons':{}}
parts=json.loads((S/'G18Integration20260929/attachment_authoring.json').read_text())
for key,entry in parts.items():
    path=root+'/Attachments/SM_G18_'+key;mesh=u.load_asset(path)
    if not mesh:R['attachments'][key]={'missing':True};continue
    data=mesh.get_editor_property('asset_import_data');files=list(data.extract_filenames()) if data else []
    sockets={}
    for name in ('Emitter','AimGuide','AimCenter','Muzzle','MountForward','MountUp'):
        socket=mesh.find_socket(name)
        if socket:sockets[name]=list(socket.get_editor_property('relative_location').to_tuple())
    stamped=E.get_metadata_tag(mesh,'G18SourceSHA256');source=Path(entry['fbx'])
    R['attachments'][key]={'asset':mesh.get_path_name(),'import_sources':files,'manifest_source':str(source),'source_hash_matches':hashlib.sha256(source.read_bytes()).hexdigest()==stamped if stamped and source.exists() else None,'sockets':sockets,'materials':{str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in mesh.static_materials}}
for path in ['/Game/ColdSteelData/Icons/ue_g18']+[p for p in expected if '/Icons/ue_g18_' in p]:
    texture=u.load_asset(path)
    if texture:
        data=texture.get_editor_property('asset_import_data')
        R['icons'][path]={'class':texture.get_class().get_name(),'source':list(data.extract_filenames()) if data else []}
    else:R['icons'][path]={'missing':True}
R['titanium_runtime_asset_exists']=E.does_asset_exist(root+'/Attachments/SM_G18_titanium_brake')
(O/'saved_asset_review.json').write_text(json.dumps(R,indent=2))
print('G18_READ_ONLY_REVIEW '+json.dumps({'receipt_assets':len(expected),'missing':R['missing_assets'],'attachments':len(R['attachments']),'icons':len(R['icons']),'titanium':R['titanium_runtime_asset_exists']}),flush=True)
