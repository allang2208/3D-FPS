#include "TemperateVillagePlanting.h"
#include "ForestRootFit.h"
#include "TemperateHillsWorld.h"
#include "TemperateVegetationPlacement.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"

namespace TemperateVillagePlanting
{
namespace
{
struct FPatch { double X,Y,RX,RY,Yaw; int32 Trees; bool Yard=false; int32 GrassSamples=0; };
// The southwest apron and the smaller west-side pocket marked in the reference.
// Keep separate islands rather than filling the crown with a uniform forest grid.
constexpr FPatch Patches[]={
    {1600,-4080,650,310,18,2}, {300,-4210,550,320,-12,2},
    {-1750,-4150,700,420,5,3}, {-3650,-3650,750,500,-26,3},
    {-5050,-2600,500,650,20,3}, {-5400,-1250,420,420,0,1},
    {-5200,1800,500,620,-30,3}, {-5250,3200,550,450,10,2},
    // Chapel beds stay inside the enclosure, below the windows and clear of graves.
    {550,-2480,360,250,15,0,true}, {1500,-2540,440,230,0,0,true},
    {2700,-2550,450,210,-8,0,true}, {3700,-2400,220,300,12,0,true},
    {3720,-1400,210,450,0,0,true}, {3650,-350,230,200,-12,0,true},
    {2600,-280,420,190,5,0,true}, {700,-340,240,250,-15,0,true},
    {-4700,-4140,630,370,23,3}, {-2800,-4460,720,230,-6,1},
    {-4300,-4650,600,220,4,0},
    // Low, broken pockets on the inside of the ramparts and on the far side
    // of the northern and southern houses. Keep the gate approaches open.
    {-5750,-2050,390,190,63,0,true,105}, {-5670,950,470,235,-71,0,true,130},
    {-4600,3420,530,265,22,0,true,160}, {-2400,3810,650,230,8,0,true,170},
    {-290,3930,380,190,-27,0,true,90}, {2450,4040,550,280,-11,0,true,145},
    {4720,3600,580,250,-32,0,true,155}, {5490,2080,520,275,64,0,true,140},
    {5570,-1420,460,195,77,0,true,115}, {4970,-3100,590,245,-33,0,true,155},
    {3550,-3770,510,275,18,0,true,130}
};

bool Clear(const FTemperateVillageSite& Village,const FTemperateChapelSite& Chapel,
           const FVector2D& Local,const FVector2D& World,double Radius,bool Tall)
{
    const double Margin=Radius+(Tall?100.:35.);
    if(FTemperateVillageSite::WorkshopEdge(Local)<=Margin)return false;
    // Stable footprint, expanded west paddock, turning court and split approach in the village's local frame (cm).
    const FBox2D StableWing(FVector2D(880.,3240.),FVector2D(5860.,4690.));
    const FBox2D StableCourt(FVector2D(4500.,1600.),FVector2D(5860.,3260.));
    if(StableWing.ComputeSquaredDistanceToPoint(Local)<=Margin*Margin ||
       StableCourt.ComputeSquaredDistanceToPoint(Local)<=Margin*Margin)return false;
    if(Local.Y>285.-Margin && Local.Y<1815.+Margin && Local.X>4380.-Margin && Local.X<6115.+Margin)
    {
        static const FVector2D CartLane[]={{5900.,500.},{5690.,530.},{5500.,630.},{5370.,810.},
                                           {5270.,1070.},{5250.,1310.},{5250.,1600.}};
        static const FVector2D HorseLane[]={{5140.,505.},{4930.,630.},{4770.,820.},{4650.,1080.},
                                            {4625.,1350.},{4625.,1600.}};
        const auto NearLane=[&](const auto& Points,double HalfWidth)
        {
            for(int32 I=1;I<UE_ARRAY_COUNT(Points);++I)
            {
                const FVector2D Nearest=FMath::ClosestPointOnSegment2D(Local,Points[I-1],Points[I]);
                if(FVector2D::DistSquared(Local,Nearest)<=FMath::Square(Margin+HalfWidth))return true;
            }
            return false;
        };
        if(NearLane(CartLane,200.)||NearLane(HorseLane,110.))return false;
    }
    // Both wall states occupy this same footprint. Keep crowns and roots inside
    // the repaired wall, clear of the ruined wall's rubble and repair corridor.
    if(FMath::Abs(Local.X)>Village.PadHalfX-800.-Margin||
       FMath::Abs(Local.Y)>Village.PadHalfY-800.-Margin)return false;
    for(const auto& Road:TemperateVillageLayout::Roads)
    {
        const FVector2D A(Road.X,Road.Y),D(Road.DX,Road.DY);
        const double T=FMath::Clamp(FVector2D::DotProduct(Local-A,D)/FMath::Max(1.,D.SizeSquared()),0.,1.);
        if(FVector2D::DistSquared(Local,A+D*T)<FMath::Square(Road.HalfWidth+Margin+80.))return false;
    }
    // These authored beds include house bounds, service yards and masonry.
    for(const auto& Bed:TemperateVillageLayout::Beds)
    {
        const FVector2D D=Local-FVector2D(Bed.X,Bed.Y);
        if(FMath::Abs(D.X*Bed.Cos+D.Y*Bed.Sin)<Bed.HalfX+Margin&&
           FMath::Abs(D.Y*Bed.Cos-D.X*Bed.Sin)<Bed.HalfY+Margin)return false;
    }
    const FVector2D Yard=Chapel.Local(World)/FTemperateChapelSite::AssemblyScale;
    for(const FVector2D Grave:{FVector2D(-570,907),FVector2D(-377,950),FVector2D(-199,886)})
        if(FMath::Abs(Yard.X-Grave.X)<80.+Radius/1.25&&FMath::Abs(Yard.Y-Grave.Y)<90.+Radius/1.25)return false;
    // Reserve each inward gate swing, including the full leaf radius.
    for(int32 Side:{-1,1})
    {
        const double GateX=Side*Village.WallHalfSize().X,GateY=Village.GateY(Side);
        if(FMath::Abs(Local.X-GateX)<550.+Radius&&FMath::Abs(Local.Y-GateY)<580.+Radius)return false;
    }
    if(Chapel.Clears(World.X,World.Y,Tall?FMath::Max(500.,Margin):Margin))return false;
    return !Tall||!Village.InLandmarkView(World.X,World.Y);
}

void GatherWallFoot(const ATemperateHillsWorld& Hills,int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out)
{
    using namespace TemperateHillsSurface;
    const auto& V=Hills.GetVillageSite();
    const auto& A=*Hills.Assets;
    const auto& E=Hills.EcologyProfile();
    const FVector2D Wall=V.WallHalfSize();
    // Each straight wall has occasional rubble fans and longer sheltered grass beds.
    // Leave the bevels and both gates open, including the ruined wall's approach.
    for(int32 Face=0;Face<4;++Face)
    {
        const bool End=Face<2;
        const double Sign=(Face%2==0)?-1.:1.;
        const double Limit=(End?Wall.Y:Wall.X)-650.;
        const int32 Bays=FMath::Max(1,FMath::FloorToInt(2.*Limit/960.));
        for(int32 Bay=0;Bay<Bays;++Bay)
        {
            const uint32 Patch=Key(Face,Bay,Hills.Seed,4657);
            const double Station=-Limit+(Bay+.20+.60*Unit(Patch+2))*2.*Limit/Bays;
            // Two pockets with a sightline between them on the walk back to the gate.
            const bool Thicket=Face==0&&Station>-.84*Limit&&Station<-.47*Limit;
            const bool Toe=Face==0&&Station>-.44*Limit&&Station<-.18*Limit;
            if(!Thicket&&!Toe&&Unit(Patch+1)<.18)continue;
            const double Reach=Thicket?740.:Toe?460.:310.+400.*Unit(Patch+3);
            const double Breadth=Thicket?660.:Toe?480.:90.+220.*Unit(Patch+4);
            auto LocalAt=[&](double Along,double Depth)
            {return End?FVector2D(Sign*(Wall.X+Depth),Along):FVector2D(Along,Sign*(Wall.Y+Depth));};
            const auto Mid=LocalAt(Station,220.+.5*Breadth);
            const auto Center=V.World(Mid.X,Mid.Y);
            if(!Bounds.ExpandBy(FVector(Reach+Breadth+250.,Reach+Breadth+250.,0.)).IsInsideOrOnXY(FVector(Center,0.)))continue;
            const bool Rubble=Toe||(!Thicket&&Unit(Patch+5)<.42);
            const bool Bloom=!Rubble&&Unit(Patch+6)<.46;
            const bool Shrub=Layer==4;
            if(Shrub&&!Thicket&&!Toe&&(Rubble||Unit(Patch+10)<.27))continue;
            const int32 Count=Shrub?(Thicket?10:Toe?4:3):FMath::Min(360,FMath::RoundToInt(Reach*Breadth/620.));
            const double Lean=Thicket||Toe?FVector2D::DotProduct(FVector2D(Hills.SurfaceNormal(Center.X,Center.Y)),FVector2D(-V.Axis.Y,V.Axis.X)):0.;
            for(int32 I=0;I<Count;++I)
            {
                const uint32 K=Mix(Patch^uint32(I+1)*0x9e3779b9U);
                const bool Young=Shrub&&Thicket&&I<2&&!A.ForestSaplings.IsEmpty();
                const double T=Young?(I==0?-.46:.48):Unit(K+1)*2.-1.;
                const double Along=Station+T*Reach*(Shrub?.68:1.)+FMath::Clamp(Lean*5.,-.8,.8)*Breadth*Unit(K+2);
                if(FMath::Abs(Along)>Limit||(End&&FMath::Abs(Along-V.GateY(Sign))<V.GateHalfGap(Sign)+(Shrub?300.:165.)))continue;
                const double Fringe=Young?.72:Unit(K+2);
                const double Depth=(Shrub?260.:Rubble?175.:86.)+Fringe*Breadth*(1.-T*T)+32.*FMath::Sin(3.*T+Unit(Patch)*PI)
                    +(Thicket?170.:Toe?110.:0.)*(1.-T*T);
                const auto Local=LocalAt(Along,Depth);
                const auto At=V.World(Local.X,Local.Y);
                if(At.X<Bounds.Min.X-180.||At.X>=Bounds.Max.X+180.||At.Y<Bounds.Min.Y-180.||At.Y>=Bounds.Max.Y+180.)continue;
                const bool Stone=!Shrub&&Rubble&&Unit(K+3)<.48*(1.-Fringe);
                const bool Flower=!Shrub&&Bloom&&Fringe>.48&&Unit(K+3)<.38;
                const bool Accent=!Shrub&&!Stone&&!Flower&&Unit(K+4)<.26;
                const double Density=Young?E.Saplings.Density:Shrub?E.Hazel.Density:Stone?A.GroundDebrisCoverage:Flower?E.MeadowFlowers.Density:Accent?E.GrassAccents.Density:E.Grass.Density;
                if(Unit(K+5)>=Density)continue;
                const auto& Palette=Shrub?A.Shrubs:Stone?A.Rocks:Flower?A.MeadowFlowers:Accent?A.GrassAccents:A.Grass;
                if(!Young&&Palette.IsEmpty())continue;
                const UObject* Object=nullptr;FSoftObjectPath Mesh;
                auto Use=[&](const auto& Ref){Object=Ref.Get();Mesh=Ref.ToSoftObjectPath();};
                if(Young)Use(A.ForestSaplings[(Patch+I)%A.ForestSaplings.Num()]);
                else Use(Palette[(Unit(K+6)<.76?Patch:K)%Palette.Num()]);
                const FBox Box=HillsVegetation::BoundsOf(Object);
                if(!Box.IsValid)continue;
                const FVector Size=Box.GetSize();
                const double ShrubHeight=Young?(I==0?330.:248.):Thicket?185.-92.*Fringe+38.*Unit(K+7):Toe?128.-52.*Fringe:
                    I==0?100.+35.*Unit(K+7):58.+30.*Unit(K+7);
                const double Scale=Shrub?ShrubHeight/FMath::Max(1.,Size.Z):
                    Stone?(16.+(Toe?73.:42.)*(1.-Fringe)*Unit(K+7))/FMath::Max(1.,FMath::Max(Size.X,Size.Y)):
                    FMath::Min(1.3,(19.+23.*Unit(K+7)+11.*(1.-Fringe))/FMath::Max(1.,Size.Z));
                if(Shrub&&FMath::Max(Size.X,Size.Y)*Scale>2.*(Depth-90.))continue;
                const FVector N=Hills.SurfaceNormal(At.X,At.Y);
                if(N.Z<.90)continue;
                const FVector Up=Stone?N:FMath::Lerp(FVector::UpVector,N,.35).GetSafeNormal();
                const FQuat Rot=FQuat(Up,2.*PI*Unit(K+8))*FQuat::FindBetweenNormals(FVector::UpVector,Up);
                const FVector Root=Shrub?FVector(0.,0.,Hills.IsForestVillage()?FMath::Max(0.,Box.Min.Z):Box.Min.Z):FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
                const FVector Offset=Rot.RotateVector(Root*Scale);
                if(Offset.SizeSquared2D()>180.*180.)continue;
                const double Ground=Shrub && Hills.IsForestVillage()
                    ? ForestRootFit::Seat(At,FMath::Clamp(ShrubHeight*(Young?.055:.085),8.,42.),0.,
                        [&Hills](double X,double Y){return Hills.Height(X,Y);})
                    : Hills.Height(At.X,At.Y)-(Stone?Size.Z*Scale*.28:1.5);
                const FVector Pivot=FVector(At,Ground)-Offset;
                if(Pivot.X<Bounds.Min.X||Pivot.X>=Bounds.Max.X||Pivot.Y<Bounds.Min.Y||Pivot.Y>=Bounds.Max.Y)continue;
                auto& P=Out.Emplace_GetRef();
                P.Mesh=Mesh;P.Key=K;P.Transform=FTransform(Rot,Pivot,FVector(Scale));
                P.CandidateId=0x6000000000000000ULL|(uint64(256+Face*64+Bay)<<24)|(uint64(Young?0:Shrub?1:2)<<16)|uint64(I);
                P.bVillagePlanting=true;
            }
        }
    }
}

void GatherApronDeposits(const ATemperateHillsWorld& Hills,const FBox& Bounds,TArray<FTemperatePlacement>& Out)
{
    using namespace TemperateHillsSurface;
    using namespace TemperateVillageApron;
    if(Hills.Seed!=TemperateHillsMap::Seed)return;
    const auto& V=Hills.GetVillageSite();
    const auto& Assets=*Hills.Assets;
    const auto& Ecology=Hills.EcologyProfile();
    const FBox NearBounds=Bounds.ExpandBy(FVector(120.,120.,0.));
    for(int32 Index=0;Index<UE_ARRAY_COUNT(Folds);++Index)
    {
        const FFold& Fold=Folds[Index];
        // Three small catches on each fan, separated by exposed ground. Grass
        // goes on their fringes; the coarsest fragments stay near the head.
        const FVector2D Fan=LocalPoint(Fold,.74*V.Shoulder,Fold.Station(.74),V.PadHalfX,V.PadHalfY);
        const FVector2D FanWorld=V.World(Fan.X,Fan.Y);
        if(!Bounds.ExpandBy(2200.).IsInsideOrOnXY(FVector(FanWorld,0.)))continue;
        for(int32 Pocket=0;Pocket<3;++Pocket)
        {
            const uint32 Parent=Key(Index,Pocket,Hills.Seed,6421);
            const double Station=.57+.12*Pocket+.05*Unit(Parent);
            const double Side=(Unit(Parent+1)-.5)*.85;
            const auto Center=LocalPoint(Fold,V.Shoulder*Station,Fold.Station(Station)+Fold.Width*Side,V.PadHalfX,V.PadHalfY);
            if(!Bounds.ExpandBy(820.).IsInsideOrOnXY(FVector(V.World(Center.X,Center.Y),0.)))continue;
            for(int32 Piece=0;Piece<17;++Piece)
            {
                const uint32 K=Mix(Parent^uint32(Piece+1)*0x9e3779b9U);
                const bool Plant=Piece>=11;
                const double Density=Plant?Ecology.Grass.Density:Assets.GroundDebrisCoverage;
                if(Density<=0. || (Piece!=0 && Unit(K+9)>=Density))continue;
                const double T=Station+(Unit(K+2)-.5)*.086;
                const double Offset=Fold.Width*Side+(Unit(K+3)-.5)*(Plant?380.:240.)
                    +(Plant?(Side<0.?-165.:165.):0.);
                const auto P=LocalPoint(Fold,V.Shoulder*T,Fold.Station(T)+Offset,V.PadHalfX,V.PadHalfY);
                const auto At=V.World(P.X,P.Y);
                if(!NearBounds.IsInsideOrOnXY(FVector(At,0.)))continue;
                if(Sample(P,V.PadHalfX,V.PadHalfY,V.Shoulder).Gravel<.15)continue;
                const auto& Family=Plant?Assets.Grass:Assets.Rocks;
                if(Family.IsEmpty())continue;
                const auto& Ref=Family[(Unit(K+4)<.65?Parent:K)%Family.Num()];
                const FBox Box=HillsVegetation::BoundsOf(Ref.Get());
                if(!Box.IsValid)continue;
                const FVector Size=Box.GetSize(), Normal=Hills.SurfaceNormal(At.X,At.Y);
                const double Span=Piece==0?56.-12.*Pocket:10.+19.*Unit(K+5);
                const double Scale=Plant?FMath::Min(1.3,(18.+12.*Unit(K+6))/FMath::Max(1.,Size.Z)):
                    Span/FMath::Max(1.,FMath::Max(Size.X,Size.Y));
                const FVector Up=Plant?FMath::Lerp(FVector::UpVector,Normal,.38).GetSafeNormal():Normal;
                const double Heading=FMath::Atan2(Normal.Y,Normal.X)+(Size.Y>Size.X?.5*PI:0.)+(Unit(K+7)-.5)*1.8;
                const FQuat Rotation=FQuat(Up,Heading)*FQuat::FindBetweenNormals(FVector::UpVector,Up);
                const FVector Foot=Rotation.RotateVector(FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z)*Scale);
                if(Foot.SizeSquared2D()>120.*120.)continue;
                const FVector Pivot=FVector(At,Hills.Height(At.X,At.Y)-(Plant?1.5:Size.Z*Scale*.32))-Foot;
                if(Pivot.X<Bounds.Min.X||Pivot.X>=Bounds.Max.X||Pivot.Y<Bounds.Min.Y||Pivot.Y>=Bounds.Max.Y)continue;
                auto& PileItem=Out.Emplace_GetRef();
                PileItem.Transform=FTransform(Rotation,Pivot,FVector(Scale));
                PileItem.Mesh=Ref.ToSoftObjectPath();PileItem.Key=K;
                PileItem.CandidateId=0x6100000000000000ULL|(uint64(Index)<<16)|(uint64(Pocket)<<8)|uint64(Piece);
            }
        }
    }
}
}

