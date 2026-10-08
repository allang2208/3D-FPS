import unreal as u
s=u.get_default_object(u.SlateInspectorToolset)
print('CLICK '+str(s.call_method('Click',('b55','left',False,u.SlateInspectorToolsetModifierKeys()))))
