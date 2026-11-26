#include "TemperateHillsWorld.h"
#include "TemperateForestHabitat.h"
#include "TemperateHillsLandform.h"
#include "TemperateVegetationPlacement.h"
#include "TemperateWestVerge.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"

namespace
{
enum class EUplandPatch { Meadow, StonyShoulder, DampSwale };

// A shared ground anchor for road grass, embedded rock and fallen branches.
// Own by the final mesh pivot so neighbouring PCG cells can enumerate a whole pocket.
void AddVergeItem(const ATemperateHillsWorld& Hills,const FBox& Bounds,TArray<FTemperatePlacement>& Out,
    const TSoftObjectPtr<UStaticMesh>& Ref,FVector2D XY,double Span,bool Flat,double Burial,double Heading,
    uint32 Key,uint64 Id,bool AlignLongAxis=false)
{
    const FBox Box=HillsVegetation::BoundsOf(Ref.Get());
    if(!Box.IsValid)return;
    const FVector N=Hills.SurfaceNormal(XY.X,XY.Y),Size=Box.GetSize();
    if(N.Z<.92)return;
    const double Scale=Flat?Span/FMath::Max(1.,FMath::Max(Size.X,Size.Y)):FMath::Min(1.3,Span/FMath::Max(1.,Size.Z));
    const FVector Up=Flat?N:FMath::Lerp(FVector::UpVector,N,.35).GetSafeNormal();
    const FQuat Rot=FQuat(Up,Heading+(AlignLongAxis&&Flat&&Size.Y>Size.X?.5*PI:0.))*FQuat::FindBetweenNormals(FVector::UpVector,Up);
    const FVector Base=Rot.RotateVector(FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z)*Scale);
    if(Base.SizeSquared2D()>150.*150.)return;
    const FVector Pivot=FVector(XY,Hills.Height(XY.X,XY.Y)-(Flat?Burial*Size.Z*Scale:1.5))-Base;
    if(Pivot.X<Bounds.Min.X||Pivot.X>=Bounds.Max.X||Pivot.Y<Bounds.Min.Y||Pivot.Y>=Bounds.Max.Y)return;
    auto& P=Out.Emplace_GetRef();
    P.Transform=FTransform(Rot,Pivot,FVector(Scale));P.Key=Key;P.Mesh=Ref.ToSoftObjectPath();P.CandidateId=Id;
}

}

