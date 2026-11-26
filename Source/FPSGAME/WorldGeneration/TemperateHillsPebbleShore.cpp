#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "TemperateShoreHabitat.h"
#include "TemperateLakeCoveOutlet.h"
#include "TemperateVegetationPlacement.h"
#include "Engine/StaticMesh.h"

namespace
{
int32 PebbleVariant(double AboveWater, uint32 Key, int32 Count)
{
    // The damp contact band breaks up across several centimetres of elevation.
    return Count == 1 || AboveWater < 8. + 13. * TemperateHillsSurface::Unit(Key + 23)
        ? 0 : 1 + Key % (Count - 1);
}

// Loose gravel is shorter than the difference between the continuous bank
// profile and its rendered triangles. Interpolate the three vertices beneath
// the stone on the detailed shore grid (the diagonal runs SW to NE).
double ShoreStoneBed(const ATemperateHillsWorld& Hills,double X,double Y,double ProfileHeight,bool bFinishBank)
{
    using namespace TemperateRiver::LakeShoreDetail;
    if(!bFinishBank&&!NearSurveyTile(X,Y,Hills.Seed)&&!CoveOutlet::Near(X,Y,Hills.Seed))return ProfileHeight;
    constexpr double Step=100.;
    const double Half=Hills.SizeMeters*50.;
    const double X0=FMath::FloorToDouble((X+Half)/Step)*Step-Half;
    const double Y0=FMath::FloorToDouble((Y+Half)/Step)*Step-Half;
    const double U=(X-X0)/Step,V=(Y-Y0)/Step;
    const double A=Hills.Height(X0,Y0),C=Hills.Height(X0+Step,Y0+Step);
    const double Triangle=U>V ? (1.-U)*A+(U-V)*Hills.Height(X0+Step,Y0)+V*C :
        (1.-V)*A+(V-U)*Hills.Height(X0,Y0+Step)+U*C;
    return FMath::Min(ProfileHeight,Triangle);
}

// Interlocking beds, in centimetres along/across the cape. One fork disappears
// under water, another breaks up into two smaller blocks on the landward side.
struct FShelfBed {double Along,Inland,Length,Width,Height,Yaw;};
constexpr FShelfBed CapeBeds[]={
    {-260.,-355.,225.,159.,49., 4.},{-170.,-221.,282.,178.,64.,-10.},
    { -79.,-102.,234.,119.,61.,14.},{ 123., 114.,252.,156.,78.,-12.},
    { 239., 250.,255.,142.,66., 8.},{ 342., 348.,191.,109.,47., 24.},
    { 228., -40.,169., 89.,43.,40.}
};

void AppendCapeBeds(const ATemperateHillsWorld& Hills,const FTemperatePlacement& Support,
    const FBox& Bounds,TArray<FTemperatePlacement>& Out)
{
    using namespace TemperateRiver::LakeShoreDetail;
    // Only this surveyed parent owns the beds. Every PCG strip computes the
    // same transforms; the final pivot assigns a single strip owner.
    if(Hills.Seed!=SurveySeed || Support.CandidateId!=0xbfffffc8ffffffe2ULL)return;
    const UStaticMesh* Rock=Cast<UStaticMesh>(Support.Mesh.ResolveObject());
    if(!Rock)return;
    const FBox Local=HillsVegetation::BoundsOf(Rock);
    if(!Local.IsValid)return;
    const FVector Size=Local.GetSize();
    const FVector2D Direction=Cape.Inland+Cape.Along()*.62;
    const double BaseYaw=FMath::Atan2(Direction.Y,Direction.X);
    for(int32 Index=0;Index<UE_ARRAY_COUNT(CapeBeds);++Index)
    {
        const auto& Bed=CapeBeds[Index];
        const FVector2D XY=Cape.Point(Bed.Along,Bed.Inland);
        const FVector N=Hills.SurfaceNormal(XY.X,XY.Y);
        const double Yaw=BaseYaw+FMath::DegreesToRadians(Bed.Yaw)+(Index%2?UE_PI:0.);
        const FQuat Rot=FQuat(N,Yaw)*FQuat::FindBetweenNormals(FVector::UpVector,N);
        const FVector Scale(Bed.Length/FMath::Max(1.,Size.X),Bed.Width/FMath::Max(1.,Size.Y),Bed.Height/FMath::Max(1.,Size.Z));
        const FVector Tip=Rot.RotateVector(FVector(Bed.Length*.36,0.,0.));
        const double Z=FMath::Min3(Hills.Height(XY.X,XY.Y),Hills.Height(XY.X+Tip.X,XY.Y+Tip.Y)-Tip.Z,
            Hills.Height(XY.X-Tip.X,XY.Y-Tip.Y)+Tip.Z);
        const FVector Base(Local.GetCenter().X,Local.GetCenter().Y,Local.Min.Z);
        const FVector Pivot=FVector(XY,Z)-Rot.RotateVector(Base*Scale)-N*(Bed.Height*.33);
        if(Pivot.X<Bounds.Min.X||Pivot.X>=Bounds.Max.X||Pivot.Y<Bounds.Min.Y||Pivot.Y>=Bounds.Max.Y)continue;
        auto& Item=Out.Emplace_GetRef();
        Item.Mesh=Support.Mesh;Item.Transform=FTransform(Rot,Pivot,Scale);
        Item.Key=TemperateHillsSurface::Mix(Support.Key+16+Index);
        Item.CandidateId=TemperateShore::CompanionId(Support.CandidateId,16+Index);
    }
}
}

