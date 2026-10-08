import unreal as u
s=u.get_default_object(u.SlateInspectorToolset)
print(s.call_method('Windows',('select',0)))
print('OBSERVE '+s.call_method('Observe',('w1',40)))
