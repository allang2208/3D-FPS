"""Inspect the current project's reflected instance-component editor API only."""
from pathlib import Path
import json,traceback
import unreal as u
R=Path(__file__).resolve().parent
MAP='/Game/GameMaps/L_CyberpunkApartment'
def row(o):
    return {'name':str(o),'doc':str(o.__doc__),'has_call':hasattr(o,'__call__')}
def main():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve running game')
    dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty:raise RuntimeError('Preserve dirty maps')
    out={'game_run':False,'modified':False,'saved':False}
    for name in ['SubobjectDataSubsystem','SubobjectDataBlueprintFunctionLibrary','AddNewSubobjectParams','AttachmentRule','AttachmentRules','KBoxElem']:
        cls=getattr(u,name,None)
        out[name]={'present':cls is not None,'members':{n:row(getattr(cls,n,None)) for n in dir(cls) if n in ['k2_gather_subobject_data_for_instance','k2_find_subobject_data_from_handle','add_new_subobject','attach_subobject','find_handle_for_object','get_associated_object','get_object','get_parent_handle','is_handle_valid','keep_world','snap_to_target','keep_relative']}} if cls else None
    ss=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    out['subsystem']=str(ss)
    out['object_dirty_method']={'uobject':hasattr(u.Object,'mark_package_dirty'),'package':hasattr(u.Package,'mark_package_dirty')}
    out['vector']=str(u.Vector(1,2,3).to_tuple())
    box=u.KBoxElem();box.set_editor_property('center',u.Vector(1,2,3))
    for axis,value in zip(('x','y','z'),(4,5,6)):box.set_editor_property(axis,value)
    out['box']=str(box)
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world or world.get_path_name()!=MAP+'.'+MAP.rsplit('/',1)[-1]:raise RuntimeError('Wrong map')
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if str(a.get_editor_property('container_id'))=='Apartment.Fridge_Upper' if isinstance(a,u.ColdSteelSceneContainer))
    handles=ss.k2_gather_subobject_data_for_instance(actor)
    out['handles']=str(handles)
    out['count']=len(handles)
    lib=u.SubobjectDataBlueprintFunctionLibrary
    for h in handles:
        d=ss.k2_find_subobject_data_from_handle(h)
        if not d:continue
        obj=lib.get_associated_object(d)
        if obj:
            out.setdefault('components',[]).append({'name':obj.get_name(),'class':obj.get_class().get_name(),'handle':str(h),'object':obj.get_path_name()})
    ph=ss.find_handle_for_object(handles[0],actor.door_hinge)
    out['parent_handle']=str(ph)
    params=u.AddNewSubobjectParams()
    params.new_class=u.StaticMeshComponent
    params.parent_handle=ph
    params.blueprint_context=None
    nh,reason=ss.add_new_subobject(params)
    out['new_handle']=str(nh);out['failure_reason']=str(reason)
    nd=ss.k2_find_subobject_data_from_handle(nh)
    out['new_data']=str(nd)
    c=lib.get_associated_object(nd)
    out['new_object']=c.get_path_name() if c else None
    if not c:raise RuntimeError('Probe could not create an instance component; not saved')
    c.rename('KP_Probe_Unsaved')
    c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_static_mesh(u.load_asset('/Game/Props/CyberpunkApartmentKitchen20261024/Meshes/SM_KP_FridgeUpperDoor'))
    c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    out['pre_attach_parent']=c.get_attach_parent().get_path_name() if c.get_attach_parent() else None
    out['attach_result']=ss.attach_subobject(ph,nh)
    out['parent_after_subsystem_attach']=c.get_attach_parent().get_path_name() if c.get_attach_parent() else None
    c.set_relative_transform(u.Transform(),False,False)
    out['relative_transform']={'location':list(c.relative_location.to_tuple()),'rotation':{'pitch':c.relative_rotation.pitch,'yaw':c.relative_rotation.yaw,'roll':c.relative_rotation.roll},'scale':list(c.relative_scale3d.to_tuple())}
    out['deleted']=ss.k2_delete_subobject_from_instance(handles[0],nh)
    out['parent_expected']=actor.door_hinge.get_path_name()
    (R/'probe-subobjects.json').write_text(json.dumps(out,indent=2),encoding='utf8')
    print('KITCHEN_SUBOBJECT_PROBE_READY',json.dumps(out))
if __name__=='__main__':
    try:main()
    except Exception:
        (R/'probe-subobjects.json').write_text(json.dumps({'error':traceback.format_exc()},indent=2),encoding='utf8')
        raise
