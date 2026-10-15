#include "HeQueMonster.h"
#include "HeQuePsychicTiming.h"
#include "MonsterAIController.h"
#include "HandBrainMonster.h"
#include "HandBrainFearComponent.h"
#include "FPSCombatHealthComponent.h"
#include "../Skills/MagicOcclusion.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"

float AHeQueMonster::PsychicAge() const {return FMath::Max(0.f,float(ActionClock()-Psychic.StartedAt));}
FVector AHeQueMonster::PsychicCore() const
{
    return GetMesh()->GetSocketTransform(TEXT("Bone_000")).TransformPosition(PsychicCoreOffset);
}
bool AHeQueMonster::CanPsychic(APawn* Victim) const
{
    if(Busy()||SweepBlocked()||ActionClock()<NextPsychicAt||!PsychicClip||!PsychicWaveMesh||!PsychicWaveMaterial||
        !IsValid(Victim)||!Victim->IsPlayerControlled())return false;
    const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Vitals&&Vitals->IsDead())return false;
    const FVector Origin=PsychicCore();
    if(FVector::DistSquared(Origin,Victim->GetActorLocation())>FMath::Square(PsychicRadius))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQuePsychicSight),true,this);
    return MagicOcclusion::HasExposure(GetWorld(),Victim,Origin,Query,this);
}
bool AHeQueMonster::StartPsychic(APawn* Victim)
{
    const uint32 Version=Psychic.Serial+1;Psychic=FHeQuePsychicState();Psychic.Serial=Version;
    Psychic.Active=true;Psychic.StartedAt=ActionClock();Psychic.Origins.Init(PsychicCore(),3);
    PsychicFeared.Reset();
    for(int32 I=0;I<3;++I){PsychicVictims[I].Reset();PsychicTravel[I]=-1.f;}
    NextPsychicAt=Psychic.StartedAt+FMath::Max(HeQuePsychicTiming::End,PsychicCooldown);
    const double OtherReady=Psychic.StartedAt+HeQuePsychicTiming::End+.4;
    NextClampAt=FMath::Max(NextClampAt,OtherReady);NextSweepAt=FMath::Max(NextSweepAt,OtherReady);NextRiftAt=FMath::Max(NextRiftAt,OtherReady);
    NextJumpAt=FMath::Max(NextJumpAt,OtherReady);
    CombatTarget=Victim;GetCharacterMovement()->StopMovementImmediately();OnRep_Psychic();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
void AHeQueMonster::CancelPsychic()
{
    if(!HasAuthority()||!Psychic.Active)return;
    Psychic.Active=false;++Psychic.Serial;PsychicFeared.Reset();
    for(auto& Victims:PsychicVictims)Victims.Reset();
    OnRep_Psychic();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void AHeQueMonster::AdvancePsychic(int32 Index,float Age)
{
    const float Release=HeQuePsychicTiming::Releases[Index];
    if(Age<Release||PsychicTravel[Index]>=PsychicRadius)return;
    if(!(Psychic.ReleasedMask&(1<<Index)))
    {
        Psychic.Origins[Index]=PsychicReleasePoints.IsValidIndex(Index)?
            GetMesh()->GetComponentTransform().TransformPosition(PsychicReleasePoints[Index]):PsychicCore();
        Psychic.ReleasedMask|=1<<Index;ForceNetUpdate();
    }
    const FVector Origin=Psychic.Origins[Index];
    const float Previous=PsychicTravel[Index];
    const float Radius=PsychicRadius*FMath::Clamp((Age-Release)/HeQuePsychicTiming::WaveSeconds,0.f,1.f);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQuePsychicCover),true,this);
    // Players do not shield each other from this area wave. World cover still
    // uses complete rays, including solid geometry behind friendly monsters.
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(const auto* PC=It->Get())Query.AddIgnoredActor(PC->GetPawn());
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* Player=It->Get()?It->Get()->GetPawn().Get():nullptr;
        if(!Player||PsychicVictims[Index].Contains(Player))continue;
        const auto* Vitals=Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if(Vitals&&Vitals->IsDead())continue;
        const float Distance=FVector::Distance(Origin,Player->GetActorLocation());
        const float BodyRadius=Player->GetSimpleCollisionRadius();
        if(Distance-BodyRadius>Radius||Distance+BodyRadius<Previous)continue;
        PsychicVictims[Index].Add(Player);
        if(!MagicOcclusion::HasExposure(GetWorld(),Player,Origin,Query,this))continue;
        const float Applied=UGameplayStatics::ApplyDamage(Player,PsychicDamage,GetController(),this,UHandBrainMagicDamage::StaticClass());
        if(!IsPsychic()||IsActorBeingDestroyed())return;
        if(Applied<=0.f||(Vitals&&Vitals->IsDead())||PsychicFeared.Contains(Player))continue;
        // One attempt per cast, including immunity/cleanse; later waves never
        // refresh this cast's fear duration or refill it after purification.
        PsychicFeared.Add(Player);
        auto* Fear=Player->FindComponentByClass<UHandBrainFearComponent>();
        if(!Fear){Fear=NewObject<UHandBrainFearComponent>(Player);Player->AddInstanceComponent(Fear);Fear->RegisterComponent();}
        Fear->Apply(this);
    }
    PsychicTravel[Index]=Radius;
}
void AHeQueMonster::TickPsychic()
{
    if(!Psychic.Active)return;
    const float Age=PsychicAge();
    if(HasAuthority())
    {
        const auto* AI=Cast<AMonsterAIController>(GetController());
        if(SweepBlocked()||!AI||!AI->bDecisionEnabled){CancelPsychic();return;}
        for(int32 I=0;I<3;++I)
        {
            AdvancePsychic(I,Age);
            if(!IsPsychic()||IsActorBeingDestroyed())return;
        }
        if(Age>=HeQuePsychicTiming::End){CancelPsychic();return;}
    }
    if(GetNetMode()!=NM_DedicatedServer)PresentPsychic(Age);
}
