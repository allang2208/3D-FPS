"""Resolve current production attachment sources for A762 authoring, no tests."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent; O.mkdir(exist_ok=True)
paths={}
for k,n in {'holographic':'SM_M4_Holographic','panoramic_red_dot':'SM_PanoramicRedDot','prism_scope_2x':'SM_PrismScope2X','lpvo_1_6x':'SM_LPVO1to6X','lpvo_ring':'SM_LPVORing'}.items():
    paths[k]='/Game/Weapons/AttachmentFinish20260913/M4/Meshes/'+n
for k in ['vertical','prism','drum','canted']:
    paths[k]='/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_'+k+('_CompactMount' if k=='canted' else '')
paths.update({
 'angled':'/Game/Weapons/ResonanceGrip20260913/MeshyIntegration/AKM/SM_ResonanceGrip',
 'tactical_vertical':'/Game/Weapons/TacticalVerticalForegrip20260919/AKM/SM_TacticalVerticalForegrip',
 'skeleton':'/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock',
 'core_stock':'/Game/Weapons/CoreStock20260914/Meshy0914005605/AKM/SM_CoreStock',
 'qr_performance':'/Game/Weapons/QRPerformanceStock/Meshy20260913/AKM/SM_PerformanceStock',
 'tactical_telescopic':'/Game/Weapons/TacticalTelescopicStock20260914/AKM/SM_TacticalTelescopicStock',
 'phantom_reargrip':'/Game/Weapons/RearGripFinish20260913/AKM/phantom/SM_PhantomRearGrip',
 'balanced_reargrip':'/Game/Weapons/RearGripFinish20260913/AKM/balanced/SM_BalancedRearGrip',
 'stable_antislip_reargrip':'/Game/Weapons/StableAntiSlipRearGrip/Selected91727/AKM/SM_StableAntiSlipRearGrip',
 'laser':'/Game/Weapons/TacticalDevices20260913/AKM/laser/SM_TacticalDevice',
 'flashlight':'/Game/Weapons/TacticalDevices20260913/HunyuanV3/AKM/flashlight/SM_TacticalDevice',
})
for k in ['suppressor','brake','titanium_brake']:
    paths[k]='/Game/Weapons/M4MuzzlesV1/SM_M4_'+k
paths['tactical_suppressor']='/Game/Weapons/TacticalSuppressor20260913/M4/SM_TacticalSuppressor'
result={'meshes':{},'animations':{}}
def source(a):
    d=a.get_editor_property('asset_import_data')
    return list(d.extract_filenames()) if d else []
def material(m):
    return {'slot':str(m.material_slot_name),'path':m.material_interface.get_path_name() if m.material_interface else None}
for key,path in paths.items():
    a=u.load_asset(path)
    if not a:
        result['meshes'][key]={'asset':path,'missing':True};continue
    b=a.get_bounds()
    result['meshes'][key]={'asset':path,'source':source(a),'materials':[material(m) for m in a.static_materials],
       'bounds_center':list(b.origin.to_tuple()),'bounds_extent':list(b.box_extent.to_tuple()),'sockets':{}}
    for name in ['Emitter','AimGuide','AimCenter']:
        socket=a.find_socket(name)
        if socket:result['meshes'][key]['sockets'][name]=list(socket.relative_location.to_tuple())
for family in ['base','vertical','canted','prism','angled']:
    for clip in (['drum_reload','drum_reload_empty'] if family=='base' else ['idle','aim','fire','aim_fire','equip','reload','reload_empty','drum_reload','drum_reload_empty']):
        if clip.startswith('drum'):
            path='/Game/Weapons/AKMDrumFreeDrop20260920/'+family+'/A_AKM_'+('' if family=='base' else family+'_')+clip
        else:
            directory='GripVRENatural' if family=='vertical' else 'GripVREExtensions' if family in ['prism','canted'] else 'GripErgonomic'
            path=f'/Game/Weapons/AKMIntegration/SovietFab/{directory}/{family}/A_AKM_{family}_{clip}'
        a=u.load_asset(path)
        if not a:raise RuntimeError(path)
        result['animations'][family+'/'+clip]={'asset':path,'source':source(a),'duration':a.get_play_length()}
(O/'sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
u.log('A762_ACCESSORY_SOURCES_PREPARED')
