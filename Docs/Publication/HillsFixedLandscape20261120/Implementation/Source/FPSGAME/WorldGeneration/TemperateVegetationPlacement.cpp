#include "TemperateVegetationPlacement.h"
#include "TemperateHillsWorld.h"
#include "TemperateVillagePlanting.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace HillsVegetation
{
using EKind=ETemperatePlantKind;
bool Woody(EKind Kind){return Kind==EKind::Sapling||Kind==EKind::Shrub;}
bool Low(EKind Kind){return Kind==EKind::Grass||Kind==EKind::GroundCover||Kind==EKind::Reed;}
FBox BoundsOf(const UObject* Object)
{
    if(const auto* Mesh=Cast<UStaticMesh>(Object))
    {
        FBox Box=Mesh->GetBoundingBox();
        // Wind/culling padding is not geometry below the roots. Using that
        // padding as Min.Z would lift a correctly authored plant into the air.
        Box.Min+=Mesh->GetNegativeBoundsExtension();Box.Max-=Mesh->GetPositiveBoundsExtension();
        return Box;
    }
    if(const auto* Mesh=Cast<USkeletalMesh>(Object))return Mesh->GetImportedBounds().GetBox();
    return FBox(ForceInit);
}
FVector LocalRoot(const FBox& Box,EKind Kind)
{
    // Single woody stems use their authored pivot; a grass cluster has several
    // stems spread around the bounds centre. Leaf crowns are not root discs.
    return Low(Kind)?FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z):FVector(0,0,Box.Min.Z);
}
double TreeRootRadius(double Height){return FMath::Clamp(Height*.03,28.0,85.0);}

struct FInfo{FBox Box=FBox(ForceInit);EKind Kind=EKind::None;int32 Layer=3;};
struct FCatalog
{
    TMap<FSoftObjectPath,FInfo> Info;
    double UnderstoryReach=0,LowReach=0,LowRootOffset=0;
    template<class T> void Add(const TArray<TSoftObjectPtr<T>>& List,EKind Kind,int32 Layer,double MaxHeight=0)
    {
        for(const auto& Ref:List)if(const auto* Mesh=Ref.Get())
        {
            FInfo Entry;Entry.Box=BoundsOf(Mesh);Entry.Kind=Kind;Entry.Layer=Layer;
            Info.Add(Ref.ToSoftObjectPath(),Entry);
            const FVector Root=LocalRoot(Entry.Box,Kind);
            // Skeletal wind bounds are rendering margins, not plant height.
            double Height=Mesh->GetBounds().BoxExtent.Z*2;
            if constexpr(std::is_same_v<T,USkeletalMesh>)Height=Entry.Box.GetSize().Z;
            const double Scale=MaxHeight>0?MaxHeight/FMath::Max(1.0,Height):1.30;
            const double Radius=(Entry.Box.Min-Root).GetAbs().ComponentMax((Entry.Box.Max-Root).GetAbs()).Size();
            // Bounds include shifted pivots and tilted bases. A visible circle
            // is centred at the real root, but cell ownership uses the old XY.
            const double Reach=(Root.Size()+Radius)*Scale;
            if(Layer!=3)
            {
                UnderstoryReach=FMath::Max(UnderstoryReach,Reach);
            }
            else{LowReach=FMath::Max(LowReach,Reach);LowRootOffset=FMath::Max(LowRootOffset,Root.Size()*Scale);}
        }
    }
    explicit FCatalog(const UTemperateHillsAssets& Assets,bool VillagePlanting)
    {
        Add(Assets.Grass,EKind::Grass,3);Add(Assets.GrassAccents,EKind::Grass,3);
        Add(Assets.RainforestGrass,EKind::Grass,3);
        Add(Assets.RainforestCarpetGrass,EKind::Grass,3);
        // The third slot is the bank sedge. Its roots can stand in the shallow
        // lip; treating all three as dry grass vetoed every emergent candidate.
        if(Assets.RainforestGrass.IsValidIndex(2))
            if(auto* Sedge=Info.Find(Assets.RainforestGrass[2].ToSoftObjectPath()))Sedge->Kind=EKind::Reed;
        Add(Assets.RainforestHerbs,EKind::GroundCover,3);
        for(const auto& Family:Assets.ClearingFlowers)Add(Family.Variants,EKind::Grass,3);
        Add(Assets.MeadowFlowers,EKind::Grass,3);Add(Assets.RiverGroundCover,EKind::GroundCover,3,44);
        Add(Assets.RiverReeds,EKind::Reed,3,195);Add(Assets.RiverBankGrasses,EKind::Grass,3,103);
        Add(Assets.RiverUnderstory,EKind::GroundCover,3,64);
        Add(Assets.Shrubs,EKind::Shrub,2,VillagePlanting?380.:240.);
        Add(Assets.WetBankSaplings,EKind::Sapling,2,260.);
        Add(Assets.ForestSaplings,EKind::Sapling,4,VillagePlanting?TemperateVillagePlanting::MaxSaplingHeight:275.);
        Add(Assets.ForestShrubs,EKind::Shrub,4,VillagePlanting?380.:235.);Add(Assets.ForestFerns,EKind::Fern,4,105);
    }
};

