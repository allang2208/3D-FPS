"""Record the unit repair after the import batches; does not run the monster."""
exec(compile(open('D:/FPS3D/FPSGAME/Tools/WitchRebuilt/finish_integration.py',encoding='utf-8').read(),'finish_integration.py','exec'))
report.update({
    'status':'Unit repair imported and saved; runtime/visual test pending user',
    'regular_editor_build':{'result':'Succeeded','log':'Saved/BuildEditor/build-20260922-092832.log'},
    'editable_animation_scenes':'All 8 scenes regenerated with the Foundation armature conversion and world bone scale retained',
    'unit_repair':{
        'date':'2026-09-22',
        'armature_object_scale':0.01,
        'gesture_world_bone_scale':'Retained when reconstructing rotated bone transforms',
        'robe_horizontal_expansion':1.0,
        'cloth_asset':'WitchRebuilt_WaistDrapeUnits01',
        'imports':['ue_units_mesh_01.txt','ue_units_anims_a_03.txt','ue_units_anims_b_02.txt','ue_units_cloth_01.txt'],
        'actor_scale_compensation':False
    }
})
(root/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Saved unit repair delivery record; gameplay and visual testing remain with the user')