bool Near(const ATemperateHillsWorld& Hills,const FBox& Bounds)
{
    const auto& Village=Hills.GetVillageSite();
    if(!Village.bPlaced||!Village.bHilltop)return false;
    const FVector2D Extent=Village.Extent();
    return Bounds.Min.X<Village.Ground.X+Extent.X&&Bounds.Max.X>Village.Ground.X-Extent.X&&
           Bounds.Min.Y<Village.Ground.Y+Extent.Y&&Bounds.Max.Y>Village.Ground.Y-Extent.Y;
}

void Gather(const ATemperateHillsWorld& Hills,int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out)
{
    if((Layer!=3&&Layer!=4)||!Hills.Assets||!Near(Hills,Bounds))return;
    using namespace TemperateHillsSurface;
    const auto& Assets=*Hills.Assets;
    const auto& Village=Hills.GetVillageSite();const auto Chapel=Village.ChapelLot();
    const auto& Ecology=Hills.EcologyProfile();
    const double VillageYaw=FMath::Atan2(Village.Axis.Y,Village.Axis.X);
    GatherWallFoot(Hills,Layer,Bounds,Out);
    if(Layer==3)GatherApronDeposits(Hills,Bounds,Out);
    for(int32 PatchIndex=0;PatchIndex<UE_ARRAY_COUNT(Patches);++PatchIndex)
    {
        const FPatch& Patch=Patches[PatchIndex];
        const FVector2D PatchWorld=Village.World(Patch.X,Patch.Y);
        const double Reach=FMath::Max(Patch.RX,Patch.RY)+650.;
        if(PatchWorld.X+Reach<Bounds.Min.X||PatchWorld.X-Reach>=Bounds.Max.X||
           PatchWorld.Y+Reach<Bounds.Min.Y||PatchWorld.Y-Reach>=Bounds.Max.Y)continue;
        const uint32 Colony=Mix(uint32(Hills.Seed)^uint32(PatchIndex+1)*0x9e3779b9U^0x416e29b3U);
        // Pass 0: uneven young-tree group; 1: shrub pockets; 2: broken grass fringe.
        for(int32 Pass=Layer==4?0:2;Pass<=(Layer==4?1:2);++Pass)
        {
            const double Density=Pass==0?Ecology.Saplings.Density:Pass==1?Ecology.Hazel.Density:Ecology.Grass.Density;
            if(Density<=0)continue;
            const bool Yard=Patch.Yard;
            const int32 GrassSamples=Patch.GrassSamples>0?Patch.GrassSamples:(Yard?620:680);
            const int32 ShrubSamples=Patch.GrassSamples>0?FMath::Max(3,GrassSamples/24):(Yard?26:16);
            const int32 Count=Pass==0?Patch.Trees:Pass==1?ShrubSamples:GrassSamples;
            for(int32 I=0;I<Count;++I)
            {
                const uint32 K=Mix(Colony^uint32(Pass+1)*0x85ebca6bU^uint32(I+1)*0xc2b2ae35U);
                if(Unit(K+37)>FMath::Min(1.,Density))continue;
                const double Angle=Unit(K+3)*2.*PI;
                const double Distance=FMath::Sqrt(Unit(K+7))*(Pass==0?.60:1.);
                const double Edge=1.+.19*FMath::Sin(Angle*3.+Unit(Colony)*6.28)+.13*FMath::Cos(Angle*7.);
                // Thin the outside gradually and leave small bare breaks in each patch.
                if(Pass>0&&Unit(K+11)>.95-.50*FMath::SmoothStep(.45,1.,Distance))continue;
                const FVector2D Offset=FVector2D(FMath::Cos(Angle)*Patch.RX*Distance*Edge,
                    FMath::Sin(Angle)*Patch.RY*Distance*Edge).GetRotated(Patch.Yaw);
                const FVector2D Local=FVector2D(Patch.X,Patch.Y)+Offset;
                const FVector2D At=Village.World(Local.X,Local.Y);
                if(At.X<Bounds.Min.X||At.X>=Bounds.Max.X||At.Y<Bounds.Min.Y||At.Y>=Bounds.Max.Y)continue;
                FSoftObjectPath Path;const UObject* Object=nullptr;
                if(Pass<2)
                {
                    if(Pass==0&&I%3!=0)
                    {
                        const auto& Palette=Assets.ForestSaplings;if(Palette.IsEmpty())continue;
                        const auto& Ref=Palette[(Colony+uint32(I%3))%Palette.Num()];Object=Ref.Get();Path=Ref.ToSoftObjectPath();
                    }
                    else
                    {
                        // The approved hazel palette is static; ForestShrubs is an optional skeletal slot.
                        const auto& Palette=Assets.Shrubs;if(Palette.IsEmpty())continue;
                        const auto& Ref=Palette[(Colony+uint32(I%3))%Palette.Num()];Object=Ref.Get();Path=Ref.ToSoftObjectPath();
                    }
                }
                else
                {
                    const auto& Palette=!Assets.GrassAccents.IsEmpty()&&Unit(K+17)<.22?Assets.GrassAccents:Assets.Grass;
                    if(Palette.IsEmpty())continue;
                    const auto& Ref=Palette[K%Palette.Num()];Object=Ref.Get();Path=Ref.ToSoftObjectPath();
                }
                const FBox Box=HillsVegetation::BoundsOf(Object);if(!Box.IsValid)continue;
                const double TargetHeight=Pass==0?(I%3==0?280.+Unit(K+19)*100.:320.+Unit(K+19)*(MaxSaplingHeight-320.)):
                    Pass==1?(Yard?65.+Unit(K+19)*45.:85.+Unit(K+19)*85.):(Yard?28.+Unit(K+19)*24.:18.+Unit(K+19)*26.);
                // Preserve the existing grass catalogue's 1.3 maximum scale contract.
                const double Scale=FMath::Min(TargetHeight/FMath::Max(1.,Box.GetSize().Z),Pass==2?1.3:DBL_MAX);
                const FVector Normal=Hills.SurfaceNormal(At.X,At.Y);
                if(Normal.Z<.94)continue;
                const FVector Up=FMath::Lerp(FVector::UpVector,Normal,Pass==2?.65:.10).GetSafeNormal();
                const FQuat Rotation=FQuat(Up,VillageYaw+Unit(K+23)*2.*PI)*FQuat::FindBetweenNormals(FVector::UpVector,Up);
                const FVector Root=Pass==2?FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z):FVector(0,0,Hills.IsForestVillage()?FMath::Max(0.,Box.Min.Z):Box.Min.Z);
                const FVector RootOffset=Rotation.RotateVector(Root*Scale);
                const FVector2D RootAt=At+FVector2D(RootOffset);
                // Imported plants can have an off-centre pivot and a one-sided
                // crown. Reserve their actual rooted footprint, not half their width.
                const FBox Crown=Box.TransformBy(FTransform(Rotation,-RootOffset,FVector(Scale)));
                const FVector ReachFromRoot=Crown.Min.GetAbs().ComponentMax(Crown.Max.GetAbs());
                const double Radius=FMath::Max(ReachFromRoot.X,ReachFromRoot.Y);
                if(!Clear(Village,Chapel,Village.Local(RootAt.X,RootAt.Y),RootAt,Radius,Pass==0))continue;
                const double Height=Pass<2 && Hills.IsForestVillage()
                    ? ForestRootFit::Seat(RootAt,FMath::Clamp(TargetHeight*(Pass==0?.055:.085),8.,42.),0.,
                        [&Hills](double X,double Y){return Hills.Height(X,Y);})
                    : Hills.Height(RootAt.X,RootAt.Y)-2.;
                FTemperatePlacement& Plant=Out.Emplace_GetRef();
                Plant.Transform=FTransform(Rotation,FVector(At,Height-RootOffset.Z),FVector(Scale));
                Plant.Mesh=Path;Plant.Key=K;
                Plant.CandidateId=0x6000000000000000ULL|(uint64(PatchIndex)<<24)|(uint64(Pass)<<16)|uint64(I);
                Plant.bVillagePlanting=true;
            }
        }
    }
}
}
