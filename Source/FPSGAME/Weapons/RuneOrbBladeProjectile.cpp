#include "RuneOrbBladeProjectile.h"
#include "RuneOrbBladesComponent.h"
#include "RuneOrbBladeDamage.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/FPSIceSpikeVolley.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Kismet/GameplayStatics.h"

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
    Aura = CreateDefaultSubobject<UNiagaraComponent>(TEXT("Aura"));
    Aura->SetupAttachment(Root);
    Aura->SetCastShadow(false);
    Aura->SetAutoActivate(false);
    Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
    Light->SetupAttachment(Root);
    Light->SetLightColor(FLinearColor(0.35f, 0.7f, 1.f));
    Light->SetIntensity(900.f);
    Light->SetAttenuationRadius(220.f);
    Light->SetCastShadows(false);
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> Frost(
        TEXT("/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals.NS_FrostCrystals"));
    if (Frost.Succeeded()) Aura->SetAsset(Frost.Object);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shard(
        TEXT("/Game/Weapons/RuneOrbBlade20260921/SM_RuneBladeShard.SM_RuneBladeShard"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> ShardSkin(
        TEXT("/Game/Weapons/RuneOrbBlade20260921/M_RuneBlade_Shards.M_RuneBlade_Shards"));
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
    // Keep the authored opaque crystal, bright ridge and cyan edge slots distinct.
    // Tip points along the player's facing while hovering; the launch recomputes it.
    Aura->SetFloatParameter(TEXT("User.Strength"), 1.f);
    Aura->SetFloatParameter(TEXT("User.Flight"), 0.f);
    Aura->Activate(true);
}

void ARuneOrbBlade::Launch(const FVector& TargetPoint)
{
    if (!CanLaunch()) return;
    bFlying = true;
    Velocity = (TargetPoint - GetActorLocation()).GetSafeNormal(UE_SMALL_NUMBER, GetActorForwardVector()) * Speed;
    SetActorRotation(Velocity.Rotation());
    Aura->SetFloatParameter(TEXT("User.Flight"), 1.f);
    Aura->SetVectorParameter(TEXT("User.FlightDirection"), Velocity.GetSafeNormal());
}

void ARuneOrbBlade::StartFade()
{
    if (bFinished || FadeAge >= 0.f) return;
    FadeAge = 0.f;
    Aura->Deactivate();
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
    // Retire the intact sword on the contact frame, then scatter small blue crystals.
    Blade->SetVisibility(false);
    if (ShardMesh && ShardMaterial)
        if (auto* Fragments = GetWorld()->SpawnActor<AFPSIceSpikeFragments>(Hit.ImpactPoint + Hit.ImpactNormal * 2.f, FRotator::ZeroRotator))
            Fragments->Setup(ShardMesh, ShardMaterial, Hit.ImpactNormal);
    Aura->Deactivate();
    Light->SetIntensity(0.f);
    SetLifeSpan(FadeSeconds);
}

void ARuneOrbBlade::Tick(float Delta)
{
    Super::Tick(Delta);
    if (bFinished) return;
    if (!Shooter.IsValid() || !Source.IsValid()) { Destroy(); return; }
    if (FadeAge >= 0.f)
    {
        FadeAge += Delta;
        const float Alpha = FMath::Clamp(1.f - FadeAge / FadeSeconds, 0.f, 1.f);
        Blade->SetVisibility(Alpha > 0.f);
        SetActorScale3D(FVector(FMath::Max(0.01f, Alpha)));
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
