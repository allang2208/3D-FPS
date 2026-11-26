#include "StableRidingHorse.h"
#include "StableManeComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Materials/MaterialInterface.h"

uint8 AStableRidingHorse::HomeStall() const
{
    return RegisteredStall;
}
FStableMountRecord AStableRidingHorse::Condition() const
{
    FStableMountRecord Out;
    Out.Level=HorseLevel;Out.BirthVersion=BirthVersion;
    // Whole-record saves on dismissal or departure retain progression from the owner's journal.
    if(const auto* Model=KeeperModel.Get())
        if(const auto* Saved=Model->ProfileView().MountRoster.Find(IndividualId))Out=*Saved;
    Out.HorseId=IndividualId;Out.SourceResident=OriginId;Out.Stall=HomeStall();Out.Health=Health;Out.Stamina=Stamina;Out.bExhausted=bExhausted;
    Out.MaxHealth=MaxHealth;Out.MaxStamina=MaxStamina;
    return Out;
}
void AStableRidingHorse::RestoreCondition(const FStableMountRecord& Saved)
{
    IndividualId=Saved.HorseId;HorseLevel=Saved.Level;BirthVersion=Saved.BirthVersion;OnRep_Individual();
    Health=FMath::Clamp(Saved.Health,0.f,MaxHealth);
    Stamina=FMath::Clamp(Saved.Stamina,0.f,MaxStamina);
    bExhausted=Stamina<=0.f || (Saved.bExhausted && Stamina<MaxStamina*StaminaRates.SprintRestartRatio);
    if(Health>0.f && Health<MaxHealth)ScheduleInjuryRecovery();
    ForceNetUpdate();
}
void AStableRidingHorse::SetKeeper(UColdSteelStatusModel& Model,const FStableMountRecord& Entry)
{
    KeeperModel=&Model;KeeperProfile=Model.ProfileView().NetworkProfileId;RegisteredStall=Entry.Stall;IndividualId=Entry.HorseId;OriginId=Entry.SourceResident;
    HorseLevel=Entry.Level;BirthVersion=Entry.BirthVersion;OnRep_Individual();
    if(auto* Pawn=Model.RuntimePawn())SetOwner(Pawn->GetController());
    ForceNetUpdate();
}
void AStableRidingHorse::ApplyEarnedLevel(const FStableMountRecord& Entry)
{
    if(!HasAuthority() || Entry.HorseId!=IndividualId || Entry.Level==HorseLevel)return;
    const float HealthRatio=Health/FMath::Max(1.f,MaxHealth);
    const float StaminaRatio=Stamina/FMath::Max(1.f,MaxStamina);
    HorseLevel=Entry.Level;
    OnRep_Individual();
    Health=MaxHealth*FMath::Clamp(HealthRatio,0.f,1.f);
    Stamina=MaxStamina*FMath::Clamp(StaminaRatio,0.f,1.f);
    ForceNetUpdate();
}

