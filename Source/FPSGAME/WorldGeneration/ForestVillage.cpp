#include "TemperateHillsWorld.h"
#include "ForestVillageMap.h"
#include "AI/NavigationSystemBase.h"
#include "ForestVillageRelief.h"
#include "ForestVillageRegion.h"
#include "RiverPilotFXSubsystem.h"
#include "TemperateHillsChapel.h"
#include "TemperateHillsGroundLayers.h"
#include "TemperateHillsStreamingPrivate.h"
#include "HillsTavernInterior.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Components/BoxComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "TemperateHillsSurface.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/Level.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/StreamableManager.h"
#include "EngineUtils.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "VT/RuntimeVirtualTexture.h"

namespace
{
// The R3 centreline begins at (-10775,25130), 70 cm inside its northern edge.
// The annex is wholly outside that Landscape. Its south row shares the original
// 1 m vertex grid; its gate faces the photographed southbound stretch.
constexpr int32 EdgeY=25200, GateX=-10800, GateY=25800;
constexpr int32 CenterX=GateX-500, CenterY=GateY+6500;
constexpr int32 MinX=CenterX-5900, MaxX=CenterX+5900, MaxY=CenterY+7400;
constexpr int32 Step=100, Columns=(MaxX-MinX)/Step+1, Rows=(MaxY-EdgeY)/Step+1;
static_assert(MinX==ForestVillageRelief::MinX && EdgeY==ForestVillageRelief::MinY &&
              Step==ForestVillageRelief::Step && Columns==ForestVillageRelief::Columns && Rows==ForestVillageRelief::Rows);

// Same six-metre chamfers as the perimeter wall. The foundation's surrounding forest shares the existing road/forest layer.
float VillageEarthWeight(const FTemperateVillageSite& Site,double X,double Y)
{
    if(!Site.bPlaced)return 0.f;
    const FVector2D Q=Site.Local(X,Y).GetAbs()*.01;
    const double Inside=FMath::Min3(65.-Q.X,50.-Q.Y,(109.-Q.X-Q.Y)*.7071067811865475);
    return float(FMath::SmoothStep(-4.5,.45,Inside));
}

// Registration already submitted the component's real PSOs, including material overrides.
// Inspect those requests during full local preload without spawning a second copy of a mesh.
bool ForestEntryPSOsReady(FTemperateHillsStreamingState& State,const ULevel& Village)
{
    auto Collect=[&State](AActor* Actor)
    {
        if(!IsValid(Actor))return;
        for(auto* Part:TInlineComponentArray<UPrimitiveComponent*>(Actor))
            if(Part->IsRegistered() && Part->IsPSOPrecaching())State.ForestPendingPSOs.Add(Part);
    };
    if(State.ForestPSOActorIndex==0)
    {
        Collect(State.ForestRegion.Get());
        Collect(State.ForestLandscape.Get());
    }
    const double Deadline=FPlatformTime::Seconds()+.001;
    while(State.ForestPSOActorIndex<Village.Actors.Num())
    {
        Collect(Village.Actors[State.ForestPSOActorIndex++]);
        if(FPlatformTime::Seconds()>=Deadline)return false;
    }
    State.ForestPendingPSOs.RemoveAllSwap([](const TWeakObjectPtr<UPrimitiveComponent>& Weak)
    {
        const auto* Part=Weak.Get();
        return !Part || !Part->IsRegistered() || !Part->IsPSOPrecaching();
    });
    return State.ForestPendingPSOs.IsEmpty();
}
}

bool ATemperateHillsWorld::LoadVillageSettlement()
{
    ApplySmithYardGround();
    const FRotator Rotation=FVector(VillageSite.Axis,0.).Rotation();
    bool Queued=false;
    auto* Level=ULevelStreamingDynamic::LoadLevelInstance(this,
        TEXT("/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage"),
        VillageSite.Ground,Rotation,Queued,TEXT("HillsAbandonedVillage"));
    if(!Queued||!Level) return false;
    Streaming->VillageLevel=Level;
    GroundMID->SetVectorParameterValue(TEXT("VillageRoadPose"),FLinearColor(
        VillageSite.Ground.X,VillageSite.Ground.Y,VillageSite.Axis.X,VillageSite.Axis.Y));
    Level->OnLevelShown.AddDynamic(this,&ATemperateHillsWorld::BindStreamedVillageBuildings);
    if(Level->IsLevelVisible()) BindStreamedVillageBuildings();
    AssembleOldChapel();
    UpdateMechanicalWorkshop();
    return true;
}

