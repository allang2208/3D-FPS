#include "M08AirCannonProjectile.h"
#include "LurkerM08Monster.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

AM08AirCannonProjectile::AM08AirCannonProjectile()
{
    PrimaryActorTick.bCanEverTick = true; bReplicates = true; SetReplicateMovement(true); SetNetUpdateFrequency(30.f);
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("PressureOrigin"));
    for (int32 I = 0; I < 3; ++I)
    {
        auto* Ring = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("PressureRing%d"), I));
        Ring->SetupAttachment(RootComponent); Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Ring->SetCastShadow(false); Ring->SetCanEverAffectNavigation(false); Ring->bReceivesDecals = false;
        Ring->SetRelativeRotation(FRotator(90, 0, 0)); // Authored ring normal +Z -> flight +X.
        Rings.Add(Ring);
    }
}

void AM08AirCannonProjectile::BeginPlay() { Super::BeginPlay(); OnRep_Visuals(); }
void AM08AirCannonProjectile::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AM08AirCannonProjectile, RingMesh); DOREPLIFETIME(AM08AirCannonProjectile, RingMaterial);
    DOREPLIFETIME(AM08AirCannonProjectile, ReleaseSound); DOREPLIFETIME(AM08AirCannonProjectile, SoundAttenuation);
    DOREPLIFETIME(AM08AirCannonProjectile, bSpent);
    DOREPLIFETIME(AM08AirCannonProjectile, EmissionFrame);
}
void AM08AirCannonProjectile::OnRep_Visuals()
{
    for (const auto& Ring : Rings) { if (RingMesh) Ring->SetStaticMesh(RingMesh); if (RingMaterial) Ring->SetMaterial(0, RingMaterial); }
    if (Age <= 0.f)
        for (const auto& Ring : Rings)
        {
            Ring->SetRelativeRotation(GetActorQuat().Inverse() * EmissionFrame.GetRotation());
            Ring->SetRelativeScale3D(EmissionFrame.GetScale3D() * .38f);
            Ring->SetCustomPrimitiveDataFloat(0, .6f);
        }
    if (!bSoundPlayed && ReleaseSound && SoundAttenuation && GetNetMode() != NM_DedicatedServer)
    {
        bSoundPlayed = true;
        UGameplayStatics::PlaySoundAtLocation(this, ReleaseSound, GetActorLocation(), .9f, 1.f, 0.f, SoundAttenuation);
    }
}
void AM08AirCannonProjectile::OnRep_Impact() { ImpactAge = 0.f; }
void AM08AirCannonProjectile::Launch(ALurkerM08Monster* Source, const FVector& Direction, const FTransform& MuzzleFrame)
{
    EmissionFrame = MuzzleFrame;
    Shooter = Source; Velocity = Direction.GetSafeNormal() * FMath::Max(1.f, Source->AirCannonSpeed);
    Remaining = Source->AirCannonRange; Damage = Source->AirCannonDamage; StunSeconds = Source->AirCannonStunSeconds;
    RingMesh = Source->AirRingMesh; RingMaterial = Source->AirRingMaterial;
    ReleaseSound = Source->AirReleaseSound; SoundAttenuation = Source->AirSoundAttenuation;
    OnRep_Visuals(); SetLifeSpan(Remaining / Velocity.Size() + .3f); ForceNetUpdate();
}

void AM08AirCannonProjectile::Impact(const FHitResult& Hit)
{
    bSpent = true; ImpactAge = 0.f; SetActorLocation(Hit.Location);
    SetLifeSpan(.24f); ForceNetUpdate();
    AActor* Actor = Hit.GetActor();
    if (const auto* Pawn = Cast<APawn>(Actor); Pawn && Pawn->IsPlayerControlled())
    {
        auto* Health = Actor->FindComponentByClass<UFPSCombatHealthComponent>();
        if (Health && !Health->IsDead())
        {
            const float Before = Health->Health;
            UGameplayStatics::ApplyPointDamage(Actor, Damage, Velocity.GetSafeNormal(), Hit,
                Shooter->GetController(), Shooter.Get(), UEnemyRangedDamage::StaticClass());
            // Apply control only after an accepted physical hit. Existing dodge,
            // invulnerability, guard and status immunity retain their authority.
            if (Health->Health < Before && !Health->IsDead() && !Health->IsInvulnerable())
                if (auto* Status = UCombatStatusFormula::GetOrAdd(Actor)) Status->AddStun(StunSeconds);
        }
    }
    else if (Actor && Actor->IsA<AFPSIceWall>())
        UGameplayStatics::ApplyPointDamage(Actor, Damage, Velocity.GetSafeNormal(), Hit,
            Shooter->GetController(), Shooter.Get(), UEnemyRangedDamage::StaticClass());
}

void AM08AirCannonProjectile::Tick(float Dt)
{
    Super::Tick(Dt); Age += Dt;
    if (bSpent) ImpactAge += Dt;
    if (HasAuthority() && !bSpent)
    {
        if (!Shooter.IsValid() || Shooter->Dead()) { Destroy(); return; }
        const float Step = FMath::Min(Remaining, float(Velocity.Size()) * Dt);
        const FVector Start = GetActorLocation(), End = Start + Velocity.GetSafeNormal() * Step;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(M08AirCannon), false, this); Query.AddIgnoredActor(Shooter.Get());
        FCollisionObjectQueryParams Objects;
        Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic); Objects.AddObjectTypesToQuery(ECC_Pawn);
        TArray<FHitResult> Contacts;
        GetWorld()->SweepMultiByObjectType(Contacts, Start, End, FQuat::Identity, Objects, FCollisionShape::MakeSphere(34.f), Query);
        const FHitResult* First = nullptr;
        for (const auto& Contact : Contacts)
        {
            const auto* Component = Contact.GetComponent(); const auto* Pawn = Cast<APawn>(Contact.GetActor());
            const bool PlayerBody = Pawn && Pawn->IsPlayerControlled() && Component == Pawn->GetRootComponent();
            if (!Component || (!PlayerBody && Component->GetCollisionResponseToChannel(ECC_Visibility) != ECR_Block)) continue;
            if (!First || Contact.Time < First->Time) First = &Contact;
        }
        if (First) Impact(*First);
        else { SetActorLocation(End); Remaining -= Step; if (Remaining <= 0.f) { Destroy(); return; } }
    }
    if (GetNetMode() == NM_DedicatedServer) return;
    const float Release = FMath::Clamp(Age / .10f, 0.f, 1.f);
    const float ImpactT = FMath::Clamp(ImpactAge / .24f, 0.f, 1.f);
    for (int32 I = 0; I < Rings.Num(); ++I)
    {
        const FVector Scale = FMath::Lerp(EmissionFrame.GetScale3D() * .38f, FVector(.82f + .09f * I), Release) * (1.f + ImpactT * .7f);
        const float Lag = FMath::Min(I * 16.f, float(FVector::Distance(GetActorLocation(), EmissionFrame.GetLocation())));
        Rings[I]->SetRelativeLocation(FVector(-Lag, 0, 0));
        Rings[I]->SetRelativeRotation(FQuat::Slerp(GetActorQuat().Inverse() * EmissionFrame.GetRotation(), FRotator(90, 0, 0).Quaternion(), Release));
        Rings[I]->SetRelativeScale3D(Scale);
        Rings[I]->SetCustomPrimitiveDataFloat(0, (.72f - I * .15f) * (1.f - ImpactT));
    }
}