void ATemperateHillsWorld::GetRiverPebblePlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!RiverPlan||!Assets||Assets->RiverPebbles.IsEmpty()||!RiverPlan->IntersectsCell(Bounds.Min.X,Bounds.Min.Y,
        FMath::Max(Bounds.Max.X-Bounds.Min.X,Bounds.Max.Y-Bounds.Min.Y)))return;
    using namespace TemperateHillsSurface;
    const double Tile=2*FMath::Clamp(Assets->RiverPebbleSpacingCm,45.f,180.f);
    const double Coverage=FMath::Clamp(Assets->RiverPebbleCoverage,0.f,1.f);
    const double Half=SizeMeters*50-500;
    const FVector2D Start(GetStartLocation());
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/Tile);Y<=FMath::FloorToInt(Bounds.Max.Y/Tile);++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/Tile);X<=FMath::FloorToInt(Bounds.Max.X/Tile);++X)
    {
        using namespace TemperateRiver::LakeShoreDetail;
        const double CX=(X+.5)*Tile,CY=(Y+.5)*Tile;
        const bool SurveyTile=CoveOutlet::Near(CX,CY,Seed)||NearSurveyTile(CX,CY,Seed);
        const int32 Candidates=SurveyTile?16:RiverPlan->Lake.HasBankTile(CX,CY)?8:4;
        for(int32 Index=0;Index<Candidates;++Index)
        {
            const uint32 K=Mix(Key(X,Y,Seed,2333)^uint32(Index+1)*0x9e3779b9U);
            const double PX=(X+Unit(K+1))*Tile,PY=(Y+Unit(K+2))*Tile;
            if(PX<Bounds.Min.X||PX>=Bounds.Max.X||PY<Bounds.Min.Y||PY>=Bounds.Max.Y||FMath::Abs(PX)>Half||FMath::Abs(PY)>Half)continue;
            if(FVector2D::DistSquared(FVector2D(PX,PY),Start)<2400*2400)continue;
            const auto River=RiverPlan->Sample(PX,PY);
            const auto& Local=River.LocalShore;
            const bool Lag=Index>=4&&!Assets->Rocks.IsEmpty()&&Unit(K+18)<.29*Local.Stones;
            if(Index>=4 && !Lag && Unit(K+17)>=FMath::Max3(double(Local.Bar),double(Local.Spine)*.86,double(Local.Roots)*.52))continue;
            const double Cover=Index<4?TemperateRiver::PebbleCover(PX,PY,Seed,River):0.;
            const double Ledge=Index<4?TemperateShore::Margin(PX,PY,Seed,River,Cover).Ledge:0.;
            const bool Slab=Lag||(Index<4&&!Assets->Rocks.IsEmpty()&&Unit(K+12)<.54*Ledge);
            const double Patch=Index<4?FMath::Max(Cover,Slab?Ledge:0.):.68+.26*Unit(K+21);
            if(Unit(K+3)>=Coverage*Patch)continue;
            const double Z=Height(PX,PY),Above=Z-River.WaterZ;
            if(Above<(Slab?-23.:-13.)||Above>240.)continue;
            const FVector N=SurfaceNormal(PX,PY);if(N.Z<.85)continue;
            // First variant is wet; dry bars use the remaining colour variants.
            const int32 Variant=PebbleVariant(Above,K,Assets->RiverPebbles.Num());
            const auto& Mesh=Slab?Assets->Rocks[K%Assets->Rocks.Num()]:Assets->RiverPebbles[Variant];
            const UStaticMesh* Loaded=Mesh.Get();if(!Loaded)continue;
            const FBox Box=HillsVegetation::BoundsOf(Loaded);
            const FVector Size=Box.GetSize();
            const double Coarse=TemperateShore::Exposure(River)*(1.-FMath::SmoothStep(80.,440.,River.Distance-River.HalfWidth));
            const double Length=Lag?33.+38.*Unit(K+4):Slab?35.+64.*Ledge*(.35+.65*Unit(K+4)):
                6.+FMath::Pow(Unit(K+4),1.6)*FMath::Lerp(15.,38.,Coarse);
            const double Width=Length*(.62+Unit(K+5)*.30);
            const double StoneHeight=Length*(Slab?.27+Unit(K+6)*.12:.30+Unit(K+6)*.22);
            const FVector Scale(Length/FMath::Max(1.0,Size.X),Width/FMath::Max(1.0,Size.Y),StoneHeight/FMath::Max(1.0,Size.Z));
            double Yaw=Unit(K+7)*2*PI;
            if(Lag)
            {
                Yaw=Local.StoneYaw+(Unit(K+7)-.5)*1.16+(Index%2?UE_PI:0.);
            }
            else if(Slab&&!River.bLake&&Local.Stones>.16f)
            {
                Yaw=FMath::Atan2(River.Flow.Y,River.Flow.X)+(Unit(K+7)-.5)*1.04+(K&1U?UE_PI:0.);
            }
            const FQuat Rotation=FQuat(N,Yaw)*FQuat::FindBetweenNormals(FVector::UpVector,N);
            // Align the mesh's base centre with the shared terrain and bury a
            // portion of each stone. No floating flat-bottom pebbles on slopes.
            const FVector BaseCenter(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
            const bool bFinishBank=Local.DepositedGravel>0.f||Local.Stones>0.f||(River.bLake&&Local.Spine>0.f);
            double BedZ=Slab&&!Lag&&!bFinishBank?Z:ShoreStoneBed(*this,PX,PY,Z,bFinishBank);
            if(Slab)
            {
                // Seat both ends of the shelf into real ground where the local
                // plane bridges a hollow; an irregular edge may protrude into water.
                const FVector Tip=Rotation.RotateVector(FVector(Length*.39,0.,0.));
                BedZ=FMath::Min3(BedZ,Height(PX+Tip.X,PY+Tip.Y)-Tip.Z,Height(PX-Tip.X,PY-Tip.Y)+Tip.Z);
            }
            const FVector Location=FVector(PX,PY,BedZ)-Rotation.RotateVector(BaseCenter*Scale)
                -N*(StoneHeight*((Lag?.45:.29)+Unit(K+8)*.15)+1.6);
            FTemperatePlacement& P=Out.Emplace_GetRef();
            P.Transform=FTransform(Rotation,Location,Scale);P.Mesh=Mesh.ToSoftObjectPath();P.Key=K;
            // Decorative stones use a distinct low-byte namespace in the grass PCG
            // layer, without harvest identities or per-stone collision bodies.
            P.CandidateId=(uint64(uint32(X)&0xffffffU)<<32)|(uint64(uint32(Y)&0xffffffU)<<8)|uint64(0x60+Index);
        }
    }
}