struct FPlant
{
    FTemperatePlacement Placement;
    EKind Kind=EKind::None;
    int32 Layer=0;
    FVector2D Root=FVector2D::ZeroVector;
    double Radius=0,Core=0;
    uint32 Priority=0;
};
FPlant Describe(const FTemperatePlacement& P,const FInfo& Info)
{
    FPlant Plant;Plant.Placement=P;Plant.Kind=Info.Kind;Plant.Layer=Info.Layer;
    Plant.Root=FVector2D(P.Transform.TransformPosition(LocalRoot(Info.Box,Info.Kind)));
    const FBox Box=Info.Box.TransformBy(P.Transform);
    Plant.Radius=FMath::Max(FMath::Max(FMath::Abs(Box.Min.X-Plant.Root.X),FMath::Abs(Box.Max.X-Plant.Root.X)),
        FMath::Max(FMath::Abs(Box.Min.Y-Plant.Root.Y),FMath::Abs(Box.Max.Y-Plant.Root.Y)));
    const double R=Plant.Radius;
    Plant.Core=Info.Kind==EKind::Tree?TreeRootRadius(Info.Box.GetSize().Z*P.Transform.GetScale3D().Z):
        Info.Kind==EKind::Sapling?FMath::Max(12.0,R*.24):Info.Kind==EKind::Shrub?FMath::Max(18.0,R*.38):
        Info.Kind==EKind::Fern?FMath::Max(6.0,R*.26):
        Info.Kind==EKind::Reed?FMath::Clamp(R*.18,5.0,28.0):FMath::Clamp(R*.18,3.0,18.0);
    Plant.Priority=TemperateHillsSurface::Mix(P.Key^0x3c6ef372U);
    return Plant;
}
bool Earlier(const FPlant& A,const FPlant& B)
{
    if(A.Priority!=B.Priority)return A.Priority<B.Priority;
    if(A.Layer!=B.Layer)return A.Layer<B.Layer;
    return A.Placement.CandidateId<B.Placement.CandidateId;
}
double PeerGap(const FPlant& A,const FPlant& B)
{
    const double Core=A.Core+B.Core;
    return Woody(A.Kind)?FMath::Max(Core,.65*(A.Radius+B.Radius)):
        A.Kind==EKind::Fern?FMath::Max(Core,.42*(A.Radius+B.Radius)):Core;
}

