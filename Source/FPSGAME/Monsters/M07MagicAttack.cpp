#include "M07MagicAttack.h"
#include "FPSCombatHealthComponent.h"
#include "MonsterCombatComponent.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FireballDamage.h"
#include "../Skills/IceSpikeDamage.h"
#include "../Skills/LightningDamage.h"
#include "../Skills/FPSFireballProjectile.h"
#include "../Skills/FPSIceSpikeVolley.h"
#include "../Skills/FPSLightningArc.h"
#include "../Skills/LightningTypes.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraFunctionLibrary.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
void ConfigureSpellMesh(UStaticMeshComponent* Component)
{
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Component->SetGenerateOverlapEvents(false);
    Component->SetCanEverAffectNavigation(false);
    Component->SetCastShadow(false);
    Component->SetReceivesDecals(false);
    Component->bAffectDistanceFieldLighting = false;
    Component->SetVisibility(false);
}

FCollisionObjectQueryParams SpellObjectTypes()
{
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    Objects.AddObjectTypesToQuery(ECC_Pawn);
    Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    return Objects;
}
}

AM07MagicAttack::AM07MagicAttack()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
    bReplicates = true;
    SetReplicateMovement(true);
    NetUpdateFrequency = 30.f;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("SpellRoot")));
    Core = CreateDefaultSubobject<UNiagaraComponent>(TEXT("FireCore"));
    Core->SetupAttachment(RootComponent); Core->SetAutoActivate(false); Core->SetCastShadow(false);
    Trail = CreateDefaultSubobject<UNiagaraComponent>(TEXT("FlightTrail"));
    Trail->SetupAttachment(RootComponent); Trail->SetAutoActivate(false); Trail->SetCastShadow(false);
    ColdMist = CreateDefaultSubobject<UNiagaraComponent>(TEXT("ColdMist"));
    ColdMist->SetupAttachment(RootComponent); ColdMist->SetAutoActivate(false); ColdMist->SetCastShadow(false);
    IceShell = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("IceShell"));
    IceShell->SetupAttachment(RootComponent); ConfigureSpellMesh(IceShell);
    IceHeart = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("IceHeart"));
    IceHeart->SetupAttachment(IceShell); ConfigureSpellMesh(IceHeart);
    SpellLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("SpellLight"));
    SpellLight->SetupAttachment(RootComponent); SpellLight->SetCastShadows(false);
    SpellLight->SetIntensity(0.f); SpellLight->SetAttenuationRadius(170.f);
    SpellLight->SetVolumetricScatteringIntensity(0.f); SpellLight->SetIndirectLightingIntensity(0.f);

    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> FireCoreSource(TEXT("/Game/Skills/Fireball/NS_FireballSlowBurnCore.NS_FireballSlowBurnCore"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> FireTrailSource(TEXT("/Game/Skills/Fireball/NS_FireballVelocityTrail.NS_FireballVelocityTrail"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> FireImpactSource(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic.NS_FireballImpactRealistic"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> WaveSource(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/M_FireballHeatShockwave.M_FireballHeatShockwave"));
    static ConstructorHelpers::FObjectFinder<USoundBase> FireSoundSource(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/S_FireballImpactLayered.S_FireballImpactLayered"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> IceSource(TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01.SM_IceSpike_01"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> ShardSource(TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> ShellSource(TEXT("/Game/Skills/IceSpike/FrostV2/M_IceShell.M_IceShell"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> HeartSource(TEXT("/Game/Skills/IceSpike/FrostV2/M_IceHeart.M_IceHeart"));
    static ConstructorHelpers::FObjectFinder<UParticleSystem> IceImpactSource(TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"));
    static ConstructorHelpers::FObjectFinder<USoundBase> IceSoundSource(TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> CrystalSource(TEXT("/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals.NS_FrostCrystals"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> MistSource(TEXT("/Game/Skills/IceSpike/FrostV2/NS_ColdMist.NS_ColdMist"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> ArcSource(TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> ChargeSource(TEXT("/Game/Skills/ElectricMagic/NS_ThunderCharge.NS_ThunderCharge"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> ElectricImpactSource(TEXT("/Game/Skills/ElectricMagic/NS_ElectricImpact.NS_ElectricImpact"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ElectricSoundSource(TEXT("/Game/Skills/Lightning/S_LightningCast1.S_LightningCast1"));
    FireCoreAsset = FireCoreSource.Object; FireTrailAsset = FireTrailSource.Object;
    FireImpactAsset = FireImpactSource.Object; FireWaveMaterial = WaveSource.Object; FireHitSound = FireSoundSource.Object;
    IceMesh = IceSource.Object; IceShardMesh = ShardSource.Object;
    IceShellMaterial = ShellSource.Object; IceHeartMaterial = HeartSource.Object;
    IceImpactAsset = IceImpactSource.Object; IceHitSound = IceSoundSource.Object;
    IceCrystalAsset = CrystalSource.Object; IceMistAsset = MistSource.Object;
    LightningArcAsset = ArcSource.Object; LightningChargeAsset = ChargeSource.Object;
    LightningImpactAsset = ElectricImpactSource.Object; LightningSound = ElectricSoundSource.Object;
}

UNiagaraSystem* AM07MagicAttack::ChargeSystem(EM07MagicElement Element)
{
    const auto* Defaults = GetDefault<AM07MagicAttack>();
    switch (Element)
    {
    case EM07MagicElement::Fireball: return Defaults->FireCoreAsset;
    case EM07MagicElement::IceColumn: return Defaults->IceCrystalAsset;
    case EM07MagicElement::Lightning: return Defaults->LightningChargeAsset;
    }
    return nullptr;
}

void AM07MagicAttack::ConfigureCharge(UNiagaraComponent* FX, EM07MagicElement Element, float Fraction)
{
    if (!FX) return;
    const float Amount = FMath::Clamp(Fraction, 0.f, 1.f);
    const float Grow = .22f + .62f * FMath::SmoothStep(0.f, 1.f, Amount);
    FX->SetRelativeScale3D(FVector(Grow));
    if (Element == EM07MagicElement::Fireball)
    {
        FX->SetVariableFloat(TEXT("User.Flight"), 0.f);
        FX->SetVariableFloat(TEXT("User.FlightAge"), 0.f);
    }
    else if (Element == EM07MagicElement::IceColumn)
    {
        const FVector Position = FX->GetComponentLocation();
        FX->SetVariablePosition(TEXT("User.PreviousPosition"), Position);
        FX->SetVariablePosition(TEXT("User.CurrentPosition"), Position);
        FX->SetVariableVec3(TEXT("User.FlightDirection"), FX->GetForwardVector());
        FX->SetVariableVec3(TEXT("User.Side"), FX->GetRightVector());
        FX->SetVariableVec3(TEXT("User.Up"), FX->GetUpVector());
        FX->SetVariableFloat(TEXT("User.Flight"), 0.f);
        FX->SetVariableFloat(TEXT("User.Strength"), .35f + .65f * Amount);
        FX->SetVariableFloat(TEXT("User.DetailReduction"), .45f);
        FX->SetVariableFloat(TEXT("User.ReleasePulse"), 0.f);
    }
    else FX->SetVariableFloat(TEXT("User.Charge"), Amount);
}

void AM07MagicAttack::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AM07MagicAttack, Presentation);
}

void AM07MagicAttack::Initialize(APawn* Caster, const FVector& AimPoint, EM07MagicElement Element,
    float Damage, float RangeCm, float ProjectileSpeedCmS, float ImpactRadiusCm)
{
    if (!HasAuthority() || Presentation.bInitialized) return;
    Shooter = Caster;
    ShooterCombat = IsValid(Caster) ? Caster->FindComponentByClass<UMonsterCombatComponent>() : nullptr;
    ShooterHealth = IsValid(Caster) ? Caster->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
    if (!CasterAlive()) { Destroy(); return; }
    SetOwner(Caster); SetInstigator(Caster);
    Presentation.Element = Element;
    Presentation.Start = GetActorLocation();
    FVector Direction = (AimPoint - GetActorLocation()).GetSafeNormal();
    if (Direction.IsNearlyZero()) Direction = Caster->GetActorForwardVector();
    Presentation.Direction = Direction;
    Presentation.Speed = FMath::Clamp(ProjectileSpeedCmS, 1.f, 10000.f);
    Presentation.Radius = FMath::Max(1.f, ImpactRadiusCm);
    HitDamage = FMath::Max(0.f, Damage);
    RemainingRange = FMath::Max(1.f, RangeCm);
    CollisionRadius = Element == EM07MagicElement::IceColumn ? Presentation.Radius : 16.f;
    Presentation.bInitialized = true;
    Caster->OnEndPlay.AddDynamic(this, &AM07MagicAttack::OnCasterEndPlay);
    if (Caster->ActorHasTag(TEXT("DevelopmentSpawned"))) Tags.Add(TEXT("DevelopmentSpawned"));
    if (HasActorBegunPlay()) BeginAttack();
}

void AM07MagicAttack::BeginPlay()
{
    Super::BeginPlay();
    if (Presentation.bInitialized)
    {
        if (Presentation.bResolved && !Presentation.bCancelled) PresentImpact();
        else if (!Presentation.bResolved) BeginAttack();
    }
}

bool AM07MagicAttack::CasterAlive() const
{
    if (!Shooter.IsValid() || Shooter->IsActorBeingDestroyed()) return false;
    if (ShooterCombat.IsValid() && ShooterCombat->IsDead()) return false;
    if (ShooterHealth.IsValid() && ShooterHealth->IsDead()) return false;
    return true;
}

bool AM07MagicAttack::IsHostilePlayer(APawn* Pawn) const
{
    if (!IsValid(Pawn) || Pawn == Shooter.Get() || !Pawn->IsPlayerControlled()) return false;
    if (Shooter.IsValid() && (Shooter->ActorHasTag(TEXT("Friendly")) || Shooter->ActorHasTag(TEXT("Summoned")))) return false;
    const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    return Health && !Health->IsDead();
}

bool AM07MagicAttack::FirstBlockingContact(const FVector& Start, const FVector& End, float Radius, FHitResult& Hit) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M07MagicFlight), false, this);
    if (Shooter.IsValid()) Query.AddIgnoredActor(Shooter.Get());
    TArray<FHitResult> Contacts;
    GetWorld()->SweepMultiByObjectType(Contacts, Start, End, FQuat::Identity, SpellObjectTypes(),
        FCollisionShape::MakeSphere(FMath::Max(.1f, Radius)), Query);
    bool bBlocked = false;
    for (const FHitResult& Contact : Contacts)
    {
        const auto* Component = Contact.GetComponent();
        const auto* Pawn = Cast<APawn>(Contact.GetActor());
        // FPS capsules ignore Visibility; overlap-only triggers and fog must not stop a spell.
        const bool bPlayerBody = Pawn && Pawn->IsPlayerControlled() && Component == Pawn->GetRootComponent();
        if (!Component || (!bPlayerBody && Component->GetCollisionResponseToChannel(ECC_Visibility) != ECR_Block)) continue;
        if (!bBlocked || Contact.Time < Hit.Time) { Hit = Contact; bBlocked = true; }
    }
    return bBlocked;
}

bool AM07MagicAttack::BlastVisible(APawn* Target, const FVector& Start, const FVector& End) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M07MagicBlastSight), false, this);
    Query.AddIgnoredActor(Target);
    if (Shooter.IsValid()) Query.AddIgnoredActor(Shooter.Get());
    FHitResult Blocker;
    return !GetWorld()->LineTraceSingleByChannel(Blocker, Start, End, ECC_Visibility, Query);
}

void AM07MagicAttack::BeginAttack()
{
    if (bStarted || !Presentation.bInitialized || Presentation.bResolved) return;
    bStarted = true;
    if (HasAuthority() && !CasterAlive()) { CancelUnresolved(); return; }
    SetActorRotation(FVector(Presentation.Direction).Rotation());
    PreviousVisualPosition = GetActorLocation();
    if (Presentation.Element == EM07MagicElement::Lightning)
    {
        if (HasAuthority())
        {
            FHitResult Hit;
            const FVector End = GetActorLocation() + FVector(Presentation.Direction) * RemainingRange;
            if (FirstBlockingContact(GetActorLocation(), End, .35f, Hit)) Resolve(&Hit);
            else { SetActorLocation(End); Resolve(nullptr); }
        }
        return;
    }
    PresentFlight();
    SetActorTickEnabled(true);
    if (HasAuthority()) SetLifeSpan(RemainingRange / Presentation.Speed + 1.1f);
    ForceNetUpdate();
}

void AM07MagicAttack::PresentFlight()
{
    if (bFlightPresented || Presentation.Element == EM07MagicElement::Lightning) return;
    bFlightPresented = true;
    if (GetNetMode() == NM_DedicatedServer) return;
    Core->AddTickPrerequisiteActor(this); Trail->AddTickPrerequisiteActor(this); ColdMist->AddTickPrerequisiteActor(this);
    if (Presentation.Element == EM07MagicElement::Fireball)
    {
        Core->SetAsset(FireCoreAsset); Core->SetRelativeScale3D(FVector(.82f));
        Core->SetVariableFloat(TEXT("User.Flight"), 1.f); Core->SetVariableFloat(TEXT("User.FlightAge"), 0.f);
        Trail->SetAsset(FireTrailAsset);
        SpellLight->SetLightColor(FLinearColor(1.f, .24f, .035f)); SpellLight->SetIntensity(300.f);
        Core->Activate(true);
    }
    else
    {
        IceShell->SetStaticMesh(IceMesh); IceShell->SetMaterial(0, IceShellMaterial);
        IceHeart->SetStaticMesh(IceMesh); IceHeart->SetMaterial(0, IceHeartMaterial);
        const FVector Scale(1.55f, .92f, .92f);
        IceShell->SetRelativeScale3D(Scale);
        if (IceMesh) IceShell->SetRelativeLocation(-IceMesh->GetBounds().Origin * Scale);
        IceHeart->SetRelativeScale3D(FVector(.965f, .78f, .78f));
        IceShell->SetVisibility(true); IceHeart->SetVisibility(true);
        Trail->SetAsset(IceCrystalAsset); ColdMist->SetAsset(IceMistAsset);
        ColdMist->Activate(true);
    }
    UpdateFlightPresentation(0.f, GetActorLocation());
    Trail->Activate(true);
}

void AM07MagicAttack::UpdateFlightPresentation(float DeltaSeconds, const FVector& PreviousPosition)
{
    if (GetNetMode() == NM_DedicatedServer) return;
    FlightAge += DeltaSeconds;
    const FVector Direction = Presentation.Direction;
    Trail->SetVariablePosition(TEXT("User.PreviousPosition"), PreviousPosition);
    Trail->SetVariablePosition(TEXT("User.CurrentPosition"), GetActorLocation());
    Trail->SetVariableVec3(TEXT("User.FlightDirection"), Direction);
    Trail->SetVariableFloat(TEXT("User.FlightSpeed"), Presentation.Speed);
    if (Presentation.Element == EM07MagicElement::Fireball)
    {
        Core->SetVariableFloat(TEXT("User.FlightAge"), FlightAge);
        return;
    }
    for (auto* FX : {Trail.Get(), ColdMist.Get()})
    {
        FX->SetVariablePosition(TEXT("User.PreviousPosition"), PreviousPosition);
        FX->SetVariablePosition(TEXT("User.CurrentPosition"), GetActorLocation());
        FX->SetVariableVec3(TEXT("User.FlightDirection"), Direction);
        FX->SetVariableVec3(TEXT("User.Side"), GetActorRightVector());
        FX->SetVariableVec3(TEXT("User.Up"), GetActorUpVector());
        FX->SetVariableFloat(TEXT("User.Flight"), 1.f);
        FX->SetVariableFloat(TEXT("User.Strength"), .65f);
        FX->SetVariableFloat(TEXT("User.ReleasePulse"), FMath::Clamp(1.f - FlightAge / .16f, 0.f, 1.f));
    }
    if (FlightAge >= NextEnvironmentUpdate)
    {
        if (auto* Budget = GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
        {
            const int32 Granted = Budget->AllocateDetail(GetActorLocation(), 3, false);
            ColdMist->SetVariableFloat(TEXT("User.DetailReduction"), 1.f - float(Granted) / 3.f);
            ColdMist->SetVariableVec3(TEXT("User.Wind"), Budget->WindAt(GetActorLocation()) * .25f);
        }
        NextEnvironmentUpdate = FlightAge + .1f;
    }
}

void AM07MagicAttack::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!Presentation.bInitialized || Presentation.bResolved) return;
    const FVector Start = GetActorLocation();
    if (HasAuthority())
    {
        // Like the existing enemy venom projectile, an unhit released spell cancels on death.
        if (!CasterAlive()) { CancelUnresolved(); return; }
        const float Step = FMath::Min(RemainingRange, Presentation.Speed * FMath::Max(0.f, DeltaSeconds));
        const FVector End = Start + FVector(Presentation.Direction) * Step;
        FHitResult Hit;
        if (FirstBlockingContact(Start, End, CollisionRadius, Hit))
        {
            SetActorLocation(Hit.Location);
            UpdateFlightPresentation(DeltaSeconds * Hit.Time, Start);
            Resolve(&Hit); return;
        }
        SetActorLocation(End); RemainingRange -= Step;
        UpdateFlightPresentation(DeltaSeconds, Start);
        if (RemainingRange <= UE_KINDA_SMALL_NUMBER) { Resolve(nullptr); return; }
    }
    else UpdateFlightPresentation(DeltaSeconds, PreviousVisualPosition);
    PreviousVisualPosition = GetActorLocation();
}

void AM07MagicAttack::ApplyPlayerHit(APawn* Target, const FHitResult& Hit, const FVector& IncomingDirection)
{
    if (!HasAuthority() || !CasterAlive() || !IsHostilePlayer(Target) || HitPlayers.Contains(Target)) return;
    HitPlayers.Add(Target);
    TSubclassOf<UDamageType> DamageType = UFireballDamage::StaticClass();
    if (Presentation.Element == EM07MagicElement::IceColumn) DamageType = UIceSpikeDamage::StaticClass();
    else if (Presentation.Element == EM07MagicElement::Lightning) DamageType = ULightningDamage::StaticClass();
    // Point delivery identifies a ranged enemy hit to the player's existing dodge route,
    // while the elemental type selects mdef and the electric status multiplier exactly once.
    UGameplayStatics::ApplyPointDamage(Target, HitDamage, IncomingDirection, Hit,
        Shooter->GetController(), Shooter.Get(), DamageType);
}

void AM07MagicAttack::Resolve(const FHitResult* Hit)
{
    if (!HasAuthority() || Presentation.bResolved) return;
    Presentation.bResolved = true;
    Presentation.bSurfaceHit = Hit != nullptr;
    Presentation.Impact = Hit ? FVector(Hit->ImpactPoint) : GetActorLocation();
    const FVector Normal = Hit ? Hit->ImpactNormal.GetSafeNormal() : -FVector(Presentation.Direction);
    Presentation.Normal = Normal.IsNearlyZero() ? FVector::UpVector : Normal;
    SetActorTickEnabled(false);
    if (CasterAlive())
    {
        if (Hit) ApplyPlayerHit(Cast<APawn>(Hit->GetActor()), *Hit, Presentation.Direction);
        if (Presentation.Element == EM07MagicElement::Fireball)
        {
            // At most one pass per connected player, after the direct-hit dedup entry.
            const FVector Center = Presentation.Impact;
            const FVector SightStart = Center + FVector(Presentation.Normal) * 3.f;
            for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            {
                const auto* Controller = It->Get();
                APawn* Target = Controller ? Controller->GetPawn() : nullptr;
                if (!IsHostilePlayer(Target) || HitPlayers.Contains(Target)) continue;
                FVector TargetPoint = Target->GetActorLocation();
                if (const auto* Capsule = Target->FindComponentByClass<UCapsuleComponent>())
                {
                    const FVector CapsuleCenter = Capsule->GetComponentLocation();
                    const float AxisHalf = FMath::Max(0.f, Capsule->GetScaledCapsuleHalfHeight() - Capsule->GetScaledCapsuleRadius());
                    TargetPoint = CapsuleCenter;
                    TargetPoint.Z = FMath::Clamp(Center.Z, CapsuleCenter.Z - AxisHalf, CapsuleCenter.Z + AxisHalf);
                    const FVector Toward = (Center - TargetPoint).GetSafeNormal();
                    TargetPoint += Toward * FMath::Min(float(FVector::Distance(Center, TargetPoint)), Capsule->GetScaledCapsuleRadius());
                }
                if (FVector::DistSquared(Center, TargetPoint) > FMath::Square(Presentation.Radius)
                    || !BlastVisible(Target, SightStart, TargetPoint)) continue;
                FHitResult Splash(Target, Cast<UPrimitiveComponent>(Target->GetRootComponent()), TargetPoint, (TargetPoint - Center).GetSafeNormal());
                ApplyPlayerHit(Target, Splash, (TargetPoint - Center).GetSafeNormal());
            }
        }
    }
    PresentImpact(); ForceNetUpdate();
    SetLifeSpan(Presentation.Element == EM07MagicElement::Lightning ? .85f : .9f);
}

void AM07MagicAttack::PresentImpact()
{
    if (bImpactPresented || Presentation.bCancelled) return;
    bImpactPresented = true;
    if (GetNetMode() == NM_DedicatedServer) return;
    Core->DeactivateImmediate(); Trail->Deactivate(); ColdMist->SetVariableFloat(TEXT("User.Strength"), 0.f); ColdMist->Deactivate();
    IceShell->SetVisibility(false); IceHeart->SetVisibility(false); SpellLight->SetIntensity(0.f);
    const FVector Position = Presentation.Impact;
    const FVector Normal = Presentation.Normal;
    const FRotator Facing = FRotationMatrix::MakeFromZ(Normal).Rotator();
    if (Presentation.Element == EM07MagicElement::Fireball)
    {
        // Keep the current player's authored impact footprint and Niagara growth contract.
        const float Scale = FMath::Clamp(Presentation.Radius / 210.375f, .3f, 1.5f);
        if (auto* FX = UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, FireImpactAsset,
            Position + Normal * 8.f, Facing, FVector(Scale * .765f), true, false, ENCPoolMethod::AutoRelease))
        {
            FX->SetVariableFloat(TEXT("User.SurfaceHit"), Presentation.bSurfaceHit ? 1.f : 0.f);
            FX->SetVariableVec3(TEXT("User.LocalUp"), Facing.UnrotateVector(FVector::UpVector));
            FX->SetVariableFloat(TEXT("User.ImpactGrowth"), Scale - 1.f);
            if (auto* Budget = GetWorld()->GetSubsystem<UFluidPresentationSubsystem>()) Budget->ConfigureSmoke(FX, 4, false);
            FX->Activate(true);
        }
        if (FireWaveMaterial)
            if (auto* Wave = GetWorld()->SpawnActor<AFireballShockwave>(Position + Normal * 4.f, Facing))
                Wave->Setup(FireWaveMaterial, Presentation.Radius, Presentation.bSurfaceHit);
        if (FireHitSound) UGameplayStatics::PlaySoundAtLocation(this, FireHitSound, Position, .65f);
    }
    else if (Presentation.Element == EM07MagicElement::IceColumn)
    {
        // Reaching the range limit without contact quietly removes the ice, like the player volley.
        if (!Presentation.bSurfaceHit) return;
        if (auto* Budget = GetWorld()->GetSubsystem<UFluidPresentationSubsystem>()) Budget->EmitColdImpact(Position, Normal);
        if (IceImpactAsset) UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), IceImpactAsset,
            Position, Facing, FVector(.7f), true, EPSCPoolMethod::AutoRelease);
        if (IceShardMesh && IceHeartMaterial)
            if (auto* Shards = GetWorld()->SpawnActor<AFPSIceSpikeFragments>(Position, FRotator::ZeroRotator))
                Shards->Setup(IceShardMesh, IceHeartMaterial, Normal);
        if (IceHitSound) UGameplayStatics::PlaySoundAtLocation(this, IceHitSound, Position, .65f);
    }
    else
    {
        FLightningCast Spell; Spell.Duration = .24f; Spell.Fade = .17f; Spell.Segments = 10; Spell.Jitter = .065f;
        if (auto* Arc = GetWorld()->SpawnActor<AFPSLightningArc>(Presentation.Start, FRotator::ZeroRotator))
            Arc->InitializeArc(LightningArcAsset, Presentation.Start, Position, Spell, .5f, true, 50.f);
        if (Presentation.bSurfaceHit && LightningImpactAsset)
            UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, LightningImpactAsset, Position, Facing, FVector(.5f), true, true, ENCPoolMethod::AutoRelease);
        if (LightningSound) UGameplayStatics::PlaySoundAtLocation(this, LightningSound, Presentation.Start, .65f);
    }
}

void AM07MagicAttack::OnRep_Presentation()
{
    if (!Presentation.bInitialized) return;
    if (Presentation.bCancelled) { Core->DeactivateImmediate(); Trail->DeactivateImmediate(); ColdMist->DeactivateImmediate(); SetActorTickEnabled(false); return; }
    if (Presentation.bResolved) { SetActorTickEnabled(false); PresentImpact(); return; }
    BeginAttack();
}

void AM07MagicAttack::CancelUnresolved()
{
    if (Presentation.bResolved) return;
    Presentation.bCancelled = true; Presentation.bResolved = true;
    Core->DeactivateImmediate(); Trail->DeactivateImmediate(); ColdMist->DeactivateImmediate();
    SpellLight->SetIntensity(0.f); SetActorTickEnabled(false); Destroy();
}

void AM07MagicAttack::OnCasterEndPlay(AActor* Actor, EEndPlayReason::Type Reason)
{
    CancelUnresolved();
}

void AM07MagicAttack::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Shooter.IsValid()) Shooter->OnEndPlay.RemoveDynamic(this, &AM07MagicAttack::OnCasterEndPlay);
    Core->DeactivateImmediate(); Trail->DeactivateImmediate(); ColdMist->DeactivateImmediate();
    Super::EndPlay(Reason);
}
