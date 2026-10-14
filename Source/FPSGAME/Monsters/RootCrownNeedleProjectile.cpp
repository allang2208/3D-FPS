#include "RootCrownNeedleProjectile.h"
#include "RootCrownRigPreview.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"

ARootCrownNeedleProjectile::ARootCrownNeedleProjectile()
{
    PrimaryActorTick.bCanEverTick=true;bReplicates=true;SetReplicateMovement(true);SetNetUpdateFrequency(60.f);
    Visual=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BoneNeedle"));RootComponent=Visual;
    Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visual->SetCanEverAffectNavigation(false);
    Visual->SetCastShadow(false);Visual->bReceivesDecals=false;Visual->bAffectDistanceFieldLighting=false;
}
void ARootCrownNeedleProjectile::Launch(ARootCrownRigPreview* Source,const FVector& Direction,uint32 Salvo,int32 Wave)
{
    Shooter=Source;SalvoId=Salvo;WaveIndex=Wave;
    Velocity=Direction.GetSafeNormal()*Source->NeedleSpeed;Remaining=Source->NeedleMaxRange;Damage=Source->NeedleDamage;
    NeedleMesh=Source->NeedleMesh;NeedleMaterial=Source->NeedleMaterial;ImpactSound=Source->NeedleImpactSound;
    SetActorRotation(Direction.Rotation());OnRep_Visual();
    SetLifeSpan(Remaining/FMath::Max(1.f,Source->NeedleSpeed)+.5f);ForceNetUpdate();
}
void ARootCrownNeedleProjectile::OnRep_Visual()
{
    Visual->SetStaticMesh(NeedleMesh);if(NeedleMaterial)Visual->SetMaterial(0,NeedleMaterial);
}
void ARootCrownNeedleProjectile::OnRep_Stopped(){SetActorTickEnabled(false);}
void ARootCrownNeedleProjectile::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ARootCrownNeedleProjectile,NeedleMesh);DOREPLIFETIME(ARootCrownNeedleProjectile,NeedleMaterial);
    DOREPLIFETIME(ARootCrownNeedleProjectile,ImpactSound);DOREPLIFETIME(ARootCrownNeedleProjectile,bStopped);
}
void ARootCrownNeedleProjectile::PlayImpact_Implementation(FVector_NetQuantize Position)
{
    if(GetNetMode()==NM_DedicatedServer || !ImpactSound)return;
    auto* Attenuation=NewObject<USoundAttenuation>(this);
    Attenuation->Attenuation.bAttenuate=true;Attenuation->Attenuation.bSpatialize=true;
    Attenuation->Attenuation.FalloffDistance=900.f;
    UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Position,.45f,1.f,0.f,Attenuation);
}
void ARootCrownNeedleProjectile::Tick(float Dt)
{
    Super::Tick(Dt);
    if(!HasAuthority() || bStopped)return;
    auto* Source=Shooter.Get();if(!IsValid(Source)||Source->Dead()){Destroy();return;}
    const float Step=FMath::Min(Remaining,Velocity.Size()*Dt);
    const FVector Start=GetActorLocation(),Direction=Velocity.GetSafeNormal(),End=Start+Direction*Step;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RootCrownNeedle),false,this);Query.AddIgnoredActor(Source);
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FHitResult> Hits;
    RangedAttackQuery::SweepObjects(GetWorld(),Source,Hits,Start,End,FQuat::Identity,Objects,FCollisionShape::MakeSphere(3.f),Query);
    const FHitResult* First=nullptr;
    for(const auto& Hit:Hits)
    {
        const auto* Component=Hit.GetComponent();const auto* Pawn=Cast<APawn>(Hit.GetActor());
        const bool Player=Pawn&&Pawn->IsPlayerControlled()&&Component==Pawn->GetRootComponent();
        if(!Component || (!Player&&Component->GetCollisionResponseToChannel(ECC_Visibility)!=ECR_Block))continue;
        if(!First || Hit.Time<First->Time)First=&Hit;
    }
    if(!First)
    {
        SetActorLocation(End);Remaining-=Step;if(Remaining<=0.f)Destroy();return;
    }
    AActor* Victim=First->GetActor();const auto* Pawn=Cast<APawn>(Victim);
    const bool Player=Pawn&&Pawn->IsPlayerControlled();
    bStopped=true;SetActorLocation(First->ImpactPoint-Direction*10.f);PlayImpact(First->ImpactPoint);
    if(Player)
    {
        const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
        if((!Vitals||(!Vitals->IsDead()&&!Vitals->IsInvulnerable())) && Source->RegisterNeedleHit(SalvoId,WaveIndex,Victim))
            UGameplayStatics::ApplyPointDamage(Victim,Damage,Direction,*First,Source->GetController(),Source,UEnemyRangedDamage::StaticClass());
        SetActorHiddenInGame(true);
    }
    else if(Victim&&Victim->IsA<AFPSIceWall>()&&Source->RegisterNeedleHit(SalvoId,WaveIndex,Victim))
        UGameplayStatics::ApplyPointDamage(Victim,Damage,Direction,*First,Source->GetController(),Source,UEnemyRangedDamage::StaticClass());
    // A short wall remnant makes the cover contact readable; it has no collision.
    ForceNetUpdate();SetLifeSpan(Player?.15f:1.2f);OnRep_Stopped();
}
