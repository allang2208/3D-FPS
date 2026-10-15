#include "HeQueMonster.h"
#include "HeQueClampTiming.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "Components/AudioComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"

float AHeQueMonster::ClampAge() const {return FMath::Max(0.f,float(ActionClock()-Clamp.StartedAt));}
bool AHeQueMonster::CanClamp(APawn* Victim) const
{
    if(Busy()||SweepBlocked()||!ClampClip||ClampFrames.Num()<2||ActionClock()<NextClampAt||
        !IsValid(Victim)||!Victim->IsPlayerControlled())return false;
    const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Vitals&&Vitals->IsDead())return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    return Delta.Size2D()<=ClampTriggerRange&&FMath::Abs(Victim->GetNavAgentLocation().Z-GetNavAgentLocation().Z)<80.f&&
        FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())>=FMath::Cos(FMath::DegreesToRadians(18.f))&&HasSweepSight(Victim);
}
bool AHeQueMonster::StartClamp(APawn* Victim)
{
    CombatTarget=Victim;ClampVictims.Reset();NextClampFrame=1;
    Clamp.Active=true;Clamp.StartedAt=ActionClock();++Clamp.Serial;
    NextClampAt=Clamp.StartedAt+FMath::Max(HeQueClampTiming::End,ClampCooldown);
    NextSweepAt=FMath::Max(NextSweepAt,Clamp.StartedAt+HeQueClampTiming::End+.4);
    NextRiftAt=FMath::Max(NextRiftAt,Clamp.StartedAt+HeQueClampTiming::End+.4);
    NextPsychicAt=FMath::Max(NextPsychicAt,Clamp.StartedAt+HeQueClampTiming::End+.4);
    NextJumpAt=FMath::Max(NextJumpAt,Clamp.StartedAt+HeQueClampTiming::End+.4);
    GetCharacterMovement()->StopMovementImmediately();OnRep_Clamp();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
void AHeQueMonster::CancelClamp()
{
    if(!HasAuthority()||!Clamp.Active)return;
    Clamp.Active=false;++Clamp.Serial;ClampVictims.Reset();OnRep_Clamp();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void AHeQueMonster::OnRep_Clamp()
{
    RefreshPoseTick();
    if(GetNetMode()==NM_DedicatedServer||PresentedClampSerial==Clamp.Serial)return;
    PresentedClampSerial=Clamp.Serial;ClampVoice->Stop();
    if(Clamp.Active&&ClampSound&&ClampAge()<HeQueClampTiming::End)
    {
        ClampVoice->SetSound(ClampSound);ClampVoice->AttenuationSettings=ClampAttenuation;ClampVoice->Play(ClampAge());
    }
}
void AHeQueMonster::TickClamp()
{
    if(!HasAuthority()||!Clamp.Active)return;
    const auto* AI=Cast<AMonsterAIController>(GetController());
    if(SweepBlocked()||!AI||!AI->bDecisionEnabled){CancelClamp();return;}
    const float Age=ClampAge();
    while(NextClampFrame<ClampFrames.Num()&&ClampFrames[NextClampFrame].Time<=FMath::Min(Age,HeQueClampTiming::ContactEnd)+.0001f)
    {
        const int32 Frame=NextClampFrame++;
        if(ClampFrames[Frame].Time>=HeQueClampTiming::ContactStart)
            MeleeContact(ClampFrames,Frame,ClampHitRadius,ClampDamage,0.f,ClampVictims,true);
        if(!IsClamping()||IsActorBeingDestroyed())return;
    }
    // Losing the target, missing, or hitting it never bypasses this recovery.
    // The entire ContactEnd-End interval has no damage, chase or follow-up.
    if(Age>=HeQueClampTiming::End)CancelClamp();
}
