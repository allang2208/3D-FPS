#include "EastRiverRoad.h"
#include "TemperateHillsWorld.h"
#include "TemperateHillsMathPrivate.h"
#include "TemperateHillsMap.h"
#include "PCGComponent.h"
#include "PCGManagedResource.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInterface.h"
#include "Math/RotationMatrix.h"

namespace EastRiverRoad
{
namespace
{
struct FStation { double X, Y; int16 Height[37]; };
constexpr FStation Stations[] = {
#include "EastRiverRoadProfile.inl"
};
constexpr int32 Count = UE_ARRAY_COUNT(Stations);
constexpr double Reach = 1900., Bin = 800.;
FVector2D Position(int32 I) { return {Stations[I].X, Stations[I].Y}; }
FIntPoint Key(double X,double Y) { return {FMath::FloorToInt32(X/Bin),FMath::FloorToInt32(Y/Bin)}; }
struct FIndex
{
    TMap<FIntPoint,TArray<int32>> Bins;
    double Chainage[Count] = {};
    FIndex()
    {
        for(int32 I=0;I<Count-1;++I)
        {
            const FVector2D A=Position(I),B=Position(I+1);
            Chainage[I+1]=Chainage[I]+(B-A).Size();
            const auto Min=Key(FMath::Min(A.X,B.X)-Reach,FMath::Min(A.Y,B.Y)-Reach);
            const auto Max=Key(FMath::Max(A.X,B.X)+Reach,FMath::Max(A.Y,B.Y)+Reach);
            for(int32 Y=Min.Y;Y<=Max.Y;++Y)for(int32 X=Min.X;X<=Max.X;++X)
                Bins.FindOrAdd({X,Y}).Add(I);
        }
    }
};
const FIndex& Index() { static const FIndex Data; return Data; }
struct FRun {int32 Y,Start,End;};
constexpr FRun Runs[]={
#include "EastRiverRoadMask.inl"
};
const FRun* FirstRun(int32 Y)
{
    int32 Lo=0,Hi=UE_ARRAY_COUNT(Runs);
    while(Lo<Hi){const int32 Mid=(Lo+Hi)/2;if(Runs[Mid].Y<Y)Lo=Mid+1;else Hi=Mid;}
    return Runs+Lo;
}
bool IntersectsForest(double X0,double Y0,double X1,double Y1)
{
    for(const FRun* R=FirstRun(FMath::FloorToInt32(Y0/100.));R!=Runs+UE_ARRAY_COUNT(Runs)&&R->Y*100.<Y1;++R)
        if(R->Start*100.<X1&&R->End*100.>X0)return true;
    return false;
}
constexpr TCHAR Root[] = TEXT("/Game/WorldGeneration/TemperateHills/EastRiverRoad/");
FSoftObjectPath Local(const TCHAR* Name) {return FSoftObjectPath(FString(Root)+Name+TEXT(".")+Name);}
const FSoftObjectPath& Surface() { static const FSoftObjectPath P=Local(TEXT("MI_EastRiverRoad"));return P; }
const TArray<FSoftObjectPath>& Canopy()
{
    static const TArray<FSoftObjectPath> Paths={
        FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/EastRiverRoad/CanopyR2/SK_RoadHornbeam_04.SK_RoadHornbeam_04")),
        FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/EastRiverRoad/CanopyR2/SK_RoadHornbeam_05.SK_RoadHornbeam_05"))};
    return Paths;
}
const TArray<FSoftObjectPath>& Decals()
{
    static const TArray<FSoftObjectPath> P={
        FSoftObjectPath(TEXT("/Game/ForestPathStudy/Scans/slqlwtd/M_slqlwtd_Decal.M_slqlwtd_Decal")),
        FSoftObjectPath(TEXT("/Game/ForestPathStudy/Scans/tdipmjh/M_tdipmjh_Decal.M_tdipmjh_Decal")),
        Local(TEXT("M_EastRoad_MossPatch")),Local(TEXT("M_EastRoad_SoilPatch"))};
    return P;
}
FSoftObjectPath Scan(const TCHAR* Id,int32 Tier)
{
    const FString Name=FString::Printf(TEXT("%s_tier_%d"),Id,Tier);
    return FSoftObjectPath(FString::Printf(TEXT("/Game/ForestPathStudy/Scans/%s/%s/StaticMeshes/%s.%s"),Id,*Name,*Name,*Name));
}
}

bool Enabled(int32 Seed,int32 Version,const FTemperateVillageSite& Village)
{
    return Seed==TemperateHillsMap::Seed && Version==TemperateHillsMap::GeneratorVersion && Village.bPlaced &&
        Village.bHilltop && FMath::Abs(Village.Ground.X-337.47)<1. && FMath::Abs(Village.Ground.Y+25432.53)<1.;
}

bool Owns(double X,double Y)
{
    const int32 Row=FMath::FloorToInt32(Y/100.),Col=FMath::FloorToInt32(X/100.);
    for(const FRun* R=FirstRun(Row);R!=Runs+UE_ARRAY_COUNT(Runs)&&R->Y==Row;++R)
        if(Col>=R->Start&&Col<R->End)return true;
    return false;
}

void ForLegacyBounds(const ATemperateHillsWorld& World,const FBox& Bounds,TFunctionRef<void(const FBox&)> Generate)
{
    if(!Enabled(World.Seed,World.GeneratorVersion,World.GetVillageSite())||
       !IntersectsForest(Bounds.Min.X,Bounds.Min.Y,Bounds.Max.X,Bounds.Max.Y))
    {Generate(Bounds);return;}
    // Hand legacy samplers only the complement of the authored mask. Join equal
    // runs vertically so broad areas outside the forest are generated just once.
    using FIntervals=TArray<FVector2D,TInlineAllocator<4>>;
    FIntervals Previous;
    double StartY=Bounds.Min.Y;
    auto Flush=[&](double EndY)
    {
        for(const auto& Span:Previous)
            Generate(FBox(FVector(Span.X,StartY,Bounds.Min.Z),FVector(Span.Y,EndY,Bounds.Max.Z)));
    };
    for(double Y=Bounds.Min.Y;Y<Bounds.Max.Y;)
    {
        const int32 Row=FMath::FloorToInt32(Y/100.);
        FIntervals Current;
        double Left=Bounds.Min.X;
        for(const FRun* R=FirstRun(Row);R!=Runs+UE_ARRAY_COUNT(Runs)&&R->Y==Row;++R)
        {
            const double A=FMath::Clamp(R->Start*100.,Bounds.Min.X,Bounds.Max.X);
            if(A>Left)Current.Add({Left,A});
            Left=FMath::Max(Left,FMath::Min(R->End*100.,Bounds.Max.X));
        }
        if(Left<Bounds.Max.X)Current.Add({Left,Bounds.Max.X});
        if(Previous!=Current){Flush(Y);Previous=Current;StartY=Y;}
        Y=FMath::Min((Row+1)*100.,Bounds.Max.Y);
    }
    Flush(Bounds.Max.Y);
}

bool TouchesCell(double X,double Y,double Size)
{
    const auto Min=Key(X,Y),Max=Key(X+Size,Y+Size);
    for(int32 BY=Min.Y;BY<=Max.Y;++BY)for(int32 BX=Min.X;BX<=Max.X;++BX)
        if(const auto* List=Index().Bins.Find({BX,BY}))
            for(int32 I:*List)
            {
                const FVector2D A=Position(I),B=Position(I+1);
                if(FMath::Max(A.X,B.X)+Reach>=X && FMath::Min(A.X,B.X)-Reach<=X+Size &&
                   FMath::Max(A.Y,B.Y)+Reach>=Y && FMath::Min(A.Y,B.Y)-Reach<=Y+Size)return true;
            }
    return false;
}

FSample Sample(double X,double Y)
{
    FSample R;
    const auto* List=Index().Bins.Find(Key(X,Y));
    if(!List)return R;
    const FVector2D P(X,Y);
    int32 Best=INDEX_NONE;
    double MinSq=Reach*Reach, T=0.;
    for(int32 I:*List)
    {
        const FVector2D A=Position(I),D=Position(I+1)-A;
        const double U=FMath::Clamp(FVector2D::DotProduct(P-A,D)/D.SizeSquared(),0.,1.);
        const FVector2D C=A+D*U;
        const double Sq=(P-C).SizeSquared();
        if(Sq<MinSq){Best=I;MinSq=Sq;T=U;R.Center=C;}
    }
    if(Best==INDEX_NONE)return R;
    const FVector2D Dir=(Position(Best+1)-Position(Best)).GetSafeNormal();
    const double Forward=FVector2D::DotProduct(P-R.Center,Dir);
    if((Best==0&&Forward<0.)||(Best==Count-2&&Forward>0.))return FSample{};
    R.Along=FMath::Lerp(Index().Chainage[Best],Index().Chainage[Best+1],T);
    const double Left=Index().Chainage[Count-1]-R.Along;
    R.Distance=FMath::Sqrt(MinSq);
    const double Cross=FVector2D::DotProduct(P-R.Center,FVector2D(-Dir.Y,Dir.X));
    const double U=FMath::Clamp(Cross/100.+18.,0.,36.);
    const int32 J=FMath::Min(35,FMath::FloorToInt32(U));
    const auto HeightAt=[&](int32 I){return FMath::Lerp(double(Stations[I].Height[J]),double(Stations[I].Height[J+1]),U-J);};
    R.Elevation=FMath::Lerp(HeightAt(Best),HeightAt(Best+1),T);
    const double Band=330.+1470.*FMath::SmoothStep(0.,2000.,R.Along)*FMath::SmoothStep(0.,1850.,Left);
    R.GradeWeight=FMath::SmoothStep(0.,250.,Band-R.Distance)*FMath::SmoothStep(0.,550.,R.Along)*FMath::SmoothStep(0.,480.,Left);
    R.Width=195.+26.*FMath::Sin(R.Along/1460.)+14.*FMath::Sin(R.Along/490.);
    const double Fade=FMath::SmoothStep(0.,320.,R.Along)*FMath::SmoothStep(0.,280.,Left);
    const double Noise=TemperateHillsSurface::Noise5(X/450.,Y/450.,TemperateHillsMap::Seed,8917);
    R.Paint.X=float(1.-FMath::SmoothStep(R.Width-48.,R.Width+104.,R.Distance+Noise*46.));
    const double Moss=(.62+.36*Noise)*FMath::SmoothStep(R.Width-80.,R.Width+140.,R.Distance);
    R.Paint.Y=float(Moss*Fade);
    return R;
}

double Height(const FSample& R,TFunctionRef<double()> Native)
{
    if(R.GradeWeight>=1.)return R.Elevation;
    return FMath::Lerp(Native(),R.Elevation,R.GradeWeight);
}

void AddSurfacePaths(TArray<FSoftObjectPath>& Out)
{
    Out.Add(Surface());Out.Append(Decals());
}
void AddTreePaths(TArray<FSoftObjectPath>& Out){Out.Append(Canopy());}
bool TreesLoaded(){return Canopy()[0].ResolveObject()&&Canopy()[1].ResolveObject();}
UMaterialInterface* Material(){return Cast<UMaterialInterface>(Surface().ResolveObject());}

bool IsExtraTree(int32 X){return X>=32768;}
int32 CanopyForm(const FSoftObjectPath& Mesh){return Canopy().Find(Mesh);}
TArray<FIntPoint> ForestTiles()
{
    TSet<FIntPoint> Cells;
    for(const auto& Run:Runs)
        for(int32 X=FMath::FloorToInt32(Run.Start/12.);X<=FMath::FloorToInt32((Run.End-1)/12.);++X)
            Cells.Add({X,FMath::FloorToInt32(Run.Y/12.)});
    auto Result=Cells.Array();
    Result.Sort([](FIntPoint A,FIntPoint B){return A.Y==B.Y?A.X<B.X:A.Y<B.Y;});
    return Result;
}
FTreeKeys TreeKeys(const ATemperateHillsWorld& World,int32 X,int32 Y)
{
    FTreeKeys Keys;Keys.Add({X,Y});
    if(Enabled(World.Seed,World.GeneratorVersion,World.GetVillageSite())&&IntersectsForest(X*1200.,Y*1200.,(X+1)*1200.,(Y+1)*1200.))
        for(int32 J=0;J<2;++J)for(int32 I=0;I<2;++I)Keys.Add({65536+X*2+I,Y*2+J});
    return Keys;
}

bool Tree(const ATemperateHillsWorld& World,int32 GX,int32 GY,FVector2D Original,FTemperatePlacement& Out)
{
    const uint32 Seed=World.PlaythroughSeed?uint32(World.PlaythroughSeed):uint32(World.Seed);
    const uint32 K=TemperateHills::Key(GX,GY,Seed,8953);
    FVector2D P=Original;
    if(IsExtraTree(GX))
    {
        // Four jittered corner sites surround the retained harvest-ID site in each 12 m cell.
        const int32 Col=GX-65536;
        P={(Col+((Col&1)?.61:.39)+.16*(TemperateHills::Unit(K+1)-.5))*600.,
           (GY+((GY&1)?.61:.39)+.16*(TemperateHills::Unit(K+2)-.5))*600.};
        const int32 BX=FMath::FloorToInt32(Col*.5),BY=FMath::FloorToInt32(GY*.5);
        const uint32 Old=TemperateHills::Key(BX,BY,uint32(World.Seed),11);
        const FVector2D Mature((BX+.5+(TemperateHills::Unit(Old+1)-.5)*.56)*1200.,
                               (BY+.5+(TemperateHills::Unit(Old+2)-.5)*.56)*1200.);
        if(FVector2D::DistSquared(P,Mature)<250.*250.)return false;
    }
    if(!Owns(P.X,P.Y))return false;
    const FSample Road=Sample(P.X,P.Y);
    if(Road.Distance<Road.Width+145. || Road.Along<850. || World.SampleForestWater(P.X,P.Y).Wet)return false;
    const auto River=World.SampleRiver(P.X,P.Y);
    if(River.Wet>.15 || World.SurfaceNormal(P.X,P.Y).Z<.72)return false;
    const double CanopyNoise=TemperateHillsSurface::Noise5(P.X/1450.,P.Y/1450.,Seed,8959);
    if(TemperateHills::Unit(K+3)>.91+.075*CanopyNoise)return false;
    Out.Mesh=Canopy()[K&1];Out.Key=K;Out.CandidateId=TemperateHills::CellId(GX,GY);
    Out.Transform=FTransform(FRotator(0,360.*TemperateHills::Unit(K+4),0),
        FVector(P,World.Height(P.X,P.Y)),FVector(.8+.4*TemperateHills::Unit(K+5)));
    return true;
}

namespace
{
// One candidate per world-space bin. Half-open bounds give adjacent PCG cells unique ownership.
void Candidates(const ATemperateHillsWorld& World,const FBox& Bounds,double Spacing,uint32 Salt,
    TFunctionRef<void(const FSample&,const FVector2D&,uint32)> Place)
{
    if(!Enabled(World.Seed,World.GeneratorVersion,World.GetVillageSite()) ||
       !TouchesCell(Bounds.Min.X,Bounds.Min.Y,FMath::Max(Bounds.GetSize().X,Bounds.GetSize().Y)))return;
    const uint32 Seed=World.PlaythroughSeed?uint32(World.PlaythroughSeed):uint32(World.Seed);
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/Spacing);Y<=FMath::FloorToInt(Bounds.Max.Y/Spacing);++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/Spacing);X<=FMath::FloorToInt(Bounds.Max.X/Spacing);++X)
    {
        const uint32 K=TemperateHills::Key(X,Y,Seed,Salt);
        const FVector2D P((X+.12+.76*TemperateHills::Unit(K+1))*Spacing,
                          (Y+.12+.76*TemperateHills::Unit(K+2))*Spacing);
        if(P.X<Bounds.Min.X||P.X>=Bounds.Max.X||P.Y<Bounds.Min.Y||P.Y>=Bounds.Max.Y)continue;
        const FSample Road=Sample(P.X,P.Y);
        if(!Owns(P.X,P.Y)||Road.Along<340.)continue;
        Place(Road,P,K);
    }
}
}

