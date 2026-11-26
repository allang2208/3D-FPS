#include "TemperateHillsWorld.h"
#include "EastRiverRoad.h"
#include "TemperateVillageGround.h"
#include "TemperateQuarryYard.h"
#include "Algo/Compare.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Net/UnrealNetwork.h" // M4: DOREPLIFETIME
#include "TemperateHillsSurface.h"
#include "TemperateHillsVisibility.h"
#include "TemperateForestHabitat.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Engine/GameInstance.h"
#include "PCGComponent.h"
#include "PCGManagedResource.h"
#include "PCGGraph.h"
#include "PCGWorldActor.h"
#include "Subsystems/PCGSubsystem.h"
#include "RuntimeGen/SchedulingPolicies/PCGSchedulingPolicyDistanceAndDirection.h"
#include "Components/BoxComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/ConfigCacheIni.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HighResScreenshot.h"
#include "TimerManager.h"
#include "../FPSWeatherManager.h"
#include "../Production/ProductionOreRocks.h"
#include "TemperateVegetationPlacement.h"
#include "../UI/ColdSteelStatusModel.h"

#include "TemperateHillsMathPrivate.h"
namespace TemperateHills
{
// Terrain destruction limits (cm). Digging and craters stop this far below the generated
// surface; refilling stops this far above it.
static TAutoConsoleVariable<float> MaxDropCm(
    TEXT("fps.Hills.MaxDropCm"), 400.f,
    TEXT("How far terrain destruction may sink below the generated surface (cm)."));
static TAutoConsoleVariable<float> MaxRiseCm(
    TEXT("fps.Hills.MaxRiseCm"), 100.f,
    TEXT("How far refilling may raise terrain above the generated surface (cm)."));
}
double ATemperateHillsWorld::Noise(double X,double Y,uint32 Salt) const
{
    const int32 IX=FMath::FloorToInt(X),IY=FMath::FloorToInt(Y);
    const double FX=TemperateHills::Smooth(X-IX),FY=TemperateHills::Smooth(Y-IY);
    auto V=[&](int32 A,int32 B){return TemperateHills::Unit(TemperateHills::Key(A,B,uint32(Seed),Salt))*2-1;};
    return FMath::Lerp(FMath::Lerp(V(IX,IY),V(IX+1,IY),FX),FMath::Lerp(V(IX,IY+1),V(IX+1,IY+1),FX),FY);
}