void ATemperateHillsWorld::BeginForestVillage()
{
    Streaming=MakeShared<FTemperateHillsStreamingState>();
    auto& S=*Streaming;
    HillsStreaming::AcquireStreamingBudget();
    bTerrainDestructionEnabled=false;
    TArray<FSoftObjectPath> Paths{Assets->GroundMaterial.ToSoftObjectPath(),ForestPondMaterial.ToSoftObjectPath()};
    if(GetNetMode()!=NM_DedicatedServer)
    {
        Paths.Add(ForestVillageRoadMaterial.ToSoftObjectPath());
        if(!Assets->ValleyFogClass.IsNull()) Paths.Add(Assets->ValleyFogClass.ToSoftObjectPath());
        if(!Assets->ValleyFogMaterial.IsNull()) Paths.Add(Assets->ValleyFogMaterial.ToSoftObjectPath());
    }
    TemperateHillsChapel::AddMeshPaths(Paths);
    FHillsTavernInterior::AddBlockingMeshPaths(Paths);
    TemperateVillageGround::AddMeshPaths(Paths);
    const auto AddPalette=[&Paths](const auto& Palette)
    {
        for(const auto& Ref:Palette)
            if(!Ref.IsNull()) Paths.AddUnique(Ref.ToSoftObjectPath());
    };
    AddPalette(Assets->Trees);
    Paths.Add(Assets->TrunkCollisionMesh.ToSoftObjectPath());
    AddPalette(Assets->ForestSaplings);
    AddPalette(Assets->ForestShrubs);
    AddPalette(Assets->Shrubs);
    AddPalette(Assets->Grass);
    AddPalette(Assets->GrassAccents);
    AddPalette(Assets->Rocks);
    AddPalette(Assets->MeadowFlowers);
    if(!Assets->VillageColorCache.IsNull()) Paths.Add(Assets->VillageColorCache.ToSoftObjectPath());
    if(!Assets->VillageHeightCache.IsNull()) Paths.Add(Assets->VillageHeightCache.ToSoftObjectPath());
    S.Handles.Add(UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths));
}

