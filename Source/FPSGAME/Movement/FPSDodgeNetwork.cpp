#include "FPSCharacterMovementComponent.h"
#include "FPSLeapRootMotionSource.h"
#include "../Skills/LeapStrikeMotion.h"
#include "../Production/ProductionToolComponent.h"
#include "../Weapons/Kukri/HatchetCharmComponent.h"
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
    LeapSequence=FPS.LeapSequence;LeapMotionStartedAt=FPS.LeapMotionStartedAt;LeapSimulatedThrough=FPS.LeapSimulatedThrough;
}
bool FFPSNetworkMoveData::Serialize(UCharacterMovementComponent& Movement,FArchive& Ar,UPackageMap* Map,ENetworkMoveType Type)
{
    const bool Base=Super::Serialize(Movement,Ar,Map,Type);
    Ar.SerializeIntPacked(DodgeSequence);
    Ar.SerializeIntPacked(SlideJumpSequence);
    Ar.SerializeIntPacked(LeapSequence);if(LeapSequence)Ar<<LeapMotionStartedAt<<LeapSimulatedThrough;
    bool OK=true;
    if(DodgeSequence){DodgeDirection.NetSerialize(Ar,Map,OK);Ar<<DodgeStartedAt;}
    Ar.SerializeIntPacked(MeleeRequest.Sequence);
    if(MeleeRequest.Sequence)
    {
        uint8 Kind=uint8(MeleeRequest.Kind);Ar<<Kind;MeleeRequest.Kind=EFPSMeleeMove(Kind);
        bool DirectionOK=true,MomentumOK=true;
        MeleeRequest.Direction.NetSerialize(Ar,Map,DirectionOK);Ar<<MeleeRequest.Distance;
        if(IsMeleeMomentumMove(MeleeRequest.Kind))MeleeRequest.Momentum.NetSerialize(Ar,Map,MomentumOK);
        if(IsHammerSprintMove(MeleeRequest.Kind))Ar.SerializeIntPacked(MeleeRequest.HammerAttackId);
        else if(Ar.IsLoading())MeleeRequest.HammerAttackId=0;
        Ar.SerializeIntPacked(MeleeRequest.KukriAttackId);
        OK=OK&&DirectionOK&&MomentumOK&&Kind<=uint8(EFPSMeleeMove::ShadowStep);
    }
    return Base&&OK&&!Ar.IsError();
}
void UFPSCharacterMovementComponent::QueueDodgeRequest(const FVector& Direction)
{
    ++DodgeRequestSequence;if(!DodgeRequestSequence)++DodgeRequestSequence;
    DodgeRequestDirection=Direction.GetSafeNormal2D();
}
bool UFPSCharacterMovementComponent::ForcePositionUpdate(float DeltaTime)
{
    if(CharacterOwner&&IsFalling()&&GetRootMotionSource(LeapStrike::MotionName))
    {
        // A short packet gap can be one stalled client frame. Let its saved
        // move arrive before advancing this ballistic flight without input.
        // A longer outage still advances the authoritative pawn each update.
        const auto* Prediction=GetPredictionData_Server_Character();
        const float MaxStep=Prediction->MaxMoveDeltaTime*CharacterOwner->GetActorTimeDilation(*GetWorld());
        if(MaxStep>0.f)
        {
            if(!Prediction->bTriggeringForcedUpdates&&DeltaTime<4.f*MaxStep)return false;
            DeltaTime=FMath::Min(DeltaTime,MaxStep);
        }
    }
    return Super::ForcePositionUpdate(DeltaTime);
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
    {
        // Process a queued slide jump above while the previous slide is still
        // active, then apply the same packet's released slide/sprint flags.
        if(IsHammerSprintMove(Data->MeleeRequest.Kind)||Data->MeleeRequest.KukriAttackId)UpdateFromCompressedFlags(Flags);
        ProcessMeleeNetworkMove(*Data,Player->HasAuthority());
    }
    if(Player&&Player->HasAuthority())
    {
        const auto* Data=static_cast<const FFPSNetworkMoveData*>(GetCurrentNetworkMoveData());
        if(Data&&Data->LeapSequence&&FMath::IsFinite(Data->LeapMotionStartedAt)
            &&Data->LeapMotionStartedAt<=ClientTimeStamp&&Data->LeapMotionStartedAt>ClientTimeStamp-LeapStrike::MaxAirTime)
        {
            auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();
            if(Tool&&Tool->bLeapStrike&&!Tool->bLeapLaunched&&Tool->LeapSerial==Data->LeapSequence
                &&Tool->LeapAge>=LeapStrike::Charge-.02f&&Tool->LaunchLeapStrike())
            {
                if(auto Source=GetRootMotionSource(LeapStrike::MotionName))
                {Source->StartTime=Data->LeapMotionStartedAt;}
            }
            // CMC gives the server extra simulation time for missing packets.
            // A single long client frame also creates a timestamp gap, but the
            // owner only simulated one capped move. Distinguish it from lost moves.
            if(Tool&&Tool->bLeapStrike&&Tool->LeapSerial==Data->LeapSequence&&FMath::IsFinite(Data->LeapSimulatedThrough))
            {
                if(const auto Source=GetRootMotionSource(LeapStrike::MotionName))
                {
                    const float OneMove=GetPredictionData_Server_Character()->MaxMoveDeltaTime*Player->GetActorTimeDilation(*GetWorld());
                    const float Simulated=Data->LeapSimulatedThrough-Source->GetTime();
                    DeltaTime=FMath::Clamp(Simulated,FMath::Min(DeltaTime,OneMove),DeltaTime);
                }
            }
        }
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
    if(Sequence==DodgeRequestSequence)
    {
        CancelDodge();
        if(auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner);Player&&Player->HatchetCharms)Player->HatchetCharms->RejectDodge();
    }
}