double ATemperateHillsWorld::PathDistance(double X,double Y) const
{
    const double Original=FMath::Abs(Y-TemperateHills::ValleyY(X,Seed));
    if(!RiverPlan || RiverPlan->WhiteCliffs.Weight(X,Y)<=.05)return Original;
    const auto P=RiverPlan->WhiteCliffs.Local(X,Y);
    return FMath::Min3(Original,FMath::Abs(P.X-TemperateQuarry::RoadX(P.Y)),TemperateQuarry::ServiceDistance(P));
}
double ATemperateHillsWorld::Height(double X,double Y) const
{return BaseHeight(X,Y)+TerrainOffsetAt(X,Y);}
double ATemperateHillsWorld::BaseHeight(double X,double Y) const
{
    if(IsForestVillage()) return ForestVillageHeight(X,Y);
    const auto Native=[&]()
    {
        if(VillageSite.bPlaced&&VillageSite.bHilltop&&FMath::Abs(X-VillageSite.Ground.X)<8300.&&FMath::Abs(Y-VillageSite.Ground.Y)<8300.)
        {
            const auto P=VillageSite.Local(X,Y);
            if(FMath::Abs(P.X)<=VillageSite.PadHalfX&&FMath::Abs(P.Y)<=VillageSite.PadHalfY)
                return ChapelSite.Grade(X,Y,VillageSite.Ground.Z);
        }
        const double Z=RiverPlan?RiverPlan->Height(X,Y,Seed):TemperateHillsSurface::Height(X,Y,Seed,GeneratorVersion);
        return ChapelSite.Grade(X,Y,VillageSite.Grade(X,Y,ForestWaterPlan?ForestWaterPlan->ShapeGround(X,Y,Z):Z,Seed));
    };
    const double Z=EastRiverRoad::Enabled(Seed,GeneratorVersion,VillageSite)?
        EastRiverRoad::Height(EastRiverRoad::Sample(X,Y),Native):Native();
    return Z+TemperateVillageGround::Offset(VillageSite,X,Y);
}
double ATemperateHillsWorld::TerrainOffsetAt(double X,double Y) const
{
    if(TerrainEdits.IsEmpty())return 0;
    const TArray<int32>* Bucket=EditBuckets.Find(
        TemperateHills::CellId(FMath::FloorToInt(X/TemperateHills::EditBucketCm),FMath::FloorToInt(Y/TemperateHills::EditBucketCm)));
    if(!Bucket||Bucket->IsEmpty())return 0;
    TArray<TemperateHillsSurface::FTerrainEdit,TInlineAllocator<8>> Local;
    Local.Reserve(Bucket->Num());
    for(const int32 Index:*Bucket)Local.Add(TerrainEdits[Index]);
    return TemperateHillsSurface::TerrainEditOffset(Local,X,Y);
}
bool ATemperateHillsWorld::TerrainEditTouchesPoint(double X,double Y) const
{
    if(TerrainEdits.IsEmpty())return false;
    // The 3x3 neighbourhood catches edits that only reach across a bucket border.
    const int32 BaseX=FMath::FloorToInt(X/TemperateHills::EditBucketCm);
    const int32 BaseY=FMath::FloorToInt(Y/TemperateHills::EditBucketCm);
    for(int32 DY=-1;DY<=1;++DY)for(int32 DX=-1;DX<=1;++DX)
    {
        const TArray<int32>* Bucket=EditBuckets.Find(TemperateHills::CellId(BaseX+DX,BaseY+DY));
        if(!Bucket)continue;
        for(const int32 Index:*Bucket)
            if(TemperateHillsSurface::TerrainEditTouches(TerrainEdits[Index],X,Y))return true;
    }
    return false;
}
void ATemperateHillsWorld::RebuildEditBuckets()
{
    ++TerrainEditRevision;
    EditBuckets.Reset();
    for(int32 Index=0;Index<TerrainEdits.Num();++Index)
    {
        const TemperateHillsSurface::FTerrainEdit& Edit=TerrainEdits[Index];
        const double Reach=TemperateHillsSurface::TerrainEditReach(Edit);
        const int32 MinX=FMath::FloorToInt((Edit.X-Reach)/TemperateHills::EditBucketCm);
        const int32 MaxX=FMath::FloorToInt((Edit.X+Reach)/TemperateHills::EditBucketCm);
        const int32 MinY=FMath::FloorToInt((Edit.Y-Reach)/TemperateHills::EditBucketCm);
        const int32 MaxY=FMath::FloorToInt((Edit.Y+Reach)/TemperateHills::EditBucketCm);
        for(int32 Y=MinY;Y<=MaxY;++Y)for(int32 X=MinX;X<=MaxX;++X)
            EditBuckets.FindOrAdd(TemperateHills::CellId(X,Y)).Add(Index);
    }
}
FVector ATemperateHillsWorld::SurfaceNormal(double X,double Y) const
{
    // Edits only bend the normal where they actually touch the ground; outside
    // their influence the generated normal is still exact and much cheaper.
    if(IsForestVillage()||ChapelSite.Near(X,Y)||VillageSite.Near(X,Y)||TerrainEditTouchesPoint(X,Y)||(ForestWaterPlan&&ForestWaterPlan->HasBasin(X,Y))||
       (EastRiverRoad::Enabled(Seed,GeneratorVersion,VillageSite)&&EastRiverRoad::Sample(X,Y).GradeWeight>0.))
        return TemperateHillsSurface::NumericNormal([this](double PX,double PY){return Height(PX,PY);},X,Y);
    return RiverPlan?RiverPlan->Normal(X,Y,Seed):TemperateHillsSurface::Normal(X,Y,Seed,GeneratorVersion);
}
void ATemperateHillsWorld::PersistTerrainEdits()
{
    if(Slot.IsEmpty())return;
    auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!Save)Save=Cast<UTemperateHillsSave>(UGameplayStatics::CreateSaveGameObject(UTemperateHillsSave::StaticClass()));
    if(!Save)return;
    Save->Version=6;Save->Seed=Seed;Save->WorldId=WorldId;Save->GeneratorVersion=GeneratorVersion;
    Save->PlaythroughSeed=PlaythroughSeed;
    Save->bVillageWallRepaired=bVillageWallRepaired;
    Save->bVillageBlacksmithRepaired=bVillageBlacksmithRepaired;
    Save->VillagePlansUnlocked=VillagePlansUnlocked;
    Save->bVillageBakeryRepaired=bVillageBakeryRepaired;
    Save->bVillageGunshopRepaired=bVillageGunshopRepaired;
    Save->bGarrisonMechanics=bGarrisonMechanics;
    Save->VillageDefenseGeneration=VillageDefenseGeneration;
    if(bGarrisonMechanics)Save->VillagePlanVersion=FMath::Max(11,Save->VillagePlanVersion);
    else if(IsGunshopRepaired())Save->VillagePlanVersion=FMath::Max(10,Save->VillagePlanVersion);
    else if(IsBakeryRepaired())Save->VillagePlanVersion=FMath::Max(9,Save->VillagePlanVersion);
    else if(IsWindmillRepaired())Save->VillagePlanVersion=FMath::Max(8,Save->VillagePlanVersion);
    else if(HasVillageHighWall())Save->VillagePlanVersion=FMath::Max(7,Save->VillagePlanVersion);
    else if(VillagePlansUnlocked & UTemperateHillsSave::ConstructionPlan)Save->VillagePlanVersion=FMath::Max(6,Save->VillagePlanVersion);
    else if(IsHerbalistRepaired())Save->VillagePlanVersion=FMath::Max(5,Save->VillagePlanVersion);
    else if(IsTavernRepaired())Save->VillagePlanVersion=FMath::Max(4,Save->VillagePlanVersion);
    else if(IsVillageCarpenterRepaired())Save->VillagePlanVersion=FMath::Max(3,Save->VillagePlanVersion);
    Save->Craters.Reset();
    Save->Edits.Reset(TerrainEdits.Num());
    for(const TemperateHillsSurface::FTerrainEdit& Edit:TerrainEdits)
    {
        FHillsTerrainEditRecord Record;
        Record.Type=Edit.Type;Record.X=Edit.X;Record.Y=Edit.Y;Record.Radius=Edit.Radius;
        Record.HalfX=Edit.HalfX;Record.HalfY=Edit.HalfY;Record.Amplitude=Edit.Amplitude;
        Record.Lip=Edit.Lip;Record.Seed=int32(Edit.Seed);
        Save->Edits.Add(Record);
    }
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0))UE_LOG(LogTemp,Error,TEXT("HILLS_EDIT save failed edits=%d"),TerrainEdits.Num());
}
bool ATemperateHillsWorld::ApplyCrater(const FVector& Location,double RadiusCm,double DepthCm,double RimCm)
{
    if(!HasAuthority()||!bTerrainDestructionEnabled)return false;
    if(RadiusCm<=0||DepthCm<=0)return false;
    // Sink limit: a crater may only use the depth still available under this spot.
    const double Room=FMath::Max(0.0,TemperateHills::MaxDropCm.GetValueOnGameThread()+TerrainOffsetAt(Location.X,Location.Y));
    DepthCm=FMath::Min(DepthCm,Room);
    if(DepthCm<=0)return false;
    TemperateHillsSurface::FTerrainEdit Edit;
    Edit.Type=0;
    Edit.X=Location.X;Edit.Y=Location.Y;Edit.Radius=RadiusCm;
    Edit.Amplitude=-DepthCm;Edit.Lip=RimCm;
    // Deterministic per-position seed: the same spot always gets the same outline,
    // and two blasts side by side do not share one shape.
    Edit.Seed=TemperateHills::Key(int32(Location.X),int32(Location.Y),uint32(Seed),7043);
    AddTerrainEdit(Edit);
    UE_LOG(LogTemp,Display,TEXT("HILLS_CRATER x=%.1f y=%.1f radius=%.1f depth=%.1f rim=%.1f count=%d"),
        Edit.X,Edit.Y,Edit.Radius,DepthCm,RimCm,TerrainEdits.Num());
    return true;
}
bool ATemperateHillsWorld::ApplyTerrainStep(const FVector& Location,double HalfXCm,double HalfYCm,double AmplitudeCm,uint32 EditSeed)
{
    if(!HasAuthority()||!bTerrainDestructionEnabled)return false;
    if(HalfXCm<=0||HalfYCm<=0||AmplitudeCm==0)return false;
    // Digging stops at the sink limit, refilling stops at the rise limit; both limits are
    // measured against the generated surface, so a pit can never eat into the landscape
    // forever and a dirt pile can never become a tower.
    const double Offset=TerrainOffsetAt(Location.X,Location.Y);
    if(AmplitudeCm<0)
        AmplitudeCm=-FMath::Min(-AmplitudeCm,FMath::Max(0.0,TemperateHills::MaxDropCm.GetValueOnGameThread()+Offset));
    else
        AmplitudeCm=FMath::Min(AmplitudeCm,FMath::Max(0.0,TemperateHills::MaxRiseCm.GetValueOnGameThread()-Offset));
    if(AmplitudeCm==0)return false;
    TemperateHillsSurface::FTerrainEdit Edit;
    Edit.Type=1;
    Edit.X=Location.X;Edit.Y=Location.Y;
    Edit.HalfX=HalfXCm;Edit.HalfY=HalfYCm;
    Edit.Amplitude=AmplitudeCm;Edit.Seed=EditSeed;
    AddTerrainEdit(Edit);
    UE_LOG(LogTemp,Display,TEXT("HILLS_STEP x=%.1f y=%.1f half=%.1f/%.1f amount=%.1f count=%d"),
        Edit.X,Edit.Y,Edit.HalfX,Edit.HalfY,Edit.Amplitude,TerrainEdits.Num());
    return true;
}
void ATemperateHillsWorld::AddTerrainEdit(const TemperateHillsSurface::FTerrainEdit& Edit)
{
    if(!HasAuthority()||!bTerrainDestructionEnabled)return;
    // Edits are cheap but unbounded; the oldest is retired past the cap and its
    // cells are rebuilt back to the generated height.
    constexpr int32 MaxEdits=256;
    if(TerrainEdits.Num()>=MaxEdits)
    {
        const TemperateHillsSurface::FTerrainEdit Old=TerrainEdits[0];
        // RemoveAt (not RemoveAtSwap): the swap moves the newest edit into slot 0,
        // so the next "oldest" eviction would discard a fresh player edit instead.
        TerrainEdits.RemoveAt(0);
        InvalidateTerrainCells(FVector2D(Old.X,Old.Y),TemperateHillsSurface::TerrainEditReach(Old));
    }
    TerrainEdits.Add(Edit);
    RebuildEditBuckets();
    // Only the cells the edit reaches are rebuilt; the rest of the world keeps its
    // meshes, so one crater or one shovel layer costs a few cells, not a re-stream.
    InvalidateTerrainCells(FVector2D(Edit.X,Edit.Y),TemperateHillsSurface::TerrainEditReach(Edit));
    ClearCoverForEdit(Edit);
    PersistTerrainEdits();
    if(GetNetMode()!=NM_Standalone)SyncNetEdits(); // M4：编辑广播（全量≤256条重发，粗但正确；差分留 perf 轮）
}