// Centres occur in exactly one bucket. Queries cover both radii, so there are
// no duplicate neighbours and no all-plants-against-all-plants pass.
struct FIndex
{
    TArray<FPlant> Plants;
    TMap<FIntPoint,TArray<int32>> Cells;
    double MaxRadius=0;
    static constexpr double CellSize=500;
    void Add(FPlant P)
    {
        MaxRadius=FMath::Max(MaxRadius,FMath::Max(P.Radius,P.Core));
        const FIntPoint Cell(FMath::FloorToInt(P.Root.X/CellSize),FMath::FloorToInt(P.Root.Y/CellSize));
        Cells.FindOrAdd(Cell).Add(Plants.Add(MoveTemp(P)));
    }
    bool Any(const FPlant& P,double Extra,TFunctionRef<bool(const FPlant&)> Test) const
    {
        const double Reach=FMath::Max(P.Radius,P.Core)+MaxRadius+Extra;
        for(int32 Y=FMath::FloorToInt((P.Root.Y-Reach)/CellSize);Y<=FMath::FloorToInt((P.Root.Y+Reach)/CellSize);++Y)
        for(int32 X=FMath::FloorToInt((P.Root.X-Reach)/CellSize);X<=FMath::FloorToInt((P.Root.X+Reach)/CellSize);++X)
            if(const auto* Indices=Cells.Find(FIntPoint(X,Y)))for(const int32 I:*Indices)
                if(Test(Plants[I]))return true;
        return false;
    }
};
bool ClearOfTrees(const FPlant& P,const FIndex& Trees)
{
    double Chance=1;
    const bool Blocked=Trees.Any(P,120,[&](const FPlant& Tree)
    {
        const double D=FVector2D::Distance(P.Root,Tree.Root);
        const double Hard=Tree.Core+FMath::Max(P.Core,P.Radius*(Low(P.Kind)?.55:.75))+5;
        if(D<Hard)return true;
        Chance=FMath::Min(Chance,FMath::Lerp(.65,1.0,FMath::SmoothStep(Hard,Hard+90,D)));
        return false;
    });
    return !Blocked&&TemperateHillsSurface::Unit(P.Placement.Key+3407)<Chance;
}
bool ClearOfUpperLayer(const FPlant& P,const FIndex& Upper)
{
    double Chance=1;
    const bool Blocked=Upper.Any(P,30,[&](const FPlant& U)
    {
        const double D=FVector2D::Distance(P.Root,U.Root);
        const double Hard=U.Core+(P.Kind==EKind::Fern?FMath::Max(P.Core,P.Radius*.55):P.Core);
        if(D<Hard)return true;
        const double Outer=FMath::Max(Hard+25,U.Radius+P.Radius*.45);
        const double Floor=P.Kind==EKind::Fern?.55:(U.Kind==EKind::Fern?.40:.25);
        Chance=FMath::Min(Chance,FMath::Lerp(Floor,1.0,FMath::SmoothStep(Hard,Outer,D)));
        return false;
    });
    // Smooth, seeded thinning around the dense centre, rather than treating the
    // entire leaf silhouette as a solid collision body and drawing empty rings.
    return !Blocked&&TemperateHillsSurface::Unit(P.Placement.Key+3413)<Chance;
}
bool SurvivesPeers(const FPlant& P,const FIndex& Candidates)
{
    return !Candidates.Any(P,0,[&](const FPlant& Other)
    {return Earlier(Other,P)&&FVector2D::DistSquared(P.Root,Other.Root)<FMath::Square(PeerGap(P,Other));});
}

void SelectPeers(const FIndex& Candidates,FIndex& Accepted)
{
    for(const auto& P:Candidates.Plants)
        if(SurvivesPeers(P,Candidates))Accepted.Add(P);
}
bool Owned(const FPlant& P,const FBox& Bounds)
{
    const FVector At=P.Placement.Transform.GetLocation();
    return At.X>=Bounds.Min.X&&At.X<Bounds.Max.X&&At.Y>=Bounds.Min.Y&&At.Y<Bounds.Max.Y;
}
struct FNeighborhood
{
    FNeighborhood(const UTemperateHillsAssets& InAssets,bool VillagePlanting):Catalog(InAssets,VillagePlanting){}
    FCatalog Catalog;
    FIndex Trees,Wood,Ferns;
    FBox CellBounds,SupportArea;
    double GrassHalo() const {return 2*Catalog.LowRootOffset+60.;}
    // Index floor groups by row once. A village-sized view otherwise scans
    // every twig and pebble for each 2 m strip.
    static int32 FloorRow(double Y){return FMath::FloorToInt(Y/800.);}
    TMap<int32,TArray<FTemperatePlacement>> FloorRows;
    // Wood and Ferns are immutable once peer resolution finishes. Index their
    // final origins only when a caller actually requests sliced upper layers.
    TMap<int32,TArray<const FPlant*>> UnderstoryRows;
    bool bUnderstoryRowsReady=false;
    TSharedPtr<HillsPlacement::FVegetationRockMask> RockMask;
    enum class EStage { Trees, Shrubs, Understory, NurseLogs, TreeCompanions, RockCompanions, Ground, Fit, Resolve, Done };
    EStage Stage=EStage::Trees;
    int32 NextFit=0,QuarryGroundRows=0;
    TArray<FTemperatePlacement> TreeSupports,Raw,Ground,Accepted;

};
}