void ATemperateHillsWorld::TickForestVillage()
{
    if(!Streaming || Streaming->Stopping) return;
    auto& S=*Streaming;
    auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    HillsStreaming::FinishEntryBudgetIfReady(S.PreparingBudget,bReady,S.Failed,Loading);
    if(S.Failed) return;
    if(bReady)
    {
        if(!PendingResidentAppearances.IsEmpty()) TickResidentAppearanceLoads();
        if(GetNetMode()!=NM_DedicatedServer && Assets->ValleyFogClass.IsValid() && Assets->ValleyFogMaterial.IsValid()
            && GetWorld()->GetTimeSeconds()>=Streaming->NextFogTime)
        {
            BuildValleyFog();
            Streaming->NextFogTime=GetWorld()->GetTimeSeconds()+.5;
        }
        return;
    }
    auto Fail=[&](const TCHAR* Reason)
    {
        S.Failed=true;
        UE_LOG(LogTemp,Error,TEXT("FOREST_VILLAGE %s"),Reason);
        if(Loading) Loading->FailPreparation(FText::FromString(Reason));
    };
    if(!S.GroundReady)
    {
        if(S.Handles[0] && !S.Handles[0]->HasLoadCompleted()) return;
        if(!Assets->GroundMaterial.Get() || !FHillsTavernInterior::AreBlockingMeshesLoaded())
        { Fail(TEXT("林道村庄地面或酒馆碰撞资源加载失败。")); return; }
        ALandscapeProxy* Land=nullptr;
        for(TActorIterator<ALandscapeProxy> It(GetWorld());It;++It)
            if(It->GetHeightAtLocation(FVector(GateX,EdgeY-1,0)).IsSet()) { Land=*It; break; }
        if(!Land)
        {
            for(const ULevelStreaming* Level:GetWorld()->GetStreamingLevels())
                if(Level && Level->GetLevelStreamingState()==ELevelStreamingState::FailedToLoad)
                { Fail(TEXT("测试林道子关卡加载失败。")); break; }
            return;
        }
        for(TActorIterator<AForestVillageRegion> It(GetWorld());It;++It)
            if(It->HasGround()) { S.ForestRegion=*It; break; }
        if(!S.ForestRegion.IsValid()) { Fail(TEXT("村庄外围地形数据未加载。")); return; }
        // The donor PCG lives in a shared sublevel. Scope its wind and draw distances to this map.
        for(AActor* FoliageActor:Land->GetLevel()->Actors)
            if(IsValid(FoliageActor))
                for(auto* Part:TInlineComponentArray<UInstancedStaticMeshComponent*>(FoliageActor))
                {
                    const UStaticMesh* Mesh=Part->GetStaticMesh();
                    if(!Mesh) continue;
                    const bool Canopy=Mesh->GetName().StartsWith(TEXT("SM_EuropeanHornbeam_Forest_"));
                    const bool StudyRock=Mesh->GetName().EndsWith(TEXT("_tier_1"));
                    if(Canopy || StudyRock)
                    {
                        TArray<int32> Replaced;
                        for(int32 I=Part->GetInstanceCount()-1;I>=0;--I)
                        {
                            FTransform T;
                            if(Part->GetInstanceTransform(I,T,true) && (Canopy?S.ForestRegion->ReplacesStudyTree(T.GetLocation()):S.ForestRegion->ReplacesStudyRock(T.GetLocation())))
                                Replaced.Add(I);
                        }
                        if(!Replaced.IsEmpty()) Part->RemoveInstances(Replaced,true);
                    }
                    if(!Canopy && !Mesh->GetName().StartsWith(TEXT("SM_CommonHazel_Forest_"))) continue;
                    const int32 End=Canopy?36000:16000;
                    Part->SetWorldPositionOffsetDisableDistance(Canopy?8000:4000);
                    Part->SetEvaluateWorldPositionOffsetInRayTracing(false);
                    if(!Canopy) Part->SetVisibleInRayTracing(false);
                    if(Part->InstanceEndCullDistance==0 || Part->InstanceEndCullDistance>End)
                        Part->SetCullDistances(End*3/4,End);
                }
        ForestWaterPlan=S.ForestRegion->GetWoodlandWater();
        if(!ForestWaterPlan->Pools.IsEmpty() && GetNetMode()!=NM_DedicatedServer)
            if(auto* FX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())
            {
                FX->BindForestWater(this,ForestWaterPlan,ForestPondMaterial.Get());
                for(TActorIterator<AForestVillagePoolSurface> It(GetWorld());It;++It)
                    It->UseWaterMaterial(FX->GetForestWaterMaterial());
            }
        S.ForestLandscape=Land;
        S.ForestBorderHeights.Reset(Columns);
        // On the outermost grid edge the landscape query may select the absent
        // neighbour component. Approach it from inside the final quad.
        for(int32 I=0;!S.ForestRegion->HasSitedHill() && I<Columns;++I)
        {
            const auto Z=Land->GetHeightAtLocation(FVector(MinX+I*Step,EdgeY-.01,0));
            if(!Z.IsSet()) { Fail(TEXT("无法读取林道北侧的地形接缝。")); return; }
            S.ForestBorderHeights.Add(Z.GetValue());
        }
        VillageSite.bHilltop=true;
        VillageSite.bPlaced=true;
        VillageSite.bSideLane=true;
        VillageSite.PadHalfX=7000.;
        VillageSite.PadHalfY=5500.;
        VillageSite.Shoulder=400.;
        VillageSite.Axis=FVector2D(0,-1);
        const FIntPoint Origin=S.ForestRegion->GetSettlementMinM();
        const double Datum=S.ForestRegion->HasSitedHill()?S.ForestRegion->GetSettlementDatumCm():S.ForestBorderHeights[(GateX-MinX)/Step];
        VillageSite.Ground=FVector(Origin.X*Step+(CenterX-MinX),Origin.Y*Step+(CenterY-EdgeY),Datum);
        VillageSite.bSmithYardRepaired=bVillageBlacksmithRepaired;
        ChapelSite=VillageSite.ChapelLot();
        bSettlementPlanned=true;
        GroundMID=UMaterialInstanceDynamic::Create(Assets->GroundMaterial.Get(),this);
        BuildForestVillageGround();
        // The two original footprints now open onto the surrounding terrain.
        auto Boundary=[this](FVector2D A,FVector2D B)
        {
            auto* Wall=NewObject<UBoxComponent>(this);
            AddInstanceComponent(Wall);
            Wall->SetupAttachment(RootComponent);
            Wall->SetMobility(EComponentMobility::Static);
            Wall->SetRelativeLocation(FVector((A+B)*.5,VillageSite.Ground.Z));
            Wall->SetBoxExtent(FVector((A-B).GetAbs()*.5+FVector2D(10.,10.),12000.));
            Wall->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            Wall->SetCollisionResponseToAllChannels(ECR_Ignore);
            Wall->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
            Wall->SetCanEverAffectNavigation(false);
            Wall->RegisterComponent();
        };
        const auto B=ForestVillageMap::Bounds();
        Boundary(B.Min,{B.Max.X,B.Min.Y});
        Boundary({B.Max.X,B.Min.Y},B.Max);
        Boundary(B.Max,{B.Min.X,B.Max.Y});
        Boundary({B.Min.X,B.Max.Y},B.Min);
        PrepareVillageGroundCache();
        if(!LoadVillageSettlement()) { Fail(TEXT("村庄建筑子关卡加载失败。")); return; }
        S.GroundReady=true;
        if(Loading) Loading->UpdatePreparation(FText::FromString(TEXT("正在接入村庄建筑与居民…")),.7f);
    }
    const auto* Level=S.VillageLevel.Get();
    if(Level && Level->GetLevelStreamingState()==ELevelStreamingState::FailedToLoad)
    { Fail(TEXT("村庄建筑子关卡加载失败。")); return; }
    if(!Level || !Level->IsLevelVisible()) return;
    bSurfaceReady=true;
    TickResidentAppearanceLoads();
    if(Loading && !GUsingNullRHI && GetNetMode()!=NM_DedicatedServer && Loading->IsCompletePreloadSelected())
    {
        if(!PendingResidentAppearances.IsEmpty())
        {
            Loading->UpdatePreparation(FText::FromString(TEXT("正在分批准备村庄居民…")),.96f);
            return;
        }
        if(!ForestEntryPSOsReady(S,*Level->GetLoadedLevel()))
        {
            Loading->UpdatePreparation(FText::FromString(TEXT("正在准备村庄与丘陵地形的渲染管线…")),.98f);
            return;
        }
    }
    bReady=true;
    if(Loading) Loading->CompletePreparation();
}