bool ATemperateHillsWorld::IsGroundCoverMesh(const UStaticMesh* Mesh) const
{
    if(!Mesh||!Assets)return false;
    const auto Matches=[&](const TArray<TSoftObjectPtr<UStaticMesh>>& List)
    {
        for(const TSoftObjectPtr<UStaticMesh>& Entry:List)
            if(Entry.Get()==Mesh)return true;
        return false;
    };
    // Grass layers only. Trees are skeletal instances and rocks/shrubs are props, so
    // they are never touched here. Meadow flowers are grass-layer cover too.
    return Matches(Assets->Grass)||Matches(Assets->RainforestGrass)||Matches(Assets->RainforestCarpetGrass)||Matches(Assets->RainforestHerbs)||
        Matches(Assets->GrassAccents)||Matches(Assets->MeadowFlowers)||
        Assets->ClearingFlowers.ContainsByPredicate([&](const auto& Family){return Matches(Family.Variants);});
}

int32 ATemperateHillsWorld::DestroyGroundCover(const FVector& Center,double RadiusCm)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(HillsGroundCoverEditSweep);
    if(RadiusCm<=0||!Assets)return 0;
    const double R2=RadiusCm*RadiusCm;
    const FBox Reach(Center-FVector(RadiusCm,RadiusCm,600),Center+FVector(RadiusCm,RadiusCm,600));
    int32 Removed=0;
    // PCG owns the instances, but the components themselves are ordinary streamed
    // ISMs, so they are found the same way tree instances are removed below.
    for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
    {
        auto* Instances=*It;
        if(!Instances||Instances->GetWorld()!=GetWorld()||Instances->GetInstanceCount()<=0)continue;
        // Reject distant cells before walking the soft-reference palette. The
        // periodic edit sweep otherwise repeats that lookup for every ISM in
        // the world, once per edit, even when no grass needs removing.
        if(!Instances->Bounds.GetBox().Intersect(Reach))continue;
        if(!IsGroundCoverMesh(Instances->GetStaticMesh()))continue;
        for(int32 Index=Instances->GetInstanceCount()-1;Index>=0;--Index)
        {
            FTransform Transform;
            if(!Instances->GetInstanceTransform(Index,Transform,true))continue;
            const FVector P=Transform.GetLocation();
            if(FMath::Square(P.X-Center.X)+FMath::Square(P.Y-Center.Y)>R2)continue;
            if(FMath::Abs(P.Z-Center.Z)>500)continue;
            Instances->RemoveInstance(Index);++Removed;
        }
    }
    return Removed;
}

