// FPlan extension: reserve a shared terminal from all three complete route
// frontiers. Every accepted piece still passes Place/CompleteSocketGraph and
// the normal mission budget. The old solver remains available to old catalogs.
struct FJointRoute
{
    TArray<FPlaced> Layout;
    FSocket End;
    double Limit=0,Score=0;
    int32 ExitTurns=0;
};
struct FJointTerminal
{
    FSocket Entry;
    TArray<FSocket> Tops;
    TArray<int32> Assignment;
    double Score=0;
};

FSocket ModuleSocketAt(int32 Module,int32 Port,const FTransform& T)const
{
    const auto& P=Modules[Module].Ports[Port];
    return {T.TransformPosition(P.P),T.TransformVectorNoScale(P.N),-2,P.Width,P.Height};
}

FSocket JointTerminalEntry(const FSocket& Landing,int32 HubPort)const
{
    const auto Stair=Fit(StairDrop,0,Landing);
    const auto Bottom=ModuleSocketAt(StairDrop,1,Stair);
    const auto Sleeve=Fit(Threshold,0,Bottom);
    const auto Hub=Fit(BossConfluence,HubPort,ModuleSocketAt(Threshold,1,Sleeve));
    auto Entry=ModuleSocketAt(BossConfluence,0,Hub);
    Entry.N=-Entry.N;Entry.P.Z+=BossDepth;
    return Entry;
}

TArray<FSocket> JointTerminalTops(FSocket Entry)const
{
    Entry.P.Z-=BossDepth;
    const auto Hub=Fit(BossConfluence,0,Entry);
    TArray<FSocket> Tops;
    for(int32 Port:{0,2,3})
    {
        const auto Sleeve=Fit(Threshold,0,ModuleSocketAt(BossConfluence,Port,Hub));
        const auto Stair=Fit(StairDrop,1,ModuleSocketAt(Threshold,1,Sleeve));
        Tops.Add(ModuleSocketAt(StairDrop,0,Stair));
    }
    return Tops;
}

double JointGapCost(const FJointRoute& Route,const FSocket& Top)const
{
    if(FMath::Abs(Route.End.P.Z-Top.P.Z)>.1||
       FMath::Abs(Route.End.Width-Top.Width)>=1||FMath::Abs(Route.End.Height-Top.Height)>=1)return DBL_MAX;
    const FVector D=(Route.End.P-Top.P).GetAbs();
    const double Walk=D.X+D.Y+Route.End.ReservedLead+Top.ReservedLead;
    if(Walk>Route.Limit+.1)return DBL_MAX;
    return Walk+240.*(1.+FVector::DotProduct(Route.End.N,Top.N));
}

bool GrowJointRoute(const FSocket& Lead,const FSocket& Guide,const FString& Route,TArray<FJointRoute>& Out)
{
    const auto Base=Pieces;
    TArray<FCompactBeam> Beam;
    bJointRouteCandidates=true;
    const bool Grown=GrowCompactRooms(6,Lead,Guide,Route,Beam,true);
    bJointRouteCandidates=false;
    Out.Reset();
    if(!Grown){Pieces=Base;return false;}
    for(const auto& State:Beam)
    {
        if(!CanSearch()||CompactBudget<=0)break;
        if(FMath::Abs(State.End.P.Z-ThemeFloorZ)<.1)
        {
            Out.Add({State.Layout,State.End,ThemeBridgeLimit,State.Score,0});
            continue;
        }
        // Include the return ramp before comparing frontiers. Its walking
        // length and bends remain part of this one room-to-terminal join.
        auto Links=RoomLinks(State.End);ThemeRoomLinks(Links,State.End,Route,6,1);
        for(const auto& Link:Links)
        {
            if(Link.Ramp<0)continue;
            if(!CanSearch()||--CompactBudget<0)break;
            Pieces=State.Layout;
            FSocket Goal=Link.End;Goal.N=-Goal.N;
            if(!PlaceRampRoomLink(State.End,Goal,Route,Link))continue;
            FSocket LandingExit=Link.End;LandingExit.Owner=Pieces.Num()-1;
            LandingExit.ReservedLead=State.End.ReservedLead+Link.Length;
            if(LandingExit.ReservedLead>=ThemeRampLinkLimit)continue;
            Out.Add({Pieces,LandingExit,ThemeRampLinkLimit,State.Score+Link.Length*.05,Link.Turns});
        }
    }
    Pieces=Base;
    Out.StableSort([](const FJointRoute& A,const FJointRoute& B){return A.Score<B.Score;});
    TArray<FJointRoute> Diverse;TSet<FIntVector> Seen;
    for(auto& Candidate:Out)
    {
        const FIntVector Key(FMath::RoundToInt(Candidate.End.P.X/350.),FMath::RoundToInt(Candidate.End.P.Y/350.),
                             FMath::RoundToInt(Candidate.End.N.Rotation().Yaw/90.));
        if(Seen.Contains(Key))continue;
        Seen.Add(Key);Diverse.Add(MoveTemp(Candidate));
        if(Diverse.Num()==64)break;
    }
    Out=MoveTemp(Diverse);return !Out.IsEmpty();
}