void GatherFloor(const ATemperateHillsWorld& World,const FBox& Bounds,TArray<FTemperatePlacement>& Out)
{
    static const TArray<FSoftObjectPath> Pool={Local(TEXT("SM_CommonHazel_Forest_01")),Local(TEXT("SM_CommonHazel_Forest_02")),
        Scan(TEXT("xjiifd1"),1),Scan(TEXT("xjijdiz"),1),Scan(TEXT("relu7"),3),Scan(TEXT("rioqm"),3)};
    struct FDimensions {double Width,Height,PivotX,PivotY,Bottom;};
    static constexpr FDimensions Dimensions[]={
#include "EastRiverRoadFloorPalette.inl"
    };
    static const TArray<FSoftObjectPath> Herbs={
        FSoftObjectPath(TEXT("/Game/ForestPathStudy/Scans/rbcuh/rbcuh_tier_1/StaticMeshes/SM_rbcuh_VarA.SM_rbcuh_VarA")),
        FSoftObjectPath(TEXT("/Game/ForestPathStudy/Scans/rbpir/rbpiR_tier_1/StaticMeshes/SM_rbpiR_VarB.SM_rbpiR_VarB"))};
    Candidates(World,Bounds,180.,8971,[&](const FSample& Road,const FVector2D& P,uint32 K)
    {
        if(Road.Distance<Road.Width+65. || TemperateHills::Unit(K+3)>.35+.22*Road.Paint.Y)return;
        const FVector N=World.SurfaceNormal(P.X,P.Y);
        if(N.Z<.77)return;
        auto& Item=Out.Emplace_GetRef();
        Item.Key=K;Item.CandidateId=0xEC00000000000000ULL|uint64(K);
        Item.Mesh=Herbs[K&1];
        Item.Transform=FTransform(FQuat(N,2.*PI*TemperateHills::Unit(K+6))*FQuat::FindBetweenNormals(FVector::UpVector,N),
            FVector(P,World.Height(P.X,P.Y)-1.),FVector(.65+.36*TemperateHills::Unit(K+5)));
    });
    Candidates(World,Bounds,460.,8933,[&](const FSample& Road,const FVector2D& P,uint32 K)
    {
        if(Road.Distance<Road.Width+120.)return;
        const double Roll=TemperateHills::Unit(K+3);
        const bool Shrub=Roll<.21,Rock=!Shrub&&Roll<.30;
        if(Roll>.365 || (Shrub && Road.Distance<Road.Width+340.))return;
        const FVector N=World.SurfaceNormal(P.X,P.Y);
        if(N.Z<.83)return;
        const int32 Variant=(Shrub?0:Rock?2:4)+int32(K&1);
        const FDimensions& Model=Dimensions[Variant];
        const double V=TemperateHills::Unit(K+8);
        const double Scale=Shrub?(140.+135.*V)/Model.Height:(Rock?23.+33.*V:45.+52.*V)/Model.Width;
        const FVector Up=Shrub?FVector::UpVector:N;
        const FQuat Spin(Up,2.*PI*TemperateHills::Unit(K+6));
        auto& Item=Out.Emplace_GetRef();
        Item.Key=K;Item.CandidateId=0xED00000000000000ULL|uint64(K);
        Item.Mesh=Pool[Variant];
        const FQuat Rotation=Spin*FQuat::FindBetweenNormals(FVector::UpVector,Up);
        const FVector Contact=FVector(P,World.Height(P.X,P.Y))-(Shrub?2.:Rock?3.:.8)*Up;
        Item.Transform=FTransform(Rotation,Contact-Rotation.RotateVector(
            FVector(Model.PivotX,Model.PivotY,Model.Bottom)*Scale),FVector(Scale));
    });
}