int32 ATemperateHillsWorld::ClearCoverForEdit(const TemperateHillsSurface::FTerrainEdit& Edit)
{
    if(Edit.Type==1)
    {
        // Shovel layers take the turf with them: clear a slightly larger box.
        const double Radius=FMath::Max(Edit.HalfX,Edit.HalfY)+20;
        return DestroyGroundCover(FVector(Edit.X,Edit.Y,Height(Edit.X,Edit.Y)),Radius);
    }
    // Crater: the scorched zone is a little wider than the bowl.
    const double Radius=Edit.Radius*1.15;
    const int32 Removed=DestroyGroundCover(FVector(Edit.X,Edit.Y,Height(Edit.X,Edit.Y)+40),Radius);
    UE_LOG(LogTemp,Display,TEXT("HILLS_GROUND_COVER removed=%d x=%.0f y=%.0f radius=%.0f"),Removed,Edit.X,Edit.Y,Radius);
    return Removed;
}

bool ATemperateHillsWorld::ApplySoilRefill(const FVector& Location,FString& OutMessage)
{
    if(!bTerrainDestructionEnabled){OutMessage=TEXT("地形破坏已暂停，暂不可挖掘或回填");return false;}
    if(!HasAuthority())return false;
    // Refill uses the same 20 cm unit as digging: one 20 cm layer over a 240 cm
    // footprint (12 x 12 cells of the 20 cm building grid), centre snapped to the grid.
    constexpr double SnapCm=20.0;
    constexpr double HalfCm=120.0;
    constexpr double LayerCm=20.0;
    constexpr int64 SoilPerLayer=2;   // symmetric with the 2 soil one topsoil dig yields
    const double CX=FMath::GridSnap(Location.X,SnapCm),CY=FMath::GridSnap(Location.Y,SnapCm);
    const double RiseLimit=TemperateHills::MaxRiseCm.GetValueOnGameThread();
    if(TerrainOffsetAt(CX,CY)>=RiseLimit)
    {OutMessage=FString::Printf(TEXT("这里已经回填到上限（%.0f cm），换一处再填"),RiseLimit);return false;}
    auto* Profile=ColdSteelAuthority::Model(this);
    if(!Profile){OutMessage=TEXT("找不到角色档案");return false;}
    FString Reason;
    if(!Profile->ConsumeItem(TEXT("soil"),SoilPerLayer,Reason))
    {OutMessage=FString::Printf(TEXT("回填一层需要 %lld 个泥土，当前不够"),SoilPerLayer);return false;}
    ApplyTerrainStep(FVector(CX,CY,Height(CX,CY)),HalfCm,HalfCm,LayerCm,
        TemperateHills::Key(int32(CX),int32(CY),uint32(Seed),9111));
    UE_LOG(LogTemp,Display,TEXT("HILLS_REFILL x=%.1f y=%.1f amount=%.1f soil=%lld"),CX,CY,LayerCm,SoilPerLayer);
    OutMessage=TEXT("回填 20 cm 泥土层");
    return true;
}
