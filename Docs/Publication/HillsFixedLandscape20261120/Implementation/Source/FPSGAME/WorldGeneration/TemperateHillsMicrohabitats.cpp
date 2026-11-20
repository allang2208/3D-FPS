#include "TemperateHillsWorld.h"
#include "TemperateForestHabitat.h"
#include "TemperateVegetationPlacement.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"

void ATemperateHillsWorld::GetNurseLogPlacements(const FBox& Bounds,const TArray<FTemperatePlacement>& Supports,
    TArray<FTemperatePlacement>& Ferns,TArray<FTemperatePlacement>* Floor) const
{
    if(!Assets||Assets->FallenLogs.IsEmpty())return;
    const auto& E=EcologyProfile();
    if(E.NurseLogDensity<=0)return;
    using namespace TemperateHillsSurface;
    for(const auto& Log:Supports)
    {
        const auto* Mesh=Cast<UStaticMesh>(Log.Mesh.ResolveObject());
        if(!Mesh||!Assets->FallenLogs.ContainsByPredicate([&](const auto& R){return R.Get()==Mesh;}))continue;
        const FVector Origin=Log.Transform.GetLocation();
        const double Region=RainforestWeight(Origin.X,Origin.Y);
        const double Moist=TemperateForestHabitat::Moisture(Origin.X,Origin.Y,Seed,Region, EcologyProfile());
        if(Unit(Log.Key+701)>E.NurseLogDensity*(.35+.65*Moist))continue;
        const FBox Box=Mesh->GetBoundingBox();
        const bool LongX=Box.GetSize().X>=Box.GetSize().Y;
        const FVector Center=Log.Transform.TransformPosition(Box.GetCenter());
        const FVector Axis=Log.Transform.TransformVectorNoScale(LongX?FVector::ForwardVector:FVector::RightVector);
        FVector Side(-Axis.Y,Axis.X,0);Side.Normalize();
        // Stable shade/moisture preference; never rotate colonies with the live sun.
        const double A=TemperateForestHabitat::Moisture(Center.X+Side.X*200,Center.Y+Side.Y*200,Seed,Region, EcologyProfile());
        const double B=TemperateForestHabitat::Moisture(Center.X-Side.X*200,Center.Y-Side.Y*200,Seed,Region, EcologyProfile());
        if(A+Side.Y*.08<B-Side.Y*.08)Side=-Side;
        const double HalfLength=LongX?Box.GetExtent().X*Log.Transform.GetScale3D().X:Box.GetExtent().Y*Log.Transform.GetScale3D().Y;
        const FBox WorldBox=Box.TransformBy(Log.Transform);
        const double RottenEnd=Unit(Log.Key+709)<.5?-.59:.59;
        const int32 GX=FMath::FloorToInt(Origin.X/3600.),GY=FMath::FloorToInt(Origin.Y/3600.);
        const int32 Count=Floor?12:4;
        for(int32 I=0;I<Count;++I)
        {
            const uint32 K=Mix(Log.Key^uint32(3701+I*97));
            const int32 Kind=I<4?0:I<9?1:2;
            const bool Fern=Kind==0;
            if(!Fern&&Unit(K+13)>FMath::Lerp(Kind==1?.10:.24,1.,Moist))continue;
            FSoftObjectPath Ref;
            FBox Shape(ForceInit);
            if(Fern)
            {
                if(Assets->ForestFerns.IsEmpty())continue;
                const auto& R=Assets->ForestFerns[K%Assets->ForestFerns.Num()];
                if(!R.IsValid())continue;
                Ref=R.ToSoftObjectPath();Shape=R.Get()->GetImportedBounds().GetBox();
            }
            else
            {
                const auto& List=Kind==1?Assets->ForestFungi:Assets->ForestMoss;
                if(List.IsEmpty())continue;
                const uint32 Form=Kind==1&&Unit(K+17)<.78?Log.Key:K;
                const auto& MeshRef=List[Form%List.Num()];
                if(!MeshRef.IsValid())continue;
                Ref=MeshRef.ToSoftObjectPath();Shape=HillsVegetation::BoundsOf(MeshRef.Get());
            }
            const double Size=Fern?48.+Unit(K+3)*33.:Kind==1?10.+Unit(K+3)*12.:42.+Unit(K+3)*28.;
            const double Scale=Size/FMath::Max(1.,Fern?Shape.GetSize().Z:FMath::Max(Shape.GetSize().X,Shape.GetSize().Y));
            const FVector Direction=(I==3||I==8)?-Side:Side;
            const double Station=Fern?(Unit(K+1)-.5)*1.58:RottenEnd+(Unit(K+1)-.5)*(Kind==1?.48:.78);
            const FVector StationOffset=Axis*(HalfLength*Station);
            // Follow the ray from this part of the log to the padded mask edge.
            // Projecting the entire log onto its side used to leave a wide bare
            // strip both beside and beyond the end of diagonally fallen trunks.
            const double Pad=20.+.71*FMath::Max(Shape.GetSize().X,Shape.GetSize().Y)*Scale;
            const FVector Extent=WorldBox.GetExtent()+FVector(Pad);
            const double SideReach=FMath::Min(
                (Extent.X-FMath::Sign(Direction.X)*StationOffset.X)/FMath::Max(.001,FMath::Abs(Direction.X)),
                (Extent.Y-FMath::Sign(Direction.Y)*StationOffset.Y)/FMath::Max(.001,FMath::Abs(Direction.Y)));
            const FVector At=Center+StationOffset+Direction*(SideReach+(Fern?17.:4.)+Unit(K+2)*(Fern?54.:24.));
            if(!Bounds.ExpandBy(150.).IsInsideOrOnXY(At))continue;
            if(PathDistance(At.X,At.Y)<400||ChapelSite.Clears(At.X,At.Y,180)||VillageSite.Clears(At.X,At.Y,180))continue;
            if((RiverPlan&&RiverPlan->Sample(At.X,At.Y).Bank>.10)||SampleForestWater(At.X,At.Y).Wet)continue;
            const FVector N=SurfaceNormal(At.X,At.Y);if(N.Z<.92)continue;
            const FQuat Rotation=FQuat(N,Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
            const FVector RootPoint=Fern?FVector(0,0,Shape.Min.Z):FVector(Shape.GetCenter().X,Shape.GetCenter().Y,Shape.Min.Z);
            const double GroundZ=Height(At.X,At.Y);
            if(Kind==2)
            {
                bool Flat=true;
                for(const FVector2D D:{FVector2D(1,0),FVector2D(-1,0),FVector2D(0,1),FVector2D(0,-1)})
                {
                    const FVector Offset=Rotation.RotateVector(FVector(D*Size*.40,0));
                    if(FMath::Abs(Height(At.X+Offset.X,At.Y+Offset.Y)-GroundZ-Offset.Z)>2.5){Flat=false;break;}
                }
                if(!Flat)continue;
            }
            FTemperatePlacement P;P.Mesh=Ref;P.Key=K;
            const FVector Pivot=FVector(At.X,At.Y,GroundZ+(Kind==2?.8:-1.))-Rotation.RotateVector(RootPoint*Scale);
            if(Pivot.X<Bounds.Min.X||Pivot.X>=Bounds.Max.X||Pivot.Y<Bounds.Min.Y||Pivot.Y>=Bounds.Max.Y)continue;
            P.Transform=FTransform(Rotation,Pivot,FVector(Scale));
            P.CandidateId=(uint64(uint32(GX)&0x00ffffffU)<<32)|(uint64(uint32(GY)&0x00ffffffU)<<8)|uint64(0xb0+I);
            (Fern?Ferns:*Floor).Add(MoveTemp(P));
        }
    }
}

void ATemperateHillsWorld::GetVisualAnchorPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets||!Assets->RainforestBankBoulder.IsValid()||!VillageSite.bPlaced)return;
    using namespace TemperateHillsSurface;
    const auto* Mesh=Assets->RainforestBankBoulder.Get();
    const FBox Box=Mesh->GetBoundingBox();
    auto AddAnchor = [&](FVector2D At,uint32 K,uint64 Id)
    {
        if(At.X<Bounds.Min.X||At.X>=Bounds.Max.X||At.Y<Bounds.Min.Y||At.Y>=Bounds.Max.Y)return;
        if(SurfaceNormal(At.X,At.Y).Z<.90||VillageSite.Clears(At.X,At.Y,160.)||PathDistance(At.X,At.Y)<450.)return;
        const double Scale=(230.+Unit(K+1)*120.)/FMath::Max(1.,FMath::Max(Box.GetSize().X,Box.GetSize().Y));
        FTemperatePlacement P;P.Key=K;P.Mesh=Assets->RainforestBankBoulder.ToSoftObjectPath();
        P.Transform=FTransform(FRotator(0,Unit(K+2)*360.,0),FVector(At,Height(At.X,At.Y)),FVector(Scale));
        P.CandidateId=Id;Out.Add(P);
    };
    for(int32 I=0;I<4;++I)
    {
        const uint32 K=Key(I,0,uint32(Seed),3793);
        const double Side=I<2?-1.:1.;
        const FVector2D Along=VillageSite.Approach(Side,1900.+(I%2)*3100.,Seed);
        const FVector2D Across(-VillageSite.Axis.Y,VillageSite.Axis.X);
        AddAnchor(Along+Across*((I%2?1.:-1.)*(750.+Unit(K)*260.)),K,0x3800000000000000ULL|uint64(I));
    }
    // At most one upland or outer-bank landmark per 180 m sector. Candidates
    // reside inside their own sector, so adjacent streaming cells agree.
    constexpr double Sector=18000.;
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/Sector);Y<=FMath::FloorToInt(Bounds.Max.Y/Sector);++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/Sector);X<=FMath::FloorToInt(Bounds.Max.X/Sector);++X)
    {
        const uint32 K=Key(X,Y,uint32(Seed),3847);
        if(Unit(K)>.27)continue;
        double Best=0.;FVector2D Chosen=FVector2D::ZeroVector;
        for(uint32 I=0;I<7;++I)
        {
            const FVector2D At((X+.12+.76*Unit(K+2*I+1))*Sector,(Y+.12+.76*Unit(K+2*I+2))*Sector);
            if(VillageSite.Near(At.X,At.Y,2000.)||RainforestWeight(At.X,At.Y)>.12)continue;
            const auto Bank=RiverPlan?RiverPlan->Sample(At.X,At.Y):TemperateRiver::FSample();
            if(Bank.Distance<Bank.HalfWidth+350.)continue;
            const double Z=Height(At.X,At.Y);
            const double Rise=Z-.25*(Height(At.X-1400.,At.Y)+Height(At.X+1400.,At.Y)+Height(At.X,At.Y-1400.)+Height(At.X,At.Y+1400.));
            const double Bend=FMath::Abs(Bank.Bend)*(1.-FMath::SmoothStep(650.,2500.,Bank.Distance-Bank.HalfWidth));
            const double Score=FMath::Max(FMath::Clamp((Rise-20.)/100.,0.,1.),Bend);
            if(Score>Best && SurfaceNormal(At.X,At.Y).Z>=.90){Best=Score;Chosen=At;}
        }
        if(Best>.12)AddAnchor(Chosen,K,0x3900000000000000ULL|uint64(K));
    }
}
