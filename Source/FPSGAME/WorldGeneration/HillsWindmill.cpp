#include "HillsWindmill.h"

#include "AI/NavigationSystemBase.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

namespace
{
    const FName RuinTag(TEXT("VillageWindmill.Ruin"));
    const FName RestoredTag(TEXT("VillageWindmill.Restored"));
    const FName SolidTag(TEXT("VillageWindmill.Solid"));
    constexpr double CapHeadingDegrees = 42.;
    FQuat AcrossShaft(double Degrees)
    {
        return FQuat(FVector::RightVector,FMath::DegreesToRadians(Degrees));
    }

    bool IsMillGroundDressing(const UStaticMeshComponent& Piece)
    {
        for (const FName Tag : Piece.ComponentTags)
        {
            FString Role = Tag.ToString();
            if (!Role.RemoveFromStart(TEXT("VillageWindmill.Yard."))) continue;
            int32 End;
            if (!Role.FindChar('.', End)) continue;
            Role.LeftInline(End);
            if (Role.StartsWith(TEXT("Margin")))
                return Role != TEXT("MarginBank") && Role != TEXT("MarginSurface");
            return Role == TEXT("GroveSoftGrass") || Role == TEXT("GroveFlower") ||
                Role == TEXT("GroveHerb") || Role == TEXT("GroveTwig") ||
                Role == TEXT("GroveSmallTwig") || Role == TEXT("GroveStone");
        }
        return false;
    }

    bool TouchesStableVerge(const FBox& Bounds)
    {
        // Village-local centimetres, matching the west eave, fence, hitch rails and trough.
        const FBox2D Foot(FVector2D(Bounds.Min), FVector2D(Bounds.Max));
        static const FBox2D Fixtures[] = {
            {{3265,3519},{5535,4381}}, {{2800,3238},{2816,4354}},
            {{3227,3610},{3257,3870}}, {{3227,4006},{3257,4266}},
            {{2936,3977},{3014,4183}}
        };
        for (const FBox2D& Solid : Fixtures)
            if (Foot.Intersect(Solid)) return true;

        // Sweep the lead-horse path along the north eave and through the watering yard.
        static const FVector Walk[] = {
            {4625,3070,0},{4500,3265,0},{4300,3360,0},{3520,3360,0},
            {3200,3490,0},{3150,3770,0},{3100,4090,0}
        };
        constexpr double HalfWidth = 110.;
        const FBox FlatBox(FVector(Foot.Min,-1.),FVector(Foot.Max,1.));
        const FVector2D Corners[] = {Foot.Min, {Foot.Min.X,Foot.Max.Y}, Foot.Max, {Foot.Max.X,Foot.Min.Y}};
        for (int32 I=1; I<UE_ARRAY_COUNT(Walk); ++I)
        {
            const FVector2D Start(Walk[I-1]), End(Walk[I]);
            if (Foot.ComputeSquaredDistanceToPoint(Start) <= HalfWidth*HalfWidth ||
                Foot.ComputeSquaredDistanceToPoint(End) <= HalfWidth*HalfWidth ||
                FMath::LineBoxIntersection(FlatBox,Walk[I-1],Walk[I],Walk[I]-Walk[I-1])) return true;
            for (const FVector2D& Corner : Corners)
                if (FVector2D::DistSquared(Corner,FMath::ClosestPointOnSegment2D(Corner,Start,End)) <= HalfWidth*HalfWidth)
                    return true;
        }
        return false;
    }

