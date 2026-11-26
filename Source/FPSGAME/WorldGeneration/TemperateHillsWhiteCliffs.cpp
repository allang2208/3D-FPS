#include "TemperateHillsWorld.h"
#include "TemperateQuarryYard.h"
#include "TemperateHillsStreamingPrivate.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Async/Async.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#if WITH_EDITOR
#include "StaticMeshCompiler.h"
#include "TemperateHillsFixedLayout.h"
#include "TemperateHillsMap.h"
#include "Misc/FileHelper.h"
#endif

namespace
{
enum class EQuarryStone { SlipPlate=-2, KeyBlock, Face=0, Bed, Spur, Shelf, Wedge, Blank, ChipBegin };
constexpr int32 FirstChipMesh = 4;
constexpr int32 ChipVariants = 6;

struct FCut
{
    int32 Id;
    EQuarryStone Stone;
    FVector2D At;
    FVector Size;
    double Strike, Dip, Burial;
    // Local quarry direction from the exposed face towards its debris apron.
    FVector2D Fall;
    int32 Blocks, Chips;
    double Run;
};

const FCut Cuts[] = {
    // Loose toes and abandoned stock. The continuous quarry walls are separate surveyed meshes.
#define QUARRY_FALL(Id,Shape,X,Y,SX,SY,SZ,Strike,Dip,Burial,FX,FY,Blocks,Chips,Run,Low,High,Width,Depth,Rake) \
    {Id,EQuarryStone::Shape,{X,Y},{SX,SY,SZ},Strike,Dip,Burial,{FX,FY},Blocks,Chips,Run},
#include "TemperateQuarryRockfalls.inl"
#undef QUARRY_FALL
    {30,EQuarryStone::Blank,{-1530,-2150},{204,112,83},   9, 0, 9,{.85,-.53},1,10,245},
    {31,EQuarryStone::Blank,{ 1260, -910},{161,88,63},  -17, 1, 8,{},0,0,0},
    {32,EQuarryStone::Wedge,{-1770,-2360},{109,76,49},   31,-6,12,{},0,0,0},
};

struct FWorkSite
{
    int32 Id;
    FVector2D At;
    FVector Size;
    double Yaw, Burial;
};

const FWorkSite WorkSites[] = {
    {300, TemperateQuarry::Hoist, {582,312,547}, -8, 8},
    {301, TemperateQuarry::Shed, {920,650,430}, -124, 15},
    {302, {-1550,-1860}, {218,142,103}, -124, 3},
};

struct FQuarryMesh
{
    UStaticMesh* Mesh;
    FBox Box;
    explicit FQuarryMesh(UStaticMesh* InMesh) : Mesh(InMesh), Box(ForceInit)
    {
        if(!Mesh)return;
        Box=Mesh->GetBoundingBox();
        Box.Min+=Mesh->GetNegativeBoundsExtension();
        Box.Max-=Mesh->GetPositiveBoundsExtension();
    }
};

const TArray<FSoftObjectPath>& ApproachMeshes()
{
    static const TArray<FSoftObjectPath> Paths=[] {
        TArray<FSoftObjectPath> Result;
        for(const TCHAR* Suffix:{TEXT("WestWorkingFace"),TEXT("EastLifts"),TEXT("YardDerrick"),TEXT("DressingBench"),TEXT("SlipPlate"),TEXT("KeyBlock")})
        {
            const FString Name=FString(TEXT("SM_Quarry"))+Suffix;
            Result.Emplace(TEXT("/Game/WorldGeneration/TemperateHills/WhiteCliffs/Meshes/Approach/")+Name+TEXT(".")+Name);
        }
        return Result;
    }();
    return Paths;
}
const FSoftObjectPath GroundFinish(TEXT("/Game/WorldGeneration/TemperateHills/WhiteCliffs/Materials/Approach/M_QuarryWorkGround.M_QuarryWorkGround"));

// Sheltered turf, taller dry stems, a twig caught in silt and reclaimed workshop timber.
const TArray<FSoftObjectPath> VergeMeshes={
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/WetForest/ScannedGrass/SM_SoftWildGrassLow.SM_SoftWildGrassLow")),
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/WetForest/ScannedGrass/SM_SoftWildGrassTuft.SM_SoftWildGrassTuft")),
    FSoftObjectPath(TEXT("/Game/UnrealNormandy/StaticMeshes/SM_Grass_01A.SM_Grass_01A")),
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/WetForest/Underfoot/SM_ForestTwig02.SM_ForestTwig02")),
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_VillageAbandonedTimber.SM_VillageAbandonedTimber")),
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Meshes/SM_Hazel_A.SM_Hazel_A")),
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Meshes/SM_Hazel_C.SM_Hazel_C"))};
struct FVerge { double X,Y,Length,Width,Yaw,Turf,Gravel; int32 Groups; };
constexpr FVerge Verges[]={
#include "TemperateQuarryVerges.inl"
};

// Compare the actual rotated workshop rectangle with the debris footprint.
// This lets the stone apron run alongside a gable without closing its door.
bool TouchesWorkArea(const FBox& Footprint)
{
    const FVector2D Mid(Footprint.GetCenter()),Half(Footprint.GetExtent());
    for(const FWorkSite& Site:WorkSites)
    {
        const FVector2D Along=FVector2D(1,0).GetRotated(Site.Yaw),Across(-Along.Y,Along.X);
        const FVector2D Delta=Mid-Site.At,Size=FVector2D(Site.Size)*.5+FVector2D(55.,55.);
        if(FMath::Abs(Delta.X)>Size.X*FMath::Abs(Along.X)+Size.Y*FMath::Abs(Across.X)+Half.X ||
           FMath::Abs(Delta.Y)>Size.X*FMath::Abs(Along.Y)+Size.Y*FMath::Abs(Across.Y)+Half.Y)continue;
        if(FMath::Abs(FVector2D::DotProduct(Delta,Along))<=Size.X+FMath::Abs(Along.X)*Half.X+FMath::Abs(Along.Y)*Half.Y &&
           FMath::Abs(FVector2D::DotProduct(Delta,Across))<=Size.Y+FMath::Abs(Across.X)*Half.X+FMath::Abs(Across.Y)*Half.Y)return true;
    }
    return false;
}

const TArray<FSoftObjectPath>& QuarryFractureMeshes()
{
    static const TArray<FSoftObjectPath> Paths=[] {
        TArray<FSoftObjectPath> Result;
        for(const TCHAR* Suffix : {TEXT("SplitSpur"),TEXT("BeddedShelf"),TEXT("FallenWedge"),
            TEXT("SplitBlank"),TEXT("Chip01"),
            TEXT("Chip02"),TEXT("Chip03"),TEXT("Chip04"),TEXT("Chip05"),TEXT("Chip06")})
        {
            const FString Name=FString(TEXT("SM_Quarry"))+Suffix;
            Result.Emplace(TEXT("/Game/WorldGeneration/TemperateHills/WhiteCliffs/Meshes/Fractures/")+Name+TEXT(".")+Name);
        }
        return Result;
    }();
    return Paths;
}

enum { LowGrass, GrassTuft, BentGrass, Twig, WorkshopTimber, HazelA, HazelC, FirstLooseStone };

constexpr double SlopeSpacing=630.;
constexpr int32 SlopePairsPerRow=13;
int32 SlopeSections(const TemperateQuarryLakeSlope::FField& Field)
{
    return Field.Cells.IsEmpty()?0:-FMath::FloorToInt(Field.MinY/SlopeSpacing)*SlopePairsPerRow;
}

// The broad face is visible across the lake, past the underfoot PCG radius.
// Keep the root mats and exposed stone toes in the quarry's existing instances.
void DressLakeFacingSlope(const TemperateRiver::FPlan& Plan,int32 Section,int32 Seed,double WorldHalf,
    TConstArrayView<FQuarryMesh> Edges,TFunctionRef<double(FVector2D)> FloorZ,
    TMap<FSoftObjectPath,TArray<FTransform>>& Groups)
{
    using namespace TemperateHillsSurface;
    const auto& Field=Plan.QuarryLakeSlope;
    if(Field.Cells.IsEmpty())return;
    const auto& Site=Plan.WhiteCliffs;
    const auto& Chips=QuarryFractureMeshes();
    const int32 J=FMath::FloorToInt(Field.MinY/SlopeSpacing)+Section/SlopePairsPerRow;
    const int32 FirstI=-13+2*(Section%SlopePairsPerRow);
    for(int32 I=FirstI;I<FirstI+2;++I)
    {
        const uint32 K=Key(I,J,Seed,9677);
        const FVector2D Centre=Site.World((I+Unit(K+1))*SlopeSpacing,(J+Unit(K+2))*SlopeSpacing);
        const auto S=Field.Sample(Centre.X,Centre.Y);
        const float Edge=4.f*S.Gully*(S.Coverage-S.Gully);
        if(S.Coverage<.18f||Unit(K+3)>FMath::Clamp(.22*S.Coverage+1.08*S.Turf+.45*Edge,0.,.96))continue;
        const double Z=FloorZ(Centre);
        const FVector N(FloorZ(Centre-FVector2D(50,0))-FloorZ(Centre+FVector2D(50,0)),
            FloorZ(Centre-FVector2D(0,50))-FloorZ(Centre+FVector2D(0,50)),100.);
        const FVector Normal=N.GetSafeNormal();
        if(Normal.Z<.53||Z<Plan.Lake.WaterZ+18.)continue;
        FVector2D Down=FVector2D(Normal).GetSafeNormal();
        if(Down.IsNearlyZero())Down=(Plan.Lake.Center-Centre).GetSafeNormal();
        const FVector2D Across(-Down.Y,Down.X);
        const double Side=Unit(K+4)>.5?1.:-1.;
        // Tufts share a sheltered seam along the contour; its open end bends into the fall line.
        const FVector2D Tangent=(Across*Side+Down*(.18+.43*Unit(K+5))).GetSafeNormal();
        const double Length=205.+265.*Unit(K+6),Width=75.+95.*Unit(K+7);
        const bool Shrub=S.Turf>.23&&S.Gully<.38&&Unit(K+8)<.26;
        const int32 GrassCount=8+int32(12.*Unit(K+9));
        const int32 GravelCount=S.Gravel+.54*S.Ledge+.38*Edge>.18?4+int32(9.*Unit(K+10)):0;
        const FVector2D StoneHead=Centre+Tangent*((Unit(K+11)-.5)*Length)+Down*(Width*(.55+.65*Unit(K+12)));
        for(int32 L=0;L<GrassCount+GravelCount;++L)
        {
            const uint32 V=Key(I*32+L,J,Seed,9689);
            const bool Woody=Shrub&&L==0,Stone=L>=GrassCount;
            const double A=2.*Unit(V+1)-1.,B=2.*Unit(V+2)-1.;
            const double Runout=Stone&&L!=GrassCount?Unit(V+8):0.;
            // A ledge sheds chips below a single half-buried block. The foot fans
            // laterally instead of tracing a second row parallel to the grass.
            const FVector2D XY=Stone?StoneHead+Down*(Runout*Length*.83)+Across*(
                Runout*(B*Width*(.30+1.12*Runout)+Side*65.*Runout)):
                Centre+Tangent*(A*Length)+Down*(Width*(B*(1.-.55*A*A)+.5*A*A));
            const auto At=Field.Sample(XY.X,XY.Y);
            if(At.Coverage<.23||(!Stone&&At.Gully>.64)||FMath::Max(FMath::Abs(XY.X),FMath::Abs(XY.Y))>WorldHalf-180.)continue;
            const double Ground=FloorZ(XY);
            if(Ground<Plan.Lake.WaterZ+10.)continue;
            const int32 Type=Stone?FirstLooseStone+int32(Mix(V+3)%ChipVariants):Woody?(V&1?HazelA:HazelC):
                Unit(V+3)<.61?LowGrass:(Unit(V+4)<.63?GrassTuft:BentGrass);
            const FBox& Box=Edges[Type].Box;
            const FVector Native=Box.GetSize();
            const double Span=Stone?(L==GrassCount?58.+43.*Unit(V+5):(23.+32.*Unit(V+5))*(1.-.55*Runout)):
                Woody?78.+88.*Unit(V+5):65.+81.*Unit(V+5);
            const double Scale=Span/FMath::Max(1.,Woody?Native.Z:FMath::Max(Native.X,Native.Y));
            FVector Size(Scale);
            if(!Woody)Size.Z=FMath::Min(Scale,(Stone?.43*Span:30.+34.*Unit(V+6))/FMath::Max(1.,Native.Z));
            const FVector2D Heading=Stone&&Runout>.20?Down.GetRotated(82.*(Unit(V+7)-.5)+(Native.Y>Native.X?90.:0.)):
                Tangent.GetRotated(Stone?80.*(Unit(V+7)-.5):360.*Unit(V+7));
            const FVector Up=Stone?FVector(FloorZ(XY-FVector2D(45.,0.))-FloorZ(XY+FVector2D(45.,0.)),
                FloorZ(XY-FVector2D(0.,45.))-FloorZ(XY+FVector2D(0.,45.)),90.).GetSafeNormal():
                FMath::Lerp(FVector::UpVector,Normal,Woody?.22:.87).GetSafeNormal();
            const FQuat Rotation=FRotationMatrix::MakeFromZX(Up,FVector(Heading,0)).ToQuat();
            const FVector Root(Woody?0.:Box.GetCenter().X,Woody?0.:Box.GetCenter().Y,Box.Min.Z);
            const double Burial=Stone?.34*Native.Z*Size.Z:Woody?6.:4.+.045*Span;
            const FVector Location=FVector(XY,Ground-Burial)-Rotation.RotateVector(Root*Size);
            const auto& Mesh=Stone?Chips[FirstChipMesh+Type-FirstLooseStone]:VergeMeshes[Type];
            Groups.FindOrAdd(Mesh).Emplace(Rotation,Location,Size);
        }
    }
}

void DressQuarryVerges(const TemperateRiver::FPlan& Plan,int32 Section,double Yaw,int32 Seed,double WorldHalf,
    TFunctionRef<double(double,double)> GroundHeight,TMap<FIntPoint,double>& Grid,TMap<FSoftObjectPath,TArray<FTransform>>& Groups)
{
    const auto& Site=Plan.WhiteCliffs;
    const auto& Paths=QuarryFractureMeshes();
    TArray<FQuarryMesh,TInlineAllocator<12>> Edges;
    for(const auto& Path:VergeMeshes)Edges.Emplace(Cast<UStaticMesh>(Path.ResolveObject()));
    for(int32 I=FirstChipMesh;I<Paths.Num();++I)Edges.Emplace(Cast<UStaticMesh>(Paths[I].ResolveObject()));
    // Small pieces sit on the actual triangle seen by the player. Interpolating
    // the analytic swale only at its centre can leave a pebble above a sloping triangle.
    constexpr double Step=HillsStreaming::CellSize/HillsStreaming::SurfaceDetailQuads;
    auto VertexZ=[&](int32 X,int32 Y)
    {
        const FIntPoint Key(X,Y);
        if(const double* Known=Grid.Find(Key))return *Known;
        const double Z=GroundHeight(X*Step-WorldHalf,Y*Step-WorldHalf);
        Grid.Add(Key,Z);return Z;
    };
    auto FloorZ=[&](FVector2D P)
    {
        const FVector2D UV=(P+FVector2D(WorldHalf,WorldHalf))/Step;
        const int32 X=FMath::FloorToInt(UV.X),Y=FMath::FloorToInt(UV.Y);
        const double U=UV.X-X,V=UV.Y-Y;
        return U>=V?VertexZ(X,Y)*(1.-U)+VertexZ(X+1,Y)*(U-V)+VertexZ(X+1,Y+1)*V:
            VertexZ(X,Y)*(1.-V)+VertexZ(X,Y+1)*(V-U)+VertexZ(X+1,Y+1)*U;
    };
    const int32 SlopeCount=SlopeSections(Plan.QuarryLakeSlope);
    if(Section<SlopeCount)
    {
        DressLakeFacingSlope(Plan,Section,Seed,WorldHalf,Edges,FloorZ,Groups);
        return;
    }
    // Use the higher of the authored rock cap and this seed's visible terrain.
    // Woody plants use their trunk pivot; grass scans use the centre of their base.
    enum { Turf=GrassTuft, DryStem=BentGrass };
    struct FRimPlant { int32 Kind; double X,Y,RockZ,Angle,Size; };
    static constexpr FRimPlant Rim[]={
#include "TemperateQuarryRim.inl"
    };
    if(Section==SlopeCount)for(const auto& Plant:Rim)
    {
        const FBox& Box=Edges[Plant.Kind].Box;
        const bool bShrub=Plant.Kind==HazelA || Plant.Kind==HazelC;
        const FVector Size=Box.GetSize();
        const double Scale=Plant.Size/FMath::Max(1.,bShrub?Size.Z:FMath::Max(Size.X,Size.Y));
        const FVector Root(bShrub?0.:Box.GetCenter().X,bShrub?0.:Box.GetCenter().Y,Box.Min.Z);
        const FVector2D XY=Site.World(Plant.X,Plant.Y);
        const double Support=FMath::Max(FloorZ(XY),Site.FloorZ+Plant.RockZ);
        const FQuat Rotation=FRotator(0.,Yaw+Plant.Angle,0.).Quaternion();
        // The scan pivot sits below a broad tuft, but the visible roots spread
        // sideways across the chipped lip. Let that root mat enter the soil.
        const double Burial=bShrub?7.:FMath::Clamp(.13*Plant.Size,11.,15.);
        const FVector Point(XY,Support-Burial);
        Groups.FindOrAdd(VergeMeshes[Plant.Kind]).Emplace(Rotation,Point-Rotation.RotateVector(Root*Scale),FVector(Scale));
    }
    auto AddEdge=[&](int32 Type,FVector2D Local,double Angle,double Span,double Burial,double Flatten=1.)
    {
        const auto& M=Edges[Type];
        const FVector Native=M.Box.GetSize();
        const double Scale=Span/FMath::Max3(1.,Native.X,Native.Y);
        const FVector Size(Scale,Scale,Scale*Flatten);
        const FVector2D XY=Site.World(Local.X,Local.Y);
        const FQuat Q=FRotator(0.,Yaw+Angle,0.).Quaternion();
        const FVector Base(M.Box.GetCenter().X,M.Box.GetCenter().Y,M.Box.Min.Z);
        // Sample the ends of long pieces so an offcut beds into the lower support.
        double Z=FloorZ(XY);
        if(Type==WorkshopTimber || Span>80.)
        {
            const FVector D=Q.RotateVector((Native.X>Native.Y?FVector::ForwardVector:FVector::RightVector)*Span*.37);
            Z=FMath::Min3(Z,FloorZ(XY+FVector2D(D)),FloorZ(XY-FVector2D(D)));
        }
        const FSoftObjectPath& Path=Type<VergeMeshes.Num()?VergeMeshes[Type]:Paths[FirstChipMesh+Type-VergeMeshes.Num()];
        Groups.FindOrAdd(Path).Emplace(Q,FVector(XY,Z-Burial)-Q.RotateVector(Base*Size),Size);
    };
    const int32 VergeIndex=Section-SlopeCount-1;
    if(VergeIndex>=0&&VergeIndex<int32(UE_ARRAY_COUNT(Verges)))
    {
        const auto& V=Verges[VergeIndex];
        FRandomStream R(TemperateHillsSurface::Key(VergeIndex,0,Seed,7927));
        const FVector2D Along=FVector2D(1.,0.).GetRotated(V.Yaw),Across(-Along.Y,Along.X);
        for(int32 J=0;J<V.Groups;++J)
        {
            const double A=R.FRandRange(-PI,PI),Radius=FMath::Sqrt(R.FRand());
            const double U=Radius*FMath::Cos(A),Offset=.24*FMath::Sin(3.*U)+Radius*FMath::Sin(A);
            const FVector2D Root=FVector2D(V.X,V.Y)+Along*V.Length*U+Across*V.Width*Offset;
            const double Edge=FMath::Abs(Root.X-TemperateQuarry::RoadX(Root.Y));
            if(Edge<265. || TemperateQuarry::ServiceDistance(Root)<143. ||
                TouchesWorkArea(FBox(FVector(Root,0)-FVector(45),FVector(Root,0)+FVector(45))))continue;
            const bool Plant=R.FRandRange(0.,V.Turf+V.Gravel)<V.Turf;
            const int32 Members=Plant?R.RandRange(3,6):R.RandRange(3,7);
            for(int32 K=0;K<Members;++K)
            {
                const FVector2D At=Root+Along*R.FRandRange(-68.,68.)+Across*R.FRandRange(-37.,37.);
                const double Lane=FMath::Abs(At.X-TemperateQuarry::RoadX(At.Y));
                if(Lane<245. || TemperateQuarry::ServiceDistance(At)<114.)continue;
                const double Bearing=V.Yaw+R.FRandRange(-72.,72.);
                if(Plant)
                {
                    const int32 Type=Lane<340.?LowGrass:(K==0&&V.Turf>.5?BentGrass:R.RandRange(LowGrass,GrassTuft));
                    const double Width=Type==BentGrass?R.FRandRange(51.,83.):R.FRandRange(28.,63.);
                    AddEdge(Type,At,Bearing,Width,2.6,Lane<355.?.54:.82);
                }
                else
                {
                    const double Width=K==0?R.FRandRange(25.,62.):R.FRandRange(7.,24.);
                    AddEdge(VergeMeshes.Num()+R.RandRange(0,ChipVariants-1),At,Bearing,Width,Width*.055,.68);
                }
            }
            if(Plant && J%9==0 && Edge>410.)AddEdge(Twig,Root,V.Yaw+R.FRandRange(-21.,21.),R.FRandRange(36.,70.),1.1);
        }
    }
    if(Section!=SlopeCount+1+int32(UE_ARRAY_COUNT(Verges)))return;
    // Where boots leave the cart route, partly buried flats take repeated traffic.
    // Timber stays on the storage side, away from the doorway and jib travel line.
    struct FWorkEdge { int32 Type; double X,Y,Yaw,Span,Burial,Thickness; };
    const FWorkEdge WorkEdges[]={
        {FirstLooseStone,-864,-1776,-19,48,4,.32},{FirstLooseStone+3,-938,-1732,-49,66,5,.34},{FirstLooseStone+4,-1003,-1690,-72,37,3,.36},
        {FirstLooseStone+2,-1014,-1837,22,43,3,.55},{FirstLooseStone+1,-1352,-1944,-20,56,3,.42},{FirstLooseStone+5,-1432,-1970,13,29,2,.50},
        {WorkshopTimber,-1460,-2110,29,199,8,.75},{WorkshopTimber,1207,-1030,74,166,7,.74},
        {FirstLooseStone+3,836,-1235,10,57,3,.44},{FirstLooseStone,870,-1195,20,38,2,.44},{FirstLooseStone+2,931,-1188,36,27,2,.45}};
    for(const auto& W:WorkEdges)AddEdge(W.Type,{W.X,W.Y},W.Yaw,W.Span,W.Burial,W.Thickness);
    // Sweepings from the bench die out along one side of the threshold.
    FRandomStream Sweep(TemperateHillsSurface::Key(0,0,Seed,7929));
    for(int32 I=0;I<28;++I)
    {
        const double T=FMath::Square(Sweep.FRand());
        const FVector2D At=FMath::Lerp(FVector2D(-1064,-1835),FVector2D(-863,-1810),T)+
            FVector2D(Sweep.FRandRange(-19.,19.),Sweep.FRandRange(-33.,33.)*(1.-.6*T));
        const double Width=Sweep.FRandRange(5.,16.)*(1.-.35*T);
        AddEdge(FirstLooseStone+Sweep.RandRange(0,ChipVariants-1),At,Sweep.FRandRange(-54.,83.),Width,.8+Width*.045,.66);
    }
}
}

const FSoftObjectPath& ATemperateHillsWorld::QuarrySlopeStoneMesh(uint32 Variant,bool bLedge)
{
    // The sawn blank belongs to the yard. The natural spur, shelf and wedge
    // can crop out below it, and their fracture chips can run downslope.
    return QuarryFractureMeshes()[bLedge?Variant%3:FirstChipMesh+Variant%ChipVariants];
}

void ATemperateHillsWorld::AddQuarryRockLoadPaths(TArray<FSoftObjectPath>& Out) const
{
    // The third legacy slot holds the whole gravel pack. Each visible stone now has its own mesh.
    for(int32 I=0;I<FMath::Min(2,Assets->WhiteCliffMeshes.Num());++I)
        Out.AddUnique(Assets->WhiteCliffMeshes[I].ToSoftObjectPath());
    const auto& Paths=QuarryFractureMeshes();
    const int32 Count=GetNetMode()==NM_DedicatedServer?FirstChipMesh:Paths.Num();
    if(GetNetMode()!=NM_DedicatedServer)
        for(const auto& Chip:Assets->QuarryShoreChips)
            if(!Chip.IsNull())Out.AddUnique(Chip.ToSoftObjectPath());
    Out.Append(Paths.GetData(),Count);
    Out.Append(ApproachMeshes());
    if(Assets->QuarryProps.IsValidIndex(1))Out.AddUnique(Assets->QuarryProps[1].ToSoftObjectPath());
    if(GetNetMode()!=NM_DedicatedServer){Out.AddUnique(GroundFinish);Out.Append(VergeMeshes);}
}

void ATemperateHillsWorld::GetWhiteCliffPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool bIncludeChips,int32 Section) const
{
    using namespace TemperateHillsSurface;
    if(!Assets || !RiverPlan || !RiverPlan->WhiteCliffs.Valid || Assets->WhiteCliffMeshes.Num()<2)return;
    const auto& Region=RiverPlan->WhiteCliffs;
    auto NearQuery=[&](FVector2D P,double Radius)
    {
        return P.X+Radius>=Bounds.Min.X && P.X-Radius<=Bounds.Max.X &&
               P.Y+Radius>=Bounds.Min.Y && P.Y-Radius<=Bounds.Max.Y;
    };
    const auto& Outcrops=RiverPlan->QuarryLakeSlope.Outcrops;
    if(!NearQuery(Region.Center,14500.)&&!Outcrops.ContainsByPredicate([&](FVector2D At)
        {return NearQuery(Region.World(At.X,At.Y),960.);}))return;
    if(Section==INDEX_NONE && !bIncludeChips && IsInGameThread() && Streaming && Streaming->Quarry.HasBlockers() &&
        Streaming->QuarryBlockerRevision==TerrainEditRevision)
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(HillsCollectAssembledQuarrySolids);
        for(const auto& Blocker:Streaming->QuarryBlockers)
            if(Blocker.Bounds.Intersect(Bounds))Out.Add(Blocker.Item);
        return;
    }

    const double RegionYaw=FMath::RadiansToDegrees(FMath::Atan2(Region.Axis.Y,Region.Axis.X));
    const FQuat RegionRotation=FRotator(0,RegionYaw,0).Quaternion();
    const double WorldLimit=SizeMeters*50.-100.;
    TArray<FQuarryMesh,TInlineAllocator<13>> Kit;
    Kit.Emplace(Assets->WhiteCliffMeshes[0].Get());
    Kit.Emplace(Assets->WhiteCliffMeshes[1].Get());
    const auto& Paths=QuarryFractureMeshes();
    for(int32 I=0;I<(bIncludeChips?Paths.Num():FirstChipMesh);++I)
        Kit.Emplace(Cast<UStaticMesh>(Paths[I].ResolveObject()));

    auto Place=[&](int32 Id,const FQuarryMesh& Rock,FVector2D At,FVector Size,FRotator Attitude,double Burial,bool bWorkSite=false)
    {
        if(!Rock.Mesh)return false;
        const FVector2D P=Region.World(At.X,At.Y);
        const bool bInRange=NearQuery(P,Size.Size());
        const FVector Scale=Size/Rock.Box.GetSize().ComponentMax(FVector(1));
        const FVector Pivot(Rock.Box.GetCenter().X,Rock.Box.GetCenter().Y,Rock.Box.Min.Z);
        const FQuat LocalRotation=Attitude.Quaternion();
        const FBox Footprint=Rock.Box.ShiftBy(-Pivot).TransformBy(FTransform(LocalRotation,FVector(At,0),Scale));
        if(!bWorkSite)
        {
            // The steepest horizontal derivative of the surveyed road is under 1.05.
            const FVector Mid=Footprint.GetCenter(), Extent=Footprint.GetExtent();
            const FVector2D MidWorld=Region.World(Mid.X,Mid.Y);
            if(Region.TrailDistance(MidWorld.X,MidWorld.Y)<305.+Extent.X+Extent.Y*1.05 ||
                TemperateQuarry::ServiceDistance(FVector2D(Mid))<122.+FVector2D(Extent).Size() ||
                TouchesWorkArea(Footprint))return false;
        }
        if(RiverPlan->Protection(P.X,P.Y)>.001)return false;
        const FQuat Rotation=RegionRotation*LocalRotation;
        double Ground=bInRange?Height(P.X,P.Y):0.;
        for(double SX : {-.5,.5})for(double SY : {-.5,.5})
        {
            const FVector2D Corner=Region.World(SX<0?Footprint.Min.X:Footprint.Max.X,SY<0?Footprint.Min.Y:Footprint.Max.Y);
            if(FMath::Abs(Corner.X)>WorldLimit || FMath::Abs(Corner.Y)>WorldLimit ||
                RiverPlan->Protection(Corner.X,Corner.Y)>.001)return false;
            if(!bInRange)continue;
            const FVector Support=Rotation.RotateVector(FVector(SX*.8*Size.X,SY*.8*Size.Y,0));
            Ground=FMath::Min(Ground,Height(P.X+Support.X,P.Y+Support.Y)-Support.Z);
        }
        // A valid parent can sit outside a cell containing the far end of its apron.
        if(!bInRange)return true;
        const FTransform T(Rotation,FVector(P,Ground-Burial)-Rotation.RotateVector(Pivot*Scale),Scale);
        if(!Rock.Box.TransformBy(T).Intersect(Bounds))return true;
        FTemperatePlacement& Item=Out.AddDefaulted_GetRef();
        Item.Mesh=FSoftObjectPath(Rock.Mesh);
        Item.Key=Key(Id,0,Seed,3593);
        Item.CandidateId=0x5000000000000000ULL|uint64(Id);
        Item.Transform=T;
        return true;
    };

    // These exposed heads belong to the same bedrock as the cut. Their scale
    // carries across the lake while the small gravel and grass stream locally.
    for(int32 I=0;I<Outcrops.Num();++I)
    {
        if(Section!=INDEX_NONE&&Section!=I)continue;
        const FVector2D Head=Outcrops[I],World=Region.World(Head.X,Head.Y);
        if(!NearQuery(World,960.))continue;
        const FVector LocalNormal=RegionRotation.UnrotateVector(SurfaceNormal(World.X,World.Y));
        FVector2D Fall=FVector2D(LocalNormal).GetSafeNormal();
        if(Fall.IsNearlyZero())Fall=FVector2D(0.,-1.);
        const uint32 K=Key(I,0,Seed,9653);
        const double Side=Unit(K)>.5?1.:-1.;
        const FVector2D Strike=Fall.GetRotated(Side*(42.+31.*Unit(K+1)));
        const double Span=250.+130.*Unit(K+2);
        const int32 Count=2+int32(Mix(K+3)%3);
        for(int32 J=0;J<Count;++J)
        {
            const uint32 V=Key(I,J,Seed,9659);
            const double T=double(J)/Count;
            const FVector2D At=Head+Fall*(T*Span*1.65)+Strike*(T*Span*(1.4*Unit(V)-.7));
            const FVector2D P=Region.World(At.X,At.Y);
            const auto Surface=RiverPlan->QuarryLakeSlope.Sample(P.X,P.Y);
            if(Surface.Coverage<.65||Surface.Gully>.24)continue;
            const auto& Rock=Kit[int32(EQuarryStone::Spur)+int32((I+J)%3)];
            if(!Rock.Mesh)continue;
            const FVector Native=Rock.Box.GetSize();
            FVector Size=Native*((1.-.83*T)*Span/FMath::Max(1.,Native.GetMax()));
            Size.Z*=.72+.22*Unit(V+1);
            const FVector Normal=RegionRotation.UnrotateVector(SurfaceNormal(P.X,P.Y));
            const FVector2D Axis=Strike.GetRotated(42.*(Unit(V+2)-.5)+(Native.Y>Native.X?90.:0.));
            const FRotator Attitude=FRotationMatrix::MakeFromZX(Normal,FVector(Axis,0)).Rotator();
            if(!Place(850000+I*8+J,Rock,At,Size,Attitude,Size.Z*(J?.28:.43))&&J==0)break;
        }
    }

    const auto& Approach=ApproachMeshes();
    const FQuarryMesh Plate(Cast<UStaticMesh>(Approach[4].ResolveObject())),KeyBlock(Cast<UStaticMesh>(Approach[5].ResolveObject()));
    for(int32 CutIndex=0;CutIndex<UE_ARRAY_COUNT(Cuts);++CutIndex)
    {
        if(Section!=INDEX_NONE&&Section!=Outcrops.Num()+CutIndex)continue;
        const FCut& Cut=Cuts[CutIndex];
        const FVector2D Parent=Region.World(Cut.At.X,Cut.At.Y);
        if(!NearQuery(Parent,Cut.Size.Size()+Cut.Run*1.5+600))continue;
        const auto& ParentRock=Cut.Stone==EQuarryStone::SlipPlate?Plate:Cut.Stone==EQuarryStone::KeyBlock?KeyBlock:Kit[int32(Cut.Stone)];
        FVector ParentSize=Cut.Size;
        if(ParentRock.Mesh && (Cut.Stone==EQuarryStone::SlipPlate || Cut.Stone==EQuarryStone::KeyBlock))
        {
            // Fragments have the source socket's outline. Scale uniformly; the missing rim feeds the fan.
            const FVector Native=ParentRock.Box.GetSize();
            ParentSize=Native*(Cut.Size.X/FMath::Max(1.,Native.X));
        }
        const bool bPlaced=Place(Cut.Id,ParentRock,Cut.At,ParentSize,FRotator(Cut.Dip,Cut.Strike,0),Cut.Burial);
        if(!bPlaced || !Cut.Blocks)continue;

        // Start at the exposed toe. On a bench lip the apron turns downhill;
        // on level ground the dominant direction remains the face's open side.
        const FVector2D Along=FVector2D(1,0).GetRotated(Cut.Strike);
        const double Foot=.5*(ParentSize.X*FMath::Abs(FVector2D::DotProduct(Along,Cut.Fall))+
                              ParentSize.Y*FMath::Abs(FVector2D::CrossProduct(Along,Cut.Fall)));
        const FVector2D Toe=Cut.At+Cut.Fall*(Foot*.9);
        const FVector2D ToeWorld=Region.World(Toe.X,Toe.Y);
        const FVector Normal=SurfaceNormal(ToeWorld.X,ToeWorld.Y);
        const FVector2D Slope=FVector2D(RegionRotation.UnrotateVector(Normal));
        const FVector2D Fall=(Cut.Fall+Slope*.85).GetSafeNormal();
        const FVector2D Across(-Fall.Y,Fall.X);
        const double LobeSign=Unit(Key(Cut.Id,0,Seed,3602))<.5?-1.:1.;
        const int32 Count=Cut.Blocks+(bIncludeChips?Cut.Chips:0);
        for(int32 I=0;I<Count;++I)
        {
            const bool bChip=I>=Cut.Blocks;
            const uint32 K=Key(Cut.Id,I,Seed,3613);
            const double T=bChip?.10+.90*Unit(K):.06+.63*(I+.65*Unit(K))/Cut.Blocks;
            const double Side=(I%3==0?-.64:1.)*LobeSign;
            const double Width=Cut.Run*(.16+.39*T);
            const FVector2D At=Toe+Fall*(Cut.Run*T)+Across*(Width*(Side*.56+1.18*(Unit(K+1)-.5)));
            constexpr EQuarryStone BlockShapes[]={EQuarryStone::Shelf,EQuarryStone::Spur,EQuarryStone::Wedge};
            const int32 Model=bChip?int32(EQuarryStone::ChipBegin)+int32(Mix(K+2)%ChipVariants):
                int32(BlockShapes[(I+Cut.Id)%UE_ARRAY_COUNT(BlockShapes)]);
            const FQuarryMesh& Rock=Kit[Model];
            if(!Rock.Mesh)continue;
            const FVector Native=Rock.Box.GetSize();
            // Plate-sized fragments bridge the gap between metre blocks and loose gravel.
            const double Span=bChip?FMath::Lerp(62.,10.,T)*(.59+.88*Unit(K+3)):
                Cut.Run*(I==0?.21:(.135-.096*T))*(.70+.53*Unit(K+3));
            FVector Size=Native*(Span/Native.GetMax());
            Size.Z*=bChip?1.:(.72+.22*Unit(K+4));
            const double Azimuth=Cut.Strike+(bChip?150.:52.)*(Unit(K+5)-.5)+(I%3==0?68.:0.);
            const bool Placed=Place((bChip?10000:1000)+64*Cut.Id+I,Rock,At,Size,
                FRotator(-15.+28.*Unit(K+6),Azimuth,-13.+26.*Unit(K+7)),Size.Z*(.14+.13*Unit(K+8)));
            if(!bChip || !Placed || I%2)continue;
            // A plate traps fines on its downhill side. Individual small stones
            // retain scan proportions and share the same six instanced batches.
            for(int32 J=0;J<4;++J)
            {
                const uint32 G=Key(Cut.Id,I*4+J,Seed,3677);
                const auto& Fine=Kit[int32(EQuarryStone::ChipBegin)+int32(Mix(G)%ChipVariants)];
                if(!Fine.Mesh)continue;
                const double Dist=Span*(.32+.70*Unit(G+1));
                const FVector2D P=At+Fall*Dist+Across*(Span*(Unit(G+2)-.5)*1.15);
                const FVector Base=Fine.Box.GetSize();
                const FVector Pebble=Base*((3.5+9.*Unit(G+3))/Base.GetMax());
                Place(100000+Cut.Id*512+I*4+J,Fine,P,Pebble,FRotator(6.*Unit(G+4),Azimuth+95.*Unit(G+5),0),Pebble.Z*.28);
            }
        }
    }

    if((Section!=INDEX_NONE&&Section!=Outcrops.Num()+int32(UE_ARRAY_COUNT(Cuts)))||!Assets->QuarryProps.IsValidIndex(1))return;
    const auto& Build=ApproachMeshes();
    UStaticMesh* Props[]={Cast<UStaticMesh>(Build[2].ResolveObject()),Assets->QuarryProps[1].Get(),Cast<UStaticMesh>(Build[3].ResolveObject())};
    for(int32 I=0;I<UE_ARRAY_COUNT(WorkSites);++I)
    {
        const auto& S=WorkSites[I];
        Place(S.Id,FQuarryMesh(Props[I]),S.At,S.Size,FRotator(0,S.Yaw,0),S.Burial,true);
    }
}

