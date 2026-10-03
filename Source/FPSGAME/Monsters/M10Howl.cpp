#include "M10Mawcrawler.h"
#include "M10HowlDamage.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"

bool AM10Mawcrawler::IsInHowlSector(const APawn* Victim) const
{
    if(!IsValid(Victim))return false;
    const FVector Delta=Victim->GetActorLocation()-Mouth();
    if(Delta.SizeSquared2D()>FMath::Square(HowlRange)||FMath::Abs(Delta.Z)>200.f)return false;
    if(FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())<FMath::Cos(FMath::DegreesToRadians(HowlAngle*.5f)))return false;
    // Both the muzzle path and the outgoing ray must be clear: leaning the head
    // through thin geometry cannot put the wave origin behind a blocking wall.
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M10HowlSight),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit,GetMesh()->GetSocketLocation(TEXT("body_front")),Mouth(),ECC_Visibility,Query)
        &&CanSee(Victim);
}
bool AM10Mawcrawler::CanHowl(APawn* Victim) const
{
    if(!IsValid(Victim)||Busy()||HowlCooldownLeft>0.f||!HowlClip||!GetCharacterMovement()->IsMovingOnGround())return false;
    if(const auto* HealthComponent=Victim->FindComponentByClass<UFPSCombatHealthComponent>();HealthComponent&&HealthComponent->IsDead())return false;
    // Front-sector targets may be howled at immediately when a bite cannot
    // reach them. The committed channel still keeps its starting orientation.
    return !PrefersRearAttack(Victim)&&IsInHowlSector(Victim);
}
void AM10Mawcrawler::DealHowl()
{
    if(!HasAuthority()||Dead()||State!=EM10State::Howl)return;
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        APawn* Victim=It->Get()?It->Get()->GetPawn():nullptr;
        const auto* HealthComponent=Victim?Victim->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(!HealthComponent||HealthComponent->IsDead()||!IsInHowlSector(Victim))continue;
        // SAN/cripple are committed by the health component only after this hit
        // survives dodge, invulnerability and the normal magic defense chain.
        UGameplayStatics::ApplyDamage(Victim,HowlDamagePerTick,GetController(),this,UM10HowlDamage::StaticClass());
        if(State!=EM10State::Howl||Dead())return;
    }
}
void AM10Mawcrawler::TickHowl()
{
    if(!HasAuthority())
        if(const auto* GS=GetWorld()->GetGameState())StateSeconds=FMath::Max(0.f,float(GS->GetServerWorldTimeSeconds()-HowlStartedAt));
    const float Duration=HowlWindup+HowlChannel+HowlRecovery;
    if(HasAuthority())
    {
        SetActorRotation(FRotator(0,LockedYaw,0));
        // Six half-open channel samples: .6, 1.1, 1.6, 2.1, 2.6, 3.1 s.
        // Frame hitches consume each index once; recovery adds no seventh hit.
        while(NextHowlPulse<6&&StateSeconds>=HowlWindup+NextHowlPulse*HowlInterval)
        {
            Sample(HowlWindup+NextHowlPulse*HowlInterval);GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();
            ++NextHowlPulse;DealHowl();if(State!=EM10State::Howl)return;
        }
    }
    Sample(FMath::Min(StateSeconds,Duration));UpdateHowlPresentation(StateSeconds);
    if(HasAuthority()&&StateSeconds>=Duration)
    {
        SetState(EM10State::Idle);
        if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
    }
}
void AM10Mawcrawler::PrepareHowlPresentation()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    HowlVoice->SetSound(HowlSound);
    for(const auto& Wave:HowlWaves)
    {
        Wave->SetStaticMesh(HowlWaveMesh);
        auto* Material=HowlWaveMaterial?UMaterialInstanceDynamic::Create(HowlWaveMaterial,this):nullptr;
        HowlMaterials.Add(Material);if(Material)Wave->SetMaterial(0,Material);
    }
}
void AM10Mawcrawler::StopHowlPresentation()
{
    bHowlVoiceStarted=false;if(HowlVoice)HowlVoice->Stop();
    for(const auto& Wave:HowlWaves)Wave->SetVisibility(false);
}
void AM10Mawcrawler::UpdateHowlPresentation(float Seconds)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const float Elapsed=Seconds-HowlWindup;
    if(Elapsed<0.f)return;
    if(Elapsed>=HowlChannel){StopHowlPresentation();return;}
    if(!bHowlVoiceStarted){bHowlVoiceStarted=true;if(HowlSound)HowlVoice->Play(Elapsed);}
    // Three fixed components recycle expanding curved ribbons; no actor or
    // particle allocation, no collision and no gameplay work on render ticks.
    constexpr float TravelSeconds=1.f;
    const int32 Pulse=FMath::FloorToInt(Elapsed/HowlInterval);
    for(int32 I=0;I<HowlWaves.Num();++I)
    {
        auto* Wave=HowlWaves[I].Get();const int32 Emission=Pulse-I;
        const float Age=Elapsed-Emission*HowlInterval,Progress=Age/TravelSeconds;
        const bool Visible=Emission>=0&&Progress>=0.f&&Progress<1.f;
        Wave->SetVisibility(Visible);if(!Visible)continue;
        Wave->SetWorldLocation(Mouth());Wave->SetWorldRotation(FRotator(0,GetActorRotation().Yaw,0));
        Wave->SetWorldScale3D(FVector(FMath::Max(.02f,Progress)*HowlRange/100.f));
        if(HowlMaterials.IsValidIndex(I)&&HowlMaterials[I])
        {
            HowlMaterials[I]->SetScalarParameterValue(TEXT("Opacity"),.65f*(1.f-Progress));
            HowlMaterials[I]->SetScalarParameterValue(TEXT("HalfAngle"),HowlAngle*.5f);
        }
    }
}