TArray<FJointTerminal> JointTerminalChoices(const TArray<FJointRoute> (&Routes)[3])
{
    static const int32 Assignments[6][3]={{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}};
    TArray<FJointTerminal> Choices;TSet<FIntVector> Seen;
    auto Add=[&](const FSocket& Entry)
    {
        if(!CanSearch())return;
        const FIntVector Key(FMath::RoundToInt(Entry.P.X/200.),FMath::RoundToInt(Entry.P.Y/200.),
                             FMath::RoundToInt(Entry.N.Rotation().Yaw/90.));
        if(Seen.Contains(Key))return;Seen.Add(Key);
        const auto Tops=JointTerminalTops(Entry);
        double Cost[3][3];
        for(int32 R=0;R<3;++R)for(int32 P=0;P<3;++P)
        {
            Cost[R][P]=DBL_MAX;
            for(const auto& Candidate:Routes[R])Cost[R][P]=FMath::Min(Cost[R][P],JointGapCost(Candidate,Tops[P]));
        }
        for(const auto& Assignment:Assignments)
        {
            double Total=0,Worst=0;bool Feasible=true;
            for(int32 R=0;R<3;++R)
            {
                const double C=Cost[R][Assignment[R]];
                if(C==DBL_MAX){Feasible=false;break;}
                Total+=C;Worst=FMath::Max(Worst,C);
            }
            if(Feasible)Choices.Add({Entry,Tops,{Assignment[0],Assignment[1],Assignment[2]},Total+Worst});
        }
    };
    // Each route gets equal opportunity to propose the shared terminal. The
    // small offsets retain a bounded connector instead of pinning a staircase
    // directly to whichever route happened to grow first.
    for(int32 R=0;R<3;++R)for(int32 I=0;I<FMath::Min(24,Routes[R].Num());++I)
    {
        if(!CanSearch())break;
        const auto& RouteExit=Routes[R][I].End;
        for(int32 Port:{0,2,3})
        {
            for(double Gap:{0.,800.,1600.})
            {auto Landing=RouteExit;Landing.P+=RouteExit.N*Gap;Add(JointTerminalEntry(Landing,Port));}
            for(double Sign:{-1.,1.})
            {
                auto Landing=RouteExit;const FVector Side(-RouteExit.N.Y*Sign,RouteExit.N.X*Sign,0);
                Landing.P+=RouteExit.N*800.+Side*800.;Landing.N=Side;
                Add(JointTerminalEntry(Landing,Port));
            }
        }
    }
    Choices.StableSort([](const FJointTerminal& A,const FJointTerminal& B){return A.Score<B.Score;});
    if(Choices.Num()>128)Choices.SetNum(128);
    return Choices;
}

