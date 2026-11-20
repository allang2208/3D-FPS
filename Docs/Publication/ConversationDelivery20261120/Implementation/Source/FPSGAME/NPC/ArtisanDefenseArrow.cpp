#include "ArtisanDefenseArrow.h"
#include "../Combat/MonsterToughnessTypes.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

AArtisanDefenseArrow::AArtisanDefenseArrow()
{
    bReplicates = true;
    SetReplicateMovement(true);
    SetNetUpdateFrequency(60.f);
    PrimaryActorTick.bCanEverTick = true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Tip")));
    Shaft = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WoodenArrow"));
    Shaft->SetupAttachment(GetRootComponent());
    Shaft->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Shaft->SetCanEverAffectNavigation(false);
}

void AArtisanDefenseArrow::FitWoodArrow(UStaticMeshComponent& Mesh, const FVector& Tail, const FVector& Tip)
{
    if (!Mesh.GetStaticMesh()) return;
    const FBoxSphereBounds Bounds = Mesh.GetStaticMesh()->GetBounds();
    const bool bAlongX = Bounds.BoxExtent.X > Bounds.BoxExtent.Z;
    const FVector Axis = bAlongX ? FVector::XAxisVector : FVector::ZAxisVector;
    const float Length = FVector::Distance(Tip, Tail);
    const float Scale = Length / FMath::Max(0.01, 2. * FVector::DotProduct(Bounds.BoxExtent, Axis));
    const FVector Scale3D = bAlongX ? FVector(Scale, 1, 1) : FVector(1, 1, Scale);
    const FQuat Rotation = FQuat::FindBetweenNormals(Axis, (Tip - Tail).GetSafeNormal());
    const FVector Center = Axis * FVector::DotProduct(Bounds.Origin, Axis);
    Mesh.SetRelativeTransform(FTransform(Rotation, (Tip + Tail) * .5 - Rotation.RotateVector(Center * Scale3D), Scale3D));
}

void AArtisanDefenseArrow::BeginPlay()
{
    Super::BeginPlay();
    if (GetNetMode() != NM_DedicatedServer)
    {
        Shaft->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,
            TEXT("/Game/Weapons/DarkBow20260925/ArmsV2/SM_Bow_WoodArrow.SM_Bow_WoodArrow")));
        FitWoodArrow(*Shaft, FVector(-76, 0, 0), FVector::ZeroVector);
    }
    SetActorTickEnabled(HasAuthority());
}

void AArtisanDefenseArrow::Launch(const FVector& Direction, float Damage)
{
    Velocity = Direction * 9800.f;
    HitDamage = Damage;
    SetLifeSpan(3200.f / 9800.f);
    ForceNetUpdate();
}

void AArtisanDefenseArrow::Tick(float Dt)
{
    Super::Tick(Dt);
    if (!HasAuthority() || Velocity.IsNearlyZero()) return;
    const FVector Start = GetActorLocation();
    const FVector Gravity(0, 0, -520);
    const FVector End = Start + Velocity * Dt + Gravity * (.5f * Dt * Dt);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ArtisanWoodArrow), false, GetOwner());
    Query.AddIgnoredActor(this);
    FHitResult Hit;
    if (!RangedAttackQuery::SweepSingle(GetWorld(), GetOwner(), Hit, Start, End, FQuat::Identity, ECC_Visibility,
            FCollisionShape::MakeSphere(.8f), Query))
    {
        Velocity += Gravity * Dt;
        SetActorLocationAndRotation(End, Velocity.Rotation());
        return;
    }
    SetActorLocation(Hit.ImpactPoint);
    if (UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(), GetOwner()))
    {
        const MonsterToughness::FScopedForm Form(EMonsterAttackForm::Blade);
        UGameplayStatics::ApplyPointDamage(Hit.GetActor(), HitDamage, Velocity.GetSafeNormal(), Hit,
            GetInstigatorController(), GetOwner(), UBladeToughnessDamage::StaticClass());
    }
    Velocity = FVector::ZeroVector;
    SetActorTickEnabled(false);
    ForceNetUpdate();
    SetLifeSpan(.7f);
}
