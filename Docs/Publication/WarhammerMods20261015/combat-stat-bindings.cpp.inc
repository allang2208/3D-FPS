// Apply inside UProductionToolComponent::ApplyToolStats after ToolStats has been evaluated.
// These replace the existing authored charge/radius assignments; do not append duplicate fields.
        BluntChargeSeconds=float(ToolStats.HeavyChargeSeconds);
        BluntWaveRadius=WarhammerCombat::ShockwaveRadius(*Item,Profile);
