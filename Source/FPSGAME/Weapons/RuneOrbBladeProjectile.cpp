#include "RuneOrbBladeProjectile.h"
#include "RuneOrbBladesComponent.h"
#include "RuneOrbBladeDamage.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "Materials/MaterialInterface.h"
#include "Kismet/GameplayStatics.h"

namespace
{
constexpr int32 SpectralImpactLayerCount = 3; // Flash, shockwave, blue corona.
constexpr int32 SpectralImpactMinParticles = 32;
constexpr int32 SpectralImpactMaxParticles = 48;
}

ARuneOrbBlade::ARuneOrbBlade()
{
    PrimaryActorTick.bCanEverTick = true;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);
    Blade = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Blade"));
    Blade->SetupAttachment(Root);
    Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Blade->SetCanEverAffectNavigation(false);
    Blade->SetCastShadow(false);
    Blade->SetReceivesDecals(false);
    Wake = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SpectralWake"));
    Wake->SetupAttachment(Root);
    Wake->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Wake->SetCanEverAffectNavigation(false);
    Wake->SetCastShadow(false);
    Wake->SetReceivesDecals(false);
    Wake->SetVisibility(false);
    ImpactWisps = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("SpectralImpactWisps"));
    ImpactWisps->SetupAttachment(Root);
    ImpactWisps->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    ImpactWisps->SetCanEverAffectNavigation(false);
    ImpactWisps->SetCastShadow(false);
    ImpactWisps->SetReceivesDecals(false);
    ImpactWisps->SetVisibility(false);
    ImpactWisps->SetNumCustomDataFloats(2); // Material role and stable random seed.
    Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
    Light->SetupAttachment(Root);
    Light->SetLightColor(FLinearColor(0.06f, 0.25f, 1.f));
    Light->SetIntensity(90.f);
    Light->SetAttenuationRadius(100.f);
    Light->SetCastShadows(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> WakeAsset(
        TEXT("/Game/Weapons/RuneSpectralBlade20260927/SM_SpectralWake.SM_SpectralWake"));
    if (WakeAsset.Succeeded()) Wake->SetStaticMesh(WakeAsset.Object);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shard(
        TEXT("/Game/Weapons/RuneSpectralBlade20260927/SM_SpectralImpactParticle.SM_SpectralImpactParticle"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> ShardSkin(
        TEXT("/Game/Weapons/RuneSpectralBlade20260927/M_SpectralImpact.M_SpectralImpact"));
    if (Shard.Succeeded()) ShardMesh = Shard.Object;
    if (ShardSkin.Succeeded()) ShardMaterial = ShardSkin.Object;
}

void ARuneOrbBlade::Setup(URuneOrbBladesComponent* InSource, APawn* InOwner, float InDamage, UStaticMesh* Mesh)
{
    Source = InSource;
    Shooter = InOwner;
    Damage = InDamage;
    MaxDistance = FMath::Max(0.f, InSource->BladeRangeCM());
    VulnerabilityStacks = InSource->BladeVulnerabilityStacks();
    if (Mesh) Blade->SetStaticMesh(Mesh);
    // All shader motion stays in the authored local UVs. Independent phases avoid
    // four swords pulsing together; no per-frame material allocation or texture IO.
    const float Phase = FMath::FRandRange(0.f, 20.f);
    Blade->SetScalarParameterValueOnMaterials(TEXT("SpectralPhase"), Phase);
    Blade->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), 1.f);
    Wake->SetScalarParameterValueOnMaterials(TEXT("SpectralPhase"), Phase);
    Wake->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), 1.f);
}

void ARuneOrbBlade::Launch(const FVector& TargetPoint)
{
    if (!CanLaunch()) return;
    bFlying = true;
    Velocity = (TargetPoint - GetActorLocation()).GetSafeNormal(UE_SMALL_NUMBER, GetActorForwardVector()) * Speed;
    SetActorRotation(Velocity.Rotation());
    Wake->SetVisibility(true);
}

