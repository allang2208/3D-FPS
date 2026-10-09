// Included inside FPlan. Elevation moves whole authored cores, never their mesh scale.
bool IsThemeRamp(int32 Module)const{return ThemeRamps.Contains(Module);}

void ConfigureThemeLevels(int32 Attempt,double FloorZ)
{
    ThemeFloorZ=FloorZ;ThemeCoreLevels.Reset();
    if(!bThemedRoutes||ThemeRamps.IsEmpty()||Attempt<2)return;
    // Keep the first pair of compact planar attempts, then rotate which core is
    // above, on, and below the common transition floor. No room-count redraw.
    const int32 Profile=(Attempt-2)/2;
    const double Rise=Profile%6<4?1620.:Profile%6==4?1080.:540.;
    if(bPairedFacility)
    {
        // The terminal is anchored to the last spine room. Keep it on the hub
        // floor; outer paired routes rise/fall and return through authored ramps.
        const double Sign=Profile%2?1.:-1.;
        ThemeCoreLevels.Add(TEXT("Route1"),0.);
        ThemeCoreLevels.Add(TEXT("Route2"),Rise*Sign);
        ThemeCoreLevels.Add(TEXT("Route3"),-Rise*Sign);return;
    }
    const double Levels[3]={0.,Rise,-Rise};
    for(int32 R=1;R<=3;++R)
        ThemeCoreLevels.Add(FString::Printf(TEXT("Route%d"),R),Levels[(R-1+Profile)%3]);
}

double ThemeRoomFloor(const FString& Route,int32 Ordinal)const
{
    return ThemeFloorZ+(ThemeRequirement(Route,Ordinal)>=0?ThemeCoreLevels.FindRef(Route):0.);
}

int32 RampEntryForDelta(int32 Ramp,double Delta)const
{
    const auto& P=Modules[Ramp].Ports;
    const double Rise=P[1].P.Z-P[0].P.Z;
    return FMath::Abs(Delta-Rise)<.1?0:FMath::Abs(Delta+Rise)<.1?1:INDEX_NONE;
}

void ThemeRoomLinks(TArray<FShortLink>& Links,const FSocket& Start,const FString& Route,int32 Ordinal,int32 Step)const
{
    if(!bThemedRoutes||ThemeRamps.IsEmpty())return;
    const double TargetZ=ThemeRoomFloor(Route,Ordinal),Delta=TargetZ-Start.P.Z;
    if(FMath::Abs(Delta)<.1)
    {
        if(bPairedFacility&&ThemeGapAllowsBridge(Route,Ordinal-Step,Ordinal))
        {
            const FVector P=Start.P,F=Start.N,R(-F.Y,F.X,0);
            for(double Length:{1440.,1840.,2240.})AddShortLink(Links,Start,{P,P+F*Length},0.,ThemeBridgeLimit);
            for(double Sign:{-1.,1.})for(double Lead:{480.,800.})for(double Tail:{800.,1200.})
            {const FVector Corner=P+F*Lead;AddShortLink(Links,Start,{P,Corner,Corner+R*Sign*Tail},0.,ThemeBridgeLimit);}
        }
        return;
    }
    const auto Flat=MoveTemp(Links);Links.Reset();
    if(!ThemeGapAllowsBridge(Route,Ordinal-Step,Ordinal))return;
    for(int32 Ramp:ThemeRamps)
    {
        const int32 Entry=RampEntryForDelta(Ramp,Delta);if(Entry<0)continue;
        for(const auto& Approach:Flat)
        {
            if(Approach.Length>640.1||Approach.Turns>1)continue;
            FShortLink Link=Approach;Link.Ramp=Ramp;Link.RampEntry=Entry;
            Link.RampTransform=Fit(Ramp,Entry,Approach.End);
            const auto& Port=Modules[Ramp].Ports[1-Entry];
            const FVector N=Link.RampTransform.TransformVectorNoScale(Port.N);
            Link.End={Link.RampTransform.TransformPosition(Port.P)+N*ExitLeadLength,N,-2,Port.Width,Port.Height};
            Link.Length+=AuthoredWalk(Ramp)+ExitLeadLength;Link.Turns+=2;
            if(Link.Length+Start.ReservedLead<=ThemeRampLinkLimit+.1)Links.Add(MoveTemp(Link));
        }
    }
}

