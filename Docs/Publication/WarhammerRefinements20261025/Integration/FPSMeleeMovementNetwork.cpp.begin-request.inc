// Source/FPSGAME/Movement/FPSMeleeMovementNetwork.cpp
// Replace existing method; preserve generic sword/kukri movement kinds when AttackId is zero.
void UFPSCharacterMovementComponent::BeginMeleeLungeRequest(EFPSMeleeMove Kind,const FVector& Direction,uint32 HammerAttackId)
{
    if(!CharacterOwner||CharacterOwner->GetLocalRole()!=ROLE_AutonomousProxy)return;
    const uint32 Next=MeleeRequest.Sequence+1;
    MeleeRequest=FFPSMeleeMoveRequest();MeleeRequest.Sequence=Next?Next:1;
    MeleeRequest.Kind=HammerAttackId?(Kind==EFPSMeleeMove::Dash?EFPSMeleeMove::HammerDash:EFPSMeleeMove::HammerAirMomentum):Kind;
    MeleeRequest.HammerAttackId=HammerAttackId;MeleeRequest.Direction=Direction.GetSafeNormal2D();
}