void ARuneOrbBlade::StartFade()
{
    if (bFinished || FadeAge >= 0.f) return;
    FadeAge = 0.f;
    Light->SetIntensity(0.f);
}

void ARuneOrbBlade::ApplyHit(const FHitResult& Hit)
{
    bFinished = true;
    if (auto* Target = Hit.GetActor())
    {
        auto* Combat = Target->FindComponentByClass<UMonsterCombatComponent>();
        if (Combat && !Combat->IsDead() && !Target->ActorHasTag(TEXT("Friendly")))
        {
            bool bCritical = false;
            double CritChance = 0, CritBonus = 0, Pen = 0, DmgBonus = 0;
            if (Shooter.IsValid() && Shooter->GetGameInstance())
                if (auto* Profile = Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
                {
                    CritChance = Profile->Derived(TEXT("crit"));
                    CritBonus = Profile->CriticalStrikeEffect().CriticalDamageBonus;
                    Pen = Profile->SetEffect(TEXT("magicPenetration"));
                    DmgBonus = Profile->SetEffect(TEXT("magicDamage"));
                }
            const CombatFormulaRuntime::MagicHit Magic{CritChance, CritBonus, Pen, DmgBonus, &bCritical, ColdSteelSkills::IsCriticalHit(Hit)};
            const TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(
                CombatFormulaRuntime::ActiveMagicHit, &Magic);
            const float Applied = UGameplayStatics::ApplyPointDamage(
                Target, Damage, Velocity.GetSafeNormal(), Hit, Shooter.IsValid() ? Shooter->GetController() : nullptr, Shooter.Get(),
                URuneOrbBladeDamage::StaticClass());
            if (Applied > 0)
                if (auto* Player = Cast<AFPSGAMECharacter>(Shooter.Get()))
                    Player->NotifyConfirmedWeaponHit(Target, Applied);
            // 毁灭符文 (2D magicVulnerabilityOnHit): the blade stacks the target's
            // magic vulnerability so follow-up magic lands harder.
            if (VulnerabilityStacks > 0 && Applied > 0 && !Combat->IsDead())
                UCombatStatusFormula::GetOrAdd(Target)->AddMagicVulnerability(VulnerabilityStacks);
            if (Source.IsValid() && Applied > 0) Source->NotifyBladeResult(Combat->IsDead());
        }
    }
    // Flash, expanding shockwave and corona share the same bounded ISM as sparks.
    // This is presentation only; collision and point damage stay unchanged.
    Blade->SetVisibility(false);
    Wake->SetVisibility(false);
    if (ShardMesh && ShardMaterial)
    {
        // Sample once per contact. Tick only advances the captured burst, so its
        // random shape is continuous rather than changing chaotically each frame.
        FRandomStream Random(FMath::Rand());
        ImpactLifetime = Random.FRandRange(.85f, 1.15f);
        ImpactDrag = Random.FRandRange(2.6f, 3.8f);
        ImpactLightPeak = Random.FRandRange(3600.f, 5000.f);
        ImpactFlashSeconds = Random.FRandRange(.19f, .29f);
        const float BurstScale = Random.FRandRange(.85f, 1.15f);
        const float StreakChance = Random.FRandRange(.18f, .38f);
        const int32 ParticleCount = Random.RandRange(SpectralImpactMinParticles, SpectralImpactMaxParticles);
        const FVector SurfaceNormal = Hit.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER, -Velocity.GetSafeNormal());
        auto OutwardDirection = [&Random, SurfaceNormal]()
        {
            FVector Direction = Random.VRand();
            if (FVector::DotProduct(Direction, SurfaceNormal) < 0.f) Direction *= -1.f;
            return (Direction + SurfaceNormal * .15f).GetSafeNormal();
        };
        const FVector Jets[] = { OutwardDirection(), OutwardDirection(), OutwardDirection() };
        ImpactAge = 0.f;
        ImpactWisps->SetStaticMesh(ShardMesh);
        ImpactWisps->SetMaterial(0, ShardMaterial);
        const FVector BurstOrigin = Hit.ImpactPoint + SurfaceNormal * 6.f;
        ImpactWisps->SetWorldLocationAndRotation(BurstOrigin, FRotator::ZeroRotator);
        ImpactWisps->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), 1.f);
        ImpactWisps->SetScalarParameterValueOnMaterials(TEXT("SpectralPhase"), Random.FRandRange(0.f, 100.f));
        WispTransforms.Reserve(SpectralImpactLayerCount + ParticleCount);
        WispVelocities.Reserve(SpectralImpactLayerCount + ParticleCount);
        ImpactLayers.Reserve(SpectralImpactLayerCount);
        for (int32 I = 0; I < SpectralImpactLayerCount; ++I)
        {
            const float Radius = (I == 0 ? 18.f : I == 1 ? 12.f : 24.f) * BurstScale;
            FImpactLayerMotion Motion;
            Motion.BaseScale = FVector(Random.FRandRange(.75f, 1.25f), Random.FRandRange(.75f, 1.25f), Random.FRandRange(.75f, 1.25f)) * Radius;
            Motion.SpinPerSecond = FRotator(Random.FRandRange(-65.f, 65.f), Random.FRandRange(-100.f, 100.f), Random.FRandRange(-65.f, 65.f));
            Motion.Growth = (I == 0 ? 1.55f : I == 1 ? 8.58f : 2.33f) * Random.FRandRange(.85f, 1.15f);
            Motion.ExpansionRate = (I == 0 ? 16.f : I == 1 ? 5.f : 6.f) * Random.FRandRange(.8f, 1.2f);
            ImpactLayers.Add(Motion);
            const FRotator Rotation(Random.FRandRange(-180.f, 180.f), Random.FRandRange(-180.f, 180.f), Random.FRandRange(-180.f, 180.f));
            const FTransform Transform(Rotation, OutwardDirection() * Random.FRandRange(0.f, 6.f), Motion.BaseScale);
            const int32 Index = ImpactWisps->AddInstance(Transform);
            ImpactWisps->SetCustomDataValue(Index, 0, float(I + 1), false);
            ImpactWisps->SetCustomDataValue(Index, 1, Random.FRand(), false);
            WispTransforms.Add(Transform);
            WispVelocities.Add(OutwardDirection() * Random.FRandRange(6.f, 22.f));
        }
        for (int32 I = 0; I < ParticleCount; ++I)
        {
            const FVector Direction = (OutwardDirection() + Jets[Random.RandRange(0, 2)] * Random.FRandRange(0.f, 1.8f)).GetSafeNormal();
            const bool bStreak = Random.FRand() < StreakChance;
            const float Width = Random.FRandRange(.9f, 1.6f);
            const FVector Scale = (bStreak ? FVector(Random.FRandRange(8.f, 18.f), Width, Width)
                : FVector(Random.FRandRange(2.3f, 5.6f))) * BurstScale;
            FRotator Rotation = Direction.Rotation(); Rotation.Roll = Random.FRandRange(-180.f, 180.f);
            const FTransform Transform(Rotation, Direction * Random.FRandRange(3.f, 14.f), Scale);
            const int32 Index = ImpactWisps->AddInstance(Transform);
            ImpactWisps->SetCustomDataValue(Index, 0, 0.f, false);
            ImpactWisps->SetCustomDataValue(Index, 1, Random.FRand(), I == ParticleCount - 1);
            WispTransforms.Add(Transform);
            WispVelocities.Add(Direction * Random.FRandRange(240.f, 500.f) * BurstScale);
        }
        ImpactWisps->SetVisibility(true);
        // Reuse the flight light for a brief surface flash, with no extra light.
        Light->SetWorldLocation(BurstOrigin + SurfaceNormal * 12.f);
        Light->SetLightColor(FLinearColor(.025f, .20f, 1.f));
        Light->SetAttenuationRadius(220.f * BurstScale);
        Light->SetIntensity(ImpactLightPeak);
    }
    else Light->SetIntensity(0.f);
    SetLifeSpan(ImpactLifetime + .05f);
}

