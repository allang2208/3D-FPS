// Source/FPSGAME/Production/ProductionToolComponent.h
// Merge beside existing sprint readiness; add uint32 BluntLastServerRequestId=0.
    FVector BluntSprintDirection=FVector::ForwardVector,BluntSprintAnchorLocation=FVector::ZeroVector;
    float BluntSprintLungeDistance=0.f;
    double BluntServerSprintContactAt=0.;
    double BluntServerSprintStartedAt=0.,BluntServerSprintMoveUntil=0.;
    bool bBluntSprintLungeBlocked=true,bBluntServerSprintAttack=false;
    void AdvanceBluntSprintLunge(float FromTime,float ToTime);
    void UpdateBluntSprintAnchor(bool bUpdateFloor);