bool PlaceRampRoomLink(const FSocket& Start,const FSocket& Goal,const FString& Route,const FShortLink& Link)
{
    const int32 Before=Pieces.Num();
    if(!Place(Link.Ramp,Link.RampTransform,Route))return false;
    const int32 RampIndex=Pieces.Num()-1;
    const FSocket Entry=Socket(RampIndex,Link.RampEntry);
    if(!PlaceRoutePolyline(Start,Entry,Route,Link.Points,ShortLinkLimit-Start.ReservedLead,ShortLinkLimit))
    {Pieces.SetNum(Before);return false;}
    FSocket Out=Socket(RampIndex,1-Link.RampEntry);
    if(!StraightTo(Out,Goal.P,Route,Goal.Owner)||FVector::DotProduct(Out.N,Goal.N)>-.999)
    {Pieces.SetNum(Before);return false;}
    for(int32 I=Before;I<Pieces.Num();++I)Pieces[I].bThemeBridge=true;
    return true;
}

bool CloseSplitLevelGap(const FSocket& Start,const FSocket& Goal,const FString& Route)
{
    if(!CanSearch()||CompactBudget<=0||FMath::Abs(Start.Width-Goal.Width)>=1.||FMath::Abs(Start.Height-Goal.Height)>=1.)return false;
    const int32 Before=Pieces.Num();const FString Tag=Route+TEXT("_Closure");
    // Reserve a ramp at either end of the gap, with a genuine 80 cm flat landing
    // before its doorway. Complete the remaining same-floor gap with short pieces.
    for(int32 Direction=0;Direction<2;++Direction)for(int32 Ramp:ThemeRamps)
    {
        const FSocket& Near=Direction==0?Start:Goal;
        const FSocket& Far=Direction==0?Goal:Start;
        const int32 Entry=RampEntryForDelta(Ramp,Far.P.Z-Near.P.Z);
        if(Entry<0)continue;
        const double FlatLimit=ThemeRampLinkLimit-AuthoredWalk(Ramp)-Near.ReservedLead-Far.ReservedLead;
        for(const auto& Approach:RoomLinks(Near))
        {
            if(Approach.Length>640.1||Approach.Turns>1||Approach.Length>=FlatLimit)continue;
            if(--CompactBudget<0||!CanSearch()){Pieces.SetNum(Before);return false;}
            Pieces.SetNum(Before);
            const FTransform T=Fit(Ramp,Entry,Approach.End);
            const auto& ExitPort=Modules[Ramp].Ports[1-Entry];
            const FVector ExitAt=T.TransformPosition(ExitPort.P);
            if((ExitAt-Far.P).Size()>FlatLimit-Approach.Length)continue;
            if(!Place(Ramp,T,Tag))continue;
            const int32 RampIndex=Pieces.Num()-1;
            if(!PlaceRoutePolyline(Near,Socket(RampIndex,Entry),Tag,Approach.Points,ShortLinkLimit,ShortLinkLimit))continue;
            const auto Exit=Socket(RampIndex,1-Entry);
            const int32 Available=CompactBudget,Allowance=FMath::Min(Available,900);
            if(Allowance<=0)break;
            CompactBudget=Allowance;
            const bool Joined=RouteTo(Exit,Far,Tag,FMath::Min(ThemeBridgeLimit,FlatLimit-Approach.Length),ThemeBridgeLimit,750);
            CompactBudget=Available-(Allowance-FMath::Max(0,CompactBudget));
            int32 Turns=2;for(int32 I=Before;I<Pieces.Num();++I)if(Pieces[I].Module==Elbow)++Turns;
            if(!Joined||Turns>ThemeBridgeMaxTurns)continue;
            for(int32 I=Before;I<Pieces.Num();++I)Pieces[I].bThemeBridge=true;
            return true;
        }
    }
    Pieces.SetNum(Before);return false;
}
