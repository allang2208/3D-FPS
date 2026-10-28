"""Prepare independent Cadence sources from the project's established string interface."""
from pathlib import Path
P=Path(__file__).parent
old=P.parent/'MountainEchoV13'
s=(old/'author_model.py').read_text(encoding='utf-8').replace('MountainEcho','Cadence').replace('MOUNTAIN_ECHO','CADENCE')
s=s.replace('approved Mountain Echo string','approved Cadence string')
s=s.replace('color=[.40,.46,.49],metallic=.15,roughness=.48','color=[.022,.105,.17],metallic=.10,roughness=.46')
s=s.replace('color=[.50,.57,.60],metallic=.88,roughness=.28','color=[.60,.66,.69],metallic=.88,roughness=.26')
s=s.replace('color=[.43,.25,.075],metallic=.82,roughness=.31','color=[.50,.42,.28],metallic=.82,roughness=.32')
s=s.replace('color=[.50,.28,.075],metallic=.65,roughness=.32','color=[.62,.66,.70],metallic=.80,roughness=.29')
s=s.replace("helix('Buried antique gold filament',LOW+1.2,UP-1.2,.088,.009,3.8,3)","helix('Fine silver counterbraid',LOW+1.2,UP-1.2,.088,.010,3.8,2)\nhelix('Warm silver companion filament',LOW+1.2,UP-1.2,.089,.009,3.8,3,math.pi,-1)")
s=s.replace("tube('Satin silver bound neck',[(X,0,z-sign*.25),(X,0,z+sign*.25)],.115,2,20,bone=bone)","helix('Flexible close-wound loop neck',z-.25,z+.25,.108,.020,.047,1,bone=bone)")
s='\n'.join(line for line in s.split('\n') if "Three peak sleeve inlay" not in line)
a=s.index('for k in range(3):');b=s.index('\nmesh=bpy.data.meshes.new',a)
s=s[:a]+'''# Five soft rhythmic bands, spread along the loaded string, clear of nock/fingers.
for k,z in enumerate([LOW+22,LOW+51,NOCK+8,NOCK+32,UP-17]):
    for j in range(7):
        ring('Cadence fine winding '+str(k+1),z+(j-3)*.053,.099,.017,5,None,(k+1)/5)
    for dz in [-.24,.24]:ring('Champagne bound edge',z+dz,.102,.012,3,None)
    for face in [-1,1]:
        for offset in [-.065,.065]:
            tube('Fine cadence chevron '+str(k+1),[(X-.058,face*.078,z+.10+offset),(X,face*.105,z-.015+offset),(X+.058,face*.078,z+.10+offset)],.009,5,5,False,None,(k+1)/5)
'''+s[b:]
s=s.replace('../CadenceStringConceptV12/Cadence_String_Concept_v1.png','../CadenceStringConcept20261028/concept-v1.png')
(P/'author_model.py').write_text(s,encoding='utf-8')
s=(old/'author_icon_input.py').read_text(encoding='utf-8').replace('MountainEcho','Cadence')
s=s.replace('scene.cycles.samples=64','scene.cycles.samples=48')
s=s.replace('math.tau*6.25+.5;radius=3.9+.55*t','math.tau*2.25+.5;radius=3.5+.9*t')
s=s.replace("scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.18,.18,.18,1)\nscene.world.node_tree.nodes.get('Background').inputs[1].default_value=.4", "nodes=scene.world.node_tree.nodes;links=scene.world.node_tree.links\nbackground=nodes.new('ShaderNodeBackground');output=nodes.new('ShaderNodeOutputWorld')\nlinks.new(background.outputs['Background'],output.inputs['Surface'])\nbackground.inputs[0].default_value=(.18,.18,.18,1);background.inputs[1].default_value=.4")
(P/'author_icon_input.py').write_text(s,encoding='utf-8')
s=(old/'import_assets.py').read_text(encoding='utf-8').replace('MountainEchoV13','CadenceV1').replace('MountainEcho','Cadence').replace('mountain_echo','cadence').replace('MOUNTAIN_ECHO','CADENCE')
a=s.index("editor=u.get_editor_subsystem");b=s.index('for package in',a)
s=s[:a]+"if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():\n    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)\n    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE active: preserving the running session')\n"+s[b:]
s=s.replace('const_b=3.','const_b=5.').replace('threshold=scalar(m,3.)','threshold=scalar(m,5.)')
s=s.replace('[2.5,1.0,.16] if name.endswith(\'Resonance\') else [.45,.18,.028]','[1.9,1.65,1.1] if name.endswith(\'Resonance\') else [.26,.22,.14]')
a=s.index("name='M_Cadence_Arrow'");b=s.index("name=author['mesh']",a)
s=s[:a]+s[b:]
(P/'import_assets.py').write_text(s,encoding='utf-8')
(P/'build.ps1').write_bytes((P.parent/'MountainEchoAlpineV23/build.ps1').read_bytes())
print('CADENCE_AUTHORING_SOURCES_READY')
