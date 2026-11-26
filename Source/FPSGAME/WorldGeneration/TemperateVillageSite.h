#pragma once

#include "CoreMinimal.h"
#include "TemperateVillageLayout.inl"
#include "TemperateChapelSite.h"
#include "TemperateVillageApron.h"
#include "TemperateHillsSurface.h"

struct FTemperateVillageSite
{
    FVector Ground=FVector::ZeroVector;
    FVector2D Axis=FVector2D(1.,0.);
    // Full level footprint stays on the streaming transform datum. Only its outside apron blends.
    double Shoulder=1400.;
    // Terrain reservation is independent of the unchanged authored village level.
    double PadHalfX=TemperateVillageLayout::HalfX,PadHalfY=TemperateVillageLayout::HalfY;
    bool bHilltop=false;
    bool bPlaced=false;
    bool bSmithYardRepaired=false;
    bool bSideLane=false;
    // Optional short lane from a dry valley junction to a setback western gate.
    double FeederLength=0.,JunctionZ=0.;
    FVector2D WallHalfSize() const { return {PadHalfX-500.,PadHalfY-500.}; }
    static constexpr double WallCornerCut=600.;
    // The stable wagon gate is at (5250,1600), across the east street at Y=500.
    inline static const FVector2D WorkshopCenter{5250.,-545.};
    // Local survey of the player-built keep at the east gate. The workshop and keep have separate pivots.
    FTransform WorkshopTowerPose() const
    {
        return FTransform(FVector(Axis,0.).Rotation(),FVector(World(5873.,-605.260788747),Ground.Z));
    }
    bool IsWorkshopTowerPosition(const FVector& Location) const
    {
        return bPlaced && Location.Equals(WorkshopTowerPose().GetLocation(),30.);
    }
    static double WorkshopEdge(FVector2D Local)
    {
        const FVector2D D=Local-WorkshopCenter;
        const double House=FMath::Max(FMath::Abs(D.X)-340.,FMath::Abs(D.Y)-624.);
        const double Apron=FMath::Max(FMath::Abs(D.X)-150.,FMath::Abs(D.Y-710.)-125.);
        return FMath::Min(House,Apron);
    }
    bool ContainsVillage(const FVector& Location) const
    {
        if(!bPlaced)return false;
        const FVector2D Point=Local(Location.X,Location.Y).GetAbs();
        // Earlier valley worlds stream the same village level, without the hilltop perimeter.
        const FVector2D Half=bHilltop?WallHalfSize():FVector2D(6500.,5000.);
        return Point.X<=Half.X&&Point.Y<=Half.Y&&
            (!bHilltop||Point.X+Point.Y<=Half.X+Half.Y-WallCornerCut);
    }
    static double GateY(double Side) { return Side<0.?0.:500.; }
    static double GateHalfGap(double Side) { return Side<0.?500.:400.; }
    double ApproachLength(double Side) const
    { return Side<0.?FeederLength:(bSideLane?PadHalfX+Shoulder-TemperateVillageLayout::HalfX:0.); }
    double EdgeDistance(const FVector2D& P) const
    {
        return FVector2D(FMath::Max(0.,FMath::Abs(P.X)-PadHalfX),
                         FMath::Max(0.,FMath::Abs(P.Y)-PadHalfY)).Size();
    }
    FVector2D Extent() const
    {
        const double AX=FMath::Abs(Axis.X), AY=FMath::Abs(Axis.Y);
        return {AX*PadHalfX+AY*PadHalfY+Shoulder,
                AY*PadHalfX+AX*PadHalfY+Shoulder};
    }

