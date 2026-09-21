#include "WitchProjectile.h"
#include "WitchMonster.h"
#include "FPSCombatHealthComponent.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "Components/StaticMeshComponent.h"
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
    Visual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SpellVisual")); RootComponent = Visual;
    Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Visual->SetGenerateOverlapEvents(false); Visual->SetCanEverAffectNavigation(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Liquid(TEXT("/Game/Monsters/PoisonMaggot/VenomLiquid20260915/M_VenomCore.M_VenomCore"));
    Visual->SetStaticMesh(Sphere.Object); Visual->SetMaterial(0, Liquid.Object);
    Visual->SetRelativeScale3D(FVector(.14f)); Visual->SetCastShadow(false);
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
            Visual->SetStaticMesh(Source->Bottle->GetStaticMesh()); Visual->SetRelativeScale3D(FVector(1));
            for (int32 Index = 0; Index < Source->Bottle->GetNumMaterials(); ++Index)
                Visual->SetMaterial(Index, Source->Bottle->GetMaterial(Index));
        }
        SetLifeSpan(8.f);
    }
    else { Velocity = (Goal - Origin).GetSafeNormal() * Speed; SetLifeSpan(1000.f / FMath::Max(1.f, Speed)); }
}

void AWitchProjectile::Land(FVector Position, FVector Normal)
{
    if (Normal.Z < .65f) { Destroy(); return; }
    bPool = true; Age = 0.f; NextPulse = .5f;
    SetActorLocation(Position + Normal * 2.f); SetActorRotation(FRotationMatrix::MakeFromZ(Normal).Rotator());
    Visual->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere")));
    Visual->SetMaterial(0, LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Monsters/PoisonMaggot/VenomLiquid20260915/M_VenomLiquid.M_VenomLiquid")));
    Visual->SetRelativeScale3D(FVector(.04f, .04f, .016f)); SetLifeSpan(6.f + .05f);
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
    const float Phase = FMath::Clamp(Age / 1.5f, 0.f, 1.f);
    const FVector End = bBottle ? FMath::Lerp(Origin, Goal, Phase) + FVector(0,0,4.f * 100.f * Phase * (1-Phase)) : Start + Velocity * Delta;
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
            if (auto* Pawn = Cast<APawn>(First->GetActor())) if (Pawn->IsPlayerControlled())
                UGameplayStatics::ApplyDamage(Pawn, HitDamage, Shooter->GetController(), Shooter.Get(), UWitchMagicDamage::StaticClass());
            Destroy();
        }
        return;
    }
    SetActorLocation(End);
    if (bBottle) { SetActorRotation(FRotator(Age * 360.f, 0, 0)); if (Phase >= 1.f) Land(Goal, FVector::UpVector); }
}