uint32 ATemperateHillsWorld::GetMapSurfaceRevision() const
{
    if(!IsForestVillage()) return TerrainEditRevision;
    uint32 Layout=HashCombineFast(VillagePlansUnlocked,GetTypeHash(VillageSite.Ground));
    Layout=HashCombineFast(Layout,uint32(bVillageWallRepaired) | (uint32(bVillageBlacksmithRepaired)<<1) |
        (uint32(bVillageBakeryRepaired)<<2) | (uint32(bVillageGunshopRepaired)<<3) | (uint32(bGarrisonMechanics)<<4));
    return HashCombineFast(Layout,TerrainEditRevision);
}

double ATemperateHillsWorld::SettlementRoadWeight(double X,double Y) const
{
    const FVector2D Local=VillageSite.Local(X,Y);
    double Road=TemperateHillsGround::VillageTrack(VillageSite,X,Y,Seed);
    for(const auto& R:TemperateVillageLayout::Roads)
    {
        const FVector2D From=Local-FVector2D(R.X,R.Y),Span(R.DX,R.DY);
        const double T=FMath::Clamp(FVector2D::DotProduct(From,Span)/Span.SizeSquared(),0.,1.);
        Road=FMath::Max(Road,1.-FMath::SmoothStep(R.HalfWidth-50.,R.HalfWidth+50.,(From-T*Span).Size()));
    }
    return Road;
}