void TemperateWestVerge::Gather(const ATemperateHillsWorld& Hills,const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool Woody)
{
    using namespace TemperateHillsSurface;
    const auto& V=Hills.GetVillageSite();
    if(!V.bPlaced||!V.bHilltop||V.FeederLength<3800.)return;
    const auto Junction=V.Approach(-1.,V.FeederLength,Hills.Seed);
    if(!Bounds.ExpandBy(11500.).IsInsideOrOnXY(FVector(Junction,0.)))return;
    const auto& A=*Hills.Assets;
    const auto& E=Hills.EcologyProfile();
    const auto Incoming=V.Approach(-1.,V.FeederLength+4200.,Hills.Seed);
    const double Away=V.Ground.Y<Junction.Y?1.:-1.;
    const FVector2D Side(-V.Axis.Y,V.Axis.X);
    const auto OnDryLand=[&](FVector2D P)
    {
        if(FMath::Abs(P.Y-ValleyY(P.X,Hills.Seed))<560.||V.Clears(P.X,P.Y,230.)||
            FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y))>=Hills.SizeMeters*50.-500.)return false;
        const auto B=Hills.SampleRiver(P.X,P.Y);
        if(B.Wet>.01||B.CliffWeight>.01||Hills.SampleForestWater(P.X,P.Y).Wet)return false;
        return B.Bank<.025||Hills.Height(P.X,P.Y)>B.WaterZ+70.;
    };
    // Two separated rock outcrops turn the eye into the lane. The opposite
    // bank carries a narrower trail of wood and grass at the true forest margin.
    for(int32 Group=0;Group<4;++Group)
    {
        const bool Forest=Group>=2;
        FVector2D Root=Junction+V.Axis*(Group==0?1150.:2950.)+Side*(Group==0?870.:-790.);
        if(Forest)
        {
            const double X=Incoming.X+(Group==2?-760.:1160.);
            Root=FVector2D(X,ValleyY(X,Hills.Seed));
            int32 Steps=0;
            for(;Steps<36&&Hills.RainforestWeight(Root.X,Root.Y)<(Group==2?.40:.65);++Steps)Root.Y+=Away*180.;
            if(Steps==36)continue;
        }
        if(!Bounds.ExpandBy(3100.).IsInsideOrOnXY(FVector(Root,0.)))continue;
        // On this seed the forest entrance meets a small stream. Search its
        // dry lip rather than losing a whole group when the nominal root is wet.
        const FVector2D Outward=Forest?FVector2D(0.,Away):Side*(Group==0?1.:-1.);
        const FVector2D Tangent(-Outward.Y,Outward.X),Nominal=Root;
        bool Found=false;
        for(int32 I=0;I<16;++I)
        {
            Root=Nominal+Outward*(I/3*295.)+Tangent*((I%3==1?1:I%3==2?-1:0)*440.);
            if(OnDryLand(Root)&&Hills.SurfaceNormal(Root.X,Root.Y).Z>.93){Found=true;break;}
        }
        if(!Found||!Bounds.ExpandBy(1150.).IsInsideOrOnXY(FVector(Root,0.)))continue;
        const FVector2D Slope(Hills.SurfaceNormal(Root.X,Root.Y));
        const FVector2D Down=Slope.SizeSquared()>.0009?Slope.GetSafeNormal():Forest?FVector2D(0.,-Away):Side;
        const FVector2D Across(-Down.Y,Down.X);
        const uint32 GroupKey=Key(Group,0,Hills.Seed,4759);
        if(Woody)
        {
            // The dominant stem and smaller followers stand above the mother
            // stone, with the open side facing the trail.
            for(int32 I=0;I<(Forest?5:3);++I)
            {
                const auto& Palette=A.ForestSaplings;
                const uint32 K=Mix(GroupKey^uint32(I+59)*0x9e3779b9U);
                if(Palette.IsEmpty()||Unit(K+5)>=E.Saplings.Density)continue;
                const FVector2D P=Root-Down*(145.+I*63.)+Across*((I%2?-1.:1.)*(65.+120.*I));
                if(!OnDryLand(P)||V.InLandmarkView(P.X,P.Y))continue;
                const auto& Ref=Palette[(GroupKey+uint32(I%3))%Palette.Num()];
                const FBox Box=HillsVegetation::BoundsOf(Ref.Get());if(!Box.IsValid)continue;
                const double Height=I==0?270.:FMath::Lerp(208.,105.,I/4.)+22.*Unit(K);
                const double Scale=Height/FMath::Max(1.,Box.GetSize().Z);
                const FQuat Rot(FVector::UpVector,Unit(K+3)*2.*PI);
                const FVector At(P,Hills.Height(P.X,P.Y)-Box.Min.Z*Scale-2.);
                if(At.X<Bounds.Min.X||At.X>=Bounds.Max.X||At.Y<Bounds.Min.Y||At.Y>=Bounds.Max.Y)continue;
                auto& Plant=Out.Emplace_GetRef();Plant.Mesh=Ref.ToSoftObjectPath();Plant.Key=K;
                Plant.Transform=FTransform(Rot,At,FVector(Scale));
                Plant.CandidateId=0x7200000000000000ULL|(uint64(Group)<<16)|uint64(I+128);
            }
            continue;
        }
        for(int32 I=0;I<50;++I)
        {
            const uint32 K=Mix(GroupKey^uint32(I+1)*0x9e3779b9U);
            const bool Main=I==0;
            const bool Stone=Main||I<(Forest?5:15);
            const bool Twig=Forest&&I>=5&&I<10;
            const double Travel=Main?0.:I==1?.18:.14+.86*Unit(K+1);
            const double Spread=Main?0.:(2.*Unit(K+2)-1.)*(60.+195.*Travel);
            // The stone catches sticks on its uphill side; chips run out below.
            const auto P=Twig?Root-Down*(65.+Travel*140.)+Across*(Spread*.72):
                Root+Down*(Travel*(Forest?600.:770.))+Across*(Spread+95.*Travel*Travel);
            if(!Bounds.ExpandBy(150.).IsInsideOrOnXY(FVector(P,0.))||!OnDryLand(P))continue;
            const double Region=Hills.RainforestWeight(P.X,P.Y);
            const bool Green=Forest&&Unit(K+3)<Region;
            const bool Flower=!Stone&&!Twig&&!Green&&Spread>40.&&Unit(K+4)<.38;
            const auto& Family=Stone?A.Rocks:Twig?A.RainforestTwigs:Flower?A.MeadowFlowers:Green?A.RainforestCarpetGrass:A.GrassAccents;
            const double Density=Stone||Twig?A.GroundDebrisCoverage:Flower?E.MeadowFlowers.Density:Green?E.Grass.Density:E.GrassAccents.Density;
            if(Family.IsEmpty()||Density<=0.||(!Main&&Unit(K+5)>=Density))continue;
            const double Span=Main?(Forest?122.:215.):Stone?FMath::Lerp(83.,16.,Travel):
                Twig?FMath::Lerp(115.,43.,Travel):24.+18.*Unit(K+6);
            const double Yaw=FMath::Atan2(Down.Y,Down.X)+(Main||Twig?.5*PI:0.)+(Unit(K+7)-.5)*(Stone||Twig?.8:2.*PI);
            const auto& Ref=Family[(Unit(K+8)<.76?GroupKey:K)%Family.Num()];
            AddVergeItem(Hills,Bounds,Out,Ref,P,Span,Stone||Twig,Stone?.30:.08,Yaw,K,
                0x7200000000000000ULL|(uint64(Group)<<16)|uint64(I),true);
        }
    }
}

