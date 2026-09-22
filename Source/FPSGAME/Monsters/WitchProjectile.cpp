#include "WitchProjectile.h"
#include "WitchMonster.h"
#include "PoisonMaggotVenomFX.h"
#include "FPSCombatHealthComponent.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

AWitchProjectile::AWitchProjectile()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("SpellRoot"));
    Visual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SpellVisual"));
    Visual->SetupAttachment(RootComponent);
    Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Visual->SetGenerateOverlapEvents(false); Visual->SetCanEverAffectNavigation(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Liquid(TEXT("/Game/Monsters/PoisonMaggot/VenomLiquid20260915/M_VenomLiquid.M_VenomLiquid"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Core(TEXT("/Game/Monsters/PoisonMaggot/VenomLiquid20260915/M_VenomCore.M_VenomCore"));
    Visual->SetStaticMesh(Sphere.Object); Visual->SetMaterial(0, Liquid.Object);
    Visual->SetRelativeScale3D(FVector(.14f,.105f,.105f)); Visual->SetCastShadow(false);
    Visual->bReceivesDecals = false; Visual->bAffectDistanceFieldLighting = false;
    Visual->SetBoundsScale(1.15f);
    LiquidCore = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VenomOpaqueCore"));
    LiquidCore->SetupAttachment(Visual);
    LiquidCore->SetStaticMesh(Sphere.Object); LiquidCore->SetMaterial(0, Core.Object);
    LiquidCore->SetRelativeScale3D(FVector(.8f,.78f,.78f));
    LiquidCore->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    LiquidCore->SetGenerateOverlapEvents(false); LiquidCore->SetCanEverAffectNavigation(false);
    LiquidCore->SetCastShadow(false); LiquidCore->bReceivesDecals = false;
    LiquidCore->bAffectDistanceFieldLighting = false;
    LiquidCore->SetVisibility(false);
}

void AWitchProjectile::Launch(AWitchMonster* Source, bool Bottle, FVector Destination, float Speed, float Damage, float Radius)
{
    Shooter = Source; bBottle = Bottle; Origin = GetActorLocation(); Goal = Destination;
    HitDamage = Damage; PoolRadius = Radius;
    if (Source->ActorHasTag(TEXT("DevelopmentSpawned"))) Tags.Add(TEXT("DevelopmentSpawned"));
    if (bBottle)
    {
        FHitResult Ground; FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchBottleLanding), false, Source);
        if (auto* Target = UGameplayStatics::GetPlayerPawn(this, 0)) Query.AddIgnoredActor(Target);
        if (GetWorld()->LineTraceSingleByChannel(Ground, Goal + FVector(0,0,100), Goal - FVector(0,0,500), ECC_Visibility, Query)) Goal = Ground.ImpactPoint;
        if (Source->Bottle->GetStaticMesh())
        {
            const FTransform Held = Source->Bottle->GetComponentTransform();
            const FVector Center = Source->Bottle->GetStaticMesh()->GetBounds().Origin;
            Origin = Held.TransformPosition(Center);
            BottleReleaseRotation = Held.GetRotation();
            SetActorTransform(FTransform(BottleReleaseRotation, Origin));
            Visual->SetStaticMesh(Source->Bottle->GetStaticMesh());
            // The actor sweeps around the bottle's center. Its visible mesh retains
            // exactly the held transform, including the authored bottom pivot/scale.
            Visual->SetRelativeTransform(FTransform(FQuat::Identity,
                -Center * Held.GetScale3D(), Held.GetScale3D()));
            for (int32 Index = 0; Index < Source->Bottle->GetNumMaterials(); ++Index)
                Visual->SetMaterial(Index, Source->Bottle->GetMaterial(Index));
        }
        const FVector Direction = (Goal - Origin).GetSafeNormal2D();
        BottleSpinAxis = Direction.IsNearlyZero() ? Source->GetActorRightVector()
            : FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
        SetLifeSpan(8.f);
    }
    else
    {
        Velocity = (Goal - Origin).GetSafeNormal() * Speed;
        // Cosmetic phase does not consume the combat spread/poison random stream.
        FRandomStream CosmeticRandom{int32(GetUniqueID())};
        LiquidPhase = CosmeticRandom.FRand() * 2.f * PI;
        LiquidCore->SetVisibility(true);
        SetActorRotation(Velocity.Rotation());
        SetLifeSpan(1000.f / FMath::Max(1.f, Speed));
    }
}

