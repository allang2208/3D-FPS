"""Export only the eight upgraded fire clips and three editable fire sources."""
from pathlib import Path

job = Path(__file__).parent
recipe = job.parent / 'PitViper2011Integration20261002/author_pit_viper.py'
source = recipe.read_text(encoding='utf-8')
source = source.replace('OUT=O/', 'OUT=JOBROOT/')
source = source.replace("    if '.00' in kind:continue", "    if '.00' in kind or 'fire' not in kind or 'quick' in kind:continue")
# The existing mesh/skeleton binding is retained; this batch imports animations only.
source = '\n'.join(line for line in source.split('\n')
                   if not (line.startswith('bpy.ops.export_scene.fbx(') and 'bake_anim=False' in line))
source = source.replace("r.animation_data.action=made['idle'];r.animation_data.action_slot=made['idle'].slots[0]",
                        "r.animation_data.action=made['fire'];r.animation_data.action_slot=made['fire'].slots[0]")
source = source.split("\nif SIDE=='single':\n    (O/'icon_parts.json')")[0]
exec(compile(source, str(recipe), 'exec'), {'__file__': str(recipe), '__name__': '__main__', 'JOBROOT': job})