void ScatterDecals(ATemperateHillsWorld& World,UPCGComponent& Owner,const FBox& Bounds)
{
    if(World.GetNetMode()==NM_DedicatedServer)return;
    Candidates(World,Bounds,410.,8941,[&](const FSample& Road,const FVector2D& P,uint32 K)
    {
        if(Road.Distance>780. || TemperateHills::Unit(K+3)>.34)return;
        const bool Verge=Road.Distance>Road.Width;
        const int32 Variant=Verge?(K%3==0?0:2):(K%3==0?1:3);
        auto* Mat=Cast<UMaterialInterface>(Decals()[Variant].ResolveObject());
        if(!Mat)return;
        const FVector N=World.SurfaceNormal(P.X,P.Y);
        const double Radius=(Verge?52.:38.)+TemperateHills::Unit(K+5)*38.;
        AActor* Host=Owner.GetOwner();
        auto* Decal=NewObject<UDecalComponent>(Host);
        Decal->SetMobility(EComponentMobility::Static);
        Decal->DecalSize=FVector(12.,Radius,Radius*(.62+.27*TemperateHills::Unit(K+6)));
        Decal->SetDecalMaterial(Mat);
        Decal->SetFadeScreenSize(.012f);
        Decal->SetSortOrder(Variant<2?2:1);
        Host->AddInstanceComponent(Decal);
        Decal->SetWorldLocationAndRotation(FVector(P,World.Height(P.X,P.Y))+N,
            FQuat(-N,2.*PI*TemperateHills::Unit(K+7))*FRotationMatrix::MakeFromX(-N).ToQuat());
        Decal->RegisterComponent();
        auto* Managed=NewObject<UPCGManagedComponent>(&Owner);
        Managed->GeneratedComponent=Decal;
        Owner.AddToManagedResources(Managed);
    });
}
}