void AWitchProjectile::UpdateLiquidVisual(float DeltaTime, const FVector& Start, const FVector& End)
{
    const float PreviousAge = LiquidAge;
    LiquidAge += DeltaTime;
    const float Stretch = 1.f + .09f * FMath::Sin(LiquidAge * 17.f + LiquidPhase);
    const float Width = 1.f / FMath::Sqrt(Stretch);
    Visual->SetRelativeScale3D(FVector(.14f * Stretch, .105f * Width, .105f * Width));
    FRotator Direction = Velocity.Rotation();
    Direction.Roll = FMath::RadiansToDegrees(LiquidPhase) + LiquidAge * 48.f;
    SetActorRotation(Direction);
    LiquidCore->SetRelativeScale3D(FVector(.8f, .78f + .025f * FMath::Sin(LiquidAge * 11.f + LiquidPhase), .78f));
    auto* FX = GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>();
    if (!FX) return;
    // Share the maggot's bounded fragment pool. Sample the traveled segment so
    // a slow frame does not stack droplets at the endpoint or beyond a hit.
    int32 Emitted = 0;
    while (NextTrail <= LiquidAge && Emitted < 4)
    {
        const float Alpha = DeltaTime > UE_SMALL_NUMBER ? FMath::Clamp((NextTrail - PreviousAge) / DeltaTime, 0.f, 1.f) : 1.f;
        FX->AddTrail(FMath::Lerp(Start, End, Alpha), Velocity, (TrailCount++ % 3) == 0);
        NextTrail += .065f;
        ++Emitted;
    }
    if (NextTrail <= LiquidAge) NextTrail = LiquidAge + .065f;
}

void AWitchProjectile::Land(FVector Position, FVector Normal)
{
    if (Normal.Z < .65f) { Destroy(); return; }
    LiquidCore->SetVisibility(false);
    bPool = true; Age = 0.f; NextPulse = .5f;
    SetActorLocation(Position + Normal * 2.f); SetActorRotation(FRotationMatrix::MakeFromZ(Normal).Rotator());
    Visual->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere")));
    Visual->SetMaterial(0, LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Monsters/PoisonMaggot/VenomLiquid20260915/M_VenomLiquid.M_VenomLiquid")));
    Visual->SetRelativeTransform(FTransform(FQuat::Identity, FVector::ZeroVector, FVector(.04f, .04f, .016f)));
    SetLifeSpan(6.f + .05f);
}

void AWitchProjectile::Pulse()
{
    if (!Shooter.IsValid()) return;
    for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        APawn* Player = It->IsValid() ? It->Get()->GetPawn() : nullptr;
        auto* Health = Player ? Player->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
        if (!Health || Health->IsDead() || Health->IsInvulnerable()) continue;
        const FVector Feet = Player->GetActorLocation() - FVector(0,0,Player->GetSimpleCollisionHalfHeight());
        if (FVector::DistSquared2D(Feet, GetActorLocation()) > FMath::Square(PoolRadius)
            || FMath::Abs(Feet.Z - GetActorLocation().Z) > 50.f) continue;
        FHitResult Wall; FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchPoisonOcclusion), false, this);
        Query.AddIgnoredActor(Shooter.Get()); Query.AddIgnoredActor(Player);
        if (GetWorld()->LineTraceSingleByChannel(Wall, GetActorLocation() + FVector(0,0,15), Feet + FVector(0,0,15), ECC_Visibility, Query)) continue;
        const float Applied = UGameplayStatics::ApplyDamage(Player, HitDamage, Shooter->GetController(), Shooter.Get(), UWitchMagicDamage::StaticClass());
        if (Applied > 0 && !Health->IsDead())
        {
            auto* Poison = Player->FindComponentByClass<UColdSteelPoisonComponent>();
            if (!Poison) { Poison = NewObject<UColdSteelPoisonComponent>(Player); Player->AddInstanceComponent(Poison); Poison->RegisterComponent(); }
            Poison->AddStacks(Shooter.Get(), 1);
        }
    }
}

