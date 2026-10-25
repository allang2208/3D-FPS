// Source/FPSGAME/Movement/FPSMeleeMovementNetwork.cpp
// Inside AuthorizeMeleeMove after existing Tool/ToolAction resolution. Add !HammerSprint to generic weapon rejection guard; preserve offhand kukri and other budgets.
    FVector HammerDirection;float HammerLimit=0.f;
    const bool HammerSprint=Tool&&ColdSteelInventory::IsTwoHandedBlunt(*Tool)&&IsHammerSprintMove(R.Kind)&&ToolAction&&
        ToolAction->GetCommittedSprintMovement(R.HammerAttackId,HammerDirection,Budget,HammerLimit,Recovery);
    if(HammerSprint)return R.Kind==EFPSMeleeMove::HammerAirMomentum?
        R.Distance==0.f&&(IsFalling()||PendingLaunchVelocity.Z>0.f):R.Distance<=Budget+1.f;