void ATemperateHillsWorld::GetShoreRockCompanions(const FBox& Bounds,
    const TArray<FTemperatePlacement>& Supports, TArray<FTemperatePlacement>& Out) const
{
    using namespace TemperateHillsSurface;
    const FVector Extent = Bounds.GetSize();
    if (!Assets || !RiverPlan || Supports.IsEmpty() ||
        !RiverPlan->IntersectsCell(Bounds.Min.X, Bounds.Min.Y, FMath::Max(Extent.X, Extent.Y))) return;

    const FVector2D Start(GetStartLocation());
    const double Limit = SizeMeters * 50. - 500.;
    const FBox Search = Bounds.ExpandBy(FVector(750., 750., 0.));
    for (const FTemperatePlacement& Support : Supports)
    {
        if (!Search.IsInsideOrOnXY(Support.Transform.GetLocation())) continue;
        // Reuse the fitted boulders from the cell's rock mask. The Nordic kit
        // supplies the large silhouettes; the skirt has no solid or harvest ID.
        const auto* Rock = Cast<UStaticMesh>(Support.Mesh.ResolveObject());
        if (!Rock || !Assets->RiverRocks.ContainsByPredicate([Rock](const auto& Mesh) { return Mesh.Get() == Rock; })) continue;
        const FBox Shape = HillsVegetation::BoundsOf(Rock).TransformBy(Support.Transform);
        const FVector2D Center(Shape.GetCenter());
        const double Width = FMath::Max(Shape.GetSize().X, Shape.GetSize().Y);
        if (Width < 80. || Width > 610.) continue;
        const auto Bank = RiverPlan->Sample(Center.X, Center.Y);
        const double Edge = Bank.Distance - Bank.HalfWidth;
        if (Bank.Bank < .08 || Edge < -150. || Edge > 540.) continue;

        const uint32 Key = Mix(Support.Key ^ 0xa41d95c3U);
        FVector2D Along=Bank.Flow;
        FVector2D Inland=FVector2D(-Along.Y,Along.X)*(Bank.SignedDistance>=0.?1.:-1.);
        if(Bank.bLake)
        {
            // On a level lake shelf the outline gradient, rather than the
            // ground normal, points inland. Adjacent stones share the same drift.
            const auto EdgeAt=[this](double X,double Y)
            {
                const auto Water=RiverPlan->Sample(X,Y);
                return Water.Bank>0.?Water.Distance-Water.HalfWidth:1200.;
            };
            Inland=FVector2D(EdgeAt(Center.X+55.,Center.Y)-EdgeAt(Center.X-55.,Center.Y),
                EdgeAt(Center.X,Center.Y+55.)-EdgeAt(Center.X,Center.Y-55.)).GetSafeNormal();
            Along=FVector2D(Inland.Y,-Inland.X);
            using namespace TemperateRiver::LakeShoreDetail;
            const bool Survey=Seed!=SurveySeed||NearSurveyTile(Center.X,Center.Y,Seed)||CoveOutlet::Near(Center.X,Center.Y,Seed);
            const FVector2D Drift=Bank.LocalShore.Stones>.20f?
                FVector2D(FMath::Cos(Bank.LocalShore.StoneYaw),FMath::Sin(Bank.LocalShore.StoneYaw)):RiverPlan->Lake.Axis;
            if(Survey?Unit(Key+9)<.5:FVector2D::DotProduct(Along,Drift)<0.)Along*=-1.;
        }
        if (Inland.IsNearlyZero()) continue;
        const double Exposure = TemperateShore::Exposure(Bank);
        using namespace TemperateRiver::LakeShoreDetail;
        const bool ReedShelter=Seed==SurveySeed&&!NearSurveyTile(Center.X,Center.Y,Seed)&&
            !CoveOutlet::Near(Center.X,Center.Y,Seed)&&!Assets->RiverReeds.IsEmpty()&&
            Unit(Key+31)<.68*(1.-FMath::SmoothStep(.15,.64,Exposure));
        if(Bank.bLake && Assets->RiverPebbleCoverage>0.)AppendCapeBeds(*this,Support,Bounds,Out);

        for (int32 Piece = 0; Piece < 12; ++Piece)
        {
            const uint32 K = Mix(Key ^ (uint32(Piece + 1) * 0x9e3779b9U));
            const bool Stone = Piece < 8, Twig = Piece == 8;
            const bool Reed=Piece==10&&ReedShelter;
            const bool Chunk = Stone && (Piece == 0 || Piece == 2) && !Assets->Rocks.IsEmpty();
            if (Stone && (Assets->RiverPebbleCoverage <= 0.f || (!Chunk && Unit(K + 6) >= Assets->RiverPebbleCoverage))) continue;
            if (Twig && Unit(K + 6) >= Assets->GroundDebrisCoverage * (1. - .55 * Exposure)) continue;
            const double Travel = Stone ? (Piece + Unit(K + 1)) / 8. : Unit(K + 1);
            // A tapering downstream gravel tail, one snagged branch on the high
            // water line, and a separate pocket of rooted plants behind the rock.
            const FVector2D StreamSide = Along * (Piece % 3 == 1 || Piece == 2 ? -.65 : 1.);
            const double CrossBank = Chunk ? .38 + .72 * Unit(K + 2) : Unit(K + 2) - .56;
            const FVector2D Dir = Stone ? (StreamSide + Inland * CrossBank).GetSafeNormal() :
                Reed ? (Along-Inland*(.18+.65*Unit(K+2))).GetSafeNormal() :
                (Inland + Along * (Twig ? .85 : (Unit(K + 2) - .5) * 1.6)).GetSafeNormal();
            const double Span = Stone ? FMath::Lerp(Chunk ? 87. : 43., 9., Travel) * (.80 + .35 * Unit(K + 3)) :
                Twig ? 46. + 46. * Unit(K + 3) : Reed ? 44.+32.*Unit(K+3) : 26. + 20. * Unit(K + 3);
            const double Pad = 22. + .62 * Span;
            const FVector Half=Shape.GetExtent();
            const double Face = FMath::Min((Half.X + Pad) / FMath::Max(.001, FMath::Abs(Dir.X)),
                (Half.Y + Pad) / FMath::Max(.001, FMath::Abs(Dir.Y)));
            // The visible foot of a fitted irregular boulder lies inside its
            // rectangular bounds. Tuck the first two slabs into that foot and
            // carry the smaller grains out towards the shallows.
            const double Foot=1./FMath::Sqrt(FMath::Square(Dir.X/FMath::Max(1.,Half.X))+
                FMath::Square(Dir.Y/FMath::Max(1.,Half.Y)));
            double Offset=Foot+12.+Travel*34.; // sheltered upper-bank roots
            if(Stone)Offset=Foot*(Chunk?.76:.94)+Span*.15+(Chunk?4.:Travel*94.);
            if(Twig)Offset=Face+5.+Travel*75.;
            const FVector2D At = Center + Dir * Offset;
            if (FMath::Abs(At.X) >= Limit || FMath::Abs(At.Y) >= Limit ||
                FVector2D::DistSquared(At, Start) < 2400.*2400. || PathDistance(At.X, At.Y) < 350. ||
                VillageSite.Clears(At.X, At.Y, 120.) || ChapelSite.Clears(At.X, At.Y, 120.)) continue;
            const auto Water = RiverPlan->Sample(At.X, At.Y);
            if (Water.Bank <= .04 || SampleForestWater(At.X, At.Y).Wet) continue;
            const double Z = Height(At.X, At.Y), Above = Z - Water.WaterZ;
            if (Above < (Stone ? -19. : Reed ? -12. : 2.) || Above > (Twig ? 75. : Reed ? 45. : 170.)) continue;
            const bool Grass = Piece == 11 && Above > 16.;
            if (!Stone && !Twig)
            {
                const double Density=Grass?EcologyProfile().RiverGrass.Density:
                    Reed?EcologyProfile().RiverReeds.Density:EcologyProfile().RiverGroundCover.Density;
                if(Density<=0. || (Piece!=11 && Unit(K+6)>=Density))continue;
            }
            const auto& Palette = Chunk ? Assets->Rocks : Stone ? Assets->RiverPebbles : Twig ? Assets->RainforestTwigs :
                Grass ? Assets->RiverBankGrasses : Reed ? Assets->RiverReeds : Assets->RiverGroundCover;
            if (Palette.IsEmpty()) continue;
            const int32 Variant = Stone && !Chunk ? PebbleVariant(Above, K, Palette.Num()) : K % Palette.Num();
            const auto& Ref = Palette[Variant];
            const FBox Box = HillsVegetation::BoundsOf(Ref.Get());
            if (!Box.IsValid) continue;
            const FVector Size = Box.GetSize(), N = SurfaceNormal(At.X, At.Y);
            if (N.Z < .86) continue;
            const bool Plant = !Stone && !Twig;
            const double Scale = Span / FMath::Max(1., Plant ? Size.Z : FMath::Max(Size.X, Size.Y));
            const FVector Up = Plant ? FMath::Lerp(FVector::UpVector, N, .35).GetSafeNormal() : N;
            double Heading = FMath::Atan2(Along.Y, Along.X) + (Unit(K + 5) - .5) * (Twig ? .50 : 1.7);
            if (!Plant && Size.Y > Size.X) Heading -= UE_HALF_PI;
            const FQuat Rotation = FQuat(Up, Heading) * FQuat::FindBetweenNormals(FVector::UpVector, Up);
            if (Twig)
            {
                const FVector Tip = Rotation.RotateVector((Size.Y > Size.X ? FVector::RightVector : FVector::ForwardVector) * (.45 * Span));
                if (FMath::Abs(Height(At.X + Tip.X, At.Y + Tip.Y) - Z - Tip.Z) > 6. ||
                    FMath::Abs(Height(At.X - Tip.X, At.Y - Tip.Y) - Z + Tip.Z) > 6.) continue;
            }
            const FVector Base = Plant ? FVector(0., 0., Box.Min.Z) : FVector(Box.GetCenter().X, Box.GetCenter().Y, Box.Min.Z);
            const double Burial = Stone ? Size.Z * Scale * .32 : Plant ? 2. : 1.;
            const bool Mineral=Water.LocalShore.DepositedGravel>0.f||Water.LocalShore.Stones>0.f;
            const double BedZ=Stone&&(!Chunk||Mineral)?
                ShoreStoneBed(*this,At.X,At.Y,Z,Mineral||(Water.bLake&&RiverPlan->Lake.HasBankTile(At.X,At.Y))):Z;
            const FVector Pivot = FVector(At, BedZ) - Rotation.RotateVector(Base * Scale) - Up * Burial;
            if (Pivot.X < Bounds.Min.X || Pivot.X >= Bounds.Max.X || Pivot.Y < Bounds.Min.Y || Pivot.Y >= Bounds.Max.Y) continue;
            auto& P = Out.Emplace_GetRef();
            P.Mesh = Ref.ToSoftObjectPath(); P.Key = K; P.Transform = FTransform(Rotation, Pivot, FVector(Scale));
            // The source river-stone ID encodes its signed X/Y grid cell. Keep
            // those coordinates explicitly so a fan crossing a PCG seam has one owner.
            P.CandidateId = TemperateShore::CompanionId(Support.CandidateId,Piece);
        }
    }
}