bool ATemperateHillsWorld::FitVegetationPlacement(FTemperatePlacement& P,const FBox& Box,ETemperatePlantKind Kind) const
{
    using namespace HillsVegetation;
    if(!Box.IsValid)return false;
    const FVector Origin=P.Transform.GetLocation();
    const FVector Root=P.Transform.TransformVector(LocalRoot(Box,Kind));
    const FVector Size=Box.GetSize()*P.Transform.GetScale3D();
    const double R=FMath::Max(Size.X,Size.Y)*.5;
    const double RootRadius=Kind==EKind::Tree?TreeRootRadius(Size.Z):
        Kind==EKind::Sapling?FMath::Clamp(R*.12,8.0,28.0):Kind==EKind::Shrub?FMath::Clamp(R*.20,12.0,45.0):
        Kind==EKind::Fern?FMath::Clamp(R*.16,6.0,22.0):Kind==EKind::Reed?FMath::Clamp(R*.18,6.0,28.0):FMath::Clamp(R*.55,6.0,85.0);
    const double MaxRelief=Kind==EKind::Tree?FMath::Clamp(RootRadius*.85,24.0,72.0):
        Woody(Kind)?FMath::Clamp(Size.Z*.12,12.0,32.0):Kind==EKind::Fern?FMath::Clamp(Size.Z*.20,8.0,18.0):
        Kind==EKind::Reed?20.0:Kind==EKind::GroundCover?16.0:FMath::Clamp(Size.Z*.18,5.0,14.0);
    const double WaterMargin=Kind==EKind::Reed?-22:Kind==EKind::GroundCover?-3:
        Woody(Kind)?30:Kind==EKind::Tree?15:Kind==EKind::Fern?12:6;
    const FVector Up=P.Transform.GetRotation().GetUpVector();
    const double Half=SizeMeters*50-100;
    double LowZ=DBL_MAX,HighZ=-DBL_MAX;
    const FVector2D Directions[]={{0,0},{1,0},{-1,0},{0,1},{0,-1}};
    for(const FVector2D& Direction:Directions)
    {
        const FVector2D Delta=Direction*RootRadius;
        const double X=Origin.X+Root.X+Delta.X,Y=Origin.Y+Root.Y+Delta.Y;
        if(FMath::Abs(X)>Half||FMath::Abs(Y)>Half)return false;
        const auto River=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
        // Emergent reeds and bank cover keep their existing wet-edge habitat;
        // the abstract dry trail must not erase the planted water margin.
        const bool WetEdge=(Kind==EKind::Reed||Kind==EKind::GroundCover)&&River.Bank>.015&&River.Distance<River.HalfWidth+650;
        if(!WetEdge&&PathDistance(X,Y)<(Woody(Kind)||Kind==EKind::Tree?350:210))return false;
        const double Z=Height(X,Y);
        // Newly selected pools share this same plan with water rendering and
        // contacts. Mature roots/terrestrial plants never emerge in a pool.
        const auto Pool=SampleForestWater(X,Y);
        const double PoolMargin=Kind==EKind::Reed?-9.:WaterMargin;
        if(Pool.Wet&&Z<Pool.WaterZ+PoolMargin)return false;
        if(River.Bank>0&&Z<River.WaterZ+WaterMargin)return false;
        const double LocalPlaneZ=Root.Z-(Up.X*Delta.X+Up.Y*Delta.Y)/FMath::Max(.1,Up.Z);
        const double Support=Z-LocalPlaneZ;
        LowZ=FMath::Min(LowZ,Support);HighZ=FMath::Max(HighZ,Support);
        if(HighZ-LowZ>MaxRelief)return false;
    }
    const double Burial=Kind==EKind::Tree?FMath::Clamp(Size.Z*.004,3.0,10.0):Woody(Kind)?3.0:1.5;
    // On a sampled convex rib the visible triangle can cut below the height
    // function. Keep a candidate's grounded root when fitting its footprint.
    const double FittedZ=P.bHasTriangleSupport?FMath::Min(Origin.Z,LowZ-Burial):LowZ-Burial;
    P.Transform.SetLocation(FVector(Origin.X,Origin.Y,FittedZ));
    return true;
}

void ATemperateHillsWorld::GetVegetationPlacements(int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(auto Neighbors=PrepareVegetationCell(Bounds,Layer==3))GetVegetationStrip(Layer,Bounds,*Neighbors,Out);
}

