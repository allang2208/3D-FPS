#include "VillagePortcullisHoist.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

namespace
{
    const FSoftObjectPath LinkPath(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/Hoist/SM_HoistLink.SM_HoistLink"));
    const FSoftObjectPath SheavePath(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/Hoist/SM_HoistSheave.SM_HoistSheave"));
    const FSoftObjectPath WeightPath(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/Hoist/SM_HoistWeight.SM_HoistWeight"));
    const FSoftObjectPath BearingPath(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/Hoist/SM_HoistBearing.SM_HoistBearing"));

    constexpr float Radius = 16.f;
    constexpr float InnerAxleY = Radius; // tangent at Y=0 runs through the leaf's eyes
    constexpr float OuterAxleY = 153.f;
    constexpr float OverheadSpan = OuterAxleY - InnerAxleY;
    constexpr float QuarterArc = .5f * UE_PI * Radius;
    constexpr float ClosedReturn = 12.f;

    // Signed distance along the U-shaped reeving, measured from the first sheave.
    void AlongChain(float S, float& Y, float& RelativeZ, float& Turn)
    {
        if (S <= 0.f)
        {
            Y = 0.f;
            RelativeZ = S;
            Turn = 0.f;
        }
        else if (S < QuarterArc)
        {
            Turn = S / Radius;
            Y = InnerAxleY - Radius * FMath::Cos(Turn);
            RelativeZ = Radius * FMath::Sin(Turn);
        }
        else if (S <= QuarterArc + OverheadSpan)
        {
            Turn = .5f * UE_PI;
            Y = InnerAxleY + S - QuarterArc;
            RelativeZ = Radius;
        }
        else if (S < 2.f * QuarterArc + OverheadSpan)
        {
            Turn = .5f * UE_PI + (S - QuarterArc - OverheadSpan) / Radius;
            Y = OuterAxleY - Radius * FMath::Cos(Turn);
            RelativeZ = Radius * FMath::Sin(Turn);
        }
        else
        {
            Turn = UE_PI;
            Y = OuterAxleY + Radius;
            RelativeZ = 2.f * QuarterArc + OverheadSpan - S;
        }
    }

    void ApplyBatch(UInstancedStaticMeshComponent& Batch, const TArray<FTransform>& Poses)
    {
        if (Batch.GetInstanceCount() == 0)
            Batch.AddInstances(Poses, false, false, false);
        else
            // UE tracks the dirty instances internally. Preserve the scene proxy.
            Batch.BatchUpdateInstancesTransforms(0, Poses, false, false, false);
    }
}

UVillagePortcullisHoist::UVillagePortcullisHoist()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
}

void UVillagePortcullisHoist::AddAssetPaths(TArray<FSoftObjectPath>& Paths)
{
    for (const auto* Path : {&LinkPath, &SheavePath, &WeightPath, &BearingPath}) Paths.AddUnique(*Path);
}

bool UVillagePortcullisHoist::AssetsReady()
{
    return LinkPath.ResolveObject() && SheavePath.ResolveObject() && WeightPath.ResolveObject() && BearingPath.ResolveObject();
}

UInstancedStaticMeshComponent* UVillagePortcullisHoist::CreateBatch(UStaticMesh* Mesh)
{
    AActor* Gate = GetOwner();
    auto* Batch = NewObject<UInstancedStaticMeshComponent>(Gate, NAME_None, RF_Transient);
    Batch->SetupAttachment(Gate->GetRootComponent());
    Batch->SetMobility(EComponentMobility::Movable);
    Batch->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Batch->SetGenerateOverlapEvents(false);
    Batch->SetCanEverAffectNavigation(false);
    Batch->SetStaticMesh(Mesh);
    Batch->RegisterComponent();
    return Batch;
}

void UVillagePortcullisHoist::Initialize(bool bWest)
{
    // First link crosses the actual Meshy eye in the YZ plane. The narrower
    // eastern leaf was cut at the centre, shifting each eye inwards by 100 cm.
    EyeX = bWest ? 265.f : 165.f;
    EyeZ = bWest ? 498.f : 478.f;
    AxleZ = bWest ? 1030.f : 990.f;
    Travel = bWest ? 500.f : 480.f;
    const float Length = AxleZ - EyeZ + 2.f * QuarterArc + OverheadSpan + ClosedReturn;
    LinksPerRun = FMath::RoundToInt(Length / 11.5f) + 1;
    LinkPitch = Length / (LinksPerRun - 1);
    LinkPoses.SetNum(2 * LinksPerRun);
    WheelPoses.SetNum(4);
    WeightPoses.SetNum(2);
    Chains = CreateBatch(CastChecked<UStaticMesh>(LinkPath.ResolveObject()));
    Wheels = CreateBatch(CastChecked<UStaticMesh>(SheavePath.ResolveObject()));
    Weights = CreateBatch(CastChecked<UStaticMesh>(WeightPath.ResolveObject()));
    Bearings = CreateBatch(CastChecked<UStaticMesh>(BearingPath.ResolveObject()));
    for (const float X : {-EyeX, EyeX})
        Bearings->AddInstance(FTransform(FVector(X, 0.f, AxleZ)));
}

void UVillagePortcullisHoist::Draw(float Height)
{
    Height = FMath::Clamp(Height, 0.f, Travel);
    if (LastLift == Height) return;
    LastLift = Height;
    const FQuat CrossLink(FVector::UpVector, .5f * UE_PI);
    for (int32 Link = 0; Link < LinksPerRun; ++Link)
    {
        float Y, Z, Turn;
        AlongChain(EyeZ + Height - AxleZ + Link * LinkPitch, Y, Z, Turn);
        const FQuat Bend(FVector::ForwardVector, -Turn);
        const FQuat Rotation = (Link & 1) ? Bend * CrossLink : Bend;
        LinkPoses[Link] = FTransform(Rotation, FVector(-EyeX, Y, AxleZ + Z));
        LinkPoses[LinksPerRun + Link] = FTransform(Rotation, FVector(EyeX, Y, AxleZ + Z));
    }
    const FQuat Spin(FVector::ForwardVector, -Height / Radius);
    const FQuat WeightFacing = ((LinksPerRun - 1) & 1) ? CrossLink : FQuat::Identity;
    for (int32 Side = 0; Side < 2; ++Side)
    {
        const float X = Side == 0 ? -EyeX : EyeX;
        WheelPoses[2 * Side] = FTransform(Spin, FVector(X, InnerAxleY, AxleZ));
        WheelPoses[2 * Side + 1] = FTransform(Spin, FVector(X, OuterAxleY, AxleZ));
        WeightPoses[Side] = FTransform(WeightFacing, FVector(X, OuterAxleY + Radius, AxleZ - ClosedReturn - Height));
    }
    ApplyBatch(*Chains, LinkPoses);
    ApplyBatch(*Wheels, WheelPoses);
    ApplyBatch(*Weights, WeightPoses);
}

void UVillagePortcullisHoist::FollowGate(float Height, bool bIntact)
{
    if (!bIntact)
    {
        bObservedBreach = true;
        if (!bDetached)
        {
            bDetached = true;
            Draw(Travel); // A late join sees both weights at rest.
        }
    }
    else if (bObservedBreach)
    {
        Reattach(Height);
    }
    else if (!bDetached)
    {
        Draw(Height);
    }
}

void UVillagePortcullisHoist::Release(float ImpactLift)
{
    if (bDetached && IsComponentTickEnabled()) return;
    bDetached = true;
    ReleaseVelocity = 0.f;
    Draw(ImpactLift);
    SetComponentTickEnabled(LastLift < Travel);
}

void UVillagePortcullisHoist::Reattach(float Lift)
{
    SetComponentTickEnabled(false);
    bObservedBreach = false;
    bDetached = false;
    Draw(Lift);
}

void UVillagePortcullisHoist::TickComponent(float Delta, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(Delta, TickType, TickFunction);
    constexpr float Acceleration = 980.f;
    Draw(LastLift + ReleaseVelocity * Delta + .5f * Acceleration * Delta * Delta);
    ReleaseVelocity += Acceleration * Delta;
    if (LastLift >= Travel) SetComponentTickEnabled(false);
}
