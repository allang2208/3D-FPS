#include "ForestVillageRegion.h"
#include "ForestVillageMap.h"
#include "RiverPilotFXSubsystem.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "EngineUtils.h"
#include "Materials/MaterialInterface.h"
#if WITH_EDITOR
#include "Misc/FileHelper.h"
#endif

namespace
{
constexpr int32 TileM=64;
constexpr int32 Samples=ForestVillageMap::SideMeters+1;

TSharedPtr<TemperateForestWater::FPlan,ESPMode::ThreadSafe> SampleTile(
    const AForestVillageRegion& Region,FIntPoint OriginM)
{
    auto Tile=MakeShared<TemperateForestWater::FPlan,ESPMode::ThreadSafe>();
    Tile->Origin=FVector2D(OriginM)*100.;
    Tile->Width=Tile->Height=TileM+1;
    Tile->Ground.Reserve(Tile->Width*Tile->Height);
    for(int32 Y=0;Y<=TileM;++Y)
        for(int32 X=0;X<=TileM;++X)
            Tile->Ground.Add(Region.GroundHeight((OriginM.X+X)*100.,(OriginM.Y+Y)*100.));
    return Tile;
}
}

TemperateForestWater::FPlanPtr AForestVillageRegion::GetWoodlandWater() const
{
    if(WoodlandWater) return WoodlandWater;
    auto Plan=MakeShared<TemperateForestWater::FPlan,ESPMode::ThreadSafe>();
    Plan->Origin=ForestVillageMap::Bounds().Min;
    Plan->Width=Plan->Height=Samples;
    for(const auto& Site:WoodlandPools)
    {
        auto Tile=SampleTile(*this,Site.OriginM);
        auto& Local=Tile->Pools.Emplace_GetRef();
        auto& Regional=Plan->Pools.Emplace_GetRef();
        Local.WaterZ=Regional.WaterZ=Site.WaterZ;
        const FIntPoint Offset=Site.OriginM-FIntPoint(ForestVillageMap::West,ForestVillageMap::South);
        for(const auto Cell:Site.Cells)
        {
            Local.Cells.Add(Cell);
            Regional.Cells.Add(Cell+Offset);
            Local.Bounds+=Tile->Origin+FVector2D(Cell)*100.;
            Local.Bounds+=Tile->Origin+FVector2D(Cell+FIntPoint(1,1))*100.;
        }
        Regional.Bounds=Local.Bounds;
        Tile->RebuildShoreMoisture();
        Plan->Patches.Add(Tile);
    }
    WoodlandWater=Plan;
    return WoodlandWater;
}