TSharedPtr<HillsVegetation::FNeighborhood> ATemperateHillsWorld::PrepareVegetationCell(const FBox& Bounds,bool bNeedsGround) const
{
    auto Neighbors=BeginVegetationCell(Bounds);
    if(Neighbors)
    {
        while(!AdvanceVegetationCell(Neighbors,bNeedsGround)) {}
    }
    return Neighbors;
}

TSharedPtr<HillsVegetation::FNeighborhood> ATemperateHillsWorld::BeginVegetationCell(const FBox& Bounds) const
{
    TRACE_CPUPROFILER_EVENT_SCOPE(HillsPrepareVegetationRockMask);
    using namespace HillsVegetation;
    if(!Assets)return nullptr;
    auto Neighbors=MakeShared<FNeighborhood>(*Assets,TemperateVillagePlanting::Near(*this,Bounds.ExpandBy(2500.)));
    Neighbors->CellBounds=Bounds;
    const FCatalog& Catalog=Neighbors->Catalog;
    // Dependencies are finite: grass -> accepted ferns -> accepted woody plants
    // -> raw woody peers. Include the whole chain, not only the caller's cell.
    const double Halo=8*Catalog.UnderstoryReach+Catalog.LowReach+Neighbors->GrassHalo()+200;
    Neighbors->SupportArea=Bounds.ExpandBy(FVector(Halo,Halo,0));
    if(bReady)UpdateVegetationRockMask(Neighbors->SupportArea,650.,Neighbors->RockMask,Catalog.UnderstoryReach);
    return Neighbors;
}