namespace
{
// Two field margins and the apron outside the west wall. Build each feature
// around one supported object; leave the opposite shoulder open for the gate view.
void GatherWestFieldMargins(const ATemperateHillsWorld& Hills,const FBox& Bounds,TArray<FTemperatePlacement>& Out,
    TFunctionRef<bool(const FVector2D&)> OnDryLand)
{
    using namespace TemperateHillsSurface;
    const auto& V=Hills.GetVillageSite();
    if(!V.bPlaced||!V.bHilltop||V.FeederLength<8500.)return;
    const auto& A=*Hills.Assets;
    const FVector2D Side(-V.Axis.Y,V.Axis.X);
    const FVector2D Origins[]={
        V.Approach(-1.,V.FeederLength*.64,Hills.Seed)+Side*1010.,
        V.Approach(-1.,V.FeederLength*.38,Hills.Seed)-Side*880.,
        V.World(-V.WallHalfSize().X-1050.,-2840.)};
    for(int32 Group=0;Group<UE_ARRAY_COUNT(Origins);++Group)
    {
        const FVector2D Root=Origins[Group];
        if(!Bounds.ExpandBy(1500.).IsInsideOrOnXY(FVector(Root,0.))||!OnDryLand(Root))continue;
        const FVector N=Hills.SurfaceNormal(Root.X,Root.Y);
        if(N.Z<.92)continue;
        FVector2D Across(-N.Y,N.X);
        if(!Across.Normalize(.0004))Across=Group==2?Side:V.Axis;
        if(FVector2D::DotProduct(Across,V.Axis)<0.)Across*=-1.;
        const FVector2D Down=N.SizeSquared2D()>.0004?FVector2D(N).GetSafeNormal():Side;
        const uint32 Colony=Key(Group,0,Hills.Seed,4867);
        for(int32 I=0;I<27;++I)
        {
            const uint32 K=Mix(Colony^uint32(I+1)*0x9e3779b9U);
            const bool Timber=I==0&&Group==1;
            const bool Stone=!Timber&&I<(Group==1?5:10);
            const bool Stick=!Stone&&!Timber&&I<13;
            const double T=I==0?0.:(I%2?-1.:1.)*(.12+.88*Unit(K+1));
            // The field-clearance stones taper along the contour. Twigs catch
            // on the high side; grass and flowers colonise the lee of the spine.
            const double Along=T*(Group==0?830.:Group==1?530.:425.);
            const double Offset=I==0?0.:Stone?25.+85.*Unit(K+2):Stick?-50.-50.*Unit(K+2):80.+145.*Unit(K+2);
            const FVector2D P=Root+Across*Along+Down*(Offset+58.*T*T);
            if(!Bounds.ExpandBy(150.).IsInsideOrOnXY(FVector(P,0.))||!OnDryLand(P))continue;
            const bool Flower=!Stone&&!Timber&&!Stick&&I%3==1;
            const auto& Family=Timber?A.FallenLogs:Stone?A.Rocks:Stick?A.RainforestTwigs:Flower?A.MeadowFlowers:A.GrassAccents;
            const double Density=Timber?A.ForestFloorCoverage:Stone||Stick?A.GroundDebrisCoverage:
                Flower?Hills.EcologyProfile().MeadowFlowers.Density:Hills.EcologyProfile().GrassAccents.Density;
            if(Family.IsEmpty()||Density<=0.||(I>0&&Unit(K+3)>=Density))continue;
            const auto& Ref=Family[(I%4==0?K:Colony)%Family.Num()];
            const double Span=Timber?275.:I==0?(Group==2?158.:200.):Stone?112.-65.*FMath::Abs(T):
                Stick?60.+50.*Unit(K+4):26.+15.*Unit(K+4);
            const double Heading=FMath::Atan2(Across.Y,Across.X)+.48*(Unit(K+5)-.5);
            if(Timber)
            {
                const FVector2D Axis(FMath::Cos(Heading),FMath::Sin(Heading));
                const double Z=Hills.Height(P.X,P.Y);
                bool Supported=true;
                for(double Sign:{-1.,1.})
                {
                    const auto End=P+Axis*(Sign*Span*.43);
                    const double PlaneZ=Z-FVector2D::DotProduct(FVector2D(N),End-P)/N.Z;
                    if(!OnDryLand(End)||FMath::Abs(Hills.Height(End.X,End.Y)-PlaneZ)>18.)Supported=false;
                }
                if(!Supported)continue;
            }
            AddVergeItem(Hills,Bounds,Out,Ref,P,Span,Stone||Timber||Stick,Stone?.36:.12,Heading,K,
                0x7300000000000000ULL|(uint64(Group)<<16)|uint64(I),true);
        }
    }
}

void GatherRoadShoulders(const ATemperateHillsWorld& Hills,const FBox& Bounds,TArray<FTemperatePlacement>& Out,
    TFunctionRef<bool(const FVector2D&)> OnDryLand)
{
    using namespace TemperateHillsSurface;
    const auto& V=Hills.GetVillageSite();
    if(!V.bPlaced||!V.bHilltop)return;
    const auto& A=*Hills.Assets;
    const auto& Ecology=Hills.EcologyProfile();
    const FVector2D Center=V.Local(Bounds.GetCenter().X,Bounds.GetCenter().Y);
    const FVector Extent=Bounds.GetExtent();
    const double RX=FMath::Abs(V.Axis.X)*Extent.X+FMath::Abs(V.Axis.Y)*Extent.Y+700.;
    const double RY=FMath::Abs(V.Axis.Y)*Extent.X+FMath::Abs(V.Axis.X)*Extent.Y+700.;
    for(int32 Side:{-1,1})
    {
        const double First=V.PadHalfX+160.,Last=TemperateVillageLayout::HalfX+V.ApproachLength(Side)-400.;
        if(Last<=First||FMath::Abs(Center.Y-V.GateY(Side))>RY+650.)continue;
        constexpr double Spacing=1100.;
        const int32 Begin=FMath::Max(0,FMath::FloorToInt((Side*Center.X-RX-First)/Spacing));
        const int32 End=FMath::Min(FMath::FloorToInt((Last-First)/Spacing),FMath::FloorToInt((Side*Center.X+RX-First)/Spacing));
        for(int32 Bay=Begin;Bay<=End;++Bay)
        {
            const uint32 Colony=Key(Side,Bay,Hills.Seed,4673);
            const double Station=First+(Bay+.2+.6*Unit(Colony+1))*Spacing;
            const double ShoulderSide=Unit(Colony+2)<.5?-1.:1.;
            const bool Stony=Unit(Colony+3)<.38;
            for(int32 I=0;I<36;++I)
            {
                const uint32 K=Mix(Colony^uint32(I+1)*0x9e3779b9U);
                const double T=2.*Unit(K+1)-1.,Edge=Unit(K+2);
                const double Along=Station+T*(260.+210.*Unit(Colony+4));
                if(Along<First||Along>Last)continue;
                const double Across=350.+80.*T+Edge*(220.-120.*T*T);
                const auto XY=V.World(Side*Along,V.GateY(Side)+ShoulderSide*Across);
                if(XY.X<Bounds.Min.X-150.||XY.X>=Bounds.Max.X+150.||XY.Y<Bounds.Min.Y-150.||XY.Y>=Bounds.Max.Y+150.)continue;
                if(!OnDryLand(XY))continue;
                const bool Stone=Stony&&Edge<.60&&Unit(K+3)<.70;
                if(Unit(K+4)>=(Stone?A.GroundDebrisCoverage:Ecology.GrassAccents.Density))continue;
                const auto& Family=Stone?A.Rocks:A.GrassAccents;
                if(Family.IsEmpty())continue;
                const auto& Ref=Family[(Unit(K+5)<.8?Colony:K)%Family.Num()];
                AddVergeItem(Hills,Bounds,Out,Ref,XY,Stone?10.+20.*Unit(K+6):19.+16.*Edge+10.*Unit(K+6),
                    Stone,.32,2.*PI*Unit(K+7),K,0x7100000000000000ULL|(uint64(Side>0)<<32)|(uint64(Bay)<<8)|uint64(I));
            }
        }
    }
}
}

