# Foreman V11 publication

Published from an isolated checkout based on origin/main c35c2ad. The shared local master has unrelated unpublished work and is not pushed as a whole.

- Runtime: approved V11 model, six clips, 85 bones, 80 FPS import; updated gait calibration, explicit combat states and rally parameter consumption.
- Editable source and actual model previews: tools/ai-gen/foreman-v11; source textures packed into the Blender file. The source folder has .gdignore; runtime uses the GLB and its generated image assets.
- General test entry: run scenes/wilderness_combat_study.tscn with -- --foreman-review. Creates one foreman plus three ordinary zombies. Publication uses existing remote weapon/reserve APIs and three available zombie types; local-only M16 equipment/HUD, spitter and performance modules are excluded.
- Retired dedicated scene and portal moved to trash/foreman-v11 with their UID files. Local rejected C03/C04 candidates, render frames and Blender backups were moved to E:/无尽轮回/3d/trash/foreman-20260908; manifest.json records 43 initial moves (1,245,020,149 bytes). Source packing/import intermediates were subsequently placed there too. Necessary upstream sources and final previews remain locally available.
- Personal and repository monster skill references updated with verified rig, texture, rope and rally lessons.

Validation on this publication checkout: foreman 36 checks with zero failures; entry model/archive checks true; ordinary zombie regression zero failures; combat and both reload business markers true; real terrain setup reports four actors, 85 bones and rally active on all three allies. Shared working checkout also supplied the actual renderer screenshot. Import still reports unrelated baseline missing moss textures/AKM MTL and exit resource warnings; this is not a claim that the whole project is warning-free.