void ARuneOrbBlade::Tick(float Delta)
{
    Super::Tick(Delta);
    if (bFinished)
    {
        if (ImpactAge >= 0.f)
        {
            ImpactAge += Delta;
            const float Alpha = FMath::Clamp(1.f - ImpactAge / ImpactLifetime, 0.f, 1.f);
            ImpactWisps->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), Alpha);
            const float Flash = FMath::Clamp(1.f - ImpactAge / ImpactFlashSeconds, 0.f, 1.f);
            Light->SetIntensity(ImpactLightPeak * Flash * Flash);
            for (int32 I = 0; I < WispTransforms.Num(); ++I)
            {
                if (I < SpectralImpactLayerCount)
                {
                    const FImpactLayerMotion& Motion = ImpactLayers[I];
                    WispTransforms[I].SetScale3D(Motion.BaseScale * (1.f + Motion.Growth * (1.f - FMath::Exp(-Motion.ExpansionRate * ImpactAge))));
                    WispTransforms[I].SetRotation((Motion.SpinPerSecond * Delta).Quaternion() * WispTransforms[I].GetRotation());
                    WispTransforms[I].AddToTranslation(WispVelocities[I] * Delta);
                }
                else
                {
                    // Integrate drag analytically so burst reach is stable across frame rates.
                    const float Drag = FMath::Exp(-ImpactDrag * Delta);
                    WispTransforms[I].AddToTranslation(WispVelocities[I] * ((1.f - Drag) / ImpactDrag));
                    WispVelocities[I] *= Drag;
                }
                ImpactWisps->UpdateInstanceTransform(I, WispTransforms[I], false, I == WispTransforms.Num() - 1, true);
            }
            if (Alpha <= 0.f) Destroy();
        }
        return;
    }
    if (!Shooter.IsValid() || !Source.IsValid()) { Destroy(); return; }
    if (FadeAge >= 0.f)
    {
        FadeAge += Delta;
        const float Alpha = FMath::Clamp(1.f - FadeAge / FadeSeconds, 0.f, 1.f);
        Blade->SetVisibility(Alpha > 0.f);
        Blade->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), Alpha * Alpha);
        Wake->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), Alpha * Alpha);
        if (FadeAge >= FadeSeconds) { bFinished = true; Destroy(); }
        return;
    }
    if (!bFlying) return;
    const FVector Previous = GetActorLocation();
    const float Travel = FMath::Min(Speed * Delta, FMath::Max(0.f, MaxDistance - Distance));
    const FVector Next = Previous + Velocity.GetSafeNormal() * Travel;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RuneBladeMove), false, Shooter.Get());
    Query.AddIgnoredActor(this);
    FHitResult Hit;
    bool Blocked = false;
    // Match ice-spike bursts: an earlier blade's corpse does not eat later blades.
    for (int32 Pass = 0; Pass < 8; ++Pass)
    {
        Blocked = GetWorld()->SweepSingleByChannel(Hit, Previous, Next, FQuat::Identity,
            ECC_Visibility, FCollisionShape::MakeSphere(HitRadius), Query);
        if (!Blocked) break;
        const auto* Combat = IsValid(Hit.GetActor()) ? Hit.GetActor()->FindComponentByClass<UMonsterCombatComponent>() : nullptr;
        if (!Combat || !Combat->IsDead()) break;
        Query.AddIgnoredActor(Hit.GetActor());
    }
    if (Blocked) { SetActorLocation(Hit.Location); ApplyHit(Hit); return; }
    SetActorLocation(Next);
    Distance += Travel;
    if (Distance >= MaxDistance) StartFade();
}
