# M870 visual inspection requested by user

Scope: current saved M870 hip fire stance, ADS, normal shell reload and empty reload; left-arm twist, hand/fore-end contact and hand/sleeve obstruction of the iron sights. Check bare V7 arms and the chainmail shirt shown in the user's report.

The opt-in `Source/FPSGAME/Weapons/M870PoseAudit.cpp` runs only with `-M870PoseAudit` and a `ColdSteelProfile` containing `M870PoseAudit`. It creates a fresh, isolated inventory with M870 and ammunition, then drives actual right-mouse and R inputs. It records real rendered game screenshots, native animation/time/aim values, socket projections and loaded clothing component paths. It does not change animation assets or the normal player save.

`build_editor.ps1` serializes the necessary instrumentation build. `run_capture.ps1` starts one hidden/offscreen `-game` process on the existing lit gunplay validation map at 1280x720. Fixed simulation time is used for repeatable image sampling; it is not a measured performance result. `summarize_capture.py <label>` builds contact sheets from captured images and groups runtime records. Capture completion is distinct from visual approval.

Output: `Saved/M870PoseAudit/<label>/Frames`, `frames.jsonl`, `completion.json`, `Review` and `summary.json`. Findings are recorded only after the actual images have been inspected. Audio, damage, multiplayer and unrelated weapons are outside this inspection.