    void FitGroveToStable(AHillsWindmill& Mill)
    {
        // Use the floor instance as the survey anchor even in rotated/translated streamed villages.
        // A mill placed on its own has no adjoining stable.
        FTransform VillageFrame;
        bool bFoundFloor = false;
        for (const AActor* Actor : Mill.GetLevel()->Actors)
        {
            if (!IsValid(Actor) || !Actor->ActorHasTag(TEXT("VillageStable.Assembly"))) continue;
            const auto* Floor = Actor->FindComponentByClass<UInstancedStaticMeshComponent>();
            if (!Floor || !Floor->GetStaticMesh() || Floor->GetStaticMesh()->GetFName() != TEXT("SM_Stable_PackedFloor")) continue;
            if (!Floor->GetInstanceTransform(0,VillageFrame,true)) continue;
            VillageFrame.SetTranslation(VillageFrame.TransformPosition(FVector(-4400,-3950,0)));
            bFoundFloor = true;
            break;
        }
        if (!bFoundFloor) return;

        TInlineComponentArray<UStaticMeshComponent*> Pieces(&Mill);
        for (UStaticMeshComponent* Piece : Pieces)
        {
            if (!Piece->GetStaticMesh() || !IsMillGroundDressing(*Piece)) continue;
            const FBox LocalBox = Piece->GetStaticMesh()->GetBoundingBox();
            const auto Overlaps = [&](const FTransform& WorldPose) {
                return TouchesStableVerge(LocalBox.TransformBy(WorldPose.GetRelativeTransform(VillageFrame)));
            };
            if (auto* Group = Cast<UInstancedStaticMeshComponent>(Piece))
            {
                TArray<int32> Remove;
                for (int32 I=Group->GetInstanceCount()-1; I>=0; --I)
                {
                    FTransform Pose;
                    if (Group->GetInstanceTransform(I,Pose,true) && Overlaps(Pose)) Remove.Add(I);
                }
                if (!Remove.IsEmpty()) Group->RemoveInstances(Remove,true);
            }
            else if (Overlaps(Piece->GetComponentTransform()))
            {
                Piece->DestroyComponent();
            }
        }
    }
}

AHillsWindmill::AHillsWindmill()
{
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("MillSite")));
    RootComponent->SetMobility(EComponentMobility::Static);
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
    PrimaryActorTick.bAllowTickOnDedicatedServer = false;
    Tags.Add(TEXT("VillageWindmill.Site"));
}

void AHillsWindmill::BeginPlay()
{
    Super::BeginPlay();
    FitGroveToStable(*this);
    bReady = true;
    ShowState();
}

void AHillsWindmill::ApplyRepairState(bool bRepaired)
{
    if (bRestored == bRepaired) return;
    bRestored = bRepaired;
    if (bReady) ShowState();
}

void AHillsWindmill::EndPlay(const EEndPlayReason::Type Reason)
{
    if (IsValid(Keeper)) Keeper->Destroy();
    Keeper = nullptr;
    Super::EndPlay(Reason);
}