void AStableRidingHorse::CacheKeeperCondition(bool bSave)
{
    auto* Model=KeeperModel.Get();
    if(!HasAuthority()||!Model||Model->ProfileView().NetworkProfileId!=KeeperProfile)return;
    if(bSave && Health<=0.f)
    {
        auto Book=Model->ProfileView().MountRoster;
        if(auto* Entry=Book.Find(IndividualId))
        {
            *Entry=Condition();
            Entry->RecallAfterUtc=(FDateTime::UtcNow()+FTimespan::FromSeconds(60)).GetTicks();
            if(!Model->CommitMountRoster(Book))Model->StageMountCondition(*Entry);
        }
    }
    else if(!IsRetreating())Model->StageMountCondition(Condition());
}
void AStableRidingHorse::ApplyHorseFade(float Fade)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(!bFadeMaterialsApplied && Fade>0.f)
    {
        if(FadedCoatMaterial)GetMesh()->SetMaterial(0,FadedCoatMaterial);
        bFadeMaterialsApplied=true;
    }
    if(!bFadeMaterialsApplied)return;
    GetMesh()->SetCustomPrimitiveDataFloat(0,Fade);
    Mane->SetCustomPrimitiveDataFloat(0,Fade);
    if(Fade<=0.f)
    {
        if(CoatMaterial)GetMesh()->SetMaterial(0,CoatMaterial);
        bFadeMaterialsApplied=false;
    }
}
void AStableRidingHorse::BeginVisit(EStableHorseVisit Phase,AFPSGAMECharacter* KeeperPawn)
{
    if(!HasAuthority() || IsRetreating() || Rider || Phase==EStableHorseVisit::Present)return;
    if(Leader)SetLeader(nullptr);
    Halt();
    bRecallParking=false;bHasRecallParkGoal=false;RecallSettleSeconds=0.f;
    ArrivalLeader=Phase==EStableHorseVisit::Arriving?KeeperPawn:nullptr;
    VisitTravelYaw=GetActorRotation().Yaw;
    if(Phase==EStableHorseVisit::Arriving && KeeperPawn)
    {
        RecallAnchorPlayer=KeeperPawn->GetNavAgentLocation();
        bHasRecallParkGoal=ComputeRecallParkSpot(*KeeperPawn,RecallParkGoal,RecallParkYaw);
    }
    else if(Phase==EStableHorseVisit::Departing && KeeperPawn)
    {
        const FVector Away=(GetActorLocation()-KeeperPawn->GetActorLocation()).GetSafeNormal2D();
        const float Base=Away.IsNearlyZero()?VisitTravelYaw:Away.Rotation().Yaw;
        for(const float Offset:{0.f,40.f,-40.f,80.f,-80.f,140.f,-140.f})
        {
            const FRotator Heading(0,Base+Offset,0);
            if(ClearBody(Heading.Vector()*105.f,Heading)){VisitTravelYaw=Heading.Yaw;break;}
        }
    }
    VisitStartedAt=JumpClock();VisitState=Phase;bLeftStall=true;
    auto* Move=GetCharacterMovement();
    Move->SetMovementMode(MOVE_Walking);Move->MaxWalkSpeed=175.f;
    bPreviouslyAllowedLedges=Move->bCanWalkOffLedges;Move->bCanWalkOffLedges=false;
    OnRep_Visit();ForceNetUpdate();
}
void AStableRidingHorse::OnRep_Visit()
{
    if(IsRetreating())return;
    SetActorHiddenInGame(false);
    ApplyHorseFade(VisitState==EStableHorseVisit::Arriving?1.f:0.f);
    UpdateAuxiliaryCollision(true,true);
}
void AStableRidingHorse::TickVisit(float Delta)
{
    const bool Arriving=VisitState==EStableHorseVisit::Arriving;
    const float Age=FMath::Max(0.,JumpClock()-VisitStartedAt);
    constexpr float WalkTime=2.f,DepartFade=.65f;
    const float Fade=Arriving?1.f-FMath::SmoothStep(0.f,WalkTime,Age):FMath::SmoothStep(WalkTime,WalkTime+DepartFade,Age);
    ApplyHorseFade(Fade);
    if(!Arriving && Age>=WalkTime)UpdateAuxiliaryCollision(false,false);
    if(Age>=(Arriving?WalkTime:WalkTime+DepartFade))
    {
        if(HasAuthority())
        {
            if(!Arriving){Destroy();return;}
            VisitState=EStableHorseVisit::Present;
            GetCharacterMovement()->bCanWalkOffLedges=bPreviouslyAllowedLedges;
            auto* TargetPawn=ArrivalLeader.Get();
            ArrivalLeader.Reset();
            SetLeader(TargetPawn,true);
            ForceNetUpdate();
        }
        else if(!Arriving)SetActorHiddenInGame(true);
        return;
    }
    if(HasAuthority())
    {
        auto* Move=GetCharacterMovement();
        const float Yaw=GetActorRotation().Yaw;
        float DesiredYaw=VisitTravelYaw;
        bool bShouldAdvance=true;
        float TargetSpeed=175.f;
        if(Arriving)
        {
            if(auto* Target=ArrivalLeader.Get())
            {
                const FVector Feet=GetNavAgentLocation();
                const FVector PlayerFeet=Target->GetNavAgentLocation();
                if(FVector::DistSquared2D(PlayerFeet,RecallAnchorPlayer)>FMath::Square(320.f))
                {
                    RecallAnchorPlayer=PlayerFeet;
                    bHasRecallParkGoal=ComputeRecallParkSpot(*Target,RecallParkGoal,RecallParkYaw);
                }
                const float DistToPlayer=FVector::Dist2D(Feet,PlayerFeet);
                const float SafePlayerDist=EffectiveStopDistanceTo(PlayerFeet);
                const FVector ActiveGoal=bHasRecallParkGoal?RecallParkGoal:PlayerFeet;
                const float DistToGoal=FVector::Dist2D(Feet,ActiveGoal);
                const bool bAtParkGoal=bHasRecallParkGoal && DistToGoal<=38.f;
                const FVector Forward2D=GetActorForwardVector().GetSafeNormal2D();
                const FVector NextFeet=Feet+Forward2D*FMath::Max(18.f,175.f*Delta);
                const bool bClosingIn=FVector::Dist2D(NextFeet,PlayerFeet)<DistToPlayer;
                const bool bTooClose=DistToPlayer<=SafePlayerDist+8.f && (bClosingIn || !bHasRecallParkGoal);
                if(bAtParkGoal || bTooClose)
                {
                    bShouldAdvance=false;
                    DesiredYaw=bHasRecallParkGoal?RecallParkYaw:Yaw;
                }
                else
                {
                    const FVector GoalDir=(ActiveGoal-Feet).GetSafeNormal2D();
                    if(!GoalDir.IsNearlyZero())
                    {
                        const float GoalYaw=GoalDir.Rotation().Yaw;
                        if(Age>=.35f || FMath::Abs(FMath::FindDeltaAngleDegrees(Yaw,GoalYaw))<40.f)
                            DesiredYaw=GoalYaw;
                    }
                    const float Remaining=bHasRecallParkGoal?DistToGoal:FMath::Max(0.f,DistToPlayer-SafePlayerDist);
                    TargetSpeed=FMath::Clamp(Remaining*1.4f,80.f,175.f);
                }
            }
        }
        Move->MaxWalkSpeed=TargetSpeed;
        const float Turn=FMath::FindDeltaAngleDegrees(Yaw,DesiredYaw);
        const FRotator Next(0,Yaw+FMath::Clamp(Turn,-150.f*Delta,150.f*Delta),0);
        if(!FMath::IsNearlyZero(Turn) && ClearBody(FVector::ZeroVector,Next))SetActorRotation(Next);
        const FVector Forward=GetActorForwardVector();
        if(bShouldAdvance && FMath::Abs(Turn)<80.f && ClearBody(Forward*FMath::Max(12.f,TargetSpeed*Delta),GetActorRotation()))
            AddMovementInput(Forward,1.f,true);
        else Move->StopMovementImmediately();
    }
    const float Speed=GetVelocity().Size2D();
    UAnimSequence* Clip=Speed>8.f?WalkAnimation.Get():IdleAnimation.Get();
    if(Clip && CurrentClip!=Clip)
    {
        GetMesh()->SetAnimation(Clip);GetMesh()->Play(true);CurrentClip=Clip;
    }
    GetMesh()->SetPlayRate(Clip==WalkAnimation?FMath::Clamp(Speed/220.f,.45f,1.f):1.f);
    Mane->UpdateMotion(Delta);
}
