"""User-requested read-only audit of the active robe packages and hem materials."""
import json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'Review20261020';OUT.mkdir(exist_ok=True)
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'));r=c['items']['ue_blue_mage_robe']
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
result=dict(body={},underlayers={},lower_routes=[],failures=[],runtime_tested=False,network_transport_tested=False,saved_any_assets=False)
def need(ok,message):
    if not ok:result['failures'].append(message)
def disk(path):return P/'Content'/(path.split('.')[0][6:]+'.uasset')
for profile in ('Body','Jason'):
    for field,suffix in (('rig_meshes',''),('owner_body_meshes','_Owner')):
        key=profile+suffix;path=r[field][profile];file=disk(path);sha=hashlib.sha256(file.read_bytes()).hexdigest();m=u.load_asset(path);need(bool(m),'Missing '+path)
        if not m:continue
        cloths=list(m.get_editor_property('mesh_clothing_assets'));phys=m.get_editor_property('physics_asset');lods=S.get_lod_count(m)
        need(len(cloths)==1,'Expected one continuous cloth: '+key);need(bool(phys),'Missing cloth collision: '+key);need(lods==3,'Missing body LODs: '+key)
        if len(cloths)==1:need(cloths[0].get_editor_property('physics_asset')==phys,'Cloth/pose physics mismatch: '+key)
        result['body'][key]=dict(asset=path,lods=lods,cloth_count=len(cloths),physics=phys.get_path_name() if phys else None,author_hash=E.get_metadata_tag(m,'BlueMageRobeSHA'),unchanged=hashlib.sha256(file.read_bytes()).hexdigest()==sha)
        print('ROBE_REVIEW_BODY',key,flush=True);del m,cloths;gc.collect();u.SystemLibrary.collect_garbage()
for original,path in r['underlayer_meshes'].items():
    file=disk(path);sha=hashlib.sha256(file.read_bytes()).hexdigest();m=u.load_asset(path);need(bool(m),'Missing '+path)
    if not m:continue
    upper=[];caps=[]
    for slot in m.get_editor_property('materials'):
        name=str(slot.material_slot_name)
        if name.startswith('RobeStairCap_'):caps.append(name)
        if name.startswith('RobeStairHidden_'):
            material=slot.material_interface;params={str(n) for n in L.get_scalar_parameter_names(material)} if material else set();supported='RobeHemStrength' in params
            upper.append(dict(slot=name,material=material.get_path_name() if material else None,supported=supported));need(supported,'Missing hem WPO: '+path+' '+name)
    need(not caps,'Obsolete ankle cap: '+path);need(bool(upper) or path==original,'No continuous upper section: '+path)
    result['underlayers'][original]=dict(asset=path,lods=S.get_lod_count(m),upper_sections=upper,caps=caps,unchanged=hashlib.sha256(file.read_bytes()).hexdigest()==sha)
    del m;gc.collect();u.SystemLibrary.collect_garbage()
for key,item in c['items'].items():
    if item.get('slot') not in (13,15):continue
    variants={'default':item.get('rig_meshes',{})};variants.update(item.get('shoe_fit_meshes',{}))
    for variant,rigs in variants.items():
        for rig,path in rigs.items():
            if rig not in ('Body','Jason'):continue
            covered=path in r['underlayer_meshes'];result['lower_routes'].append(dict(item=key,variant=variant,rig=rig,covered=covered));need(covered,'Missing lower route: '+key+' '+variant+' '+rig)
result['completed']=True;result['passed']=not result['failures'];(OUT/'assets.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('ROBE_ASSET_REVIEW',len(result['body']),len(result['underlayers']),len(result['lower_routes']),'failures',result['failures'],flush=True)
if result['failures']:raise RuntimeError('Active robe asset review found failures')