void AHillsWindmill::UpdateKeeper()
{
    if (GetNetMode() == NM_Client) return;
    if (!bRestored)
    {
        if (IsValid(Keeper)) Keeper->Destroy();
        Keeper = nullptr;
        return;
    }
    if (IsValid(Keeper)) return;
    const TSoftClassPtr<AActor> KeeperType(FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/AbandonedVillage/MillKeeper/BP_MillKeeper.BP_MillKeeper_C")));
    if (UClass* Class = KeeperType.LoadSynchronous())
    {
        FActorSpawnParameters Params;
        Params.Owner = this;
        Params.OverrideLevel = GetLevel();
        // Stand on the yard side of the sorting table, clear of the stool and approach.
        const FTransform Station(FRotator(0, 180, 0), FVector(-345, 522, 73.5));
        Keeper = GetWorld()->SpawnActor<AActor>(Class, Station * GetActorTransform(), Params);
    }
}

USceneComponent* AHillsWindmill::Pivot(const TCHAR* Name, USceneComponent* Parent, const FVector& Position)
{
    USceneComponent* Joint = NewObject<USceneComponent>(this,Name);
    Joint->SetMobility(EComponentMobility::Movable);
    Joint->SetupAttachment(Parent);
    Joint->SetRelativeLocation(Position);
    AddInstanceComponent(Joint);
    Joint->RegisterComponent();
    return Joint;
}

UStaticMeshComponent* AHillsWindmill::Part(const TCHAR* Id,USceneComponent* Parent,const FVector& Position,
    bool bSolid,FQuat Rotation,FVector Scale)
{
    if (!bSolid && GetNetMode() == NM_DedicatedServer) return nullptr;
    UStaticMesh* Mesh = PartMeshes.FindRef(FName(Id));
    if (!Mesh) return nullptr;
    UStaticMeshComponent* Body = NewObject<UStaticMeshComponent>(this);
    Body->SetMobility(Parent->Mobility);
    Body->SetupAttachment(Parent);
    Body->SetRelativeTransform(FTransform(Rotation,Position,Scale));
    Body->SetStaticMesh(Mesh);
    Body->ComponentTags.Add(RestoredTag);
    if (bSolid)
    {
        Body->ComponentTags.Add(SolidTag);
        Body->ComponentTags.Add(TEXT("HillsStaticSupport"));
    }
    Body->SetCollisionProfileName(bSolid ? TEXT("BlockAll") : TEXT("NoCollision"));
    Body->SetGenerateOverlapEvents(false);
    Body->SetCanEverAffectNavigation(bSolid);
    Body->bReceivesDecals = false;
    AddInstanceComponent(Body);
    Body->RegisterComponent();
    return Body;
}

void AHillsWindmill::Assemble()
{
    bAssembled = true;
    USceneComponent* Tower = GetRootComponent();
    // Door jambs are the hinge datums. The two open leaves lie outside the entrance.
    Part(TEXT("D01"),Tower,{0,0,0},true);
    Part(TEXT("D02"),Tower,{0,0,310},true);
    Part(TEXT("D03"),Tower,{0,0,590},true);
    Part(TEXT("D04"),Tower,{-75,373,0},true,FRotator(0,100,0).Quaternion());
    Part(TEXT("D04"),Tower,{75,373,0},true,FRotator(0,-100,0).Quaternion(),{-1,1,1});
    Part(TEXT("D05"),Tower,{162,102,0},true);
    Part(TEXT("D06"),Tower,{162,102,310},true);
    Part(TEXT("D07"),Tower,{0,0,0},true);

    Part(TEXT("C01"),Tower,{-110,0,313},true);
    Part(TEXT("C03"),Tower,{-110,0,313},true);
    Part(TEXT("C04"),Tower,{-110,0,374.9},true);
    Part(TEXT("C05"),Tower,{-112,0,0},true);
    Part(TEXT("C06"),Tower,{-110,0,590},true);
    Part(TEXT("C07"),Tower,{81,-233,795},true);
    Part(TEXT("C08"),Tower,{81,-233,705},true);
    Part(TEXT("C10"),Tower,{-128,98.7,329.5},true);
    Part(TEXT("C11"),Tower,{99,-170,805},true);
    for (double Deck : {310.,590.})
    {
        Part(TEXT("C09"),Tower,{54,-156,Deck},true);
        Part(TEXT("C09"),Tower,{144,-156,Deck},true,FRotator(0,180,0).Quaternion());
    }

    // The windshaft turns inside the fixed cap heading. Keep the roof in
    // authority collision too, so the village's shelter traces hit its shingles.
    Part(TEXT("A04"),Tower,{0,0,840},true,FRotator(0,CapHeadingDegrees,0).Quaternion());
    if (GetNetMode() == NM_DedicatedServer) return;
    Part(TEXT("A05"),Tower,{0,0,840});
    USceneComponent* Cap = Pivot(TEXT("CapHeading"),Tower,{0,0,0});
    Cap->SetRelativeRotation(FRotator(0,CapHeadingDegrees,0));
    Part(TEXT("A06"),Cap,{0,0,875.9});
    Part(TEXT("A07"),Cap,{236.25,0,861.7});
    Part(TEXT("B04"),Cap,{0,64,940});
    Part(TEXT("B02"),Cap,{0,244,940});
    Part(TEXT("B02"),Cap,{0,-1,940});

    Windshaft = Pivot(TEXT("SailAndBrakeWheel"),Cap,{0,64,940});
    Part(TEXT("B01"),Windshaft,{0,0,0});
    Part(TEXT("B03"),Windshaft,{0,0,0});
    // The forward journal stays on its bearing. The extended nose clears the
    // cap gable and the wider lower masonry throughout the sweep.
    const FVector Hub(0,353,0);
    Part(TEXT("A03"),Windshaft,Hub);
    Part(TEXT("A02"),Windshaft,Hub);
    Part(TEXT("A02"),Windshaft,Hub,false,AcrossShaft(90)*FRotator(0,180,0).Quaternion());
    for (int32 Wing = 0; Wing < 4; ++Wing)
    {
        const FQuat Quarter = AcrossShaft(Wing*90.);
        Part(TEXT("A01"),Windshaft,Hub+Quarter.RotateVector(FVector(0,0,140)),false,Quarter);
    }

    UprightShaft = Pivot(TEXT("GreatSpurTrain"),Tower,{0,0,0});
    Part(TEXT("B06"),UprightShaft,{0,0,68});
    Part(TEXT("B05"),UprightShaft,{0,0,808});
    Part(TEXT("B07"),UprightShaft,{0,0,255});
    StoneSpindle = Pivot(TEXT("StoneNutAndRunner"),Tower,{-110,0,0});
    Part(TEXT("B08"),StoneSpindle,{0,0,255});
    Part(TEXT("B09"),StoneSpindle,{0,0,255});
    Part(TEXT("C02"),StoneSpindle,{0,0,338.2});
}

void AHillsWindmill::ShowState()
{
    if (bRestored && !bAssembled) Assemble();
    UpdateKeeper();
    TInlineComponentArray<UStaticMeshComponent*> Pieces(this);
    for (UStaticMeshComponent* Piece : Pieces)
    {
        const bool bRuin = Piece->ComponentHasTag(RuinTag);
        if (!bRuin && !Piece->ComponentHasTag(RestoredTag)) continue;
        const bool bShow = bRuin != bRestored;
        Piece->SetVisibility(bShow);
        Piece->SetHiddenInGame(!bShow);
        const auto Collision = bShow && Piece->ComponentHasTag(SolidTag)
            ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision;
        if (Piece->GetCollisionEnabled() != Collision)
        {
            Piece->SetCollisionEnabled(Collision);
            if (HasAuthority() && Piece->CanEverAffectNavigation()) FNavigationSystem::UpdateComponentData(*Piece);
        }
    }
    TInlineComponentArray<UPointLightComponent*> InteriorLights(this);
    for (UPointLightComponent* Light : InteriorLights)
    {
        if (Light->ComponentHasTag(RestoredTag))
        {
            const bool bLit = bRestored && GetNetMode() != NM_DedicatedServer;
            Light->SetVisibility(bLit);
            Light->SetHiddenInGame(!bLit);
        }
    }
    SetActorTickEnabled(bRestored && Windshaft != nullptr);
    if (bRestored && Windshaft) UpdateDrive();
}

void AHillsWindmill::UpdateDrive()
{
    const AGameStateBase* Clock = GetWorld()->GetGameState();
    const double Seconds = Clock ? Clock->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
    const double SailAngle = 45. + Seconds * 30.;
    // At the bottom of the brake wheel the tooth velocity is -X. At the +Y
    // side of the wallower a positive vertical spin also moves the teeth -X.
    const double GreatAngle = CapHeadingDegrees + SailAngle * (66./24.);
    const double RunnerAngle = -GreatAngle * (51./15.);
    Windshaft->SetRelativeRotation(AcrossShaft(FMath::Fmod(SailAngle,360.)));
    UprightShaft->SetRelativeRotation(FRotator(0,FMath::Fmod(GreatAngle,360.),0));
    StoneSpindle->SetRelativeRotation(FRotator(0,FMath::Fmod(RunnerAngle,360.),0));
}

void AHillsWindmill::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateDrive();
}

bool AHillsWindmill::IsRepairFootprintOccupied() const
{
    // Include old roof tiles and furniture as well as the new tower footprint.
    const FTransform& Frame = GetActorTransform();
    FBox Bounds(FVector(-390,-390,-15),FVector(390,390,1110));
    TInlineComponentArray<UStaticMeshComponent*> Pieces(this);
    for (const UStaticMeshComponent* Piece : Pieces)
        if (Piece->ComponentHasTag(RuinTag) && Piece->ComponentHasTag(SolidTag))
            Bounds += Piece->CalcBounds(Piece->GetComponentTransform().GetRelativeTransform(Frame)).GetBox();
    return GetWorld()->OverlapAnyTestByObjectType(Frame.TransformPosition(Bounds.GetCenter()),Frame.GetRotation(),
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(Bounds.GetExtent()*Frame.GetScale3D().GetAbs()),
        FCollisionQueryParams(SCENE_QUERY_STAT(VillageWindmillRepair),false,this));
}
