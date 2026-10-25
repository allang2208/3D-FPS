// Source/FPSGAME/Movement/FPSMeleeMovementNetwork.cpp
// Replace rejection and add cancellation; preserve movement sequence and attack identity separately.
void UFPSCharacterMovementComponent::ClientRejectMeleeMove_Implementation(uint32 Sequence)
{
    if(Sequence!=MeleeRequest.Sequence)return;
    RejectedMeleeSequence=Sequence;PendingMeleeStep=0.f;
    if(IsMeleeMomentumMove(MeleeRequest.Kind))bMeleeDashMomentum=false;
}

void UFPSCharacterMovementComponent::CancelHammerSprintMove(uint32 AttackId)
{
    if(!AttackId)return;
    if(ServerHammerAttackId==AttackId)
    {bServerMeleeBlocked=true;ServerMeleeRecoveryUntil=ServerMeleeWindowUntil=0.;bMeleeDashMomentum=false;}
    if(IsHammerSprintMove(MeleeRequest.Kind)&&MeleeRequest.HammerAttackId==AttackId)
    {RejectedMeleeSequence=MeleeRequest.Sequence;PendingMeleeStep=0.f;bPendingMeleeMomentum=false;bMeleeDashMomentum=false;}
}
