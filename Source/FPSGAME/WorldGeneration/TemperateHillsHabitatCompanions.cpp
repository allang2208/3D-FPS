#include "TemperateHillsWorld.h"
#include "TemperateForestHabitat.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"

namespace HillsCompanions
{
enum EPart : uint8 { Shrub,Fern,Twig,Pebble,Moss,Fungus,MeadowTuft,Flower };
constexpr EPart Recipes[3][10]={
    {Fern,Twig,Moss,Fern,Twig,Fungus,Pebble,Moss,Twig,Pebble},
    {Shrub,Pebble,Twig,Fern,Pebble,Twig,Moss,Pebble,Fern,Twig},
    {Pebble,Shrub,Pebble,Twig,Pebble,Moss,Fern,Pebble,Twig,Pebble}
};
}

void ATemperateHillsWorld::GetHabitatCompanions(const FBox& Bounds,
    const TArray<FTemperatePlacement>& Supports,bool Trees,
    TArray<FTemperatePlacement>& Plants,TArray<FTemperatePlacement>* Floor) const
{
    if(!Assets)return;
    using namespace TemperateHillsSurface;
    using namespace HillsCompanions;
    const auto& E=EcologyProfile();
    const double Half=SizeMeters*50.-500.;
    for(const auto& Support:Supports)
    {
        const uint32 AnchorKey=Mix(Support.Key^(Trees?0x5e312a9bU:0x7132d6e1U));
        const double Roll=Unit(AnchorKey+1);
        if(Roll>(Trees?.72:.62))continue;
        FBox Shape(ForceInit);
        if(Trees)
        {
            const auto* Mesh=Cast<USkeletalMesh>(Support.Mesh.ResolveObject());
            if(!Mesh)continue;
            Shape=Mesh->GetImportedBounds().GetBox().TransformBy(Support.Transform);
        }
        else
        {
            const auto* Mesh=Cast<UStaticMesh>(Support.Mesh.ResolveObject());
            if(!Mesh)continue;
            // Fallen wood already owns the nurse-log community. Large cliff
            // assemblies need authored dressing, not an oversized ring of props.
            if(Assets->FallenLogs.ContainsByPredicate([&](const auto& R){return R.Get()==Mesh;})||
               Assets->ForestRoots.ContainsByPredicate([&](const auto& R){return R.Get()==Mesh;}))continue;
            Shape=Mesh->GetBoundingBox().TransformBy(Support.Transform);
            const double Width=FMath::Max(Shape.GetSize().X,Shape.GetSize().Y);
            if(Width<100.||Width>1800.)continue;
        }
        const FVector Center=Trees?Support.Transform.GetLocation():Shape.GetCenter();
        const double Region=RainforestWeight(Center.X,Center.Y);
        const double Forest=TemperateForestHabitat::Canopy(Center.X,Center.Y,Seed,Region,E);
        if(Trees&&Roll>.72*(.35+.65*Forest))continue;
        const double Moist=TemperateForestHabitat::Moisture(Center.X,Center.Y,Seed,Region,E);
        const int32 Recipe=Moist>.57&&Forest>.35?0:(Trees?1:2);
        // The horizontal component of the surface normal points downhill.
        // Exposed rock sheds a short fan; sheltered roots catch a narrow drift of litter.
        const FVector2D Down(SurfaceNormal(Center.X,Center.Y));
        const double Aspect=Down.SizeSquared()>.0025?FMath::Atan2(Down.Y,Down.X):Unit(AnchorKey+2)*2.*PI;
        const double Heading=Aspect+(Unit(AnchorKey+7)-.5)*(Trees?1.7:.55);
        const double LobeOffset=Unit(AnchorKey+8)<.5?-.75:.75;
        const double Root=FMath::Clamp(Shape.GetSize().Z*.03,28.,85.);
        const double DryEdgeLight=(1.-Region)*(1.-FMath::SmoothStep(.20,.64,Forest));
        for(int32 I=0;I<10;++I)
        {
            const uint32 K=Mix(AnchorKey^uint32(I+1)*0x9e3779b9U);
            EPart Part=Recipes[Recipe][I];
            // The sunny tail of a stone fan or isolated tree drifts back into
            // meadow. Reuse two outer debris slots so the patch keeps its budget.
            if((I==7||I==9)&&Unit(K+23)<DryEdgeLight)
                Part=I==9&&Moist>.36?Flower:MeadowTuft;
            // Repeated species and stone faces tie the small pieces together.
            // The occasional second lobe leaves windows onto the underlying soil.
            const bool Outer=I>=6;
            const double Travel=Outer?.62+.38*Unit(K+5):.08+.46*Unit(K+5);
            const double Fan=Trees?.90:.68;
            const double Angle=Heading+(Outer?LobeOffset:0.)+(Unit(K+4)-.5)*Fan;
            const bool Plant=Part==Shrub||Part==Fern;
            const bool MeadowPlant=Part==MeadowTuft||Part==Flower;
            if(!Plant&&!Floor)continue;
            if((Part==Moss&&(Moist<.42||Forest<.12))||
               (Part==Fungus&&(!Trees||Moist<.60))||
               (Part==Fern&&Unit(K+11)>.20+.80*Moist))continue;
            if(Plant&&Unit(K+13)>=FMath::Min(1.,Part==Shrub?E.Hazel.Density:E.Ferns.Density))continue;
            if(MeadowPlant&&Unit(K+13)>=FMath::Min(1.,Part==Flower?E.MeadowFlowers.Density:E.GrassAccents.Density))continue;
            FSoftObjectPath Ref;
            FBox Box(ForceInit);
            if(Plant)
            {
                const auto& Palette=Part==Shrub?Assets->ForestShrubs:Assets->ForestFerns;
                if(Palette.IsEmpty()||!Palette[K%Palette.Num()].IsValid())continue;
                const auto& Mesh=Palette[K%Palette.Num()];
                Ref=Mesh.ToSoftObjectPath();Box=Mesh.Get()->GetImportedBounds().GetBox();
            }
            else
            {
                const auto& Palette=Part==MeadowTuft?Assets->GrassAccents:Part==Flower?Assets->MeadowFlowers:
                    Part==Twig?Assets->RainforestTwigs:Part==Pebble?Assets->Rocks:
                    Part==Moss?Assets->ForestMoss:Assets->ForestFungi;
                if(Palette.IsEmpty())continue;
                const uint32 Form=(Part==Pebble||Part==Moss)&&Unit(K+9)<.82?AnchorKey:K;
                const auto& Mesh=Palette[Form%Palette.Num()];
                if(!Mesh.IsValid())continue;
                Ref=Mesh.ToSoftObjectPath();Box=Mesh.Get()->GetBoundingBox();
                Box.Min+=Mesh.Get()->GetNegativeBoundsExtension();
                Box.Max-=Mesh.Get()->GetPositiveBoundsExtension();
            }
            const FVector Size=Box.GetSize();
            const double Span=MeadowPlant?20.+18.*Unit(K+3):
                Part==Shrub?65.+55.*Unit(K+3):Part==Fern?38.+38.*Unit(K+3):
                Part==Twig?FMath::Lerp(95.,28.,Travel)*(.80+.40*Unit(K+3)):
                Part==Pebble?FMath::Lerp(Trees?34.:65.,11.,Travel)*(.68+.56*Unit(K+3)):
                Part==Moss?26.+35.*Unit(K+3):10.+12.*Unit(K+3);
            const double Scale=Span/FMath::Max(1.,Plant||MeadowPlant?Size.Z:FMath::Max(Size.X,Size.Y));
            const FVector2D Direction(FMath::Cos(Angle),FMath::Sin(Angle));
            // Exit the rock's exclusion box along the ray. Adding its padding
            // before the ray test keeps diagonal pieces outside adjoining faces.
            const double Pad=FMath::Max(Size.X,Size.Y)*Scale*.72+24.;
            const double Boundary=Trees?Root+Pad:FMath::Min(
                (Shape.GetExtent().X+Pad)/FMath::Max(.001,FMath::Abs(Direction.X)),
                (Shape.GetExtent().Y+Pad)/FMath::Max(.001,FMath::Abs(Direction.Y)));
            const FVector2D XY=FVector2D(Center)+Direction*(Boundary+Travel*(Trees?220.:265.));
            if(FMath::Abs(XY.X)>Half||FMath::Abs(XY.Y)>Half||PathDistance(XY.X,XY.Y)<450.||
               ChapelSite.Clears(XY.X,XY.Y,180.)||VillageSite.Clears(XY.X,XY.Y,180.))continue;
            if(SampleForestWater(XY.X,XY.Y).Wet||
               (RiverPlan&&RiverPlan->Sample(XY.X,XY.Y).Bank>.12))continue;
            const FVector N=SurfaceNormal(XY.X,XY.Y);
            if(N.Z<(Plant?.90:.88))continue;
            if(MeadowPlant)
            {
                const auto& Rule=Part==Flower?E.MeadowFlowers:E.GrassAccents;
                if(Unit(K+29)>=Rule.SlopeWeight(N.Z))continue;
            }
            const double Yaw=Part==Twig?Angle+(Size.Y>Size.X?.5*PI:0.)+(Unit(K+6)-.5)*.65:Unit(K+6)*2.*PI;
            const FVector Up=Plant||MeadowPlant?FMath::Lerp(FVector::UpVector,N,.22).GetSafeNormal():N;
            const FQuat Rotation=FQuat(Up,Yaw)*FQuat::FindBetweenNormals(FVector::UpVector,Up);
            const FVector Anchor(XY,Height(XY.X,XY.Y));
            if(Part==Twig||Part==Moss)
            {
                bool Supported=true;
                for(const FVector2D D:{FVector2D(1,0),FVector2D(-1,0),FVector2D(0,1),FVector2D(0,-1)})
                {
                    const FVector Offset=Rotation.RotateVector(FVector(D.X*Size.X,D.Y*Size.Y,0)*Scale*.43);
                    if(FMath::Abs(Height(XY.X+Offset.X,XY.Y+Offset.Y)-Anchor.Z-Offset.Z)>(Part==Moss?2.5:5.))
                    {Supported=false;break;}
                }
                if(!Supported)continue;
            }
            const FVector Base=Plant?FVector(0,0,Box.Min.Z):FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
            const double Sink=Part==Moss?-.8:Part==Pebble?Size.Z*Scale*.20:Plant?2.:.5;
            const FVector Location=Anchor-Rotation.RotateVector(Base*Scale)-Up*Sink;
            if(Location.X<Bounds.Min.X||Location.X>=Bounds.Max.X||Location.Y<Bounds.Min.Y||Location.Y>=Bounds.Max.Y)continue;
            FTemperatePlacement P;P.Mesh=Ref;P.Key=K;
            P.Transform=FTransform(Rotation,Location,FVector(Scale));
            // Decorative-only identity derives from the actual support, never
            // from load order or an instance index. No harvest IDs are replaced.
            P.CandidateId=(Support.CandidateId*0x9e3779b97f4a7c15ULL)^(uint64(K)<<8)^uint64(I);
            (Plant?Plants:*Floor).Add(MoveTemp(P));
        }
    }
}