bool ATemperateHillsWorld::AdvanceVegetationCell(const TSharedPtr<HillsVegetation::FNeighborhood>& Neighbors,bool bNeedsGround) const
{
    TRACE_CPUPROFILER_EVENT_SCOPE(TemperateVegetationRelationships);
    using namespace HillsVegetation;
    const FCatalog& Catalog=Neighbors->Catalog;
    const double GrassHalo=Neighbors->GrassHalo();
    const FBox& Area=Neighbors->SupportArea;
    const FBox& Bounds=Neighbors->CellBounds;
    const double TreeHalo=FMath::Max(650.,FMath::Max(Catalog.UnderstoryReach,Catalog.LowReach)+185);
    const FBox TreeArea=Area.ExpandBy(FVector(TreeHalo,TreeHalo,0));
    FIndex& Trees=Neighbors->Trees;
    using EStage=FNeighborhood::EStage;
    auto& Raw=Neighbors->Raw;
    auto& Ground=Neighbors->Ground;
    auto& TreeSupports=Neighbors->TreeSupports;
    auto* Floor=bNeedsGround?&Ground:nullptr;
    switch(Neighbors->Stage)
    {
    case EStage::Trees:
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(HillsVegetationTreeSupports);
        for(int32 Y=FMath::FloorToInt(TreeArea.Min.Y/1200)-1;Y<=FMath::FloorToInt(TreeArea.Max.Y/1200)+1;++Y)
        for(int32 X=FMath::FloorToInt(TreeArea.Min.X/1200)-1;X<=FMath::FloorToInt(TreeArea.Max.X/1200)+1;++X)
        {
            FTemperatePlacement P;if(!TreeCandidate(X,Y,P))continue;
            FInfo Info;Info.Box=BoundsOf(P.Mesh.ResolveObject());Info.Kind=EKind::Tree;Info.Layer=0;
            if(!Info.Box.IsValid)continue;
            TreeSupports.Add(P);
            FPlant T=Describe(P,Info);T.Radius=T.Core;Trees.Add(MoveTemp(T));
        }
        // Growth presentation uses these same stored offsets. Reserve the mature
        // root size now, so lower layers need not change every growth tick.
        TArray<FTemperatePlacement> Regrowth;GetRegrowingTrees(TreeArea,Regrowth);
        for(const auto& P:Regrowth)
        {
            FPlant T;T.Root=FVector2D(P.Transform.GetLocation());T.Kind=EKind::Tree;T.Core=T.Radius=85;Trees.Add(MoveTemp(T));
        }
        Neighbors->Stage=EStage::Shrubs;
        break;
    }
    case EStage::Shrubs:
        GetBasePlacements(2,Area,Raw);
        GetQuarryLakeSlopeCover(Area,Raw,true);
        Neighbors->Stage=EStage::Understory;
        break;
    case EStage::Understory:
        GetBasePlacements(4,Area,Raw);
        TemperateVillagePlanting::Gather(*this,4,Area,Raw);
        Neighbors->Stage=EStage::NurseLogs;
        break;
    case EStage::NurseLogs:
        GetNurseLogPlacements(Area,UpdateVegetationRockMask(Area,650.,Neighbors->RockMask),Raw,Floor);
        Neighbors->Stage=EStage::TreeCompanions;
        break;
    case EStage::TreeCompanions:
        GetHabitatCompanions(Area,TreeSupports,true,Raw,Floor);
        TreeSupports.Empty();
        Neighbors->Stage=EStage::RockCompanions;
        break;
    case EStage::RockCompanions:
        GetHabitatCompanions(Area,UpdateVegetationRockMask(Area,650.,Neighbors->RockMask),false,Raw,Floor);
        Neighbors->Stage=EStage::Ground;
        break;
    case EStage::Ground:
        if(bNeedsGround)
        {
            const FBox LowArea=Bounds.ExpandBy(FVector(GrassHalo,GrassHalo,0));
            if(!GetQuarryLakeSlopeCover(LowArea,Ground,false,&Neighbors->QuarryGroundRows))break;
            GetUplandGroundPatches(LowArea,Ground);
            GetShoreRockCompanions(LowArea,UpdateVegetationRockMask(Area,650.,Neighbors->RockMask),Ground);
            for(auto& P:Ground)
            {
                const FVector At=P.Transform.GetLocation();
                if(At.X>=LowArea.Min.X&&At.X<LowArea.Max.X&&At.Y>=LowArea.Min.Y&&At.Y<LowArea.Max.Y)
                    Neighbors->FloorRows.FindOrAdd(FNeighborhood::FloorRow(At.Y)).Add(MoveTemp(P));
            }
        }
        Ground.Empty();
        Neighbors->Stage=EStage::Fit;
        break;
    case EStage::Fit:
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(HillsVegetationFitBatch);
        // Preserve raw order across yields. Peer competition still sees the
        // entire cell plus its halo, including candidates from earlier batches.
        const int32 End=FMath::Min(Neighbors->NextFit+32,Raw.Num());
        for(;Neighbors->NextFit<End;++Neighbors->NextFit)
        {
            auto& P=Raw[Neighbors->NextFit];
            const FInfo* Info=Catalog.Info.Find(P.Mesh);
            // Root fitting moves only Z. Reject occupied XY before sampling
            // the centre and four footprint edges against terrain and water.
            if(Info&&ClearOfTrees(Describe(P,*Info),Trees)&&FitVegetationPlacement(P,Info->Box,Info->Kind))
                Neighbors->Accepted.Add(MoveTemp(P));
        }
        if(End==Raw.Num())
        {
            Raw=MoveTemp(Neighbors->Accepted);
            Neighbors->Stage=EStage::Resolve;
        }
        break;
    }
    case EStage::Resolve:
    {
        ExcludeRockFootprints(Area,Raw,Neighbors->RockMask);
        FIndex WoodCandidates,FernCandidates;
        FIndex& Wood=Neighbors->Wood;
        FIndex& Ferns=Neighbors->Ferns;
        for(const auto& P:Raw)
        {
            const FInfo& Info=Catalog.Info.FindChecked(P.Mesh);
            if(Woody(Info.Kind))WoodCandidates.Add(Describe(P,Info));
        }
        SelectPeers(WoodCandidates,Wood);
        for(const auto& P:Raw)
        {
            const FInfo& Info=Catalog.Info.FindChecked(P.Mesh);
            if(Info.Kind!=EKind::Fern)continue;
            FPlant Plant=Describe(P,Info);
            if(ClearOfUpperLayer(Plant,Wood))FernCandidates.Add(MoveTemp(Plant));
        }
        SelectPeers(FernCandidates,Ferns);
        Raw.Empty();
        Neighbors->Stage=EStage::Done;
        return true;
    }
    case EStage::Done: return true;
    }
    return false;
}

