#pragma once

#include "CoreMinimal.h"
#include "TemperateVillageLayout.inl"

// World-space centimetres. This value is copied to terrain jobs along with the water plans.
struct FTemperateChapelSite
{
    FVector Ground=FVector::ZeroVector;
    FVector2D Trail=FVector2D::ZeroVector;
    double TrailHeight=0.;
    bool bPlaced=false;
    // Convert authored chapel centimetres to world centimetres around the site.
    static constexpr double AssemblyScale=1.25;
    static constexpr double FloorRise=34.*AssemblyScale;
    static constexpr int32 PathSegments=8;
    // World-space wall centreline, from one gatepost around the yard to the other.
    static constexpr int32 YardNodeCount=6;
    FVector2D YardNodes[YardNodeCount]{};
    FVector2D Axis=FVector2D(1.,0.);
    FVector2D Local(FVector2D P) const
    {
        const FVector2D D=P-FVector2D(Ground);
        return {D.X*Axis.X+D.Y*Axis.Y,D.Y*Axis.X-D.X*Axis.Y};
    }
    FVector2D World(double X,double Y) const
    {
        return {Ground.X+X*Axis.X-Y*Axis.Y,Ground.Y+X*Axis.Y+Y*Axis.X};
    }
    static constexpr double FrontX=TemperateVillageLayout::CourtFront, BackX=TemperateVillageLayout::CourtBack;
    static constexpr double SideY=TemperateVillageLayout::CourtSide, GateHalf=TemperateVillageLayout::CourtOpening;
    static constexpr double ForecourtX=-2650.;
    static constexpr double ShrineX=FrontX-900.;
    static constexpr double ShrineClearingRadius=500.;
    // Entry stays inside the yard; the monument stands on axis in the open forecourt.
    FVector2D Entry() const { return World(-1700.,0.); }
    FVector2D Shrine() const { return World(ShrineX,0.); }
    FVector2D Landing() const { return World(-916.*AssemblyScale,0.); }
    FVector2D PathPoint(double T) const
    {
        const FVector2D Approach=World(ForecourtX,0.);
        if(T>=.625)return FMath::Lerp(Approach,Landing(),(T-.625)/.375);
        const double U=T/.625;
        const FVector2D Control=World(Local(Trail).X,0.);
        return FMath::Lerp(FMath::Lerp(Trail,Control,U),FMath::Lerp(Control,Approach,U),U);
    }

    inline static const FVector2D RestPew={-849.,-276.};
    // Headstone fronts face mesh -X. Visitors approach each from the south side of the plot.
    struct FGrave
    {
        FVector2D Head;
        double Yaw;
        FVector2D FromFace(double Forward,double Across=0.) const
        {
            return Head+FVector2D(-Forward,Across).GetRotated(Yaw);
        }
    };
    inline static const FGrave Graves[]={{{-570.,907.},76.},{{-377.,950.},84.},{{-199.,886.},87.}};
    // The painted path and the placement exclusion both end at the last visitor's standing place.
    inline static const FVector2D GraveWalk[]={
        {-1480.,0.},{-1335.,360.},{-1030.,680.},{-780.,780.},Graves[2].FromFace(73.)
    };
    static double GraveWalkDistance(const FVector2D& Local)
    {
        double Best=DBL_MAX;
        for(int32 I=1;I<UE_ARRAY_COUNT(GraveWalk);++I)
        {
            const FVector2D A=GraveWalk[I-1],D=GraveWalk[I]-A;
            const double T=FMath::Clamp(FVector2D::DotProduct(Local-A,D)/D.SizeSquared(),0.,1.);
            Best=FMath::Min(Best,FVector2D::DistSquared(Local,A+T*D));
        }
        return FMath::Sqrt(Best);
    }