bool AForestVillageRegion::BakeWoodlandPools(const FString& Directory,int32 Seed)
{
#if WITH_EDITOR
    TArray<uint8> Allowed;
    if(!HasGround() || !FFileHelper::LoadFileToArray(Allowed,*(Directory/TEXT("pond_allowed.u8"))) ||
       Allowed.Num()!=Samples*Samples) return false;
    struct FCandidate
    {
        FIntPoint Tile;
        TemperateForestWater::FPool Pool;
        double Jitter;
    };
    TArray<FCandidate> Candidates;
    FRandomStream Stream(Seed);
    for(int32 Y=0;Y<Samples-1;Y+=TileM) for(int32 X=0;X<Samples-1;X+=TileM)
    {
        const FIntPoint OriginM(ForestVillageMap::West+X,ForestVillageMap::South+Y);
        auto Tile=SampleTile(*this,OriginM);
        TArray<uint8> AllowedTile;
        for(int32 J=0;J<=TileM;++J) AllowedTile.Append(Allowed.GetData()+(Y+J)*Samples+X,TileM+1);
        TemperateForestWater::FindClosedPools(*Tile,AllowedTile);
        for(auto& Pool:Tile->Pools)
            Candidates.Add({OriginM,MoveTemp(Pool),Stream.FRandRange(0.f,7500.f)});
    }
    if(Candidates.IsEmpty()) return false;
    // Give the east-gate walk a nearby pool first, then distribute the others over distinct hollows.
    TArray<FForestVillagePoolSite> Selected;
    TArray<FVector2D> Centers;
    FString Table=TEXT("x_m,y_m,water_z_cm,depth_cm,area_m2\n");
    // Rasterize the same clipped shore used by the mesh at grass-placement resolution.
    constexpr int32 WetSide=(Samples-1)*4+1;
    TArray<uint8> Wet; Wet.Init(0,WetSide*WetSide);
    const FVector2D Gate=FVector2D(GetSettlementMinM()+FIntPoint(64,0))*100.;
    TArray<uint8> Moisture,Depth;
    Moisture.Init(0,Samples*Samples);
    Depth.Init(0,WetSide*WetSide);
    constexpr int32 WoodlandPoolBudget=12;
    while(Selected.Num()<WoodlandPoolBudget)
    {
        int32 Best=INDEX_NONE; double BestScore=-DBL_MAX;
        for(int32 I=0;I<Candidates.Num();++I)
        {
            const auto& C=Candidates[I];
            if(Selected.ContainsByPredicate([&](const auto& Site){ return Site.OriginM==C.Tile; }))continue;
            const FVector2D Center=C.Pool.Bounds.GetCenter();
            double Distance=DBL_MAX;
            for(const auto& Kept:Centers) Distance=FMath::Min(Distance,FVector2D::Distance(Center,Kept));
            if(Distance<2600.)continue;
            const double Score=Centers.IsEmpty()?-FVector2D::Distance(Center,Gate)+.12*C.Jitter:
                FMath::Min(Distance,26000.)+C.Jitter;
            // The approved woodland sites are shallow puddles of roughly 12-35 m².
            // Prefer that footprint before spending the spacing score on a large basin.
            constexpr float TypicalMaxAreaM2=40.f;
            const bool Typical=Centers.IsEmpty() || C.Pool.AreaM2<=TypicalMaxAreaM2;
            const bool BestTypical=Best!=INDEX_NONE && (Centers.IsEmpty() || Candidates[Best].Pool.AreaM2<=TypicalMaxAreaM2);
            if(Best==INDEX_NONE || (Typical&&!BestTypical) || (Typical==BestTypical&&Score>BestScore))
            { BestScore=Score; Best=I; }
        }
        if(Best==INDEX_NONE)break;
        const auto& C=Candidates[Best];
        auto& Site=Selected.Emplace_GetRef();
        Site.OriginM=C.Tile; Site.WaterZ=C.Pool.WaterZ; Site.Cells=C.Pool.Cells.Array();
        Site.Cells.Sort([](FIntPoint A,FIntPoint B){return A.Y==B.Y?A.X<B.X:A.Y<B.Y;});
        auto Tile=SampleTile(*this,C.Tile);
        Tile->Pools.Add(C.Pool);
        Tile->RebuildShoreMoisture();
        for(int32 J=0;J<=TileM;++J) for(int32 I=0;I<=TileM;++I)
        {
            const double W=Tile->ShoreMoistureAt(Tile->Origin.X+I*100.,Tile->Origin.Y+J*100.);
            auto& Pixel=Moisture[(C.Tile.Y-ForestVillageMap::South+J)*Samples+C.Tile.X-ForestVillageMap::West+I];
            Pixel=FMath::Max(Pixel,uint8(FMath::RoundToInt(255.*FMath::Clamp(W,0.,1.))));
        }
        for(const auto Cell:Site.Cells)
            for(int32 Y=0;Y<=4;++Y)for(int32 X=0;X<=4;++X)
            {
                const FVector2D XY=Tile->Origin+FVector2D(Cell)*100.+FVector2D(X,Y)*25.;
                const auto At=Tile->Sample(XY.X,XY.Y);
                if(!At.Wet)continue;
                const int32 I=(C.Tile.X-ForestVillageMap::West+Cell.X)*4+X;
                const int32 J=(C.Tile.Y-ForestVillageMap::South+Cell.Y)*4+Y;
                Wet[J*WetSide+I]=255;
                Depth[J*WetSide+I]=uint8(FMath::Clamp(FMath::CeilToInt(At.Depth),1,255));
            }
        const FVector2D Center=C.Pool.Bounds.GetCenter();
        Centers.Add(Center);
        Table+=FString::Printf(TEXT("%.1f,%.1f,%.1f,%.1f,%.1f\n"),Center.X*.01,Center.Y*.01,Site.WaterZ,C.Pool.MaxDepth,C.Pool.AreaM2);
    }
    if(!FFileHelper::SaveArrayToFile(Moisture,*(Directory/TEXT("pond_shore.u8"))) ||
       !FFileHelper::SaveArrayToFile(Depth,*(Directory/TEXT("pond_depth.u8"))) ||
       !FFileHelper::SaveArrayToFile(Wet,*(Directory/TEXT("pond_wet.u8"))) ||
       !FFileHelper::SaveStringToFile(Table,*(Directory/TEXT("ponds.csv")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))return false;
    Modify();
    WoodlandPools=MoveTemp(Selected);
    WoodlandWater.Reset();
    MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

AForestVillagePoolSurface::AForestVillagePoolSurface()
{
    Water=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("ShallowWater"));
    SetRootComponent(Water);
    Water->SetCollisionProfileName(TEXT("NoCollision"));
    Water->SetGenerateOverlapEvents(false);
    Water->SetCanEverAffectNavigation(false);
    Water->SetCastShadow(false);
    Water->bVisibleInRayTracing=false;
    Water->SetCullDistance(18000.f);
    Water->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
}

void AForestVillagePoolSurface::UseWaterMaterial(UMaterialInterface* Material)
{
    if(Material) Water->SetMaterial(0,Material);
}

void AForestVillagePoolSurface::BuildSurface()
{
    if(!GetWorld() || GetNetMode()==NM_DedicatedServer) return;
    const FVector2D Origin(GetActorLocation());
    for(TActorIterator<AForestVillageRegion> It(GetWorld());It;++It)
        for(const auto& Tile:It->GetWoodlandWater()->Patches)
            if(Tile->Origin.Equals(Origin,1.))
            {
                UE::Geometry::FDynamicMesh3 Mesh;
                Tile->BuildWaterMesh(Tile->Origin.X,Tile->Origin.Y,TileM*100.,Mesh);
                Water->SetMesh(MoveTemp(Mesh));
                return;
            }
}

void AForestVillagePoolSurface::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    BuildSurface();
#if WITH_EDITOR
    if(GetWorld() && !GetWorld()->IsGameWorld())
        UseWaterMaterial(LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/WetForest/M_ForestPond.M_ForestPond")));
#endif
}

void AForestVillagePoolSurface::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer)return;
    if(!Water->GetMesh() || Water->GetMesh()->TriangleCount()==0) BuildSurface();
    if(auto* FX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>()) UseWaterMaterial(FX->GetForestWaterMaterial());
}

