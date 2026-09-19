# Phantom rear grip — three-view generation

User requested three-view reference creation and further model sampling on 2026-09-13.

## Recommended candidate

`seed_91627/textured_master_00001_.glb` is the selected candidate from this two-seed multiview batch. Editable Blender studio: `seed_91627/PhantomRearGrip_Multiview_Editable.blend`. `front.png` and `back.png` show the broad opposite sides of this candidate; `side.png` shows the narrow grip face; `angle.png` shows a three-quarter view. Generated orientation differs between seeds, so image filenames reflect camera positions rather than guaranteed semantic sides.

Actual rendered observations: compared with the earlier Pixal single-view candidates, the outer silhouette is more regular, corresponding openings remain visible on both sides, and transverse grip ribs are present. The lower fine ribs are still merged into a broad brace, some edge transitions are soft, and local surface marks remain. Candidate recommendation only; user satisfaction/approval has not been assumed.

Seed 91603 is retained, but rejected in favor of 91627 because it has extra small geometry/markings and less regular internal supports.

## Inputs and settings

`three_views.png` was generated with the built-in image_gen tool from the original user screenshot. The exact prompt is saved in `reference_prompt.txt`. The hidden side is an inferred matching design, not an observed source view. This sheet is a rendered game-art reference, not an engineering drawing. Reference rights are not established by generation.

The sheet was split with ComfyUI ImageCrop into three equal 627x836 regions, followed by background removal. The two broad sides feed front/back image inputs; the narrow grip-facing view feeds left_image.

Model: microsoft/TRELLIS.2-4B. Node: Trellis2MeshWithVoxelMultiViewGenerator. 1024_cascade; sparse structure resolution 64; steps 16/32/24; 4096 texture size; 500000 export target faces; fill_holes=false; keep_only_shell=false. This batch used the multiview generator, not Pixal single-view and not the separate mesh refiner.

Seeds and prompt receipts/workflows/history are retained in each seed directory. Generation and the user's requested actual-model renders were performed. No UE import or gameplay regression tests were performed; the user reviews/tests the candidate.