FColor ATemperateHillsWorld::ForestMapLayers(double X,double Y,double GroundZ) const
{
    const auto* Region=Streaming?Streaming->ForestRegion.Get():nullptr;
    double Road=Region?Region->MapRoadWeight(X,Y):0.;
    const bool Wet=SampleForestWater(X,Y).Wet;
    bool Building=false;
    const FVector2D Local=VillageSite.Local(X,Y);
    if(VillageSite.bPlaced && FMath::Abs(Local.X)<=VillageSite.PadHalfX && FMath::Abs(Local.Y)<=VillageSite.PadHalfY)
    {
        Road=FMath::Max(Road,SettlementRoadWeight(X,Y));
        const auto* Level=Streaming->VillageLevel.Get();
        FHitResult Hit;
        const FVector2D FromWorkshop=Local-FTemperateVillageSite::WorkshopCenter;
        Building=bGarrisonMechanics && FMath::Abs(FromWorkshop.X)<=337. && FMath::Abs(FromWorkshop.Y)<=619.;
        if(!Building && Level && Level->IsLevelVisible() && GetWorld()->LineTraceSingleByObjectType(Hit,
            FVector(X,Y,GroundZ+6000.),FVector(X,Y,GroundZ+140.),FCollisionObjectQueryParams(ECC_WorldStatic)) &&
            Hit.GetActor() && Hit.GetActor()->GetLevel()==Level->GetLoadedLevel()) Building=true;
    }
    return FColor(uint8(FMath::RoundToInt(255.*Road)),Wet?255:0,Building?255:0,uint8(FMath::RoundToInt(255.f*VillageEarthWeight(VillageSite,X,Y))));
}

double ATemperateHillsWorld::ForestVillageHeight(double X,double Y) const
{
    if(!Streaming) return 0.;
    const auto& S=*Streaming;
    const FVector2D Shift=VillageSite.bPlaced?FVector2D(VillageSite.Ground)-FVector2D(CenterX,CenterY):FVector2D::ZeroVector;
    const double LocalX=X-Shift.X,LocalY=Y-Shift.Y;
    if(LocalY<EdgeY || LocalX<MinX || LocalX>MaxX || LocalY>MaxY)
    {
        if(FMath::Abs(X)<=EdgeY && FMath::Abs(Y)<=EdgeY)
            if(const auto* Landscape=S.ForestLandscape.Get())
                if(const auto Z=Landscape->GetHeightAtLocation(FVector(
                    FMath::Clamp(X,-25199.99,25199.99),FMath::Clamp(Y,-25199.99,25199.99),0));Z.IsSet()) return Z.GetValue();
        if(const auto* Region=S.ForestRegion.Get()) return Region->GroundHeight(X,Y);
        return 0.;
    }
    return ForestVillageRelief::SurfaceAt(S.ForestVillageGroundCm,LocalX,LocalY);
}

void ATemperateHillsWorld::GetForestStandingTrees(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!IsForestVillage() || !Streaming || !Streaming->ForestRegion.IsValid())return;
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/1200.);Y<=FMath::FloorToInt(Bounds.Max.Y/1200.);++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/1200.);X<=FMath::FloorToInt(Bounds.Max.X/1200.);++X)
    {
        FTemperatePlacement P;
        if(TreeCandidate(X,Y,P) && Bounds.IsInsideXY(P.Transform.GetLocation()) && !IsProductionDepleted(0,P.CandidateId))
            Out.Add(P);
    }
}

bool ATemperateHillsWorld::ForestTreeCandidate(int32 X,int32 Y,FTemperatePlacement& P) const
{
    const auto* Region=Streaming?Streaming->ForestRegion.Get():nullptr;
    const auto* Site=Region?Region->HarvestTreeSite({X,Y}):nullptr;
    if(!Site || !Assets || Assets->Trees.Num()<8)return false;
    const uint32 K=TemperateHillsSurface::Key(X,Y,uint32(Seed),2053);
    // Poplar A-D and European beech A-D have matching authored fall/stump profiles.
    const int32 TreeSlot=(K%5==0?0:4)+int32((K>>9)&3);
    const auto* Mesh=Assets->Trees[TreeSlot].Get(); if(!Mesh)return false;
    const double Scale=.82+.25*TemperateHillsSurface::Unit(K+71);
    P.CandidateId=(uint64(uint32(X))<<32)|uint32(Y);
    P.Key=K; P.Mesh=Assets->Trees[TreeSlot].ToSoftObjectPath();
    P.Transform=FTransform(FRotator(0,Site->W,0),FVector(Site->X,Site->Y,Site->Z-8.-Mesh->GetImportedBounds().GetBox().Min.Z*Scale),FVector(Scale));
    return true;
}

