// Source/FPSGAME/Movement/FPSMeleeMovementNetwork.cpp
// Separate edits in existing shared movement implementation; retain surrounding scopes and body.
    if(!Authority&&IsMeleeMoveRejected(R.Sequence))return;
    // Falling sweep condition:
    if((R.Kind==EFPSMeleeMove::Dash||R.Kind==EFPSMeleeMove::HammerDash||R.Kind==EFPSMeleeMove::Zhufeng)&&IsFalling())
    // IsNetworkDashWindowOpen kind condition also includes HammerDash and IsMeleeMomentumMove.