namespace
{
using FQuarryStage=FTemperateHillsStreamingState::EQuarryStage;
using FQuarryAssembly=FTemperateHillsStreamingState::FQuarryAssembly;

bool IsQuarryDetail(const FSoftObjectPath& Mesh)
{
    return VergeMeshes.Contains(Mesh)||QuarryFractureMeshes().Find(Mesh)>=FirstChipMesh;
}

// Retain the original mesh group and instance order across submissions, including collision/nav flags.
bool SubmitQuarryInstances(ATemperateHillsWorld& Hills,FQuarryAssembly& Build,bool Details)
{
    auto* Part=Build.ActiveComponent.Get();
    if(!Part)
    {
        for(const auto& Pair:Build.Groups)
            if(IsQuarryDetail(Pair.Key)==Details){Build.ActiveMesh=Pair.Key;break;}
        if(Build.ActiveMesh.IsNull())return true;
        const auto& Key=Build.ActiveMesh;
        Part=NewObject<UInstancedStaticMeshComponent>(&Hills);
        Hills.AddInstanceComponent(Part);
        Part->SetupAttachment(Hills.GetRootComponent());
        Part->SetMobility(Hills.GetRootComponent()->Mobility);
        Part->SetStaticMesh(CastChecked<UStaticMesh>(Key.ResolveObject()));
        Part->SetCollisionProfileName(Details?TEXT("NoCollision"):TEXT("BlockAll"));
        if(Details)
        {
            Part->SetReceivesDecals(false);
            Part->SetAffectDistanceFieldLighting(false);
            Part->SetVisibleInRayTracing(false);
            Part->bUseAsOccluder=false;
        }
        Part->SetCanEverAffectNavigation(!Details&&Hills.HasAuthority());
        Part->SetCullDistances(Details?5000:75000,Details?7500:95000);
        Part->ComponentTags.Add(VergeMeshes.Contains(Key)?TEXT("HillsQuarryVerge"):Details?TEXT("HillsQuarryChips"):TEXT("HillsWhiteCliffs"));
        if(Key==ApproachMeshes()[0]||Key==ApproachMeshes()[1])Part->ComponentTags.Add(TEXT("HillsQuarryRimSupport"));
        Part->RegisterComponent();
        Build.ActiveComponent=Part;
    }
    const auto& Transforms=Build.Groups.FindChecked(Build.ActiveMesh);
    const int32 Count=FMath::Min(Details?128:32,Transforms.Num()-Build.NextInstance);
    TArray<FTransform> Batch;
    Batch.Append(Transforms.GetData()+Build.NextInstance,Count);
    Part->AddInstances(Batch,false,true,!Details&&Hills.HasAuthority());
    Build.InstanceCount+=Count;
    Build.NextInstance+=Count;
    if(Build.NextInstance==Transforms.Num())
    {
        Build.Groups.Remove(Build.ActiveMesh);
        Build.ActiveMesh.Reset();
        Build.ActiveComponent.Reset();
        Build.NextInstance=0;
    }
    return false;
}
}