    void LayoutCourtyard()
    {
        YardNodes[0]=World(FrontX, GateHalf);
        YardNodes[1]=World(FrontX, SideY);
        YardNodes[2]=World(BackX, SideY);
        YardNodes[3]=World(BackX,-SideY);
        YardNodes[4]=World(FrontX,-SideY);
        YardNodes[5]=World(FrontX,-GateHalf);
    }

    bool ClearsYardWall(const FVector2D& Point,double Margin) const
    {
        const double Reach=45.+Margin;
        for(int32 I=0;I<YardNodeCount;++I)
        {
            // Also reserve the opening for the path, with no physical wall across it.
            const FVector2D A=YardNodes[I],B=YardNodes[(I+1)%YardNodeCount];
            if(Point.X<FMath::Min(A.X,B.X)-Reach||Point.X>FMath::Max(A.X,B.X)+Reach||
               Point.Y<FMath::Min(A.Y,B.Y)-Reach||Point.Y>FMath::Max(A.Y,B.Y)+Reach)continue;
            const FVector2D Segment=B-A;
            const double T=FMath::Clamp(FVector2D::DotProduct(Point-A,Segment)/FMath::Max(1.,Segment.SizeSquared()),0.,1.);
            if(FVector2D::DistSquared(Point,A+T*Segment)<Reach*Reach)return true;
        }
        return false;
    }

