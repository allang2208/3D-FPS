#include "DevelopmentEnvironmentObject.h"
#include "../Production/ProductionFallingTree.h"
#include "../Production/ProductionHarvestSubsystem.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionTreeHealth.h"
#include "../Production/ProductionOreRocks.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

const TArray<FDevelopmentEnvironmentEntry>& ADevelopmentEnvironmentObject::Catalogue()
{
    static const TArray<FDevelopmentEnvironmentEntry> Entries = []
    {
        TArray<FDevelopmentEnvironmentEntry> Result;
        auto AddOre = [&Result](const TCHAR* Suffix, const TCHAR* Name, const TCHAR* Definition)
        {
            const FString Asset = FString(TEXT("SM_LS_Rock_00A_")) + Suffix;
            Result.Add({FName(Definition), Name, FSoftObjectPath(FString::Printf(
                TEXT("/Game/WorldGeneration/TemperateHills/OreRocks/%s.%s"), *Asset, *Asset)), Definition});
        };
        AddOre(TEXT("Gold"), TEXT("金矿脉"), TEXT("gold_ore"));
        AddOre(TEXT("Silver"), TEXT("银矿脉"), TEXT("silver_ore"));
        AddOre(TEXT("Copper"), TEXT("铜矿脉"), TEXT("copper_ore"));
        AddOre(TEXT("Iron"), TEXT("铁矿脉"), TEXT("iron_ore"));
        for (TCHAR Variant : FString(TEXT("ABCD")))
        {
            const FString Beech = FString::Printf(TEXT("SK_Beech_%c"), Variant);
            Result.Add({FName(*Beech), FString::Printf(TEXT("山毛榉 %c"), Variant), FSoftObjectPath(FString::Printf(
                TEXT("/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Meshes/%s.%s"), *Beech, *Beech)), FString()});
            const FString Asset = FString::Printf(TEXT("SK_BlackPoplarPCG_%c"), Variant);
            Result.Add({FName(*Asset), FString::Printf(TEXT("黑杨树 %c"), Variant), FSoftObjectPath(FString::Printf(
                TEXT("/Game/WorldGeneration/TemperateHills/%s.%s"), *Asset, *Asset)), FString()});
        }
        return Result;
    }();
    return Entries;
}

const FDevelopmentEnvironmentEntry* ADevelopmentEnvironmentObject::FindEntry(FName Id)
{
    return Catalogue().FindByPredicate([Id](const auto& Entry) { return Entry.Id == Id; });
}

ADevelopmentEnvironmentObject::ADevelopmentEnvironmentObject()
{
    bReplicates = true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Origin")));
    Rock = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Ore"));
    Tree = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("BlackPoplar"));
    Trunk = CreateDefaultSubobject<UBoxComponent>(TEXT("TrunkCollision"));
    for (UPrimitiveComponent* Part : {static_cast<UPrimitiveComponent*>(Rock.Get()),
        static_cast<UPrimitiveComponent*>(Tree.Get()), static_cast<UPrimitiveComponent*>(Trunk.Get())})
    {
        Part->SetupAttachment(RootComponent);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCanEverAffectNavigation(false);
    }
    Tree->SetComponentTickEnabled(false);
    Trunk->SetBoxExtent(FVector(21, 21, 300));
    Trunk->SetRelativeLocation(FVector(0, 0, 300));
}

bool ADevelopmentEnvironmentObject::Initialize(FName Id,int32 Shape)
{
    EntryId = Id;
    OreShape=FMath::Clamp(Shape,0,ProductionOreRocks::ShapeCount-1);
    return ApplyEntry();
}

void ADevelopmentEnvironmentObject::OnRep_Entry()
{
    ApplyEntry();
}

bool ADevelopmentEnvironmentObject::ApplyEntry()
{
    const auto* Entry = FindEntry(EntryId);
    if (!Entry) return false;
    UObject* Mesh = (Entry->IsTree()?Entry->Mesh:ProductionOreRocks::Mesh(Entry->Ore,OreShape)).TryLoad();
    if (Entry->IsTree())
    {
        auto* Asset = Cast<USkeletalMesh>(Mesh);
        if (!Asset) return false;
        Tree->SetSkeletalMeshAsset(Asset);
        Trunk->SetCollisionProfileName(TEXT("BlockAll"));
    }
    else
    {
        auto* Asset = Cast<UStaticMesh>(Mesh);
        if (!Asset) return false;
        Rock->SetStaticMesh(Asset);
        Rock->SetCollisionProfileName(TEXT("BlockAll"));
    }
    return true;
}

bool ADevelopmentEnvironmentObject::Describe(FProductionResource& Resource) const
{
    const auto* Entry = FindEntry(EntryId);
    if (!Entry || HealthRatio <= 0.f) return false;
    Resource = {};
    Resource.DevelopmentObject = const_cast<ADevelopmentEnvironmentObject*>(this);
    Resource.DevelopmentHealthRatio = HealthRatio;
    Resource.Id = GetName();
    Resource.Name = Entry->Name;
    Resource.Mesh = Entry->IsTree()?Entry->Mesh:ProductionOreRocks::Mesh(Entry->Ore,OreShape);
    Resource.Transform = GetActorTransform();
    Resource.Seed = GetTypeHash(GetActorLocation());
    if (Entry->IsTree())
    {
        Resource.Layer = 0;
        Resource.RequiredTool = TEXT("axe");
        Resource.Rewards.Add(TEXT("wood"), 4);
        Resource.MaxHealth = ProductionTreeHealth::MaxHealth(Resource);
    }
    else
    {
        Resource.Layer = 1;
        Resource.RequiredTool = TEXT("pickaxe");
        Resource.Rewards.Add(TEXT("stone"), 1);
        Resource.Rewards.Add(Entry->Ore, 2);
        Resource.MaxHealth = ProductionTreeHealth::RockMaxHealth();
    }
    return true;
}

bool ADevelopmentEnvironmentObject::FindGround(const FVector& Around, FHitResult& Ground) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DevelopmentHarvestGround), false, this);
    const double Z = GetActorLocation().Z;
    const FVector Start(Around.X, Around.Y, Z + 135.);
    return GetWorld()->LineTraceSingleByChannel(Ground, Start, Start - FVector(0, 0, 700), ECC_Visibility, Query)
        && Ground.ImpactNormal.Z >= .65;
}

void ADevelopmentEnvironmentObject::ApplyStrike(const FProductionResource& Resource, const FHitResult& Hit, bool bDepleted)
{
    HealthRatio = bDepleted ? 0.f : Resource.DevelopmentHealthRatio;
    if (!bDepleted) return;
    const bool bTree = Resource.Layer == 0;
    auto* Harvest = GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();
    if (Harvest && GetNetMode() != NM_DedicatedServer) Harvest->Burst(bTree, Hit.ImpactPoint, Resource.Seed);
    if (bTree)
    {
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if (auto* Fall = GetWorld()->SpawnActor<AProductionFallingTree>(GetActorLocation(), GetActorRotation(), Params))
        {
            Fall->InitializeFall(Resource, Resource.Direction);
            if (Harvest) Harvest->ReleasePreparedFall(Resource);
        }
    }
    Destroy();
}

void ADevelopmentEnvironmentObject::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ADevelopmentEnvironmentObject, EntryId);
    DOREPLIFETIME(ADevelopmentEnvironmentObject, OreShape);
    DOREPLIFETIME(ADevelopmentEnvironmentObject, HealthRatio);
}