bool ATemperateHillsWorld::WithinQuarryReach(const FVector& Position,double Reach) const
{
    if(!RiverPlan||!RiverPlan->WhiteCliffs.Valid)return false;
    const FVector2D P=RiverPlan->WhiteCliffs.Local(Position.X,Position.Y);
    // Include the lake-facing slope as well as the quarry and its approach.
    const double MinY=FMath::Min(-14500.,RiverPlan->QuarryLakeSlope.MinY);
    const FVector2D Nearest(FMath::Clamp(P.X,-14500.,14500.),FMath::Clamp(P.Y,MinY,14500.));
    return FVector2D::DistSquared(P,Nearest)<=FMath::Square(Reach);
}

#if WITH_EDITOR
bool ATemperateHillsWorld::ExportQuarrySurvey(const FString& Directory)
{
    Seed=TemperateHillsMap::Seed;
    GeneratorVersion=TemperateHillsMap::GeneratorVersion;
    bStartLocationCached=false;
    auto Layout=TemperateHillsFixedLayout::Load(Seed,GeneratorVersion,SizeMeters*50.,
        FVector2D(GetGenerationAnchor()),TemperateEcology::Get());
    if(!Layout.River || !Layout.River->WhiteCliffs.Valid) return false;
    const auto Fixed=TemperateQuarryFixedDressing::Load(Layout.Checksum);
    if(!Fixed) return false;
    RiverPlan=Layout.River; ForestWaterPlan=Layout.Water; VillageSite=Layout.Village;
    ChapelSite=VillageSite.ChapelLot();
    const auto& Site=RiverPlan->WhiteCliffs;
    const FTransform Survey(FVector(Site.Axis,0).Rotation(),FVector(Site.Center,Site.FloorZ));
    FString Csv=TEXT("mesh,detail,x,y,z,pitch,yaw,roll,sx,sy,sz\n");
    for(const auto& Group:Fixed->Groups)
        for(const auto& Original:Group.Value)
        {
            const FTransform Local=Original.GetRelativeTransform(Survey);
            const auto P=Local.GetTranslation(),S=Local.GetScale3D();
            const auto R=Local.Rotator();
            Csv+=FString::Printf(TEXT("%s,%d,%.5f,%.5f,%.5f,%.7f,%.7f,%.7f,%.8f,%.8f,%.8f\n"),
                *Group.Key.ToString(),int32(IsQuarryDetail(Group.Key)),P.X,P.Y,P.Z,R.Pitch,R.Yaw,R.Roll,S.X,S.Y,S.Z);
        }
    TArray<float> Grid;
    for(int32 Y=-120;Y<=120;++Y) for(int32 X=-120;X<=120;++X)
    {
        const auto P=Site.World(X*100.,Y*100.);
        Grid.Add(float(BaseHeight(P.X,P.Y)-Site.FloorZ));
    }
    return FFileHelper::SaveStringToFile(Csv,*(Directory/TEXT("quarry.csv")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
        && FFileHelper::SaveArrayToFile(MakeArrayView(reinterpret_cast<const uint8*>(Grid.GetData()),Grid.Num()*sizeof(float)),*(Directory/TEXT("quarry-ground.f32")));
}

bool ATemperateHillsWorld::BakeFixedQuarryDressing(uint32 LayoutChecksum)
{
    TArray<FSoftObjectPath> Paths;
    AddQuarryRockLoadPaths(Paths);
    const auto Loaded=UAssetManager::GetStreamableManager().RequestSyncLoad(Paths);
    TArray<UStaticMesh*> Meshes;
    for(const auto& Path:Paths)
    {
        UObject* Object=Path.ResolveObject();
        if(!Object){UE_LOG(LogTemp,Error,TEXT("Cannot bake quarry asset %s"),*Path.ToString());return false;}
        if(auto* Mesh=Cast<UStaticMesh>(Object))Meshes.AddUnique(Mesh);
    }
    FStaticMeshCompilingManager::Get().FinishCompilation(Meshes);

    const double Half=SizeMeters*50.;
    const auto& Site=RiverPlan->WhiteCliffs;
    const double Yaw=FMath::RadiansToDegrees(FMath::Atan2(Site.Axis.Y,Site.Axis.X));
    TemperateQuarryFixedDressing::FLayout Data;
    TArray<FTemperatePlacement> Items;
    GetWhiteCliffPlacements(FBox(FVector(-Half,-Half,-100000),FVector(Half,Half,100000)),Items,true);
    for(const auto& Item:Items)
    {
        Data.Groups.FindOrAdd(Item.Mesh).Add(Item.Transform);
        if(!IsQuarryDetail(Item.Mesh))
        {
            const FQuarryMesh Rock(CastChecked<UStaticMesh>(Item.Mesh.ResolveObject()));
            Data.Blockers.Add({Rock.Box.TransformBy(Item.Transform),Item});
        }
    }
    const FTransform Survey(FRotator(0,Yaw,0),FVector(Site.Center,Site.FloorZ));
    for(int32 I=0;I<2;++I)Data.Groups.FindOrAdd(ApproachMeshes()[I]).Add(Survey);
    TMap<FIntPoint,double> GroundVertices;
    const int32 Sections=SlopeSections(RiverPlan->QuarryLakeSlope)+int32(UE_ARRAY_COUNT(Verges))+2;
    for(int32 Section=0;Section<Sections;++Section)
        DressQuarryVerges(*RiverPlan,Section,Yaw,Seed,Half,[this](double X,double Y){return Height(X,Y);},GroundVertices,Data.Groups);
    return TemperateQuarryFixedDressing::Write(LayoutChecksum,Data);
}
#endif

bool ATemperateHillsWorld::PrepareQuarryForVegetation(const FBox& CellBounds)
{
    if(!Streaming||Streaming->Quarry.HasBlockers()||Streaming->Quarry.Stage==FQuarryStage::Failed)return true;
    // The rock mask also reads support in neighbouring cells. Wait only for cells whose
    // support may depend on this quarry, including a first-frame teleport onto the slope.
    if(!WithinQuarryReach(CellBounds.GetCenter(),FVector2D(CellBounds.GetExtent()).Size()+6400.))return true;
    Streaming->Quarry.Requested=true;
    return false;
}

void ATemperateHillsWorld::StreamQuarry(TConstArrayView<FVector> ViewCenters)
{
    auto& Build=Streaming->Quarry;
    if(Build.Stage==FQuarryStage::Complete||Build.Stage==FQuarryStage::Failed||!RiverPlan||!RiverPlan->WhiteCliffs.Valid)return;
    if(Build.Stage==FQuarryStage::Idle)
    {
        bool Needed=Build.Requested;
#if !UE_BUILD_SHIPPING
        Needed|=Streaming->bWhiteCliffsVisit&&Streaming->Visitor.IsValid();
#endif
        const double Prefetch=bReady?ViewRadiusMeters*100.:HillsStreaming::EntryRadius;
        for(const FVector& Center:ViewCenters)Needed|=WithinQuarryReach(Center,Prefetch);
        if(!Needed)return;
        if(Streaming->FixedLayoutChecksum && TerrainEdits.IsEmpty() && GetNetMode()!=NM_DedicatedServer)
            Build.FixedDressingJob=Async(EAsyncExecution::ThreadPool,[Checksum=Streaming->FixedLayoutChecksum]()
                {return TemperateQuarryFixedDressing::Load(Checksum);});
        AddQuarryRockLoadPaths(Build.Paths);
        Build.Handle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Build.Paths);
        Build.Stage=FQuarryStage::Loading;
        return;
    }
    if(Build.Stage==FQuarryStage::Loading)
    {
        if(Build.Handle&&!Build.Handle->HasLoadCompleted())return;
        if(Build.FixedDressingJob.IsValid()&&!Build.FixedDressingJob.IsReady())return;
        for(const auto& Path:Build.Paths)
        {
            UObject* Asset=Path.ResolveObject();
            if(!Asset)
            {
                Build.Stage=FQuarryStage::Failed;
                UE_LOG(LogTemp,Error,TEXT("HILLS_QUARRY could not load %s"),*Path.ToString());
                return;
            }
#if WITH_EDITOR
            if(auto* Mesh=Cast<UStaticMesh>(Asset);Mesh&&Mesh->IsCompiling())return;
#endif
        }
        if(Assets->WhiteCliffMeshes.Num()<2||!Assets->QuarryProps.IsValidIndex(1))
        {
            Build.Stage=FQuarryStage::Failed;
            UE_LOG(LogTemp,Error,TEXT("HILLS_QUARRY incomplete quarry mesh manifest"));
            return;
        }
        Streaming->QuarryBlockerRevision=TerrainEditRevision;
        Build.Stage=FQuarryStage::RockLayout;
        if(Build.FixedDressingJob.IsValid())
        {
            auto Data=Build.FixedDressingJob.Get();
            bool KitMatches=true;
            if(Data)
                for(const auto& Group:Data->Groups)
                    if(!Build.Paths.Contains(Group.Key) || !Cast<UStaticMesh>(Group.Key.ResolveObject()))
                    {
                        UE_LOG(LogTemp,Warning,TEXT("HILLS_QUARRY asset set changed, using current placement rules for %s"),*Group.Key.ToString());
                        KitMatches=false;
                        break;
                    }
            if(Data && KitMatches && TerrainEdits.IsEmpty())
            {
                Build.Groups=MoveTemp(Data->Groups);
                Streaming->QuarryBlockers=MoveTemp(Data->Blockers);
                Streaming->VegetationRockWindows.Reset();
                Build.UsingFixedDressing=true;
                Build.Stage=FQuarryStage::Collision;
            }
        }
        Build.Paths.Reset();
    }

    const bool Visuals=GetNetMode()!=NM_DedicatedServer;
    const auto& Site=RiverPlan->WhiteCliffs;
    const double Half=SizeMeters*50.;
    const double Yaw=FMath::RadiansToDegrees(FMath::Atan2(Site.Axis.Y,Site.Axis.X));
    const double End=FPlatformTime::Seconds()+.00125;
    do
    {
        switch(Build.Stage)
        {
        case FQuarryStage::RockLayout:
        {
            TArray<FTemperatePlacement> Items;
            GetWhiteCliffPlacements(FBox(FVector(-Half,-Half,-100000),FVector(Half,Half,100000)),Items,Visuals,Build.NextSection++);
            for(const auto& Item:Items)
            {
                Build.Groups.FindOrAdd(Item.Mesh).Add(Item.Transform);
                if(!IsQuarryDetail(Item.Mesh))
                {
                    const FQuarryMesh Rock(CastChecked<UStaticMesh>(Item.Mesh.ResolveObject()));
                    Streaming->QuarryBlockers.Add({Rock.Box.TransformBy(Item.Transform),Item});
                }
            }
            if(Build.NextSection>RiverPlan->QuarryLakeSlope.Outcrops.Num()+int32(UE_ARRAY_COUNT(Cuts)))
            {
                const FTransform Survey(FRotator(0,Yaw,0),FVector(Site.Center,Site.FloorZ));
                for(int32 I=0;I<2;++I)Build.Groups.FindOrAdd(ApproachMeshes()[I]).Add(Survey);
                Streaming->VegetationRockWindows.Reset();
                Build.Stage=FQuarryStage::Collision;
                Build.NextSection=0;
            }
            break;
        }
        case FQuarryStage::Collision:
            if(SubmitQuarryInstances(*this,Build,false))Build.Stage=Visuals?FQuarryStage::Dressing:FQuarryStage::Complete;
            break;
        case FQuarryStage::Dressing:
            if(!Build.UsingFixedDressing)
                DressQuarryVerges(*RiverPlan,Build.NextSection++,Yaw,Seed,Half,[this](double X,double Y){return Height(X,Y);},Build.GroundVertices,Build.Groups);
            if(Build.UsingFixedDressing||Build.NextSection>=SlopeSections(RiverPlan->QuarryLakeSlope)+int32(UE_ARRAY_COUNT(Verges))+2)
            {
                auto* Decal=NewObject<UDecalComponent>(this);
                AddInstanceComponent(Decal);Decal->SetupAttachment(RootComponent);
                Decal->SetMobility(RootComponent->Mobility);
                Decal->DecalSize=FVector(1800.,4780.,4780.);
                Decal->SetWorldLocationAndRotation(FVector(Site.World(0,600),Site.FloorZ+760.),FRotator(-90,Yaw,0));
                auto* Surface=UMaterialInstanceDynamic::Create(CastChecked<UMaterialInterface>(GroundFinish.ResolveObject()),Decal);
                Surface->SetVectorParameterValue(TEXT("Survey"),FLinearColor(Site.Center.X,Site.Center.Y,Site.Axis.X,Site.Axis.Y));
                Surface->SetScalarParameterValue(TEXT("FloorZ"),Site.FloorZ);
                Decal->SetDecalMaterial(Surface);Decal->SetSortOrder(-2);Decal->RegisterComponent();
                Build.GroundVertices.Empty();
                Build.Stage=FQuarryStage::Details;
            }
            break;
        case FQuarryStage::Details:
            if(SubmitQuarryInstances(*this,Build,true))Build.Stage=FQuarryStage::Complete;
            break;
        default:
            return;
        }
        if(Build.Stage==FQuarryStage::Complete)
        {
            Build.Groups.Empty();
            UE_LOG(LogTemp,Display,TEXT("HILLS_WHITE_CLIFFS assembled instances=%d"),Build.InstanceCount);
            return;
        }
    } while(FPlatformTime::Seconds()<End);
}
