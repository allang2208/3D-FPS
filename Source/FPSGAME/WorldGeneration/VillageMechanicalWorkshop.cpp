#include "VillageMechanicalWorkshop.h"
#include "TemperateHillsWorld.h"
#include "SmithYardLamp.h"
#include "VillageDefenseState.h"
#include "../Building/VillageBuildDefense.h"
#include "../NPC/VillageMasterArtisan.h"
#include "../Building/BuildingDaylight.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "Components/ChildActorComponent.h"
#include "Components/DecalComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Misc/Paths.h"
#include "UObject/ConstructorHelpers.h"

AVillageMechanicalWorkshop::AVillageMechanicalWorkshop()
{
    bReplicates=true;
    bAlwaysRelevant=true;
    SetReplicateMovement(true);
    PrimaryActorTick.bCanEverTick=false;
    Shell=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Workshop"));
    SetRootComponent(Shell);
    AssemblyBay=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("AssemblyBay"));
    AssemblyBay->SetupAttachment(Shell);
    auto* ArtisanStation = CreateDefaultSubobject<UChildActorComponent>(TEXT("MasterArtisanStation"));
    ArtisanStation->SetupAttachment(AssemblyBay);
    ArtisanStation->SetIsReplicated(true);
    // Stand beside the relocated east workbench, leaving the upgrade approach and central loading aisle clear.
    ArtisanStation->SetRelativeLocationAndRotation(FVector(-32, 128, 91), FRotator(0, -56, 0));
    ArtisanStation->SetChildActorClass(AVillageMasterArtisan::StaticClass());
    static ConstructorHelpers::FObjectFinder<UStaticMesh> House(TEXT("/Game/WorldGeneration/TemperateHills/VillageMechanicalWorkshop/SM_GarrisonWorkshop"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Fixtures(TEXT("/Game/WorldGeneration/TemperateHills/VillageMechanicalWorkshop/SM_GarrisonAssemblyBay"));
    Shell->SetStaticMesh(House.Object);
    AssemblyBay->SetStaticMesh(Fixtures.Object);
    for(UStaticMeshComponent* Part : {Shell.Get(),AssemblyBay.Get()})
    {
        Part->SetMobility(EComponentMobility::Movable);
        Part->SetCollisionProfileName(TEXT("BlockAll"));
        Part->SetGenerateOverlapEvents(false);
        Part->ComponentTags.Add(TEXT("HillsStaticSupport"));
    }
    Tags.Add(TEXT("Village.MechanicalWorkshop"));
}

FTransform AVillageMechanicalWorkshop::GetUpgradeWorkbenchTransform() const
{
    return AssemblyBay->GetSocketTransform(TEXT("UpgradeWorkbench"));
}

FTransform AVillageMechanicalWorkshop::GetUpgradeApproachTransform() const
{
    return AssemblyBay->GetSocketTransform(TEXT("UpgradeApproach"));
}

void AVillageMechanicalWorkshop::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer)return;
    // XY is the centre of each footprint, Z is its support surface. Preserve the source proportions.
    struct FProp { const TCHAR* Asset; FVector Foot; float Width; float Yaw; };
    static const FProp Props[]={
        {TEXT("VillageCarpenter/InteriorR1/SM_CarpenterHingeTray"),{-111,103,91},56,81},
        {TEXT("VillageCarpenter/InteriorR1/SM_CarpenterPegBin"),{-118,148,91},35,6},
        {TEXT("VillageCarpenter/Props/SM_CarpenterTools"),{-105,-59,91},49,78},
        {TEXT("VillageCarpenter/YardDetail/SM_CarpenterBenchCurls"),{-112,-22,91},32,22},
        {TEXT("VillageCarpenter/InteriorR1/SM_CarpenterHingeTray"),{218,-57,87},40,95},
        {TEXT("VillageBlacksmith/ArtPassR2/Meshes/SM_VillageIronStock"),{225,257,100},115,90},
        {TEXT("VillageCarpenter/InteriorR1/SM_CarpenterPegBin"),{225,402,100},55,94},
        {TEXT("VillageCarpenter/YardDetail/SM_CarpenterSeasoningBoards"),{226,319,180},170,90},
        {TEXT("VillageCarpenter/YardDetail/SM_CarpenterOffcutCrib"),{-218,-488,0},122,90},
        {TEXT("VillageCarpenter/YardDetail/SM_CarpenterHewingChips"),{-115,-350,0.5},77,18},
        {TEXT("VillageCarpenter/YardDetail/SM_CarpenterBenchCurls"),{-80,178,0.6},43,125},
        {TEXT("VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakStool"),{-124,208,0},38,13}
    };
    TMap<FString,UInstancedStaticMeshComponent*> Batches;
    for(const FProp& Item:Props)
    {
        auto*& Batch=Batches.FindOrAdd(Item.Asset);
        if(!Batch)
        {
            const FString Package=FString(TEXT("/Game/WorldGeneration/TemperateHills/"))+Item.Asset;
            const FString ObjectPath=Package+TEXT(".")+FPaths::GetCleanFilename(Package);
            auto* Mesh=LoadObject<UStaticMesh>(nullptr,*ObjectPath);
            if(!Mesh)continue;
            Batch=NewObject<UInstancedStaticMeshComponent>(this);
            AddInstanceComponent(Batch);
            Batch->SetupAttachment(Shell);
            Batch->SetStaticMesh(Mesh);
            Batch->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Batch->SetCanEverAffectNavigation(false);
            Batch->RegisterComponent();
        }
        const FBox Box=Batch->GetStaticMesh()->GetBoundingBox();
        const double Scale=Item.Width/FMath::Max(1.,FMath::Max(Box.GetSize().X,Box.GetSize().Y));
        const FRotator Facing(0,Item.Yaw,0);
        const FVector Bottom(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
        Batch->AddInstance(FTransform(Facing,Item.Foot-Facing.RotateVector(Bottom*Scale),FVector(Scale)));
    }

    // The loose windlass rests on its outer cheek. Use the same textured mesh component as the ballista.
    if (UStaticMesh* WindlassMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines/SM_BallistaWindlass.SM_BallistaWindlass")))
    {
        const FBox Bounds = WindlassMesh->GetBoundingBox();
        const double Scale = 64.0 / Bounds.GetSize().X;
        const FRotator RestingRotation(0.0, 78.0, 90.0);
        const FVector CheekCenter(Bounds.GetCenter().X, Bounds.Max.Y, Bounds.GetCenter().Z);
        const FVector BenchContact(217.0, -133.0, 87.0);
        const FVector Origin = BenchContact - RestingRotation.RotateVector(CheekCenter * Scale);

        UStaticMeshComponent* Windlass = NewObject<UStaticMeshComponent>(this, TEXT("BenchWindlass"));
        AddInstanceComponent(Windlass);
        Windlass->SetupAttachment(AssemblyBay);
        Windlass->SetStaticMesh(WindlassMesh);
        Windlass->SetRelativeTransform(FTransform(RestingRotation, Origin, FVector(Scale)));
        Windlass->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Windlass->SetCanEverAffectNavigation(false);
        Windlass->RegisterComponent();
    }

    auto Child=[this](FName Name,UClass* Class,FVector At,FRotator Facing,FName LightTag=NAME_None)
    {
        auto* Mount=NewObject<UChildActorComponent>(this,Name);
        AddInstanceComponent(Mount);
        Mount->SetupAttachment(Shell);
        Mount->SetRelativeLocationAndRotation(At,Facing);
        if(!LightTag.IsNone())Mount->ComponentTags.Add(LightTag);
        Mount->SetChildActorClass(Class);
        Mount->RegisterComponent();
        return Mount->GetChildActor();
    };
    if(auto* Vision=Cast<ABuildingDaylight>(Child(TEXT("RoomDaylight"),ABuildingDaylight::StaticClass(),FVector::ZeroVector,FRotator::ZeroRotator)))
    {
        Vision->RoomMinimum={-160,-560,0};
        Vision->RoomMaximum={276,560,310};
        Vision->EntranceTransitionCm=70.f;
        Vision->ExposureCompensation=1.f;
        Vision->OnConstruction(Vision->GetActorTransform());
    }
    // Mount the east chain lamp onto the engaged Tower-wall pilaster opposite the west assembly bay post.
    Child(TEXT("DoorBayLight"),AVillageShopChainLamp::StaticClass(),{-145.0,-192,239},FRotator::ZeroRotator,AVillageShopChainLamp::AlwaysLit);
    Child(TEXT("AssemblyBayLight"),AVillageShopChainLamp::StaticClass(),{275.5,192,239},FRotator(0,180,0),AVillageShopChainLamp::AlwaysLit);

    if(auto* Wear=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/ChapelGatehouse/M_DefenseGroundWear.M_DefenseGroundWear")))
    {
        auto* Decal=NewObject<UDecalComponent>(this);
        AddInstanceComponent(Decal);
        Decal->SetupAttachment(Shell);
        Decal->SetRelativeLocationAndRotation({108,0,-18},FRotator(-90,0,0));
        Decal->DecalSize={64,585+76,194+76};
        Decal->SetDecalColor(FLinearColor(194.f/1024,585.f/1024,76.f/256,.5f));
        Decal->SetDecalMaterial(Wear);
        Decal->SetSortOrder(-1);
        Decal->RegisterComponent();
    }
}

FTransform ATemperateHillsWorld::MechanicalWorkshopPose() const
{
    const auto Center=FTemperateVillageSite::WorkshopCenter;
    const FVector2D Anchor=VillageSite.World(Center.X,Center.Y);
    const FVector2D Roadside=VillageSite.World(Center.X,Center.Y+835.);
    // The mesh door faces -Y. Turn it south towards the stable across the east street.
    const FRotator Facing=FVector(-VillageSite.Axis,0.).Rotation();
    return FTransform(Facing,FVector(Anchor,Height(Roadside.X,Roadside.Y)+15.));
}

bool ATemperateHillsWorld::MechanicalWorkshopLotOccupied() const
{
    const auto Pose=MechanicalWorkshopPose();
    TArray<FOverlapResult> Hits;
    GetWorld()->OverlapMultiByObjectType(Hits,Pose.TransformPosition({60,-108,236}),Pose.GetRotation(),
        FCollisionObjectQueryParams::AllObjects,FCollisionShape::MakeBox(FVector(278,730,250)),
        FCollisionQueryParams(SCENE_QUERY_STAT(VillageWorkshopConstruction),false,this));
    for(const auto& Hit:Hits)
    {
        bool bOccupant=false;
        for(auto* Actor=Hit.GetActor();Actor;Actor=Actor->GetAttachParentActor())
        {
            if(const auto* Piece=Cast<AVoxelBuildPrefabActor>(Actor);
                Piece && Piece->PrefabId()==VillageBuildDefense::HighTower && VillageSite.IsWorkshopTowerPosition(Piece->GetActorLocation()))
            {
                bOccupant=false;
                break;
            }
            bOccupant |= Actor->IsA<APawn>() || Actor->IsA<AVoxelBuildPrefabActor>() || Actor->IsA<AVoxelBuildWorld>();
        }
        if(bOccupant)return true;
    }
    return false;
}

bool ATemperateHillsWorld::PurchaseSiegeUpgrade(APawn* Payer,int32 Index,int32 ExpectedRank,FText& Failure)
{
    if(!HasAuthority() || !IsVillagePlanUnlocked(VillageBuildDefense::MechanicsPlan) || !IsValid(MechanicalWorkshop))
    {Failure=FText::FromString(TEXT("机械工坊尚未开放。"));return false;}
    auto* State=GetWorld()->GetSubsystem<UVillageDefenseState>();
    const bool Bought=State->PurchaseUpgrade(WorldId,Index,ExpectedRank,Payer,Failure);
    const auto Loaded=State->SelectGeneration(WorldId,VillageDefenseGeneration);
    SiegeRanks=Loaded.Low;
    SiegeExtraRanks=Loaded.High;
    ForceNetUpdate();
    return Bought;
}

void ATemperateHillsWorld::UpdateMechanicalWorkshop()
{
    if(!HasAuthority())return;
    if(!bGarrisonMechanics)
    {
        if(IsValid(MechanicalWorkshop))MechanicalWorkshop->Destroy();
        MechanicalWorkshop=nullptr;
        return;
    }
    if(!VillageSite.bPlaced || IsValid(MechanicalWorkshop))return;
    const auto Loaded=GetWorld()->GetSubsystem<UVillageDefenseState>()->SelectGeneration(WorldId,VillageDefenseGeneration);
    SiegeRanks=Loaded.Low;
    SiegeExtraRanks=Loaded.High;
    FActorSpawnParameters Spawn;
    Spawn.Owner=this;
    Spawn.OverrideLevel=GetLevel();
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    MechanicalWorkshop=GetWorld()->SpawnActor<AVillageMechanicalWorkshop>(AVillageMechanicalWorkshop::StaticClass(),MechanicalWorkshopPose(),Spawn);
}
