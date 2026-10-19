#include "FPSCharacterMovementComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Engine/World.h"

void FFPSNetworkMoveData::ClientFillNetworkMoveData(const FSavedMove_Character& Move,ENetworkMoveType Type)
{
    Super::ClientFillNetworkMoveData(Move,Type);
    const auto& FPS=static_cast<const FSavedMove_FPSCharacter&>(Move);
    DodgeSequence=FPS.DodgeSequence;DodgeDirection=FPS.DodgeRequestDirection;DodgeStartedAt=FPS.DodgeRequestTime;
    MeleeRequest=FPS.MeleeRequest;ReplayMeleeStep=FPS.MeleeStep;bReplayMeleeMomentumStart=FPS.bMeleeMomentumStart;
    SlideJumpSequence=FPS.SlideJumpSequence;bReplaySlideJump=FPS.bSlideJumpStart;
}
bool FFPSNetworkMoveData::Serialize(UCharacterMovementComponent& Movement,FArchive& Ar,UPackageMap* Map,ENetworkMoveType Type)
{
    const bool Base=Super::Serialize(Movement,Ar,Map,Type);
    Ar.SerializeIntPacked(DodgeSequence);
    Ar.SerializeIntPacked(SlideJumpSequence);
    bool OK=true;
    if(DodgeSequence){DodgeDirection.NetSerialize(Ar,Map,OK);Ar<<DodgeStartedAt;}
    Ar.SerializeIntPacked(MeleeRequest.Sequence);
    if(MeleeRequest.Sequence)
    {
        uint8 Kind=uint8(MeleeRequest.Kind);Ar<<Kind;MeleeRequest.Kind=EFPSMeleeMove(Kind);
        bool DirectionOK=true,MomentumOK=true;
        MeleeRequest.Direction.NetSerialize(Ar,Map,DirectionOK);Ar<<MeleeRequest.Distance;
        if(MeleeRequest.Kind==EFPSMeleeMove::AirMomentum)MeleeRequest.Momentum.NetSerialize(Ar,Map,MomentumOK);
        OK=OK&&DirectionOK&&MomentumOK&&Kind<=uint8(EFPSMeleeMove::Zhufeng);
    }
    return Base&&OK&&!Ar.IsError();
}
void UFPSCharacterMovementComponent::QueueDodgeRequest(const FVector& Direction)
{
    ++DodgeRequestSequence;if(!DodgeRequestSequence)++DodgeRequestSequence;
    DodgeRequestDirection=Direction.GetSafeNormal2D();
}
void UFPSCharacterMovementComponent::MoveAutonomous(float ClientTimeStamp,float DeltaTime,uint8 Flags,const FVector& NewAccel)
{
    auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner);
    if(Player)if(const auto* Data=static_cast<const FFPSNetworkMoveData*>(GetCurrentNetworkMoveData()))
    {
        bool Jump=Data->bReplaySlideJump;
        if(Player->HasAuthority())
        {
            Jump=Data->SlideJumpSequence&&static_cast<int32>(Data->SlideJumpSequence-LastServerSlideJumpSequence)>0;
            if(Jump)
            {
                LastServerSlideJumpSequence=Data->SlideJumpSequence;
                Jump=Player->IsSliding()&&IsMovingOnGround()&&Player->CanStand()&&!IsDodging()&&!Player->IsTraversing();
                if(const auto* Status=Player->FindComponentByClass<UCombatStatusFormula>();Status&&Status->BlocksMovement())Jump=false;
                if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())Jump=false;
                if(UBoundCongregateCaptureComponent::IsCaptured(Player))Jump=false;
            }
        }
        if(Jump)
        {
            Player->LastSlideJumpAt=GetWorld()->GetTimeSeconds();Player->StopSlide(true);
            Player->LaunchCharacter(FVector(Velocity.X,Velocity.Y,650.f),true,true);
        }
    }
    if(Player)if(const auto* Data=static_cast<const FFPSNetworkMoveData*>(GetCurrentNetworkMoveData()))
        ProcessMeleeNetworkMove(*Data,Player->HasAuthority());
    if(Player&&Player->HasAuthority())
    {
        const auto* Data=static_cast<const FFPSNetworkMoveData*>(GetCurrentNetworkMoveData());
        if(Data&&Data->DodgeSequence&&static_cast<int32>(Data->DodgeSequence-LastServerDodgeSequence)>0)
        {
            LastServerDodgeSequence=Data->DodgeSequence;
            UpdateFromCompressedFlags(Flags);
            // Source age survives CMC timestamp resets and retransmitted moves.
            const float Age=Data->DodgeStartedAt;
            const bool Accepted=FMath::IsFinite(Age)&&Age>=-.05f&&Age<Player->DodgeDuration
                &&!Data->DodgeDirection.ContainsNaN()&&Player->TryDodgeInDirection(Data->DodgeDirection);
            if(Accepted)
            {
                if(auto Source=GetRootMotionSourceByID(DodgeRootMotionId))
                {Source->StartTime=ClientTimeStamp-DeltaTime;Source->SetTime(FMath::Max(0.f,Age));}
            }
            else ClientRejectDodge(Data->DodgeSequence);
        }
    }
    Super::MoveAutonomous(ClientTimeStamp,DeltaTime,Flags,NewAccel);
}
void UFPSCharacterMovementComponent::QueueSlideJumpRequest()
{
    if(CharacterOwner&&CharacterOwner->GetLocalRole()==ROLE_AutonomousProxy)
    {++SlideJumpRequestSequence;if(!SlideJumpRequestSequence)++SlideJumpRequestSequence;bPendingSlideJump=true;}
}
void UFPSCharacterMovementComponent::ClientRejectDodge_Implementation(uint32 Sequence)
{
    if(Sequence==DodgeRequestSequence)CancelDodge();
}
