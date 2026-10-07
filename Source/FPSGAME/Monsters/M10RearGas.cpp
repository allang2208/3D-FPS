#include "M10Mawcrawler.h"
#include "M10PoisonGas.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"

void AM10Mawcrawler::PrepareRearGas()
{
    const auto* Asset=GetMesh()->GetSkeletalMeshAsset();
    if(!Asset)return;
    const auto& Ref=Asset->GetRefSkeleton();RearGasBone=Ref.FindBoneIndex(TEXT("rump"));
    if(RearGasBone==INDEX_NONE)return;
    FTransform Bind=Ref.GetRefBonePose()[RearGasBone];
    for(int32 Parent=Ref.GetParentIndex(RearGasBone);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
        Bind=Bind*Ref.GetRefBonePose()[Parent];
    // V5 mesh coordinates, centimetres. Converting through the imported bind
    // transform also handles its FBX root unit scale and rump bone orientation.
    const FVector Points[]={FVector(-198,0,38),FVector(-193,28,38),FVector(-193,-28,38)};
    for(int32 I=0;I<3;++I)RearGasLocalOutlets[I]=Bind.InverseTransformPosition(Points[I]);
}
FVector AM10Mawcrawler::RearGasOutlet(int32 Index) const
{
    if(RearGasBone!=INDEX_NONE)
        return GetMesh()->GetBoneTransform(RearGasBone).TransformPosition(RearGasLocalOutlets[FMath::Clamp(Index,0,2)]);
    return GetMesh()->GetSocketLocation(TEXT("rump"))-GetActorForwardVector()*55.f;
}
bool AM10Mawcrawler::IsInRearGasRange(const APawn* Victim) const
{
    return IsValid(Victim)
        &&FVector::DistSquared2D(Victim->GetActorLocation(),RearGasOutlet())<=FMath::Square(RearGasTriggerRange)
        &&FMath::Abs(Victim->GetActorLocation().Z-GetActorLocation().Z)<=220.f;
}
bool AM10Mawcrawler::CanRearGas(APawn* Victim) const
{
    if(!IsValid(Victim)||Busy()||RearGasCooldownLeft>0.f||!RearGasClip||!GetCharacterMovement()->IsMovingOnGround())return false;
    if(const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();Vitals&&Vitals->IsDead())return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    if(FVector::DotProduct(Delta.GetSafeNormal2D(),-GetActorForwardVector())<FMath::Cos(FMath::DegreesToRadians(RearGasTriggerAngle*.5f)))return false;
    const FVector Outlet=RearGasOutlet();
    if(!IsInRearGasRange(Victim))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M10RearGasSight),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit,GetMesh()->GetSocketLocation(TEXT("rump")),Outlet,ECC_Visibility,Query)
        &&!GetWorld()->LineTraceSingleByChannel(Hit,Outlet,Victim->GetActorLocation(),ECC_Visibility,Query);
}
void AM10Mawcrawler::TickRearGas()
{
    if(!HasAuthority())
        if(const auto* GS=GetWorld()->GetGameState())StateSeconds=FMath::Max(0.f,float(GS->GetServerWorldTimeSeconds()-RearGasStartedAt));
    constexpr float Duration=RearGasWindup+RearGasChannel+RearGasRecovery;
    if(HasAuthority())
    {
        SetActorRotation(FRotator(0,LockedYaw,0));
        if(!bRearGasReleased&&StateSeconds>=RearGasWindup)
        {
            bRearGasReleased=true;
            // A hitch which skipped the entire channel must not emit a late cloud.
            if(StateSeconds<RearGasWindup+RearGasChannel)
            {
                Sample(StateSeconds);GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();
                const FTransform Spawn(GetActorRotation(),RearGasOutlet());
                auto* Gas=GetWorld()->SpawnActorDeferred<AM10PoisonGas>(AM10PoisonGas::StaticClass(),Spawn,this,this,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                if(Gas)
                {
                    Gas->MagicDamagePerSecond=RearGasDamagePerSecond;
                    UGameplayStatics::FinishSpawningActor(Gas,Spawn);
                    Gas->AttachToActor(this,FAttachmentTransformRules::KeepWorldTransform);ActiveRearGas=Gas;
                }
            }
        }
        if(StateSeconds>=RearGasWindup+RearGasChannel)StopRearGas();
    }
    Sample(FMath::Min(StateSeconds,Duration));UpdateGasPresentation(StateSeconds);
    if(HasAuthority()&&StateSeconds>=Duration)
    {
        SetState(EM10State::Idle);
        if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
    }
}
void AM10Mawcrawler::UpdateGasPresentation(float Seconds)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const float Elapsed=Seconds-RearGasWindup;
    if(Elapsed<0.f)return;
    if(Elapsed>=RearGasChannel){bGasVoiceStarted=false;if(GasVoice)GasVoice->Stop();return;}
    if(!bGasVoiceStarted&&GasVoice&&GasSound){bGasVoiceStarted=true;GasVoice->Play(Elapsed);}
}
void AM10Mawcrawler::StopRearGas()
{
    bGasVoiceStarted=false;if(GasVoice)GasVoice->Stop();
    if(auto* Gas=ActiveRearGas.Get())Gas->StopEmission();
    ActiveRearGas.Reset();
}
void AM10Mawcrawler::EndPlay(const EEndPlayReason::Type Reason)
{
    StopRearGas();Super::EndPlay(Reason);
}
