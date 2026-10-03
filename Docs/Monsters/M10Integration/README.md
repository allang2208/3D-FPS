# Deferred M10 player on-hit integration

This patch is not applied to public Source. The local full game already executes these effects, but `Source/FPSGAME/Survival/FPSSurvivalComponent` belongs to other unpublished work and is not included in this M10 publication.

After restoring that subsystem, merge the M10 damage-type branch after accepted health damage. Each accepted howl pulse calls `ApplySanityDamage(5)` and applies the existing five-second cripple to a living non-immune target. If the restored survival code already has generic `ApplySanityAttack`, keep it in the non-M10 branch so one pulse cannot deduct SAN twice. Do not copy unrelated player-body, hunger, lag-pose or replication changes from the current shared health file.

The patch is based on the public health implementation at publication time; it is a merge reference, not an auto-installer. Local multiplayer also has `ClientApplyM10HowlCripple`, which depends on the separate replication work and is outside this patch. Restore and integrate that subsystem separately if multiplayer is required. Public M10 magic damage works through the existing type hierarchy; the SAN/cripple receiver additions are deferred. No isolated-public-source build or game test was performed.
