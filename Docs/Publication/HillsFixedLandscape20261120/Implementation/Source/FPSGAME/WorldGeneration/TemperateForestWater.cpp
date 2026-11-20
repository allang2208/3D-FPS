#include "TemperateForestWater.h"
#include "TemperateForestHabitat.h"
#include "TemperateHillsMap.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include <queue>
#include <vector>

namespace TemperateForestWater
{
namespace
{
constexpr double WaterEdgeDepthCm=2.;
constexpr double ShoreWidthCm=240.;
// More shallow pools throughout the rainforest, with bounded per-sample work.
constexpr int32 MaxShapedBasins=6;
constexpr int32 MaxPools=8;
// Linear interpolation lets the last wet grid vertex influence its neighbouring cell.
constexpr double ShoreInfluenceCm=ShoreWidthCm+Step;
constexpr int32 CellTriangles[2][3]={{0,2,1},{0,3,2}};

void GetCellCorners(const FPlan& Plan,FIntPoint Cell,FVector (&V)[4])
{
    const FIntPoint Corners[]={Cell,Cell+FIntPoint(1,0),Cell+FIntPoint(1,1),Cell+FIntPoint(0,1)};
    for(int32 I=0;I<4;++I)
    {
        const auto C=Corners[I];
        V[I]=FVector(Plan.Origin+FVector2D(C)*Step,Plan.GroundAt(C.X,C.Y));
    }
}

void StampBank(FPlan& Plan,const FVector2D& A,const FVector2D& B,double WaterZ)
{
    const FVector2D Extent(ShoreWidthCm);
    const FVector2D Lo=(A.ComponentMin(B)-Extent-Plan.Origin)/Step;
    const FVector2D Hi=(A.ComponentMax(B)+Extent-Plan.Origin)/Step;
    const FVector2D Segment=B-A;
    const double LengthSquared=FMath::Max(Segment.SizeSquared(),UE_DOUBLE_SMALL_NUMBER);
    const int32 LastX=FMath::Min(Plan.Width-1,FMath::FloorToInt(Hi.X));
    const int32 LastY=FMath::Min(Plan.Height-1,FMath::FloorToInt(Hi.Y));
    for(int32 Y=FMath::Max(0,FMath::CeilToInt(Lo.Y));Y<=LastY;++Y)
    for(int32 X=FMath::Max(0,FMath::CeilToInt(Lo.X));X<=LastX;++X)
    {
        const FVector2D P=Plan.Origin+FVector2D(X,Y)*Step;
        const double T=FMath::Clamp(FVector2D::DotProduct(P-A,Segment)/LengthSquared,0.,1.);
        const double Distance=FVector2D::Distance(P,A+T*Segment);
        const double LowGround=1.-FMath::SmoothStep(4.,32.,Plan.GroundAt(X,Y)-WaterZ);
        const float Weight=float(LowGround*(1.-FMath::SmoothStep(0.,ShoreWidthCm,Distance)));
        float& Value=Plan.ShoreMoisture[Y*Plan.Width+X];
        Value=FMath::Max(Value,Weight);
    }
}

// Run once in the water-plan worker. Terrain and thousands of instances then
// read the same four samples, including where the shoreline crosses a PCG tile.
void BuildShoreMoisture(FPlan& Plan)
{
    if(Plan.Pools.IsEmpty())return;
    Plan.ShoreMoisture.Init(0.f,Plan.Width*Plan.Height);
    for(const auto& Pool:Plan.Pools)
    {
        const double Level=Pool.WaterZ-WaterEdgeDepthCm;
        for(const auto Cell:Pool.Cells)
        {
            FVector V[4];GetCellCorners(Plan,Cell,V);
            for(int32 I=0;I<4;++I)if(V[I].Z<Level)
            {
                const int32 X=Cell.X+int32(I==1||I==2),Y=Cell.Y+int32(I>=2);
                Plan.ShoreMoisture[Y*Plan.Width+X]=1.f;
            }
            for(const auto& Tri:CellTriangles)
            {
                FVector2D Ends[2];int32 Count=0;
                for(int32 I=0;I<3;++I)
                {
                    const FVector& A=V[Tri[I]];
                    const FVector& B=V[Tri[(I+1)%3]];
                    if((A.Z<Level)!=(B.Z<Level))
                        Ends[Count++]=FVector2D(FMath::Lerp(A,B,(Level-A.Z)/(B.Z-A.Z)));
                }
                if(Count==2)StampBank(Plan,Ends[0],Ends[1],Pool.WaterZ);
            }
        }
    }
}
}

namespace
{
constexpr double PatchSizeCm=6400.;
constexpr int32 PatchCells=int32(PatchSizeCm/Step);

TSharedPtr<FPlan,ESPMode::ThreadSafe> GeneratePatch(int32 Seed, const FVector2D& Origin,
    const FBasin& ShapedBasin, const TemperateRiver::FPlan& River,
    const TArray<TemperateHillsSurface::FTerrainEdit>& Edits)
{
    auto Plan=MakeShared<FPlan,ESPMode::ThreadSafe>();
    Plan->Origin=Origin;
    Plan->Width=Plan->Height=PatchCells+1;
    Plan->Basins.Add(ShapedBasin);
    const int32 W=Plan->Width,H=Plan->Height,Count=W*H;
    auto BaseHeight=[&](double X,double Y){return River.Height(X,Y,Seed);};
    Plan->Ground.SetNumUninitialized(Count);
    TArray<double> Filled;Filled.SetNumUninitialized(Count);
    TArray<uint8> Visited,Allowed;Visited.Init(0,Count);Allowed.Init(0,Count);
    using FEntry=std::pair<double,int32>;
    std::priority_queue<FEntry,std::vector<FEntry>,std::greater<FEntry>> Queue;
    for(int32 Y=0;Y<H;++Y)for(int32 X=0;X<W;++X)
    {
        const int32 I=Y*W+X;const double WX=Plan->Origin.X+X*Step,WY=Plan->Origin.Y+Y*Step;
        const double Z=Plan->ShapeGround(WX,WY,BaseHeight(WX,WY))+TemperateHillsSurface::TerrainEditOffset(Edits,WX,WY);
        Plan->Ground[I]=Filled[I]=Z;
        const auto Bank=River.Sample(WX,WY);
        Allowed[I]=River.RainforestWeight(WX,WY)>.60&&Bank.Bank<=.01
            &&FMath::Abs(WY-TemperateHillsSurface::ValleyY(WX,Seed))>1800;
        // All excluded ground acts as an outlet, never an artificial dam.
        if(!Allowed[I]||X==0||Y==0||X==W-1||Y==H-1)
        {Visited[I]=1;Queue.push({Z,I});}
    }
    while(!Queue.empty())
    {
        const auto [Level,I]=Queue.top();Queue.pop();const int32 X=I%W,Y=I/W;
        for(int32 DY=-1;DY<=1;++DY)for(int32 DX=-1;DX<=1;++DX)
        {
            const int32 NX=X+DX,NY=Y+DY;
            if((DX==0&&DY==0)||NX<0||NY<0||NX>=W||NY>=H)continue;
            const int32 N=NY*W+NX;if(Visited[N])continue;
            Visited[N]=1;Filled[N]=FMath::Max(Plan->Ground[N],Level);Queue.push({Filled[N],N});
        }
    }
    Visited.Init(0,Count);TArray<FPool> Candidates;
    for(int32 Start=0;Start<Count;++Start)
    {
        if(Visited[Start]||!Allowed[Start]||Filled[Start]-Plan->Ground[Start]<3)continue;
        const double Spill=Filled[Start];double Bottom=Plan->Ground[Start];
        TArray<int32> Basin{Start};Visited[Start]=1;
        for(int32 Cursor=0;Cursor<Basin.Num();++Cursor)
        {
            const int32 I=Basin[Cursor],X=I%W,Y=I/W;Bottom=FMath::Min(Bottom,Plan->Ground[I]);
            for(int32 DY=-1;DY<=1;++DY)for(int32 DX=-1;DX<=1;++DX)
            {
                const int32 NX=X+DX,NY=Y+DY;if(NX<0||NY<0||NX>=W||NY>=H)continue;
                const int32 N=NY*W+NX;
                if(!Visited[N]&&Allowed[N]&&FMath::Abs(Filled[N]-Spill)<.1&&Filled[N]-Plan->Ground[N]>=3)
                {Visited[N]=1;Basin.Add(N);}
            }
        }
        FPool Pool;Pool.WaterZ=FMath::Min(Spill-3.,Bottom+45.);Pool.MaxDepth=Pool.WaterZ-Bottom;
        if(Pool.MaxDepth<10)continue;
        for(const int32 I:Basin)if(Plan->Ground[I]<Pool.WaterZ-WaterEdgeDepthCm)
        {
            Pool.AreaM2+=Step*Step/10000.;const int32 X=I%W,Y=I/W;
            for(int32 DY=-1;DY<=0;++DY)for(int32 DX=-1;DX<=0;++DX)
                if(X+DX>=0&&Y+DY>=0&&X+DX<W-1&&Y+DY<H-1)Pool.Cells.Add(FIntPoint(X+DX,Y+DY));
        }
        if(Pool.AreaM2<8||Pool.AreaM2>240)continue;
        for(const auto Cell:Pool.Cells)
        {Pool.Bounds+=Plan->Origin+FVector2D(Cell)*Step;Pool.Bounds+=Plan->Origin+FVector2D(Cell+FIntPoint(1,1))*Step;}
        if(Pool.Bounds.GetSize().GetMax()>2800)continue;
        Candidates.Add(MoveTemp(Pool));
    }
    Candidates.Sort([](const FPool& A,const FPool& B)
    {if(A.AreaM2!=B.AreaM2)return A.AreaM2>B.AreaM2;return A.WaterZ<B.WaterZ;});
    for(auto& Pool:Candidates)
    {
        bool Near=false;for(const auto& Kept:Plan->Pools)
            Near|=FVector2D::DistSquared(Pool.Bounds.GetCenter(),Kept.Bounds.GetCenter())<FMath::Square(2200.);
        if(!Near)Plan->Pools.Add(MoveTemp(Pool));
        if(Plan->Pools.Num()>=MaxPools)break;
    }

    return Plan;
}
}

FPlanPtr Generate(int32 Seed,double Half,TemperateRiver::FPlanPtr River,
    const TArray<TemperateHillsSurface::FTerrainEdit>& Edits,int32 Version)
{
    auto Plan=MakeShared<FPlan,ESPMode::ThreadSafe>();
    if(!River||River->RainforestMask.IsEmpty())return Plan;
    // Broad phase covers the actual expanded biome, independent of the old
    // ellipse radii. Only six small tiles receive metre-resolution flooding.
    Plan->Origin=FVector2D(-Half);
    Plan->Width=Plan->Height=FMath::RoundToInt(Half*2/Step)+1;
    struct FCandidate { FBasin Basin; double Score; FIntPoint Tile; };
    TArray<FCandidate> Candidates;
    constexpr double SiteStep=800.;
    constexpr int32 SitesPerTile=int32(PatchSizeCm/SiteStep);
    TArray<FCandidate> Selected;
    const bool FixedSites=Seed==TemperateHillsMap::Seed && Version==TemperateHillsMap::GeneratorVersion &&
        Half==51200. && River->bRiverLake && River->Lake.bNaturalShore;
    if(FixedSites)
    {
        for(const auto& Site:TemperateHillsMap::WoodlandPools)
        {
            const FVector2D C(Site.X*100.,Site.Y*100.);
            const FIntPoint Grid(FMath::RoundToInt((C.X+Half)/SiteStep),FMath::RoundToInt((C.Y+Half)/SiteStep));
            const uint32 Key=TemperateHillsSurface::Key(Grid.X,Grid.Y,uint32(Seed),3613);
            FBasin B{C,480.+TemperateHillsSurface::Unit(Key)*100.,DBL_MAX,20.+TemperateHillsSurface::Unit(Key+7)*10.};
            // The outlet level still follows the real ground, and the normal
            // local flood below still accounts for each player's dig/fill edits.
            for(int32 I=0;I<16;++I)
            {
                const double A=I*2.*PI/16.;
                B.WaterZ=FMath::Min(B.WaterZ,River->Height(C.X+B.Radius*FMath::Cos(A),C.Y+B.Radius*FMath::Sin(A),Seed)-4.);
            }
            Selected.Add({B,0.,FIntPoint(Grid.X/SitesPerTile,Grid.Y/SitesPerTile)});
        }
    }
    const int32 Tiles=FixedSites?0:FMath::FloorToInt(Half*2/PatchSizeCm);
    for(int32 TY=0;TY<Tiles;++TY)for(int32 TX=0;TX<Tiles;++TX)
    {
        FCandidate Best;Best.Score=DBL_MAX;
        for(int32 SY=1;SY<SitesPerTile;++SY)for(int32 SX=1;SX<SitesPerTile;++SX)
        {
            const int32 GX=TX*SitesPerTile+SX,GY=TY*SitesPerTile+SY;
            const FVector2D C=Plan->Origin+FVector2D(GX,GY)*SiteStep;
            if(River->RainforestWeight(C.X,C.Y)<.75||River->WhiteCliffs.Weight(C.X,C.Y)>.01)continue;
            const auto CenterBank=River->Sample(C.X,C.Y);
            if(CenterBank.Bank>.01||FMath::Abs(C.Y-TemperateHillsSurface::ValleyY(C.X,Seed))<1800)continue;
            const uint32 Key=TemperateHillsSurface::Key(GX,GY,uint32(Seed),3613);
            FBasin B{C,480.+TemperateHillsSurface::Unit(Key)*100.,0,20.+TemperateHillsSurface::Unit(Key+7)*10.};
            double Low=DBL_MAX,High=-DBL_MAX;bool Valid=true;
            for(int32 I=0;I<16;++I)
            {
                const double Angle=I*2*PI/16;
                const FVector2D P=C+FVector2D(FMath::Cos(Angle),FMath::Sin(Angle))*B.Radius;
                if(River->RainforestWeight(P.X,P.Y)<.4||River->Sample(P.X,P.Y).Bank>.01
                    ||FMath::Abs(P.Y-TemperateHillsSurface::ValleyY(P.X,Seed))<1800){Valid=false;break;}
                const double Z=River->Height(P.X,P.Y,Seed);Low=FMath::Min(Low,Z);High=FMath::Max(High,Z);
            }
            if(!Valid||High-Low>90)continue;
            B.WaterZ=Low-4;double MaxCut=0;
            for(int32 DY=-2;DY<=2;++DY)for(int32 DX=-2;DX<=2;++DX)
            {
                const double NX=DX/2.,NY=DY/2.,D=FMath::Sqrt(NX*NX+NY*NY);if(D>=1)continue;
                const double Z=River->Height(C.X+NX*B.Radius,C.Y+NY*B.Radius,Seed);
                const double Target=FMath::Lerp(B.WaterZ-B.Depth*(1-D*D),Z,FMath::SmoothStep(.65,1.,D));
                MaxCut=FMath::Max(MaxCut,Z-Target);
            }
            if(MaxCut>75)continue;
            const double Score=High-Low+MaxCut*.25+TemperateHillsSurface::Unit(Key+19)*8;
            if(Score<Best.Score)Best={B,Score,FIntPoint(TX,TY)};
        }
        if(Best.Score<DBL_MAX)Candidates.Add(Best);
    }
    FBox2D Sites(ForceInit);for(const auto& C:Candidates)Sites+=C.Basin.Center;
    const double Spread=Candidates.IsEmpty()?2600.:FMath::Max(2600.,Sites.GetSize().Size()/FMath::Sqrt(double(MaxShapedBasins))*.6);
    while(!Candidates.IsEmpty()&&Selected.Num()<MaxShapedBasins)
    {
        int32 Best=INDEX_NONE;double BestScore=DBL_MAX;
        for(int32 I=0;I<Candidates.Num();++I)
        {
            double Distance=DBL_MAX;
            for(const auto& Kept:Selected)Distance=FMath::Min(Distance,FVector2D::Distance(Kept.Basin.Center,Candidates[I].Basin.Center));
            if(Distance<2600.)continue;
            // Keep terrain quality, but discourage all pools clustering in the
            // flattest corner. Enumeration and tie handling remain seed-stable.
            const double Score=Candidates[I].Score+120.*(1.-FMath::Clamp(Distance/Spread,0.,1.));
            if(Score<BestScore){Best=I;BestScore=Score;}
        }
        if(Best==INDEX_NONE)break;
        Selected.Add(Candidates[Best]);Candidates.RemoveAt(Best);
    }
    TArray<TSharedPtr<FPlan,ESPMode::ThreadSafe>> Patches;
    TArray<TArray<FPool>> Available;
    for(const auto& C:Selected)
    {
        Plan->Basins.Add(C.Basin);
        auto Patch=GeneratePatch(Seed,Plan->Origin+FVector2D(C.Tile)*PatchSizeCm,C.Basin,*River,Edits);
        Available.Add(MoveTemp(Patch->Pools));Patches.Add(Patch);
    }
    // One pool per selected area first, then remaining natural hollows up to
    // the shared global cap. Dry/fill edits are evaluated before this selection.
    int32 KeptCount=0;
    for(int32 Round=0;Round<MaxPools&&KeptCount<MaxPools;++Round)
    for(int32 I=0;I<Patches.Num()&&KeptCount<MaxPools;++I)
    {
        if(!Available[I].IsValidIndex(Round))continue;
        auto& Pool=Available[I][Round];bool Near=false;
        for(const auto& P:Patches)for(const auto& Kept:P->Pools)
            Near|=FVector2D::DistSquared(Pool.Bounds.GetCenter(),Kept.Bounds.GetCenter())<FMath::Square(2200.);
        if(!Near){Patches[I]->Pools.Add(MoveTemp(Pool));++KeptCount;}
    }
    for(const auto& Patch:Patches)
    {
        BuildShoreMoisture(*Patch);
        const FIntPoint Offset(FMath::RoundToInt((Patch->Origin.X-Plan->Origin.X)/Step),
            FMath::RoundToInt((Patch->Origin.Y-Plan->Origin.Y)/Step));
        for(const auto& Local:Patch->Pools)
        {
            FPool Pool;Pool.WaterZ=Local.WaterZ;Pool.AreaM2=Local.AreaM2;Pool.MaxDepth=Local.MaxDepth;Pool.Bounds=Local.Bounds;
            for(const auto Cell:Local.Cells)Pool.Cells.Add(Cell+Offset);
            Plan->Pools.Add(MoveTemp(Pool));
        }
        Plan->Patches.Add(Patch);
    }
    return Plan;
}

double FPlan::GroundAt(int32 X,int32 Y) const
{
    if(!Ground.IsEmpty())return Ground[Y*Width+X];
    for(const auto& Patch:Patches)
    {
        const int32 PX=X-FMath::RoundToInt((Patch->Origin.X-Origin.X)/Step);
        const int32 PY=Y-FMath::RoundToInt((Patch->Origin.Y-Origin.Y)/Step);
        if(PX>=0&&PY>=0&&PX<Patch->Width&&PY<Patch->Height)return Patch->GroundAt(PX,PY);
    }
    // Only retained wet-cell corners are queried on a regional plan.
    checkNoEntry();
    return 0.;
}

bool FPlan::HasBasin(double X,double Y) const
{
    for(const auto& B:Basins)if(FVector2D::DistSquared(FVector2D(X,Y),B.Center)<B.Radius*B.Radius)return true;
    return false;
}
double FPlan::ShapeGround(double X,double Y,double Original) const
{
    double Z=Original;
    for(const auto& B:Basins)
    {
        const double D=FVector2D::Distance(FVector2D(X,Y),B.Center)/B.Radius;if(D>=1)continue;
        const double Target=FMath::Lerp(B.WaterZ-B.Depth*(1-D*D),Original,FMath::SmoothStep(.65,1.,D));
        Z=FMath::Min(Z,FMath::Max(Original-75.,Target));
    }
    return Z;
}

FSample FPlan::Sample(double X,double Y) const
{
    const double GX=(X-Origin.X)/Step,GY=(Y-Origin.Y)/Step;
    const int32 IX=FMath::FloorToInt(GX),IY=FMath::FloorToInt(GY);
    if(IX<0||IY<0||IX>=Width-1||IY>=Height-1)return {};
    for(const auto& Pool:Pools)if(Pool.Cells.Contains(FIntPoint(IX,IY)))
    {
        const double FX=GX-IX,FY=GY-IY;
        // Exact diagonal used by the streamed ground mesh, not bilinear sampling.
        const double A=GroundAt(IX,IY),B=GroundAt(IX+1,IY),C=GroundAt(IX+1,IY+1),D=GroundAt(IX,IY+1);
        const double Z=FY<=FX?A+(B-A)*FX+(C-B)*FY:A+(C-D)*FX+(D-A)*FY;
        if(Pool.WaterZ>Z+WaterEdgeDepthCm)return {true,Pool.WaterZ,Pool.WaterZ-Z};
    }
    return {};
}
double FPlan::ShoreMoistureAt(double X,double Y) const
{
    if(!Patches.IsEmpty())
    {
        double Moisture=0.;
        for(const auto& Patch:Patches)Moisture=FMath::Max(Moisture,Patch->ShoreMoistureAt(X,Y));
        return Moisture;
    }
    if(ShoreMoisture.IsEmpty())return 0.;
    const double GX=(X-Origin.X)/Step,GY=(Y-Origin.Y)/Step;
    const int32 IX=FMath::FloorToInt(GX),IY=FMath::FloorToInt(GY);
    if(IX<0||IY<0||IX>=Width-1||IY>=Height-1)return 0.;
    const int32 I=IY*Width+IX;
    return FMath::BiLerp(ShoreMoisture[I],ShoreMoisture[I+1],ShoreMoisture[I+Width],ShoreMoisture[I+Width+1],GX-IX,GY-IY);
}
bool FPlan::IntersectsCell(double X,double Y,double Size) const
{
    const FBox2D Cell(FVector2D(X,Y),FVector2D(X+Size,Y+Size));
    for(const auto& B:Basins)
        if(FBox2D(B.Center-FVector2D(B.Radius),B.Center+FVector2D(B.Radius)).Intersect(Cell))return true;
    for(const auto& Pool:Pools)if(Pool.Bounds.ExpandBy(ShoreInfluenceCm).Intersect(Cell))return true;
    return false;
}
bool FPlan::IntersectSegment(const FVector& Start,const FVector& End,FVector& Position) const
{
    const double DZ=Start.Z-End.Z;if(DZ<=UE_SMALL_NUMBER)return false;
    double Best=2.;
    for(const auto& Pool:Pools)
    {
        const double T=(Start.Z-Pool.WaterZ)/DZ;if(T<0||T>1||T>=Best)continue;
        const FVector P=FMath::Lerp(Start,End,T);const auto S=Sample(P.X,P.Y);
        if(S.Wet&&FMath::Abs(S.WaterZ-Pool.WaterZ)<.1){Best=T;Position=P;}
    }
    return Best<=1.;
}
void FPlan::BuildWaterMesh(double X,double Y,double Size,UE::Geometry::FDynamicMesh3& Mesh) const
{
    Mesh.EnableAttributes();Mesh.Attributes()->EnablePrimaryColors();
    auto* N=Mesh.Attributes()->PrimaryNormals();auto* UV=Mesh.Attributes()->PrimaryUV();auto* Color=Mesh.Attributes()->PrimaryColors();
    for(const auto& Pool:Pools)for(const auto Cell:Pool.Cells)
    {
        const double WX=Origin.X+Cell.X*Step,WY=Origin.Y+Cell.Y*Step;
        if(WX<X||WY<Y||WX>=X+Size||WY>=Y+Size)continue;
        FVector V[4];GetCellCorners(*this,Cell,V);
        const double Level=Pool.WaterZ-WaterEdgeDepthCm;
        for(const auto& CornersForTri:CellTriangles)
        {
            TArray<FVector,TInlineAllocator<4>> Clipped;
            for(int32 I=0;I<3;++I)
            {
                const auto A=V[CornersForTri[I]],B=V[CornersForTri[(I+1)%3]];
                const bool InA=A.Z<Level,InB=B.Z<Level;
                if(InA)Clipped.Add(A);
                if(InA!=InB)Clipped.Add(FMath::Lerp(A,B,(Level-A.Z)/(B.Z-A.Z)));
            }
            if(Clipped.Num()<3)continue;
            const int32 First=Mesh.VertexCount();
            for(const auto P:Clipped)
            {
                const float Depth=Pool.WaterZ-P.Z;
                Mesh.AppendVertex(FVector3d(P.X-X,P.Y-Y,Pool.WaterZ));N->AppendElement(FVector3f(0,0,1));
                UV->AppendElement(FVector2f(P.X/400,P.Y/400));Color->AppendElement(FVector4f(FMath::Clamp((Depth-2)/8,0.f,1.f),.5f,0,Depth/100));
            }
            for(int32 I=1;I<Clipped.Num()-1;++I)
            {const UE::Geometry::FIndex3i Id(First,First+I,First+I+1);const int32 T=Mesh.AppendTriangle(Id);N->SetTriangle(T,Id);UV->SetTriangle(T,Id);Color->SetTriangle(T,Id);}
        }
    }
}
}