void ATemperateHillsWorld::BuildForestVillageGround()
{
    using namespace UE::Geometry;
    auto* Region=Streaming->ForestRegion.Get();
    const auto Origin=Region->GetSettlementMinM()*Step;
    const bool Hill=Region->HasSitedHill();
    // Re-evaluate the old hand-graded yards when their repair state changes.
    // The final vertex table drives both mesh sections and all village height queries.
    auto& Heights=Streaming->ForestVillageGroundCm;
    Heights.SetNumUninitialized(Rows*Columns);
    for(int32 J=0;J<Rows;++J)
    {
        const double Y=Origin.Y+J*Step;
        const double Blend=FMath::SmoothStep(0.,double(GateY-EdgeY),double(J*Step));
        for(int32 I=0;I<Columns;++I)
        {
            const double X=Origin.X+I*Step;
            const double Pad=ChapelSite.Grade(X,Y,VillageSite.Ground.Z)+TemperateVillageGround::Offset(VillageSite,X,Y);
            const double Foundation=Hill?Pad:FMath::Lerp(Streaming->ForestBorderHeights[I],Pad,Blend);
            double Z=Foundation+Region->SettlementOffsetCm(I,J);
            if(Region->GetReferenceSurface())
            {
                const int32 Rim=FMath::Min(FMath::Min(I,Columns-1-I),FMath::Min(J,Rows-1-J));
                if(Rim<3) Z=FMath::Lerp(Region->GroundHeight(X,Y),Z,FMath::SmoothStep(0.,3.,double(Rim)));
            }
            Heights[J*Columns+I]=float(Z);
        }
    }
    // Grade the plot to its own road shoulder before building the visible and physical terrain.
    const auto Center=FTemperateVillageSite::WorkshopCenter;
    const FVector2D Roadside=VillageSite.World(Center.X,Center.Y+835.);
    const float ShoulderZ=float(ForestVillageHeight(Roadside.X,Roadside.Y));
    for(int32 J=0;J<Rows;++J)
    {
        for(int32 I=0;I<Columns;++I)
        {
            const FVector2D Local=VillageSite.Local(Origin.X+I*Step,Origin.Y+J*Step);
            const double Edge=FTemperateVillageSite::WorkshopEdge(Local);
            if(Edge>=180. || Local.Y>=320.)continue;
            const double Weight=(1.-FMath::SmoothStep(0.,180.,Edge))*(1.-FMath::SmoothStep(260.,320.,Local.Y));
            float& Z=Heights[J*Columns+I];
            Z=FMath::Lerp(Z,ShoulderZ,float(Weight));
        }
    }
    UMaterialInterface* Reference=Region->GetReferenceSurface();
    UMaterialInterface* TownRoad=Reference?ForestVillageRoadMaterial.Get():nullptr;
    UMaterialInterface* Gate=Reference?nullptr:Region->GetGateSurface();
    constexpr int32 ApronRows=8;
    auto BuildPart=[&](int32 FirstRow,int32 LastRow,bool IsApron)
    {
        FDynamicMesh3 Mesh;
        Mesh.EnableAttributes();
        auto* Attr=Mesh.Attributes();
        Attr->SetNumUVLayers(TownRoad?6:Reference?5:IsApron?7:3);
        Attr->EnablePrimaryColors();
        for(int32 J=FirstRow;J<=LastRow;++J)
            for(int32 I=0;I<Columns;++I)
            {
                const double X=Origin.X+I*Step,Y=Origin.Y+J*Step,Z=Heights[J*Columns+I];
                const FVector N=TemperateHillsSurface::NumericNormal([this](double Px,double Py)
                { return ForestVillageHeight(Px,Py); },X,Y);
                Mesh.AppendVertex(FVector3d(X,Y,Z));
                const auto L=TemperateHillsGround::Layers(X,Y,Z,N,Seed,{},0.,EcologyProfile(),true,VillageSite,nullptr);
                Attr->PrimaryNormals()->AppendElement(FVector3f(N));
                const float LX=X*.01+252.,LY=Y*.01+252.,LZ=(Z-100.)*.1;
                Attr->PrimaryUV()->AppendElement(Reference?FVector2f(LX,LY):L.UV);
                Attr->GetUVLayer(1)->AppendElement(Reference?FVector2f(LX,LZ):L.Habitat);
                Attr->GetUVLayer(2)->AppendElement(Reference?FVector2f(LY,LZ):L.Upland);
                if(Reference)
                {
                    auto Paint=Region->ReferencePaintAt(I,J);
                    const int32 Rim=FMath::Min(FMath::Min(I,Columns-1-I),FMath::Min(J,Rows-1-J));
                    const float Interior=VillageEarthWeight(VillageSite,X,Y)*FMath::SmoothStep(0.f,2.f,float(Rim));
                    if(TownRoad)
                    {
                        Paint.X*=1.f-Interior; // The original road mask draws the interior streets.
                        Attr->GetUVLayer(5)->AppendElement(FVector2f(Interior,0.f));
                    }
                    else
                        Paint.X=FMath::Lerp(Paint.X,FMath::Max(Paint.X,float(SettlementRoadWeight(X,Y))),Interior);
                    Attr->GetUVLayer(3)->AppendElement(FVector2f::ZeroVector);
                    Attr->GetUVLayer(4)->AppendElement(Paint);
                }
                Attr->PrimaryColors()->AppendElement(L.Color);
                if(IsApron)
                {
                    const float Mix=1.f-FMath::SmoothStep(4.f,float(ApronRows),float(J));
                    Attr->GetUVLayer(3)->AppendElement(FVector2f::ZeroVector); // Quarry coverage in the old village ground.
                    Attr->GetUVLayer(4)->AppendElement(Region->GetGatePaint(I,J));
                    Attr->GetUVLayer(5)->AppendElement(FVector2f(X*.01,Y*.01));
                    Attr->GetUVLayer(6)->AppendElement(FVector2f(Mix,0.f));
                }
            }
        auto Triangle=[&](int32 A,int32 B,int32 C)
        {
            const FIndex3i Indices(A,B,C);
            const int32 Id=Mesh.AppendTriangle(A,B,C);
            Attr->PrimaryNormals()->SetTriangle(Id,Indices);
            for(int32 Layer=0;Layer<Attr->NumUVLayers();++Layer) Attr->GetUVLayer(Layer)->SetTriangle(Id,Indices);
            Attr->PrimaryColors()->SetTriangle(Id,Indices);
        };
        for(int32 J=0;J<LastRow-FirstRow;++J)
            for(int32 I=0;I<Columns-1;++I)
            {
                const int32 A=J*Columns+I;
                Triangle(A,A+Columns+1,A+1);
                Triangle(A,A+Columns,A+Columns+1);
            }
        const FName Name=IsApron?TEXT("ForestVillageGateApron"):TEXT("ForestVillageFoundation");
        auto* Ground=FindObject<UDynamicMeshComponent>(this,*Name.ToString());
        if(!Ground)
        {
            Ground=NewObject<UDynamicMeshComponent>(this,Name);
            AddInstanceComponent(Ground);
            Ground->SetupAttachment(RootComponent);
            Ground->SetMobility(EComponentMobility::Static);
            Ground->ComponentTags.Add(TEXT("HillsGround"));
            Ground->SetCanEverAffectNavigation(HasAuthority());
            Ground->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
            UMaterialInterface* Mat=Reference?Reference:GroundMID.Get();
            if(TownRoad || IsApron)
            {
                auto* RoadMID=UMaterialInstanceDynamic::Create(TownRoad?TownRoad:Gate,this);
                RoadMID->SetVectorParameterValue(TEXT("VillageRoadPose"),FLinearColor(
                    VillageSite.Ground.X,VillageSite.Ground.Y,VillageSite.Axis.X,VillageSite.Axis.Y));
                Mat=RoadMID;
            }
            Ground->SetMaterial(0,Mat);
            Ground->SetComplexAsSimpleCollisionEnabled(true,false);
            Ground->SetCollisionProfileName(TEXT("BlockAll"));
            Ground->SetDeferredCollisionUpdatesEnabled(true,false);
            Ground->RegisterComponent();
            Terrain.Add(Ground);
        }
        Ground->SetMesh(MoveTemp(Mesh));
        Ground->UpdateCollision(false);
        if(HasAuthority())FNavigationSystem::UpdateComponentData(*Ground);
        InvalidateVillageGroundCache(Ground);
    };
    BuildPart(Gate?ApronRows:0,Rows-1,false);
    if(Gate) BuildPart(0,ApronRows,true);
    ++TerrainEditRevision;
}
