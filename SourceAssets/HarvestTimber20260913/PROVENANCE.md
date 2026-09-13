# Harvest timber, 2026-09-13

No asset purchase was made for this revision. The log reference images were generated for this project, then processed by the existing local RTX 5080 / ComfyUI TRELLIS.2 pipeline. No third-party timber model or audio sample was downloaded.

## Authoring chain

1. `cut_surface_reference.png`: generated front/right/end-grain reference, 1774 x 887. Its end-grain panel supplies the cut-surface texture through material UV mapping.
2. `three_views.png`: generated front/right/back reference of the same upright, short, thick poplar log. Three separate camera conditions are retained in `view0_00001_.png` through `view2_00001_.png`.
3. `generate.py`: local TRELLIS.2-4B, 1024 cascade, SS64, 16/24/20 sampling steps, seed 913180, 2048 texture resolution, 80,000-face intermediate export. Generation receipt: `07cd3c99-4cfb-4293-89ef-e17746a4d138`. `workflow.json` and `receipt.json` retain the submitted generation settings.
4. `raw_00001_.glb` and `textured_master_00001_.glb`: frozen generated mother meshes. `author_meshes.py` aligns the mother, derives reduced geometry, bakes the normal map, caps the cuts, and produces three log variants, a root-flared stump and a separate tree cut cap.
5. `HarvestTimber_Editable.blend`: editable mother and local mesh derivatives. `Delivery` contains FBX files, 2K bark textures and `authoring.json` with dimensions and triangle counts.
6. `author_audio.py`: original procedural crack and wood/leaf landing sounds, synthesized without third-party recordings. The WAV files are production candidates whose sound quality has not been auditioned.
7. `import_assets.py`: imports the owned timber files into `/Game/Items/HarvestTimber`. Falling-tree material instances derive from the project's existing `MI_BlackPoplarPCG_Bark` and `MI_BlackPoplarPCG_Foliage`. Their original foliage/bark textures remain existing project dependencies and retain their original license terms.

Binary assets and authoring sources remain in the local project under its existing publication rules. The public source commit contains code, authoring scripts and these notes; it does not redistribute the existing third-party tree material or its textures. Model/tool licenses remain applicable; generating a derivative does not relicense its tools or existing project inputs.

## Reference direction

Photorealistic freshly cut poplar trunk segment, roughly 80 cm long and 30 cm across, thick grey-brown longitudinal bark, irregular but solid cylindrical trunk, clearly readable pale end grain with annual rings and restrained radial splits, natural non-uniform silhouette, no branches, no thin sticks, neutral lighting and plain background. One image supplies front/right/end-grain; the generation condition supplies front/right/back views of the same upright object.

No acceptance rendering, PIE session, gameplay test or audio audition was performed for this revision. Texture baking and import are production steps, not visual acceptance.