    FVector2D Local(double X,double Y) const
    {
        const double DX=X-Ground.X,DY=Y-Ground.Y;
        return {DX*Axis.X+DY*Axis.Y,DY*Axis.X-DX*Axis.Y};
    }
    FVector2D World(double X,double Y) const
    {
        return {Ground.X+X*Axis.X-Y*Axis.Y,Ground.Y+X*Axis.Y+Y*Axis.X};
    }
    FVector2D Mouth(double Side) const
    {
        return World(Side*TemperateVillageLayout::HalfX,GateY(Side));
    }
    FVector2D Approach(double Side,double Distance,int32 Seed) const
    {
        const FVector2D Gate=Mouth(Side);
        if(bSideLane && Side>0.)return Gate+Axis*Distance;
        if(FeederLength>0. && Side<0.)
        {
            if(Distance<=FeederLength)return Gate-Axis*Distance;
            const auto Junction=Gate-Axis*FeederLength;
            const double X=Junction.X-(Distance-FeederLength);
            return {X,TemperateHillsSurface::ValleyY(X,Seed)};
        }
        const double X=Gate.X+Side*Distance;
        return {X,TemperateHillsSurface::ValleyY(X,Seed)};
    }
    FTemperateChapelSite ChapelLot() const
    {
        using namespace TemperateVillageLayout;
        FTemperateChapelSite Chapel;
        if(bPlaced)
        {
            Chapel.Ground=FVector(World(ChapelX,ChapelY),Ground.Z);
            Chapel.Axis=Axis;
            Chapel.Trail=World(ChapelTrailX,ChapelTrailY);
            Chapel.TrailHeight=Ground.Z;
            Chapel.bPlaced=true;
            Chapel.LayoutCourtyard();
        }
        return Chapel;
    }
    bool Near(double X,double Y,double Margin=0.) const
    {
        if(!bPlaced)return false;
        const FVector2D R=Extent();
        const bool Pad=FMath::Abs(X-Ground.X)<=R.X+Margin && FMath::Abs(Y-Ground.Y)<=R.Y+Margin;
        if(Pad || FeederLength<=0.)return Pad;
        const auto Gate=Mouth(-1.),Junction=Gate-Axis*FeederLength;
        return X>=FMath::Min(Gate.X,Junction.X)-550.-Margin && X<=FMath::Max(Gate.X,Junction.X)+550.+Margin
            && Y>=FMath::Min(Gate.Y,Junction.Y)-550.-Margin && Y<=FMath::Max(Gate.Y,Junction.Y)+550.+Margin;
    }
    double Grade(double X,double Y,double Height,int32 Seed=0) const
    {
        if(!bHilltop)
        {
            const double Survey=GradeForSiteSurvey(X,Y,Height);
            if(!bPlaced || !Near(X,Y))return Survey;
            // Older valley layouts have a smaller pad. Bed the roadside annex on the village datum.
            const double Outside=WorkshopEdge(Local(X,Y));
            return FMath::Lerp(Ground.Z,Survey,FMath::SmoothStep(0.,200.,Outside));
        }
        if(!bPlaced)return Height;
        // Only the village's broad apron joins the crown to the existing hill.
        // The approach keeps its route/vegetation clearance, not an elevated embankment.
        const FVector2D P=Local(X,Y);
        const double Distance=EdgeDistance(P);
        if(Distance>=Shoulder)return Height;
        const double Crown=FMath::Lerp(Ground.Z,Height,TemperateHillsSurface::Quintic(
            FMath::Clamp(Distance/Shoulder,0.,1.)));
        if(Seed!=TemperateHillsMap::Seed || Distance<=0.)return Crown;
        return Crown+TemperateVillageApron::Sample(P,PadHalfX,PadHalfY,Shoulder).Height;
    }
    // Freeze the original survey metric so this terrain-only change cannot move
    // an existing seed's village, gate, datum, or chosen shoulder width.
    double GradeForSiteSurvey(double X,double Y,double Height) const
    {
        if(!Near(X,Y))return Height;
        const auto P=Local(X,Y);
        const double Edge=FMath::Clamp(EdgeDistance(P)/Shoulder,0.,1.);
        const double Blend=bHilltop?TemperateHillsSurface::Quintic(Edge):FMath::SmoothStep(0.,Shoulder,EdgeDistance(P));
        const double Pad=FMath::Lerp(Ground.Z,Height,Blend);
        const double Along=-P.X-TemperateVillageLayout::HalfX;
        if(FeederLength<=0. || Along<=0. || Along>=FeederLength || FMath::Abs(P.Y)>=550.)return Pad;
        const double FlatRun=bHilltop?PadHalfX-TemperateVillageLayout::HalfX:0.;
        const double T=FMath::Clamp((Along-FlatRun)/FMath::Max(1.,FeederLength-FlatRun),0.,1.);
        const double Road=FMath::Lerp(Ground.Z,JunctionZ,bHilltop?TemperateHillsSurface::Quintic(T):T*T*(3.-2.*T));
        const double Weight=(1.-FMath::SmoothStep(200.,550.,FMath::Abs(P.Y)))
            *FMath::SmoothStep(0.,250.,FeederLength-Along);
        return FMath::Lerp(Pad,Road,Weight);
    }
    bool InLandmarkView(double X,double Y) const
    {
        if(!bPlaced)return false;
        const FVector2D P(X,Y),Target=World(TemperateVillageLayout::ChapelX,TemperateVillageLayout::ChapelY);
        for(const double Side:{-1.,1.})
        {
            const FVector2D From=Mouth(Side)+Axis*Side*4200.,Span=Target-From;
            const double T=FVector2D::DotProduct(P-From,Span)/FMath::Max(1.,Span.SizeSquared());
            if(T>.04&&T<.94&&(P-From-Span*T).SizeSquared()<FMath::Square(180.+220.*T))return true;
        }
        return false;
    }
    bool Clears(double X,double Y,double Margin) const
    {
        if(!Near(X,Y,Margin))return false;
        const FVector2D P=Local(X,Y);
        if(WorkshopEdge(P)<=Margin)return true;
        if(bHilltop && FMath::Abs(P.X)<=PadHalfX+Margin && FMath::Abs(P.Y)<=PadHalfY+Margin)return true;
        if(FeederLength>0. && P.X<=-TemperateVillageLayout::HalfX && P.X>=-TemperateVillageLayout::HalfX-FeederLength-Margin
           && FMath::Abs(P.Y)<210.+Margin)return true;
        if(bSideLane && P.X>TemperateVillageLayout::HalfX && P.X<PadHalfX+Shoulder+Margin
           && FMath::Abs(P.Y-500.)<210.+Margin)return true;
        if(FMath::Abs(P.X)>TemperateVillageLayout::HalfX+Margin || FMath::Abs(P.Y)>TemperateVillageLayout::HalfY+Margin)return false;
        for(const auto& Bed:TemperateVillageLayout::Beds)
        {
            const double DX=P.X-Bed.X,DY=P.Y-Bed.Y;
            if(FMath::Abs(DX*Bed.Cos+DY*Bed.Sin)<=Bed.HalfX+Margin &&
               FMath::Abs(DY*Bed.Cos-DX*Bed.Sin)<=Bed.HalfY+Margin)return true;
        }
        for(const auto& R:TemperateVillageLayout::Roads)
        {
            const FVector2D From=P-FVector2D(R.X,R.Y),Span(R.DX,R.DY);
            const double T=FMath::Clamp(FVector2D::DotProduct(From,Span)/Span.SizeSquared(),0.,1.);
            if((From-T*Span).SizeSquared()<FMath::Square(R.HalfWidth+Margin))return true;
        }
        return false;
    }
};
