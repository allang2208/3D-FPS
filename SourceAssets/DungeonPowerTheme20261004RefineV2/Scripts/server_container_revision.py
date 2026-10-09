"""Persist the native searchable server conversion in subject and module authors."""
import json,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'ServerContainers20261006'
def manifest():
    if not (ROOT/'manifest.json').exists():return None
    receipt=ROOT/'Receipts/install.json';state=json.loads(receipt.read_text('utf8')) if receipt.exists() else {}
    if state.get('stage') not in ('assets_saved','map_saved'):raise RuntimeError('Complete the server-container asset import before rebuilding')
    return json.loads((ROOT/'manifest.json').read_text('utf8'))
def patch_world():
    if not manifest():return []
    spec=importlib.util.spec_from_file_location('power_server_container_install',ROOT/'install.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.patch_loaded_map()
def remap_draft(draft):
    data=manifest()
    if not data:return draft
    base=data['base'];body=base+'/Meshes/SM_Power_ServerContainer_Body';door=base+'/Meshes/SM_Power_ServerContainer_Cartridge'
    scene=json.loads((ROOT.parent/'Config/scene.json').read_text('utf8'))
    for module in draft['modules']:
        room=next((r for r in scene['rooms'] if r['id']==module['id']),None)
        if not room:continue
        parts=[];servers=[]
        for part in module['parts']:
            if part['mesh'].split('/')[-1]!='SM_Archive_ServerRack_V1':parts.append(part);continue
            p=part['position'];source=next(r for r in room['reused_parts'] if 'ServerRack' in r['id'] and
                all(abs(a-b)<.01 for a,b in zip(p,[100*r['position_m'][0],-100*r['position_m'][1],100*r['position_m'][2]])))
            servers.append(dict(type='scene_container',container_id='PowerTheme20261004RefineV2.Server.'+source['id'],
                position=p,yaw=part['yaw'],body=body,door=door,caption='服务器模块',storage_pages=1,
                opening_motion='Drawer',drawer_travel=data['travel_ue_cm'],hinge=data['hinge_ue_cm'],initial_open_fraction=0))
        module['parts']=parts
        if servers:
            module['runtime_actors']=[p for p in module['runtime_actors'] if not p.get('container_id','').startswith('PowerTheme20261004RefineV2.Server.')]+servers
            module['runtime_assets']=sorted(set(module.get('runtime_assets',[]))|{body,door})
    draft['module_asset_paths']=sorted(set(draft['module_asset_paths'])|{body,door}|{m for i in data['meshes'] for m in i['materials'].values()})
    draft['server_container_revision']='ServerContainers20261006'
    return draft