    bool Near(double X,double Y,double Margin=0.) const
    {
        if(!bPlaced)return false;
        const auto P=Local({X,Y}), Start=Local(Trail);
        // Callers may pass the half-size of an axis-aligned streaming cell.
        const double Reach=440.+Margin*(FMath::Abs(Axis.X)+FMath::Abs(Axis.Y));
        return P.X>=FMath::Min(Start.X,ShrineX-ShrineClearingRadius)-Reach && P.X<=BackX+Reach
            && P.Y>=FMath::Min(Start.Y,-SideY)-Reach && P.Y<=FMath::Max(Start.Y,SideY)+Reach;
    }
    double PathOffset(FVector2D P,double& Along) const
    {
        double Closest=DBL_MAX;
        FVector2D A=Trail;
        Along=0.;
        for(int32 I=1;I<=PathSegments;++I)
        {
            const FVector2D B=PathPoint(double(I)/PathSegments),V=B-A;
            const double F=FMath::Clamp(FVector2D::DotProduct(P-A,V)/FMath::Max(1.,V.SizeSquared()),0.,1.);
            const double D=FVector2D::DistSquared(P,A+F*V);
            if(D<Closest){Closest=D;Along=(I-1+F)/PathSegments;}
            A=B;
        }
        return FMath::Sqrt(Closest);
    }
    bool Clears(double X,double Y,double Margin=0.) const
    {
        if(!Near(X,Y,Margin))return false;
        const auto P=Local({X,Y});
        if(FVector2D::Distance(P,FVector2D(ShrineX,0.))<ShrineClearingRadius+Margin)return true;
        if(FMath::Abs(P.X+1630.)<470.+Margin&&FMath::Abs(P.Y+285.)<665.+Margin)return true;
        // Keep tree crowns and large rocks out of the enclosed graveyard. Small ground
        // cover can still grow away from the masonry, graves and walked approaches.
        if(Margin>=500. && P.X>=FrontX-Margin && P.X<=BackX+Margin && FMath::Abs(P.Y)<=SideY+Margin)return true;
        if(ClearsYardWall(FVector2D(X,Y),Margin))return true;
        const FVector2D Walk=P/AssemblyScale;
        const double LX=Walk.X, LY=FMath::Abs(Walk.Y);
        Margin/=AssemblyScale;
        if(FMath::Abs(LX)<817.+Margin && LY<423.+Margin)return true;
        if(LX>RestPew.X-125.-Margin && LX<RestPew.X+28.+Margin &&
            FMath::Abs(Walk.Y-RestPew.Y)<155.+Margin)return true;
        if(LX>=-930.-Margin && LX<-790. && LY<100.+Margin)return true;
        if(LY<501.+Margin)
            for(double Pier:{-754.,-400.,0.,400.,754.})
                if(FMath::Abs(LX-Pier)<46.+Margin)return true;
        if(Walk.X>=-730.-Margin && Walk.X<=-105.+Margin && Walk.Y>=730.-Margin && Walk.Y<=1080.+Margin)
            for(const FGrave& Grave : Graves)
            {
                const FVector2D Face=(Walk-Grave.Head).GetRotated(-Grave.Yaw);
                if(Face.X>=-130.-Margin && Face.X<=12.+Margin && FMath::Abs(Face.Y)<34.+Margin)return true;
            }
        if(LX>=GraveWalk[0].X-40.-Margin&&LX<=GraveWalk[UE_ARRAY_COUNT(GraveWalk)-1].X+40.+Margin
            &&Walk.Y>=-40.-Margin&&Walk.Y<=865.+Margin
            &&GraveWalkDistance(Walk)<27.+Margin)return true;
        double Along;
        return PathOffset(FVector2D(X,Y),Along)/AssemblyScale<42.+Margin;
    }
    double Grade(double X,double Y,double Z) const
    {
        if(!Near(X,Y))return Z;
        const auto P=Local({X,Y});
        const double LX=P.X/AssemblyScale,LY=P.Y/AssemblyScale;
        const double Outside=FMath::Max(FMath::Abs(LX+50.)-947.,FMath::Abs(LY)-494.);
        const double Weight=1.-FMath::SmoothStep(0.,360.,Outside);
        // Soil collects in sheltered corners and at the foot of the side walls.
        // Keep the western steps on the same datum as the worn entrance stones.
        const double Rim=FMath::Max(FMath::Abs(LX)-813.,FMath::Abs(LY)-413.);
        const double DoorClear=FMath::SmoothStep(104.,234.,FMath::Abs(LY))+
            (LX>0.?1.:0.);
        const double Bank=(1.-FMath::SmoothStep(0.,90.,FMath::Abs(Rim)))*
            FMath::Min(1.,DoorClear)*(4.5+2.7*FMath::Sin(.014*LX+.018*LY));
        const double Bed=Ground.Z+Bank*AssemblyScale;
        if(Weight>=1.)return Bed;
        double Along;
        const double Offset=PathOffset(FVector2D(X,Y),Along)/AssemblyScale;
        const double PathWeight=(1.-FMath::SmoothStep(108.,257.,Offset))*FMath::SmoothStep(0.,.09,Along);
        const double PathZ=FMath::Lerp(TrailHeight,Ground.Z,Along);
        const double Graded=FMath::Lerp(FMath::Lerp(Z,PathZ,PathWeight),Bed,Weight);
        // A shallow level bench beds both posts and the first few metres of their returns.
        const double AlongFront=FMath::Abs(P.X-FrontX);
        const double FromAxis=FMath::Abs(P.Y);
        const double Bench=(1.-FMath::SmoothStep(110.,365.,AlongFront))*(1.-FMath::SmoothStep(530.,920.,FromAxis));
        const double GateAlong=.625+.375*(FrontX-ForecourtX)/(-916.*AssemblyScale-ForecourtX);
        const double YardGrade=FMath::Lerp(Graded,FMath::Lerp(TrailHeight,Ground.Z,GateAlong),Bench);
        // Retain the entry/return clearing and bed the forecourt monument independently.
        const double EntryOutside=FMath::Max(FMath::Abs(P.X+1630.)-470.,FMath::Abs(P.Y+285.)-665.);
        const double EntryGrade=FMath::Lerp(YardGrade,Ground.Z,1.-FMath::SmoothStep(0.,110.,EntryOutside));
        const double ShrineDistance=FVector2D::Distance(P,FVector2D(ShrineX,0.));
        return FMath::Lerp(EntryGrade,Ground.Z,1.-FMath::SmoothStep(ShrineClearingRadius,ShrineClearingRadius+200.,ShrineDistance));
    }
};