void ATemperateHillsWorld::GetVegetationStrip(int32 Layer,const FBox& Bounds,HillsVegetation::FNeighborhood& Neighbors,TArray<FTemperatePlacement>& Out) const
{
    using namespace HillsVegetation;
    const auto& Wood=Neighbors.Wood;
    const auto& Ferns=Neighbors.Ferns;
    const auto& Trees=Neighbors.Trees;
    const auto& Catalog=Neighbors.Catalog;
    if(Layer!=3)
    {
        const FBox& Cell=Neighbors.CellBounds;
        const bool Inside=Bounds.Min.X>=Cell.Min.X&&Bounds.Max.X<=Cell.Max.X&&
            Bounds.Min.Y>=Cell.Min.Y&&Bounds.Max.Y<=Cell.Max.Y;
        if(Inside&&(Bounds.Min.Y>Cell.Min.Y||Bounds.Max.Y<Cell.Max.Y))
        {
            if(!Neighbors.bUnderstoryRowsReady)
            {
                for(const auto* Index:{&Wood,&Ferns})for(const FPlant& P:Index->Plants)
                    if(Owned(P,Cell))
                        Neighbors.UnderstoryRows.FindOrAdd(FNeighborhood::FloorRow(P.Placement.Transform.GetLocation().Y)).Add(&P);
                Neighbors.bUnderstoryRowsReady=true;
            }
            for(int32 Row=FNeighborhood::FloorRow(Bounds.Min.Y);Row<=FNeighborhood::FloorRow(Bounds.Max.Y);++Row)
                if(const auto* Plants=Neighbors.UnderstoryRows.Find(Row))
                    for(const FPlant* P:*Plants)if(P->Layer==Layer&&Owned(*P,Bounds))Out.Add(P->Placement);
            return;
        }
        for(const auto* Index:{&Wood,&Ferns})for(const auto& P:Index->Plants)
            if(P.Layer==Layer&&Owned(P,Bounds))Out.Add(P.Placement);
        return;
    }
    TArray<FTemperatePlacement> Raw;
    const double GrassHalo=Neighbors.GrassHalo();
    // Low-plant cores are capped at 28 cm. Include their shifted root pivots as
    // well as both cores across a border; leaf tips can interleave in clumps.
    const FBox GrassArea=Bounds.ExpandBy(FVector(GrassHalo,GrassHalo,0));
    GetBasePlacements(3,GrassArea,Raw);
    TemperateVillagePlanting::Gather(*this,3,GrassArea,Raw);
    for(int32 Row=FNeighborhood::FloorRow(GrassArea.Min.Y);Row<=FNeighborhood::FloorRow(GrassArea.Max.Y);++Row)
    {
        if(const auto* Items=Neighbors.FloorRows.Find(Row))
            for(const auto& P:*Items)
            {
                const FVector At=P.Transform.GetLocation();
                if(At.X>=GrassArea.Min.X&&At.X<GrassArea.Max.X&&At.Y>=GrassArea.Min.Y&&At.Y<GrassArea.Max.Y)Raw.Add(P);
            }
    }
    FIndex GrassCandidates;
    TArray<FTemperatePlacement> Supported;
    for(auto& P:Raw)
    {
        const FInfo* Info=Catalog.Info.Find(P.Mesh);
        if(!Info){Supported.Add(MoveTemp(P));continue;} // ground stones keep their own placement recipe
        const FPlant Plant=Describe(P,*Info);
        if(ClearOfTrees(Plant,Trees)&&ClearOfUpperLayer(Plant,Wood)&&ClearOfUpperLayer(Plant,Ferns)
            &&FitVegetationPlacement(P,Info->Box,Info->Kind))Supported.Add(MoveTemp(P));
    }
    const FBox MaskArea=bReady?Neighbors.CellBounds.ExpandBy(FVector(GrassHalo,GrassHalo,0)):GrassArea;
    ExcludeRockFootprints(MaskArea,Supported,Neighbors.RockMask);
    for(const auto& P:Supported)
    {
        if(const FInfo* Info=Catalog.Info.Find(P.Mesh))GrassCandidates.Add(Describe(P,*Info));
        else
        {
            FPlant Stone;Stone.Placement=P;
            if(Owned(Stone,Bounds))Out.Add(P);
        }
    }
    // Halo plants can veto a neighbour, but are emitted only by their own strip.
    for(const auto& P:GrassCandidates.Plants)
        if(Owned(P,Bounds)&&SurvivesPeers(P,GrassCandidates))Out.Add(P.Placement);
}