void ATemperateHillsWorld::GetUplandGroundPatches(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets||!RiverPlan||!RiverPlan->bVillageRainforest)return;
    using namespace TemperateHillsSurface;
    const auto& Ecology=EcologyProfile();
    const double Half=SizeMeters*50.-500.;
    const bool HasRunoff=TemperateHillsLandform::HasSurveyedRunoff(Seed,RiverPlan->GenerationVersion,RiverPlan->WorldHalf);
    constexpr double Sector=2400.;
    const FBox CenterBounds=Bounds.ExpandBy(1400.);
    const auto OnDryLand=[&](const FVector2D& P)
    {
        if(FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y))>=Half||PathDistance(P.X,P.Y)<480.||
            VillageSite.Clears(P.X,P.Y,170.)||ChapelSite.Clears(P.X,P.Y,170.))return false;
        const auto Bank=RiverPlan->Sample(P.X,P.Y);
        return Bank.Bank<=.015&&Bank.CliffWeight<=0.&&
            (!RiverPlan->Lake.Valid||RiverPlan->Lake.Edge(P.X,P.Y)>TemperateRiver::FPlan::FLake::MaxBankExtent)&&
            !SampleForestWater(P.X,P.Y).Wet;
    };

    GatherRoadShoulders(*this,Bounds,Out,OnDryLand);
    GatherWestFieldMargins(*this,Bounds,Out,OnDryLand);
    TemperateWestVerge::Gather(*this,Bounds,Out,false);
    // Enumerate nearby patch centres. Half-open final pivot bounds give each
    // instance one owner even when an elongated drift spans two streaming cells.
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/Sector)-1;Y<=FMath::FloorToInt(Bounds.Max.Y/Sector)+1;++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/Sector)-1;X<=FMath::FloorToInt(Bounds.Max.X/Sector)+1;++X)
    {
        const uint32 PatchKey=Key(X,Y,Seed,4813);
        const FVector2D Center((X+.12+.76*Unit(PatchKey+1))*Sector,(Y+.12+.76*Unit(PatchKey+2))*Sector);
        if(!CenterBounds.IsInsideOrOnXY(FVector(Center,0.))||!OnDryLand(Center))continue;
        const double Region=RainforestWeight(Center.X,Center.Y);
        const auto Site=TemperateHillsLandform::SlopeSite(RiverPlan->UplandOffset(Center.X,Center.Y));
        const auto Runoff=HasRunoff?TemperateHillsLandform::SurveyedRunoff(Center.X,Center.Y):TemperateHillsLandform::FRunoff{};
        const double Forest=ForestWeight(Center.X,Center.Y);
        const double Light=1.-FMath::SmoothStep(.12,.75,Forest);
        const double Shoulder=FMath::Max3(Site.Shoulder*(.42+.58*Light),.78*Runoff.Shoulder,.94*Runoff.Apron)*Ecology.UplandStoneStrength;
        const double Swale=FMath::Max(Site.Swale,Runoff.Hollow)*Region;
        const double Meadow=(1.-Region)*Light*Ecology.UplandMeadowStrength*
            (.36+.64*TemperateForestHabitat::UnderstoryPatch(Center.X,Center.Y,Seed,Ecology));
        const double Suitability=FMath::Max3(Shoulder,Swale,Meadow);
        if(Unit(PatchKey+3)>=.82*Suitability)continue;
        const EUplandPatch Patch=Suitability==Shoulder?EUplandPatch::StonyShoulder:
            Suitability==Swale?EUplandPatch::DampSwale:EUplandPatch::Meadow;

        const FVector Normal=SurfaceNormal(Center.X,Center.Y);
        if(Normal.Z<.85)continue;
        FVector2D Along(-Normal.Y,Normal.X);
        const bool InRun=!Runoff.Downstream.IsNearlyZero();
        if(InRun)
            Along=Runoff.Downstream;
        else if(HasRunoff&&Patch==EUplandPatch::DampSwale&&Normal.SizeSquared2D()>.0025)
            Along=FVector2D(Normal).GetSafeNormal();
        else if(Along.SizeSquared()>.0025)
            Along=Along.GetSafeNormal().GetRotated((Unit(PatchKey+4)-.5)*32.);
        else
            Along=FVector2D(1.,0.).GetRotated(Unit(PatchKey+4)*360.);
        const FVector2D Across(-Along.Y,Along.X);
        const double Length=380.+450.*Unit(PatchKey+5);
        const double Width=(110.+145.*Unit(PatchKey+6))*(1.-.24*Runoff.Hollow);
        const int32 Count=11+int32(7.*Unit(PatchKey+7));
        for(int32 I=0;I<Count;++I)
        {
            const uint32 K=Mix(PatchKey^uint32(I+1)*0x9e3779b9U);
            const double T=2.*Unit(K+1)-1.;
            // Material fans out towards the low end. The higher neck has
            // fewer, coarser fragments while the outside edge traps grass.
            const double Side=(2.*Unit(K+2)-1.)*FMath::Sqrt(1.-T*T)*(1.+.40*T*Runoff.Apron);
            const FVector2D P=Center+Along*(Length*T)+Across*(Width*(Side+.46*T*T));
            const double LocalRegion=RainforestWeight(P.X,P.Y);
            if(!OnDryLand(P)||(Patch==EUplandPatch::DampSwale&&LocalRegion<.50)||
                (Patch==EUplandPatch::Meadow&&LocalRegion>.55))continue;

            // A patch has one dominant species with occasional companions.
            // Exposed stones gather along its spine; the narrow ends stay sparse.
            const double Roll=Unit(K+3);
            const bool Stone=Patch==EUplandPatch::StonyShoulder&&Roll<.76-.26*FMath::Abs(T)-.20*Runoff.Apron*FMath::Abs(Side);
            const bool Flower=Patch==EUplandPatch::Meadow&&Roll<.62;
            const bool Herb=Patch==EUplandPatch::DampSwale&&Roll<.56;
            const bool Green=Unit(K+9)<LocalRegion;
            const auto& Palette=Stone?Assets->Rocks:Flower?Assets->MeadowFlowers:Herb?Assets->RainforestHerbs:
                Green?Assets->RainforestCarpetGrass:Assets->GrassAccents;
            if(Palette.IsEmpty())continue;
            const auto& Rule=Flower?Ecology.MeadowFlowers:((Green||Herb)?Ecology.Grass:Ecology.GrassAccents);
            const FVector N=SurfaceNormal(P.X,P.Y);
            const double Density=Stone?Assets->GroundDebrisCoverage:Rule.Density*Rule.SlopeWeight(N.Z);
            if(N.Z<.84||Unit(K+10)>=Density)continue;
            const uint32 FormKey=Unit(K+11)<.78?PatchKey:K;
            const auto& Ref=Palette[FormKey%Palette.Num()];
            const UStaticMesh* Mesh=Ref.Get();
            if(!Mesh)continue;
            const FBox Box=HillsVegetation::BoundsOf(Mesh);
            if(!Box.IsValid)continue;
            const FVector Size=Box.GetSize();
            const double Span=Stone?(14.+44.*Unit(K+4))*(1.-.53*Runoff.Apron*T):
                Flower?22.+21.*Unit(K+4):Herb?27.+27.*Unit(K+4):18.+18.*Unit(K+4);
            const double Scale=Stone?Span/FMath::Max(1.,FMath::Max(Size.X,Size.Y)):
                FMath::Min(1.25,Span/FMath::Max(1.,Size.Z));
            const FVector Up=Stone?N:FMath::Lerp(FVector::UpVector,N,.33).GetSafeNormal();
            const double Heading=InRun&&Stone?FMath::Atan2(Along.Y,Along.X)+(Size.Y>Size.X?.5*PI:0.)
                +(Unit(K+5)-.5)*1.3:2.*PI*Unit(K+5);
            const FQuat Rot=FQuat(Up,Heading)*FQuat::FindBetweenNormals(FVector::UpVector,Up);
            const FVector Base=Rot.RotateVector(FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z)*Scale);
            if(Base.SizeSquared2D()>FMath::Square(300.))continue;
            const double Sink=Stone?Size.Z*Scale*.25:1.5;
            const FVector At=FVector(P,Height(P.X,P.Y))-Base-FVector::UpVector*Sink;
            if(At.X<Bounds.Min.X||At.X>=Bounds.Max.X||At.Y<Bounds.Min.Y||At.Y>=Bounds.Max.Y)continue;
            auto& Item=Out.Emplace_GetRef();
            Item.Mesh=Ref.ToSoftObjectPath();Item.Key=K;Item.Transform=FTransform(Rot,At,FVector(Scale));
            Item.CandidateId=0x7000000000000000ULL|(uint64(uint32(X)&0xffffffU)<<32)|
                (uint64(uint32(Y)&0xffffffU)<<8)|uint64(I);
        }
    }
}
