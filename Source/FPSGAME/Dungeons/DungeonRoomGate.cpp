#include "DungeonRoomGate.h"
#include "DungeonRoomGateDimensions.h"
#include "DungeonRunSubsystem.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "UObject/ConstructorHelpers.h"

ADungeonRoomGate::ADungeonRoomGate()
{
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("GrilleRoot"));
    PrimaryActorTick.bCanEverTick = false;
    Panels = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("TelescopicPanels"));
    GuideLeft = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GuideLeft"));
    GuideRight = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GuideRight"));
    Head = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StorageHead"));
    for (UStaticMeshComponent* Part : {static_cast<UStaticMeshComponent*>(Panels.Get()), GuideLeft.Get(), GuideRight.Get(), Head.Get()})
    {
        Part->SetupAttachment(RootComponent);
        Part->SetMobility(EComponentMobility::Movable);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false);
    }
    // Hard references keep this runtime-spawned kit and its source finishes in cooks.
    static ConstructorHelpers::FObjectFinder<UStaticMesh> PanelAsset(TEXT("/Game/Dungeons/EliteGate20260926/Meshes/SM_EliteGrillePanel.SM_EliteGrillePanel"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> LeftAsset(TEXT("/Game/Dungeons/EliteGate20260926/Meshes/SM_EliteGrilleGuideLeft.SM_EliteGrilleGuideLeft"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> RightAsset(TEXT("/Game/Dungeons/EliteGate20260926/Meshes/SM_EliteGrilleGuideRight.SM_EliteGrilleGuideRight"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> HeadAsset(TEXT("/Game/Dungeons/EliteGate20260926/Meshes/SM_EliteGrilleHead.SM_EliteGrilleHead"));
    if (PanelAsset.Succeeded()) Panels->SetStaticMesh(PanelAsset.Object);
    if (LeftAsset.Succeeded()) GuideLeft->SetStaticMesh(LeftAsset.Object);
    if (RightAsset.Succeeded()) GuideRight->SetStaticMesh(RightAsset.Object);
    if (HeadAsset.Succeeded()) Head->SetStaticMesh(HeadAsset.Object);
    for (int32 Index = 0; Index < DungeonRoomGateDimensions::PanelCount; ++Index)
    {
        auto* Box = CreateDefaultSubobject<UBoxComponent>(*FString::Printf(TEXT("PanelBlocker%d"), Index));
        Box->SetupAttachment(RootComponent);
        Box->SetMobility(EComponentMobility::Movable);
        Box->SetCollisionProfileName(TEXT("BlockAll"));
        Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Box->SetGenerateOverlapEvents(false);
        Box->SetCanEverAffectNavigation(false);
        Blockers.Add(Box);
    }
    for (int32 Index = 0; Index < 3; ++Index)
    {
        auto* Box = CreateDefaultSubobject<UBoxComponent>(*FString::Printf(TEXT("FrameBlocker%d"), Index));
        Box->SetupAttachment(RootComponent);
        Box->SetMobility(EComponentMobility::Movable);
        Box->SetCollisionProfileName(TEXT("BlockAll"));
        Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Box->SetGenerateOverlapEvents(false);
        Box->SetCanEverAffectNavigation(false);
        FrameBlockers.Add(Box);
    }
    Tags.Add(TEXT("DungeonRoom.Grille"));
    EncounterBarrier = CreateDefaultSubobject<UBoxComponent>(TEXT("EncounterBarrier"));
    EncounterBarrier->SetupAttachment(RootComponent);
    EncounterBarrier->SetMobility(EComponentMobility::Movable);
    EncounterBarrier->SetCollisionProfileName(TEXT("BlockAll"));
    EncounterBarrier->SetCollisionResponseToAllChannels(ECR_Ignore);
    EncounterBarrier->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
    EncounterBarrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    EncounterBarrier->SetGenerateOverlapEvents(false);
    EncounterBarrier->SetCanEverAffectNavigation(false);
}

bool ADungeonRoomGate::Configure(const FDungeonRunDoor& Door)
{
    using namespace DungeonRoomGateDimensions;
    const FVector Inward = -Door.OutwardNormal.GetSafeNormal2D();
    if (Inward.IsNearlyZero() || Door.FloorCenter.ContainsNaN() ||
        !FMath::IsFinite(Door.Width) || !FMath::IsFinite(Door.Height) || Door.Width <= 0. || Door.Height <= 0. ||
        !Panels->GetStaticMesh() || !GuideLeft->GetStaticMesh() || !GuideRight->GetStaticMesh() || !Head->GetStaticMesh())
        return false;
    ClearWidth = Door.Width;
    ClearHeight = Door.Height;
    PanelHeight = ClearHeight / PanelCount + PanelOverlap;
    const double NominalPanelHeight = NominalHeight / PanelCount + PanelOverlap;
    const double GuideHeight = ClearHeight + OpenClearance + PanelHeight + HoodMargin;
    const double NominalGuideHeight = NominalHeight + OpenClearance + NominalPanelHeight + HoodMargin;
    SetActorTransform(FTransform(FRotator(0., Inward.Rotation().Yaw - 90., 0.), Door.FloorCenter));
    GuideLeft->SetRelativeLocation(FVector(-ClearWidth * .5, 0., 0.));
    GuideRight->SetRelativeLocation(FVector(ClearWidth * .5, 0., 0.));
    for (UStaticMeshComponent* Guide : {GuideLeft.Get(), GuideRight.Get()})
        Guide->SetRelativeScale3D(FVector(1., 1., GuideHeight / NominalGuideHeight));
    Head->SetRelativeLocation(FVector(0., 0., ClearHeight));
    Head->SetRelativeScale3D(FVector((ClearWidth + 22.) / (NominalWidth + 22.), 1.,
        (GuideHeight - ClearHeight) / (NominalGuideHeight - NominalHeight)));
    const double LastTrack = FirstTrack + (PanelCount - 1) * TrackPitch;
    EncounterBarrier->SetRelativeLocation(FVector(0.,(FirstTrack+LastTrack)*.5,ClearHeight*.5));
    EncounterBarrier->SetBoxExtent(FVector(ClearWidth*.5+SideOverlap,
        (LastTrack-FirstTrack+PanelThickness)*.5,ClearHeight*.5));
    SetEncounterLocked(false);
    for (int32 Index = 0; Index < 2; ++Index)
    {
        // Side volumes begin at the clear edge, never across the doorway.
        FrameBlockers[Index]->SetRelativeLocation(FVector((Index == 0 ? -1. : 1.) * (ClearWidth * .5 + 6.1),
            (15.2 + LastTrack + 3.6) * .5, GuideHeight * .5));
        FrameBlockers[Index]->SetBoxExtent(FVector(6.1, (LastTrack + 3.6 - 15.2) * .5, GuideHeight * .5));
    }
    FrameBlockers[2]->SetRelativeLocation(FVector(0., (FirstTrack - 5. + LastTrack + 5.5) * .5,
        (ClearHeight + GuideHeight) * .5));
    FrameBlockers[2]->SetBoxExtent(FVector(ClearWidth * .5 + 11.,
        (LastTrack + 5.5 - FirstTrack + 5.) * .5, (GuideHeight - ClearHeight) * .5));
    for (UBoxComponent* Box : FrameBlockers) Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Panels->ClearInstances();
    for (int32 Index = 0; Index < PanelCount; ++Index)
    {
        Panels->AddInstance(FTransform::Identity);
        Blockers[Index]->SetBoxExtent(FVector(ClearWidth * .5 + SideOverlap, PanelThickness * .5, PanelHeight * .5));
    }
    LastOpenFraction = -1.f;
    SetOpenFraction(1.f);
    return true;
}

void ADungeonRoomGate::SetOpenFraction(float Fraction)
{
    using namespace DungeonRoomGateDimensions;
    Fraction = FMath::Clamp(Fraction, 0.f, 1.f);
    if (ClearHeight <= 0. || Fraction == LastOpenFraction) return;
    LastOpenFraction = Fraction;
    const double Lift = FMath::SmoothStep(0.f, 1.f, Fraction);
    const double NominalPanelHeight = NominalHeight / PanelCount + PanelOverlap;
    const FVector Scale((ClearWidth + SideOverlap * 2.) / (NominalWidth + SideOverlap * 2.), 1., PanelHeight / NominalPanelHeight);
    for (int32 Index = 0; Index < PanelCount; ++Index)
    {
        const double ClosedBottom = -PanelOverlap * .5 + Index * ClearHeight / PanelCount;
        const double Bottom = FMath::Lerp(ClosedBottom, ClearHeight + OpenClearance, Lift);
        const FVector Position(0., FirstTrack + Index * TrackPitch, Bottom);
        Panels->UpdateInstanceTransform(Index, FTransform(FQuat::Identity, Position, Scale), false, Index == PanelCount - 1, true);
        Blockers[Index]->SetRelativeLocation(Position + FVector(0., 0., PanelHeight * .5));
        // Keep collision on the moving grille until it has actually cleared the opening.
        const auto Collision = Bottom >= ClearHeight ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics;
        if (Blockers[Index]->GetCollisionEnabled() != Collision) Blockers[Index]->SetCollisionEnabled(Collision);
    }
    // Fully stowed panels are inside the opaque folded-steel housing.
    Panels->SetHiddenInGame(Fraction >= 1.f);
}

void ADungeonRoomGate::SetEncounterLocked(bool bLocked)
{
    const auto Collision=bLocked?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision;
    if(EncounterBarrier->GetCollisionEnabled()!=Collision)EncounterBarrier->SetCollisionEnabled(Collision);
}

bool ADungeonRoomGate::IsSweepOccupied(const APawn* Pawn) const
{
    using namespace DungeonRoomGateDimensions;
    if (!IsValid(Pawn)) return false;
    const auto* Character = Cast<ACharacter>(Pawn);
    const auto* Capsule = Character ? Character->GetCapsuleComponent() : nullptr;
    const double Radius = Capsule ? Capsule->GetScaledCapsuleRadius() : 60.;
    const double HalfHeight = Capsule ? Capsule->GetScaledCapsuleHalfHeight() : 100.;
    const FVector Local = GetActorTransform().InverseTransformPosition(Pawn->GetActorLocation());
    const double LastTrack = FirstTrack + (PanelCount - 1) * TrackPitch;
    // Room containment includes the wall/door collar. Reserve its outside edge
    // too: a pawn approaching from the corridor must not start the encounter
    // before its entire capsule has crossed behind the last gate track.
    return FMath::Abs(Local.X) < ClearWidth * .5 + SideOverlap + Radius &&
        Local.Y > -Radius - 200. &&
        Local.Y < LastTrack + PanelThickness * .5 + Radius + 2. &&
        Local.Z + HalfHeight > -PanelOverlap * .5 && Local.Z - HalfHeight < ClearHeight + OpenClearance + PanelHeight;
}
