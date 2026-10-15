#include "HeQueMonster.h"
#include "HeQueRiftTiming.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

float AHeQueMonster::RiftAge() const {return FMath::Max(0.f,float(ActionClock()-Rift.StartedAt));}
bool AHeQueMonster::IsRifting() const
{
    return Rift.Active&&RiftAge()<HeQueRiftTiming::End&&!Dead()&&!Controlled();
}
uint32 AHeQueMonster::RiftSerial() const
{
    // The animation returns to locomotion at the original recovery boundary,
    // while the replicated packets can still be travelling farther away.
    return Rift.Serial*2u+(Rift.Active&&RiftAge()>=HeQueRiftTiming::End?1u:0u);
}
FVector AHeQueMonster::RiftMouth() const
{
    return GetMesh()->GetSocketLocation(TEXT("Bone_000"))+GetActorForwardVector()*12.f;
}
bool AHeQueMonster::HasRiftSight(const APawn* Victim) const
{
    if(!IsValid(Victim))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQueRiftSight),true,this);Query.AddIgnoredActor(Victim);
    FHitResult Hit;
    return !RangedAttackQuery::LineTraceSingle(GetWorld(),this,Hit,RiftMouth(),Victim->GetActorLocation()+FVector(0,0,45),ECC_Visibility,Query)
        ||(Hit.GetActor()&&Hit.GetActor()->IsA<AFPSIceWall>());
}
bool AHeQueMonster::CanRift(APawn* Victim) const
{
    if(Busy()||Rift.Active||SweepBlocked()||!RiftClip||!PressureMesh||!PressureMaterial||ActionClock()<NextRiftAt||
        !IsValid(Victim)||!Victim->IsPlayerControlled())return false;
    const auto* HealthComponent=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if(HealthComponent&&HealthComponent->IsDead())return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    const bool Elevated=FMath::Abs(Victim->GetNavAgentLocation().Z-GetNavAgentLocation().Z)>120.f;
    if(!Elevated&&Delta.Size2D()<450.f)return false;
    if(FVector::Dist(RiftMouth(),Victim->GetActorLocation())>RiftRange)return false;
    return (Delta.Size2D()<80.f||FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())>=FMath::Cos(FMath::DegreesToRadians(30.f)))&&HasRiftSight(Victim);
}
bool AHeQueMonster::StartRift(APawn* Victim)
{
    const uint32 Version=Rift.Serial+1;Rift=FHeQueRiftState();Rift.Serial=Version;
    Rift.Active=true;Rift.StartedAt=ActionClock();Rift.Origin=RiftMouth();
    // Both packets use this exact 3D direction, including elevation. No second-shot tracking.
    Rift.Direction=(Victim->GetActorLocation()+FVector(0,0,45)-Rift.Origin).GetSafeNormal();
    PressureTravel[0]=PressureTravel[1]=0.f;
    bRiftRecoveryFinished=false;
    NextRiftAt=Rift.StartedAt+FMath::Max(HeQueRiftTiming::End,RiftCooldown);
    NextSweepAt=FMath::Max(NextSweepAt,Rift.StartedAt+HeQueRiftTiming::End+.4);
    NextClampAt=FMath::Max(NextClampAt,Rift.StartedAt+HeQueRiftTiming::End+.4);
    NextPsychicAt=FMath::Max(NextPsychicAt,Rift.StartedAt+HeQueRiftTiming::End+.4);
    NextJumpAt=FMath::Max(NextJumpAt,Rift.StartedAt+HeQueRiftTiming::End+.4);
    CombatTarget=Victim;GetCharacterMovement()->StopMovementImmediately();
    OnRep_Rift();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
void AHeQueMonster::CancelRift()
{
    if(!HasAuthority()||!Rift.Active)return;
    Rift.Active=false;++Rift.Serial;OnRep_Rift();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void AHeQueMonster::AdvancePressure(int32 Index,float Age)
{
    const float Release=Index==0?HeQueRiftTiming::First:HeQueRiftTiming::Second;
    auto& Packet=Index==0?Rift.PacketA:Rift.PacketB;
    float& Stop=Packet.Stop;
    if(Age<Release||Stop>=0.f||PressureTravel[Index]>=RiftRange)return;
    if(!Packet.Released)
    {
        Packet.Released=true;
        // Exact imported release pose, independent of mesh tick order / server hitches.
        Packet.Origin=RiftReleasePoints.IsValidIndex(Index)?GetMesh()->GetComponentTransform().TransformPosition(RiftReleasePoints[Index])+Rift.Direction*12.f:RiftMouth();
        ForceNetUpdate();
    }
    const float Speed=FMath::Max(1.f,RiftSpeed),EndDistance=FMath::Min(RiftRange,(Age-Release)*Speed);
    const FVector Start=Packet.Origin+Rift.Direction*PressureTravel[Index],End=Packet.Origin+Rift.Direction*EndDistance;
    const FQuat Rotation=Rift.Direction.Rotation().Quaternion();
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_Pawn);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQuePressureWave),true,this);
    FHitResult First;bool Found=false;
    // Nine overlapping swept spheres form a thin, 2m-wide disk, matching the
    // visible wave. Every lane stops at solid pumps, walls and floor triangles.
    for(int32 Lane=0;Lane<9;++Lane)
    {
        const float Angle=(Lane-1)*PI*.25f;
        const FVector Offset=Lane==0?FVector::ZeroVector:Rotation.RotateVector(FVector(0,65.f*FMath::Cos(Angle),65.f*FMath::Sin(Angle)));
        TArray<FHitResult> Hits;
        RangedAttackQuery::SweepObjects(GetWorld(),this,Hits,Start+Offset,End+Offset,FQuat::Identity,Objects,FCollisionShape::MakeSphere(35.f),Query);
        for(const auto& Hit:Hits)
        {
            const auto* Component=Hit.GetComponent();const auto* Pawn=Cast<APawn>(Hit.GetActor());
            const bool PlayerBody=Pawn&&Pawn->IsPlayerControlled()&&Component==Pawn->GetRootComponent();
            if(!Component||(!PlayerBody&&Component->GetCollisionResponseToChannel(ECC_Visibility)!=ECR_Block&&Component->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block))continue;
            if(!Found||Hit.Time<First.Time){First=Hit;Found=true;}
        }
    }
    if(Found)
    {
        Stop=FMath::Lerp(PressureTravel[Index],EndDistance,First.Time);
        Packet.ImpactPoint=First.ImpactPoint;Packet.ImpactNormal=First.ImpactNormal.GetSafeNormal();
        Packet.HitWorld=!Cast<APawn>(First.GetActor());ForceNetUpdate();
        AActor* Victim=First.GetActor();const auto* Player=Cast<APawn>(Victim);
        const auto* Vitals=IsValid(Victim)?Victim->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(IsValid(Victim)&&((Player&&Player->IsPlayerControlled())||Victim->IsA<AFPSIceWall>())&&(!Vitals||(!Vitals->IsDead()&&!Vitals->IsInvulnerable())))
            UGameplayStatics::ApplyPointDamage(Victim,RiftDamage,Rift.Direction,First,GetController(),this,UEnemyRangedDamage::StaticClass());
    }
    PressureTravel[Index]=EndDistance;
}
void AHeQueMonster::TickRift()
{
    if(!Rift.Active)return;
    const float Age=RiftAge();
    if(HasAuthority())
    {
        const auto* AI=Cast<AMonsterAIController>(GetController());
        if(SweepBlocked()||!AI||!AI->bDecisionEnabled){CancelRift();return;}
        for(int32 I=0;I<2;++I)
        {
            AdvancePressure(I,Age);
            if(!Rift.Active||IsActorBeingDestroyed())return;
        }
        if(Age>=HeQueRiftTiming::End&&!bRiftRecoveryFinished)
        {
            bRiftRecoveryFinished=true;
            if(auto* RiftAI=Cast<AMonsterAIController>(GetController()))RiftAI->UpdateKnowledge();
        }
        // Retain both visible and authoritative waves for their complete range,
        // including the impact tail. This does not extend the boss's recovery.
        const float Speed=FMath::Max(1.f,RiftSpeed);
        const float EndA=HeQueRiftTiming::First+(Rift.PacketA.Stop>=0.f?Rift.PacketA.Stop:RiftRange)/Speed+.4f;
        const float EndB=HeQueRiftTiming::Second+(Rift.PacketB.Stop>=0.f?Rift.PacketB.Stop:RiftRange)/Speed+.4f;
        if(Age>=FMath::Max(HeQueRiftTiming::End,FMath::Max(EndA,EndB))){CancelRift();return;}
    }
    if(GetNetMode()!=NM_DedicatedServer)PresentRift(Age);
}
