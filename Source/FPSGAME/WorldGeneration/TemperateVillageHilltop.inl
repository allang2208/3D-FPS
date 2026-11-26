// Included inside TemperateHillsVillage.cpp's private namespace.
// A bounded, deterministic survey runs once before any terrain cells or village actors.
FTemperateVillageSite HilltopSite(int32 Seed,double Half,const FVector& Spawn,
    const TemperateRiver::FPlanPtr& River,const TemperateForestWater::FPlanPtr& Water,
    TFunctionRef<double(const FVector2D&)> Raw,TFunctionRef<double(const FVector2D&)> Forest)
{
    struct FSurvey { FVector2D P; double Score; };
    TArray<FSurvey> Survey;
    constexpr double PadX=7000.,PadY=5500.,MinShoulder=4500.,Grid=3600.;
    const double Limit=Half-PadX-MinShoulder-200.;
    for(int32 Y=0;Y<=FMath::FloorToInt(2.*Limit/Grid);++Y)
    for(int32 X=0;X<=FMath::FloorToInt(2.*Limit/Grid);++X)
    {
        const auto Key=TemperateHillsSurface::Key(X,Y,uint32(Seed),3197);
        const FVector2D P(-Limit+X*Grid+700.*(TemperateHillsSurface::Unit(Key)-.5),
                          -Limit+Y*Grid+700.*(TemperateHillsSurface::Unit(Key+1)-.5));
        const double Center=Raw(P);
        double RingMax=-DBL_MAX,RingSum=0.;
        for(int32 I=0;I<8;++I)
        {
            const double A=I*UE_PI/4.;
            const double Z=Raw(P+FVector2D(FMath::Cos(A),FMath::Sin(A))*11000.);
            RingMax=FMath::Max(RingMax,Z);RingSum+=Z;
        }
        // Prefer a genuine broad crown before budgeting any cut/fill work.
        Survey.Add({P,3.*FMath::Max(0.,RingMax-Center)-(Center-RingSum/8.)
            +900.*Forest(P)+.008*(P-FVector2D(Spawn)).Size()});
    }
    Survey.Sort([](const FSurvey& A,const FSurvey& B)
    {
        if(A.Score!=B.Score)return A.Score<B.Score;
        return A.P.X!=B.P.X?A.P.X<B.P.X:A.P.Y<B.P.Y;
    });
    FTemperateVillageSite Best;
    double BestScore=DBL_MAX;
    auto DryLane=[&](const FVector2D& P)
    {
        constexpr double Clearance=650.;
        if(FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y))>Half-Clearance)return false;
        if(River){const auto R=River->Sample(P.X,P.Y);if(R.Distance<=R.HalfWidth+Clearance)return false;}
        if(Water)
        {
            for(const auto& B:Water->Basins)
                if((B.Center-P).SizeSquared()<FMath::Square(B.Radius+Clearance))return false;
            for(const auto& Pool:Water->Pools)
                if(Pool.Bounds.ExpandBy(Clearance).IsInside(P))return false;
        }
        return true;
    };
    for(int32 Index=0;Index<Survey.Num();++Index)
    {
        // Usually the first 64 crowns suffice. If water excludes them all, continue
        // the same finite survey instead of returning a missing village prematurely.
        if(Index>=64&&Best.bPlaced)break;
        const FVector2D Center=Survey[Index].P;
        // A gate faces a real valley junction; offsets allow a dry approach around water.
        for(double Offset:{0.,-6000.,6000.,-12000.,12000.})
        {
            const FVector2D Junction(Center.X+Offset,TemperateHillsSurface::ValleyY(Center.X+Offset,Seed));
            const FVector2D ToTop=Center-Junction;
            const double Distance=ToTop.Size();
            if(Distance<PadX+MinShoulder+800.||!DryLane(Junction))continue;
            FTemperateVillageSite Site;
            Site.bPlaced=true;Site.bSideLane=true;Site.bHilltop=true;
            Site.PadHalfX=PadX;Site.PadHalfY=PadY;
            Site.Ground=FVector(Center,0.);Site.Axis=ToTop/Distance;
            Site.FeederLength=Distance-HalfX;Site.JunctionZ=Raw(Junction);
            Site.Shoulder=MinShoulder;
            if(!LandAvailable(Site,Half,Spawn,River,Water))continue;
            double Low=DBL_MAX,High=-DBL_MAX,Mean=0.;
            for(int32 X=-3;X<=3;++X)for(int32 Y=-2;Y<=2;++Y)
            {
                const double Z=Raw(Site.World(PadX*X/3.,PadY*Y/2.));
                Low=FMath::Min(Low,Z);High=FMath::Max(High,Z);Mean+=Z;
            }
            Mean/=35.;
            // Do not carve a shelf out of an otherwise steep hillside.
            if(High-Low>1800.)continue;
            struct FFlank { FVector2D Edge,Out; };
            TArray<FFlank,TInlineAllocator<16>> Flanks;
            for(double Side:{-1.,1.})for(double T:{-.65,0.,.65})
            {
                Flanks.Add({FVector2D(Side*PadX,T*PadY),FVector2D(Side,0.)});
                Flanks.Add({FVector2D(T*PadX,Side*PadY),FVector2D(0.,Side)});
            }
            for(double X:{-1.,1.})for(double Y:{-1.,1.})
                Flanks.Add({FVector2D(X*PadX,Y*PadY),FVector2D(X,Y).GetSafeNormal()});
            for(double Width:{4500.,6500.,8500.})
            {
                Site.Shoulder=Width;
                if(Distance<PadX+Width+800.||!LandAvailable(Site,Half,Spawn,River,Water))continue;
                double RimMax=-DBL_MAX;
                for(const auto& F:Flanks)
                {
                    const auto P=F.Edge+F.Out*Width;
                    RimMax=FMath::Max(RimMax,Raw(Site.World(P.X,P.Y)));
                }
                // The reserved crown stands above every sampled outer flank, not in a bowl.
                Site.Ground.Z=FMath::Max(Mean,RimMax+200.);
                const double Earthwork=FMath::Max(High-Site.Ground.Z,Site.Ground.Z-Low);
                if(Earthwork>2400.)continue;
                auto Height=[&](const FVector2D& P){return Site.GradeForSiteSurvey(P.X,P.Y,Raw(P));};
                double FlankGrade=0.;
                for(const auto& F:Flanks)for(double T:{.125,.25,.5,.75,.875,1.})
                {
                    const auto Local=F.Edge+F.Out*(Width*T);
                    const auto P=Site.World(Local.X,Local.Y);
                    const double DX=(Height(P+FVector2D(100,0))-Height(P-FVector2D(100,0)))/200.;
                    const double DY=(Height(P+FVector2D(0,100))-Height(P-FVector2D(0,100)))/200.;
                    FlankGrade=FMath::Max(FlankGrade,FMath::Sqrt(DX*DX+DY*DY));
                }
                if(FlankGrade>FMath::Tan(FMath::DegreesToRadians(26.)))continue;
                bool bDry=true;
                double RoadGrade=0.;
                for(double Side:{-1.,1.})
                {
                    const double Run=Side<0.?Site.FeederLength:PadX-HalfX+Width;
                    const int32 Steps=FMath::CeilToInt(Run/200.);
                    double Previous=Site.Ground.Z;
                    for(int32 I=1;I<=Steps;++I)
                    {
                        const auto P=Site.Approach(Side,Run*I/Steps,Seed);
                        if(!DryLane(P)){bDry=false;break;}
                        const double Z=Height(P);
                        RoadGrade=FMath::Max(RoadGrade,FMath::Abs(Z-Previous)/(Run/Steps));
                        Previous=Z;
                    }
                    if(!bDry)break;
                }
                if(!bDry||RoadGrade>FMath::Tan(FMath::DegreesToRadians(18.)))continue;
                const double Score=Earthwork+2000.*FlankGrade+4000.*RoadGrade
                    +20000.*FMath::Max(0.,RoadGrade-FMath::Tan(FMath::DegreesToRadians(12.)))
                    +10000.*FMath::Max(0.,FlankGrade-FMath::Tan(FMath::DegreesToRadians(22.)))
                    +1200.*Forest(Center)+.025*Site.FeederLength+.2*Survey[Index].Score;
                if(Score<BestScore){BestScore=Score;Best=Site;}
            }
        }
    }
    return Best;
}
