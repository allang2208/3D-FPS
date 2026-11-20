#include "TemperateHillsWorld.h"
#include "TemperateHillsStreamingPrivate.h"
#include "TemperateVegetationPlacement.h"
#include "Engine/StaticMesh.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace QuarryLakeCover
{
// A seed-stable pocket can straddle a streamed cell. Its final mesh pivot owns
// the instance; the neighbouring cell recreates the same source and runout.
constexpr double PocketSpacing=610., PocketReach=850.;
constexpr uint64 IdPrefix=0x7500000000000000ULL;

struct FSupport
{
    double Z;
    FVector Normal;
};
}

bool ATemperateHillsWorld::GetQuarryLakeSlopeCover(const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool bShrubs,int32* CompletedRows) const
{
    using namespace TemperateHillsSurface;
    using namespace QuarryLakeCover;
    if(!Assets||!RiverPlan||RiverPlan->QuarryLakeSlope.Cells.IsEmpty())return true;
    const auto& Field=RiverPlan->QuarryLakeSlope;
    const auto& Site=RiverPlan->WhiteCliffs;
    const FVector Centre=Bounds.GetCenter(),Extent=Bounds.GetExtent();
    const FVector2D Mid=Site.Local(Centre.X,Centre.Y);
    const FVector2D Radius(FMath::Abs(Site.Axis.X)*Extent.X+FMath::Abs(Site.Axis.Y)*Extent.Y+PocketReach,
        FMath::Abs(Site.Axis.Y)*Extent.X+FMath::Abs(Site.Axis.X)*Extent.Y+PocketReach);
    if(FMath::Abs(Mid.X)>9000.+Radius.X||Mid.Y+Radius.Y<Field.MinY||Mid.Y-Radius.Y>0.)return true;
    const auto& Ecology=EcologyProfile();
    if(bShrubs&&(Assets->Shrubs.IsEmpty()||Ecology.Shrubs.Density<=0.))return true;
    TRACE_CPUPROFILER_EVENT_SCOPE(HillsQuarryLakeSlopeCover);

    const double Half=SizeMeters*50.;
    constexpr double Cell=HillsStreaming::CellSize, Grid=Cell/HillsStreaming::SurfaceDetailQuads;
    TMap<FIntPoint,int32> CellStride;
    TMap<FIntPoint,double> Vertices;
    auto HeightAt=[&](int32 X,int32 Y)
    {
        const FIntPoint GridKey(X,Y);
        if(const double* Z=Vertices.Find(GridKey))return *Z;
        const double Z=Height(X*Grid-Half,Y*Grid-Half);
        Vertices.Add(GridKey,Z);
        return Z;
    };
    auto Floor=[&](FVector2D P)->FSupport
    {
        const FIntPoint Tile(FMath::FloorToInt((P.X+Half)/Cell),FMath::FloorToInt((P.Y+Half)/Cell));
        int32& Stride=CellStride.FindOrAdd(Tile);
        if(!Stride)
        {
            const double OX=Tile.X*Cell-Half,OY=Tile.Y*Cell-Half,CX=OX+Cell*.5,CY=OY+Cell*.5;
            const bool Fine=RiverPlan->IntersectsCell(OX,OY,Cell)||Site.Weight(CX,CY)>.01||
                (ForestWaterPlan&&ForestWaterPlan->IntersectsCell(OX,OY,Cell))||VillageSite.Near(CX,CY,Cell*.5)||ChapelSite.Near(CX,CY,Cell*.5);
            Stride=Fine?1:2;
        }
        const double Step=Grid*Stride;
        const double GX=(P.X+Half)/Step,GY=(P.Y+Half)/Step;
        const int32 IX=FMath::FloorToInt(GX),IY=FMath::FloorToInt(GY),X=IX*Stride,Y=IY*Stride;
        const double U=GX-IX,V=GY-IY;
        const double SW=HeightAt(X,Y),NE=HeightAt(X+Stride,Y+Stride);
        const double Side=U>=V?HeightAt(X+Stride,Y):HeightAt(X,Y+Stride);
        const double DX=U>=V?Side-SW:NE-Side,DY=U>=V?NE-Side:Side-SW;
        return {SW+U*DX+V*DY,FVector(-DX,-DY,Step).GetSafeNormal()};
    };

    const FBox Reach=Bounds.ExpandBy(165.);
    const int32 X0=FMath::FloorToInt(FMath::Max(-9000.,Mid.X-Radius.X)/PocketSpacing);
    const int32 X1=FMath::FloorToInt(FMath::Min(9000.,Mid.X+Radius.X)/PocketSpacing);
    const int32 Y0=FMath::FloorToInt(FMath::Max(Field.MinY,Mid.Y-Radius.Y)/PocketSpacing);
    const int32 Y1=FMath::FloorToInt(FMath::Min(0.,Mid.Y+Radius.Y)/PocketSpacing);
    // Only the populated PCG ground pass needs slicing. Each yield advances
    // the source rows, leaving cell seams and group membership unchanged.
    const int32 FirstRow=CompletedRows?Y0+*CompletedRows:Y0;
    const int32 LastRow=CompletedRows?FMath::Min(Y1,FirstRow+1):Y1;
    for(int32 Y=FirstRow;Y<=LastRow;++Y)for(int32 X=X0;X<=X1;++X)
    {
        const uint32 Group=Key(X,Y,Seed,12937);
        const FVector2D Root=Site.World((X+Unit(Group+1))*PocketSpacing,(Y+Unit(Group+2))*PocketSpacing);
        const auto Patch=Field.Sample(Root.X,Root.Y);
        if(Unit(Group+3)>=Patch.Coverage*.93)continue;
        const bool StonePocket=Unit(Group+4)<FMath::Clamp(.08+.84*Patch.Ledge+.86*Patch.Gravel+.16*Patch.Gully,0.,1.);
        // The channels keep a mostly bare damp bed. Shrubs catch on the turf
        // side of an outcrop; the distal fan is low shingle and short grass.
        if(bShrubs&&(Patch.Gully>.48||Patch.Gravel>.61||Unit(Group+5)>=Ecology.Shrubs.Density*(.12+.48*Patch.Turf)))continue;
        const FSupport RootFloor=Floor(Root);
        if(RootFloor.Normal.Z<.62)continue;
        FVector2D Down=FVector2D(RootFloor.Normal).GetSafeNormal();
        if(Down.IsNearlyZero())Down=(RiverPlan->Lake.Center-Root).GetSafeNormal();
        const FVector2D Across(-Down.Y,Down.X);
        const double Hand=Unit(Group+6)>.5?1.:-1.,Run=190.+Unit(Group+7)*310.,Width=70.+Unit(Group+8)*130.;
        const int32 Stones=StonePocket?3+int32(Unit(Group+9)*(4.+6.*Patch.Gravel)):0;
        const int32 Grass=4+int32((7.+13.*Patch.Turf)*(1.-.77*Patch.Gully));
        const uint64 PocketId=IdPrefix|(uint64(uint32(X)&0xffffffU)<<32)|(uint64(uint32(Y)&0xffffffU)<<8);
        for(int32 I=0;I<(bShrubs?1:Stones+Grass);++I)
        {
            const int32 Piece=bShrubs?128:I;
            const uint32 K=Mix(Group^uint32(Piece+1)*0x9e3779b9U);
            const bool Stone=!bShrubs&&I<Stones,Anchor=Stone&&I==0;
            const double Travel=Anchor?0.:Unit(K+1),Side=2.*Unit(K+2)-1.;
            double Along=Travel*Run,Offset=(.22+.78*Travel)*Width*Side;
            if(bShrubs){Along=-80.-Unit(K+3)*60.;Offset=Hand*Width*.65;}
            else if(!Stone)
            {
                Along=(Travel-.28)*Run;
                Offset=StonePocket?Hand*(50.+Travel*Width)+Side*Width*.52:Side*Width*1.15;
            }
            const FVector2D P=Root+Down*Along+Across*(Offset+Hand*55.*Travel*Travel);
            if(!Reach.IsInsideOrOnXY(FVector(P,0.))||FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y))>Half-175.)continue;
            const auto S=Field.Sample(P.X,P.Y);
            if(S.Coverage<.065||(!Stone&&S.Gully>.52&&Unit(K+4)<S.Gully)||
                PathDistance(P.X,P.Y)<(bShrubs?510.:Anchor?410.:300.)||
                ChapelSite.Clears(P.X,P.Y,bShrubs?115.:55.)||VillageSite.Clears(P.X,P.Y,bShrubs?115.:55.))continue;

            const bool Chip=Stone&&!Anchor&&Travel>.34;
            const bool DampGrass=!Stone&&!bShrubs&&S.Damp>.10&&Unit(K+5)<FMath::Min(.85,2.4*S.Damp);
            const bool Green=!Stone&&!bShrubs&&!DampGrass&&Unit(K+6)<RainforestWeight(P.X,P.Y);
            const auto& Grasses=DampGrass&&!Assets->RiverGroundCover.IsEmpty()?Assets->RiverGroundCover:
                Green&&!Assets->RainforestCarpetGrass.IsEmpty()?Assets->RainforestCarpetGrass:Assets->Grass;
            const bool WetGravel=Chip&&(Assets->Rocks.IsEmpty()||(S.Damp>.24&&S.Gravel>.15))&&!Assets->RiverPebbles.IsEmpty();
            const auto& Family=bShrubs?Assets->Shrubs:Stone?(WetGravel?Assets->RiverPebbles:Assets->Rocks):Grasses;
            const double Density=Stone?Assets->GroundDebrisCoverage:bShrubs?1.:DampGrass?Ecology.RiverGroundCover.Density:Ecology.Grass.Density;
            if(Family.IsEmpty()||Density<=0.||(!Stone&&Unit(K+7)>=Density)||
                (Stone&&!Anchor&&Unit(K+7)>=FMath::Min(1.,Density*2.5)))continue;
            const uint32 Variant=Unit(K+8)<.62?Group:K;
            const auto& Ref=Family[Variant%Family.Num()];
            UStaticMesh* Mesh=Ref.Get();
            // Pale broken limestone accumulates in fans below this face. Rounded
            // dark gravel takes over as the runout reaches the damp shore.
            const bool LocalChip=Chip&&!Assets->QuarryShoreChips.IsEmpty()&&
                Unit(K+12)<FMath::Clamp(.28+.72*S.Gravel+.32*S.Ledge-.85*S.Damp,0.,.94);
            if(LocalChip)
            {
                if(UStaticMesh* Limestone=Assets->QuarryShoreChips[Variant%Assets->QuarryShoreChips.Num()].Get())
                    Mesh=Limestone;
            }
            else if(Stone&&(S.Ledge>.16||(!Chip&&S.Gravel>.28)))
                if(auto* QuarryMesh=Cast<UStaticMesh>(QuarrySlopeStoneMesh(Variant,Anchor&&S.Ledge>.27).ResolveObject()))Mesh=QuarryMesh;
            const FBox Box=HillsVegetation::BoundsOf(Mesh);
            if(!Box.IsValid)continue;
            const FSupport Ground=Floor(P);
            if(Ground.Normal.Z<(Stone?.59:bShrubs?.78:.65)||Ground.Z<RiverPlan->Lake.WaterZ+8.)continue;
            const auto Pond=SampleForestWater(P.X,P.Y);
            if(Pond.Wet&&Ground.Z<Pond.WaterZ+20.)continue;
            const FVector Size=Box.GetSize();
            const double Span=Anchor?48.+69.*S.Ledge+29.*Unit(K+9):
                Stone?FMath::Lerp(62.,8.,Travel)*(.74+.48*Unit(K+9)):
                bShrubs?64.+56.*Unit(K+9):16.+(16.+17.*S.Turf)*Unit(K+9);
            const double Factor=Stone?Span/FMath::Max(1.,FMath::Max(Size.X,Size.Y)):FMath::Min(1.30,Span/FMath::Max(1.,Size.Z));
            FVector Scale(Factor);
            if(Stone)Scale.Z=FMath::Min(Factor,Span*(.30+.24*Unit(K+10))/FMath::Max(1.,Size.Z));
            // FitVegetationPlacement measures root relief in this plane. A
            // flatter plane rejects even an unbroken 40-degree bank as a step.
            const FVector Up=bShrubs?FMath::Lerp(FVector::UpVector,Ground.Normal,.24).GetSafeNormal():Ground.Normal;
            const double Heading=Stone?FMath::Atan2(Down.Y,Down.X)+(Anchor&&S.Ledge>S.Gravel?PI*.5:0.)+
                (Size.Y>Size.X?PI*.5:0.)+(Unit(K+11)-.5)*1.2:Unit(K+11)*2.*PI;
            const FQuat Rotation=FRotationMatrix::MakeFromZX(Up,FVector(FMath::Cos(Heading),FMath::Sin(Heading),0.)).ToQuat();
            const FVector Base=bShrubs?FVector(0,0,Box.Min.Z):FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
            const FVector BaseOffset=Rotation.RotateVector(Base*Scale);
            if(BaseOffset.SizeSquared2D()>160.*160.)continue;
            double Z=Ground.Z;
            if(Stone&&Span>35.)
            {
                const FVector Axis=Size.X>=Size.Y?FVector::ForwardVector:FVector::RightVector;
                const FVector D=Rotation.RotateVector(Axis)*(Span*.32);
                Z=FMath::Min3(Z,Floor(P+FVector2D(D)).Z-D.Z,Floor(P-FVector2D(D)).Z+D.Z);
            }
            const double Burial=Stone?Size.Z*Scale.Z*(Anchor?.41:.28):bShrubs?3.:1.5;
            const FVector Pivot=FVector(P,Z-Burial)-BaseOffset;
            if(Pivot.X<Bounds.Min.X||Pivot.X>=Bounds.Max.X||Pivot.Y<Bounds.Min.Y||Pivot.Y>=Bounds.Max.Y)continue;
            auto& Item=Out.Emplace_GetRef();
            Item.Mesh=FSoftObjectPath(Mesh);Item.Key=K;Item.CandidateId=PocketId|uint64(Piece);
            Item.bHasTriangleSupport=!Stone;
            Item.Transform=FTransform(Rotation,Pivot,Scale);
        }
    }
    if(CompletedRows)*CompletedRows+=LastRow-FirstRow+1;
    return LastRow>=Y1;
}