bool CloseJointRoute(const FJointRoute& Candidate,FSocket RouteExit,const FSocket& Top,const FString& Route)
{
    const double Limit=Candidate.Limit-RouteExit.ReservedLead-Top.ReservedLead;
    if(Limit<0||JointGapCost(Candidate,Top)==DBL_MAX)return false;
    const int32 Before=Pieces.Num(),Available=CompactBudget;
    if(Available<=0)return false;
    const int32 Quota=FMath::Min(Available,1200);CompactBudget=Quota;
    const bool Joined=RouteTo(RouteExit,Top,Route+TEXT("_Closure"),Limit,Limit,950);
    CompactBudget=Available-(Quota-FMath::Max(0,CompactBudget));
    int32 Turns=Candidate.ExitTurns;
    for(int32 I=Before;I<Pieces.Num();++I)if(Pieces[I].Module==Elbow)++Turns;
    if(!Joined||Turns>ThemeBridgeMaxTurns)
    {if(bLayoutProbe)++ProbeRejects.FindOrAdd(TEXT("joint/closure_failed"));Pieces.SetNum(Before);return false;}
    for(int32 I=Before;I<Pieces.Num();++I)Pieces[I].bThemeBridge=true;
    return true;
}

bool FitJointRoutes(const TArray<FJointRoute> (&Routes)[3],const FJointTerminal& Terminal,
                    const TArray<FSocket>& Tops,int32 PrefixCount,const FSocket& Start,int32& Most)
{
    TArray<int32> Candidates[3];
    for(int32 R=0;R<3;++R)
    {
        const auto& Top=Tops[Terminal.Assignment[R]];
        for(int32 I=0;I<Routes[R].Num();++I)if(JointGapCost(Routes[R][I],Top)!=DBL_MAX)Candidates[R].Add(I);
        Candidates[R].StableSort([&](int32 A,int32 B){return JointGapCost(Routes[R][A],Top)<JointGapCost(Routes[R][B],Top);});
        if(Candidates[R].IsEmpty())return false;
        if(Candidates[R].Num()>16)Candidates[R].SetNum(16);
    }
    TArray<int32> Order{0,1,2};
    Order.StableSort([&](int32 A,int32 B){return Candidates[A].Num()<Candidates[B].Num();});
    TFunction<bool(int32)> Search=[&](int32 Depth)
    {
        if(!CanSearch()||CompactBudget<=0)return false;
        Most=FMath::Max(Most,Depth);
        if(Depth==3)
        {
            CompactFailure.Empty();
            return CompleteSocketGraph(Start)&&FinalizeMissionLayout(Start);
        }
        const int32 R=Order[Depth],Before=Pieces.Num();
        for(int32 I:Candidates[R])
        {
            Pieces.SetNum(Before);
            if(!CanSearch()||CompactBudget<=0)break;
            const auto& Candidate=Routes[R][I];bool Fits=true;
            for(int32 P=PrefixCount;P<Candidate.Layout.Num();++P)
            {
                const auto& Item=Candidate.Layout[P];
                if(--CompactBudget<0||!Place(Item.Module,Item.Transform,Item.Route,-2,-2,{}, {},-2,Item.ActivePorts))
                {if(bLayoutProbe)++ProbeRejects.FindOrAdd(TEXT("joint/route_overlap"));Fits=false;break;}
                Pieces.Last()=Item;
            }
            if(!Fits)continue;
            FSocket RouteExit=Candidate.End;RouteExit.Owner+=Before-PrefixCount;
            if(!CloseJointRoute(Candidate,RouteExit,Tops[Terminal.Assignment[R]],FString::Printf(TEXT("Route%d"),R+1)))continue;
            if(Search(Depth+1))return true;
        }
        Pieces.SetNum(Before);return false;
    };
    return Search(0);
}