void AWitchProjectile::Tick(float Delta)
{
    Super::Tick(Delta); if (!HasAuthority()) return;
    if (!Shooter.IsValid()) { Destroy(); return; }
    Age += Delta;
    if (bPool)
    {
        const float Scale = PoolRadius / 50.f * FMath::Clamp(Age / .3f, .01f, 1.f);
        Visual->SetRelativeScale3D(FVector(Scale, Scale, .016f));
        while (NextPulse <= 6.f && Age >= NextPulse) { Pulse(); NextPulse += .5f; }
        if (Age >= 6.f) Destroy();
        return;
    }
    if (Shooter->State == ENurseState::Dead) { Destroy(); return; }
    const FVector Start = GetActorLocation();
    constexpr float FlightSeconds = 1.5f, ArcHeight = 100.f;
    const float Phase = FMath::Clamp(Age / FlightSeconds, 0.f, 1.f);
    FVector End = Start + Velocity * Delta;
    if (bBottle)
    {
        End = FMath::Lerp(Origin, Goal, Phase) + FVector(0,0,4.f * ArcHeight * Phase * (1-Phase));
        if (Age > FlightSeconds)
        {
            // Missing/moving ground is not a landing. Continue from the arc's
            // end velocity until a real swept contact or the lifetime expires.
            const float FallSeconds = Age - FlightSeconds;
            const FVector EndVelocity = (Goal - Origin - FVector(0,0,4.f * ArcHeight)) / FlightSeconds;
            End += EndVelocity * FallSeconds + FVector(0,0,.5f * GetWorld()->GetGravityZ() * FMath::Square(FallSeconds));
        }
    }
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchSpellCollision), false, this); Query.AddIgnoredActor(Shooter.Get());
    FCollisionObjectQueryParams Objects; Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic); Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FHitResult> Contacts; GetWorld()->SweepMultiByObjectType(Contacts, Start, End, FQuat::Identity, Objects, FCollisionShape::MakeSphere(5.f), Query);
    const FHitResult* First = nullptr;
    for (const auto& Hit : Contacts)
    {
        const auto* Part = Hit.GetComponent(); const auto* Pawn = Cast<APawn>(Hit.GetActor());
        const bool Player = Pawn && Pawn->IsPlayerControlled() && Part == Pawn->GetRootComponent();
        if (Part && (Player || Part->GetCollisionResponseToChannel(ECC_Visibility) == ECR_Block)
            && (!First || Hit.Time < First->Time)) First = &Hit;
    }
    if (First)
    {
        if (bBottle)
        {
            if (Cast<APawn>(First->GetActor()))
            {
                FHitResult Ground; auto GroundQuery = Query; GroundQuery.AddIgnoredActor(First->GetActor());
                if (GetWorld()->LineTraceSingleByChannel(Ground, First->ImpactPoint, First->ImpactPoint - FVector(0,0,300), ECC_Visibility, GroundQuery)) Land(Ground.ImpactPoint, Ground.ImpactNormal);
                else Destroy();
            }
            else Land(First->ImpactPoint, First->ImpactNormal);
        }
        else
        {
            UpdateLiquidVisual(Delta * First->Time, Start, First->Location);
            if (auto* FX = GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>()) FX->AddImpact(*First, Velocity);
            if (auto* Pawn = Cast<APawn>(First->GetActor())) if (Pawn->IsPlayerControlled())
                UGameplayStatics::ApplyDamage(Pawn, HitDamage, Shooter->GetController(), Shooter.Get(), UWitchMagicDamage::StaticClass());
            Destroy();
        }
        return;
    }
    SetActorLocation(End);
    if (bBottle)
        SetActorRotation(FQuat(BottleSpinAxis, FMath::DegreesToRadians(Age * 360.f)) * BottleReleaseRotation);
    else UpdateLiquidVisual(Delta, Start, End);
}