bool BuildJointFacility(int32 Seed,const FSocket& Start)
{
    constexpr int32 Profiles=42;
    int32 ReadyProfiles=0,TerminalTrials=0,Most=0;
    FString FinalReject;
    for(int32 Attempt=0;Attempt<Profiles&&CanSearch();++Attempt)
    {
        NoteSearch(Attempt+1,Profiles);
        Pieces.Reset();Counts=TopologyCounts;TerminalWalkLengths.Reset();
        Random.Initialize(int32(uint32(Seed)+uint32(Attempt)*7919u));
        CompactBudget=40000;SearchBudget=2500;
        bThemeBridgeSearch=true;bCompactLaneHint=false;bForwardTerminalHint=false;
        bExtendedSpineHint=true;SpineLinkLimit=ShortLinkLimit;
        if(!SelectFacilityArrangement(Attempt%6))return false;
        // Sample all authored heights and both side assignments. A 16.2 m
        // return ramp leaves only ~6 m of the join for planar alignment.
        // Lower profiles can use more of the same budget; collision still
        // decides whether their room volumes can coexist.
        static constexpr double Rises[]={1620.,-1620.,1080.,-1080.,540.,-540.,0.};
        const double Rise=Rises[(Attempt/6+Attempt%6)%UE_ARRAY_COUNT(Rises)];
        ThemeFloorZ=Start.P.Z;ThemeCoreLevels.Reset();
        ThemeCoreLevels.Add(TEXT("Route1"),0.);
        ThemeCoreLevels.Add(TEXT("Route2"),Rise);
        ThemeCoreLevels.Add(TEXT("Route3"),-Rise);
        TArray<FSocket> Leads;
        if(!BuildMissionPrefix(Start,Leads,Attempt))continue;
        CompactLeads=Leads;
        const auto Prefix=Pieces;
        TArray<double> Spans;
        for(int32 R=1;R<=3;++R)Spans.Add(ThemeSpanRange(FString::Printf(TEXT("Route%d"),R),0,6).X);
        Spans.Sort();
        const double GuideDistance=Spans[1]*(Attempt<21?.65:.9);
        FSocket Guide{Leads[0].P+LaneForward*GuideDistance,LaneForward,-2,300,280};
        const auto GuideTops=JointTerminalTops(Guide);
        TArray<FJointRoute> Routes[3];bool Ready=true;
        for(int32 R=0;R<3;++R)
        {
            Pieces=Prefix;
            const int32 Available=CompactBudget,Quota=FMath::Min(Available,8500);
            CompactBudget=Quota;
            const bool Grew=GrowJointRoute(Leads[R],GuideTops[R],FString::Printf(TEXT("Route%d"),R+1),Routes[R]);
            CompactBudget=Available-(Quota-FMath::Max(0,CompactBudget));
            if(!Grew)
            {
                if(bLayoutProbe)++ProbeRejects.FindOrAdd(FString::Printf(TEXT("joint/route%d_incomplete"),R+1));
                Ready=false;break;
            }
        }
        Pieces=Prefix;
        if(!Ready)continue;
        ++ReadyProfiles;
        const auto Choices=JointTerminalChoices(Routes);
        if(bLayoutProbe&&Choices.IsEmpty())++ProbeRejects.FindOrAdd(TEXT("joint/no_common_terminal"));
        for(const auto& Choice:Choices)
        {
            if(!CanSearch()||CompactBudget<=0)break;
            Pieces=Prefix;TArray<FSocket> Tops;
            if(!ReserveCompactTerminal(Choice.Entry,Tops))
            {if(bLayoutProbe)++ProbeRejects.FindOrAdd(TEXT("joint/terminal_overlap"));continue;}
            ++TerminalTrials;
            if(FitJointRoutes(Routes,Choice,Tops,Prefix.Num(),Start,Most))
            {CompactFailure.Empty();return true;}
            if(!CompactFailure.IsEmpty())FinalReject=CompactFailure;
        }
    }
    bJointRouteCandidates=false;
    CompactFailure=FString::Printf(TEXT("三路联合布局未完成；三路候选齐备=%d，共用终点候选=%d，最多接通路线=%d；%s保留原场景"),
        ReadyProfiles,TerminalTrials,Most,FinalReject.IsEmpty()?TEXT(""):*(FinalReject+TEXT("；")));
    return false;
}
