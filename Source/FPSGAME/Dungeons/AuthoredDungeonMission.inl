// Mission rules are selected before embedding. Optional edges have a finite
// candidate set; failed embeddings remain explicitly unrealized in the manifest.
bool bMissionEnabled=false;
int32 ForkLeft=-1,ForkRight=-1,RequestedGrammar=0,ActualGrammar=0,SplitAfter=0;
double CorridorBudget=0,RouteBudget=0,CorridorTotal=0,LongestRouteEstimate=0;
TArray<double> RouteEstimates;
// FixedWalk belongs to authored rooms/hubs and the shared terminal. Only Links
// can grow with the embedding; their allowance comes from the drawn room slots.
struct FMissionRouteLength {double FixedWalk=0,Links=0,LinkLimit=0;};
TArray<FMissionRouteLength> RouteLengthDetails;
struct FMissionEdge {FString From,To,Purpose;bool bOptional=false,bRealized=false;};
TArray<FMissionEdge> MissionEdges;
TMap<FString,int32> MissionRouteStarts;

FString MissionRoom(const FString& Route,int32 Ordinal)const
{return FString::Printf(TEXT("%s.%d"),*Route,Ordinal);}

void ConfigureMission(int32 Seed,const JObject& Catalog)
{
    const JObject* Rules=nullptr;
    bMissionEnabled=Catalog->TryGetObjectField(TEXT("mission_rules"),Rules)&&Rules->IsValid();
    ForkLeft=Find(TEXT("ForkLeft"));ForkRight=Find(TEXT("ForkRight"));
    if(!bMissionEnabled)return;
    FRandomStream Stream(int32(HashCombineFast(uint32(Seed),0x4D495353u)));
    RequestedGrammar=bThemedRoutes?0:Stream.RandRange(0,2);
    if(ForkLeft<0||ForkRight<0)RequestedGrammar=0;
    SplitAfter=Stream.RandRange(1,FMath::Max(1,TopologyCounts[0]-1));
    double PerRoom=900,Fixed=4000;
    (*Rules)->TryGetNumberField(TEXT("corridor_cm_per_room"),PerRoom);
    (*Rules)->TryGetNumberField(TEXT("fixed_corridor_cm"),Fixed);
    RouteBudget=36000;(*Rules)->TryGetNumberField(TEXT("route_estimate_max_cm"),RouteBudget);
    int32 RoomCount=0;for(int32 Count:TopologyCounts)RoomCount+=Count;
    CorridorBudget=FMath::Max(0.,Fixed+PerRoom*RoomCount);
    if(bThemedRoutes)
    {
        // Each core may change floor at its entrance and return at its exit;
        // the final planar closure stays compact. Count real ramp walking length.
        const double ExtraPerRoute=2.*(ThemeRampLinkLimit-ShortLinkLimit)+ThemeBridgeLimit-ShortLinkLimit;
        CorridorBudget+=3.*ExtraPerRoute;
        // The themed route limit is measured per selected room chain below.
        // The legacy scalar limit cannot represent 5-7 rooms of different sizes.
    }
}

void MakeMissionGraph(int32 Grammar)
{
    ActualGrammar=Grammar;MissionEdges.Reset();
    auto Add=[&](FString From,FString To,FString Purpose,bool Optional=false)
    {MissionEdges.Add({From,To,Purpose,Optional,false});};
    FString Previous=TEXT("entry");
    for(int32 I=0;I<Counts[0];++I)
    {
        const FString Id=MissionRoom(TEXT("Approach"),I);Add(Previous,Id,TEXT("approach"));Previous=Id;
        if(Grammar&&I+1==SplitAfter){Add(Previous,TEXT("fork.early"),TEXT("split"));Previous=TEXT("fork.early");}
    }
    Add(Previous,TEXT("fork.late"),TEXT("split"));
    const int32 EarlyRoute=Grammar==1?2:3;
    for(int32 R=1;R<=3;++R)
    {
        const FString Route=FString::Printf(TEXT("Route%d"),R);
        Previous=Grammar&&R==EarlyRoute?TEXT("fork.early"):TEXT("fork.late");
        for(int32 I=0;I<Counts[R];++I)
        {const FString Id=MissionRoom(Route,I);Add(Previous,Id,R==1?TEXT("risk_shortcut"):TEXT("exploration"));Previous=Id;}
        Add(Previous,TEXT("confluence"),TEXT("descent"));
    }
    if(bThemedRoutes)
    {
        Add(TEXT("confluence"),TEXT("archive"),TEXT("shared_archive"));
        Add(TEXT("archive"),TEXT("boss"),TEXT("any_route_clear_then_archive"));
    }
    else Add(TEXT("confluence"),TEXT("boss"),TEXT("boss_approach"));
    Add(TEXT("boss"),TEXT("reward.final"),TEXT("boss_locked_reward"));
    if(bThemedRoutes)return;
    // Only optional edges between ordinary branch rooms: neither entry nor the
    // boss/reward gate can acquire a bypass through a return link.
    for(int32 R=1;R<=3;++R)for(int32 I=0;I<Counts[R];++I)
        for(int32 S=R;S<=3;++S)for(int32 J=0;J<Counts[S];++J)
        {
            if(R==S&&(J-I<2||J-I>4))continue;
            if(R!=S&&FMath::Abs(I-J)>1)continue;
            Add(MissionRoom(FString::Printf(TEXT("Route%d"),R),I),
                MissionRoom(FString::Printf(TEXT("Route%d"),S),J),R==S?TEXT("return"):TEXT("cross_route"),true);
        }
}

bool BuildMissionPrefix(const FSocket& Start,TArray<FSocket>& Leads,int32 Attempt)
{
    // Fixed fallback order is part of the recipe. Never retain a partially
    // embedded graph or silently change the underground terminal contract.
    const int32 Grammar=bMissionEnabled&&Attempt<8?RequestedGrammar:0;
    if(bMissionEnabled)MakeMissionGraph(Grammar);else MissionEdges.Reset();
    MissionRouteStarts.Reset();
    FSocket S=Start,Early;int32 Hub=INDEX_NONE;
    if(Grammar)
    {
        if(!Chain(SplitAfter,S,TEXT("Approach"))||!Corridor(1,S,TEXT("Approach")))return false;
        const int32 First=Grammar==1?ForkLeft:ForkRight,Last=Grammar==1?ForkRight:ForkLeft;
        if(!Place(First,Fit(First,0,S),TEXT("JunctionEarly"),-2,S.Owner))return false;
        const int32 EarlyHub=Pieces.Num()-1;Pieces[EarlyHub].MissionId=TEXT("fork.early");
        Early=Socket(EarlyHub,2);S=Socket(EarlyHub,1);const FVector Heading=S.N;
        if(!Chain(Counts[0]-SplitAfter,S,TEXT("Approach"))||FVector::DotProduct(S.N,Heading)<.999||
           !Corridor(1,S,TEXT("Approach")))return false;
        if(!Place(Last,Fit(Last,0,S),TEXT("Junction"),-2,S.Owner))return false;
        Hub=Pieces.Num()-1;
        Leads={Socket(Hub,1),Grammar==1?Early:Socket(Hub,2),Grammar==1?Socket(Hub,2):Early};
    }
    else
    {
        if(!Chain(Counts[0],S,TEXT("Approach"))||!Corridor(1,S,TEXT("Approach")))return false;
        if(!Place(Junction,Fit(Junction,0,S),TEXT("Junction"),-2,S.Owner))return false;
        Hub=Pieces.Num()-1;Leads={Socket(Hub,1),Socket(Hub,2),Socket(Hub,3)};
    }
    Pieces[Hub].MissionId=TEXT("fork.late");
    LaneCenter=Pieces[Hub].Bounds.GetCenter();LaneForward=Socket(Hub,1).N;LaneRight=FVector(-LaneForward.Y,LaneForward.X,0);
    for(int32 I=0;I<Leads.Num();++I)
    {
        const FString Route=FString::Printf(TEXT("Route%d"),I+1);
        const FVector Door=Leads[I].P;
        // Reserve the authored 80 cm door collar on every compact branch.
        // A forced 4 m side lead spends one third of the short-link allowance
        // before the solver can turn, starving legitimate three-room routes.
        if(!Corridor(1,Leads[I],Route,bCompactBoss?Threshold:Transit))return false;
        // The reserved junction lead belongs to the same doorway-to-room link.
        // Without carrying it into either direction's closure solve, a 4 m lead
        // plus a nominally legal 12 m link silently becomes a 16 m corridor.
        Leads[I].ReservedLead=(Leads[I].P-Door).Size();
        MissionRouteStarts.Add(Route,Leads[I].Owner);
    }
    return true;
}

void BindMainMissions(const FSocket& Start)
{
    const auto Graph=PieceGraph(false);
    for(const FString Route:{FString(TEXT("Approach")),FString(TEXT("Route1")),FString(TEXT("Route2")),FString(TEXT("Route3"))})
    {
        // Do not discover a long branch backwards through the shorter branch's
        // confluence. Identity follows the authored entrance of each mission chain.
        const int32 Root=Route==TEXT("Approach")?EntryPiece(Start):MissionRouteStarts.FindRef(Route);
        TArray<int32> Depth;Depth.Init(MAX_int32,Pieces.Num());TArray<int32> Queue;
        if(Pieces.IsValidIndex(Root)){Depth[Root]=0;Queue.Add(Root);}
        for(int32 Head=0;Head<Queue.Num();++Head)for(int32 Next:Graph[Queue[Head]])
            if((Pieces[Next].Route==Route||Pieces[Next].Route==Route+TEXT("_Closure")||
                (Route==TEXT("Approach")&&Pieces[Next].MissionId==TEXT("fork.early")))&&Depth[Next]==MAX_int32)
            {Depth[Next]=Depth[Queue[Head]]+1;Queue.Add(Next);}
        TArray<int32> Rooms;
        for(int32 I=0;I<Pieces.Num();++I)if(Pieces[I].Route==Route&&Combat.Contains(Pieces[I].Module))Rooms.Add(I);
        Rooms.StableSort([&](int32 A,int32 B){return Depth[A]!=Depth[B]?Depth[A]<Depth[B]:A<B;});
        for(int32 I=0;I<Rooms.Num();++I)
        {
            auto& P=Pieces[Rooms[I]];P.MissionId=MissionRoom(Route,I);
            const bool EarlyBranch=ActualGrammar&&(Route==(ActualGrammar==1?TEXT("Route2"):TEXT("Route3")));
            // Crossing the early fork advances the approach stage as well.
            // Otherwise its following room shares the fork's depth and lags the
            // branch stages by one despite being physically farther from entry.
            P.MissionDepth=I+1+(Route==TEXT("Approach")?(ActualGrammar&&I>=SplitAfter?1:0):EarlyBranch?SplitAfter+1:Counts[0]+(ActualGrammar?2:1));
            P.EncounterRole=Route==TEXT("Route1")?TEXT("risk"):Route==TEXT("Approach")?TEXT("approach"):TEXT("exploration");
            P.ThreatBonus=Route==TEXT("Route1")?2:0;P.RewardMultiplier=Route==TEXT("Route1")?1.5:1.;
            if(Route==TEXT("Route1")&&I==Rooms.Num()-1)P.EncounterRole=TEXT("risk_elite");
            Modules[P.Module].Data->TryGetStringField(TEXT("encounter_role"),P.EncounterRole);
        }
    }
    int32 MaxStage=0;for(const auto& P:Pieces)MaxStage=FMath::Max(MaxStage,P.MissionDepth);
    for(auto& P:Pieces)
    {
        if(P.MissionId==TEXT("fork.early"))P.MissionDepth=SplitAfter+1;
        if(P.MissionId==TEXT("fork.late"))P.MissionDepth=Counts[0]+(ActualGrammar?2:1);
        if(P.Module==BossConfluence){P.MissionId=TEXT("confluence");P.MissionDepth=MaxStage+1;}
        if(bThemedRoutes&&P.Module==SharedArchive){P.MissionId=TEXT("archive");P.MissionDepth=MaxStage+2;P.EncounterRole=TEXT("special_combat");}
        if(P.Module==BossRoom){P.MissionId=TEXT("boss");P.MissionDepth=MaxStage+(bThemedRoutes?3:2);}
        if(P.Module==Treasure&&P.Route.StartsWith(TEXT("Boss")))P.MissionId=TEXT("reward.final");
    }
}

bool MissionAllowsLoop(int32 A,int32 B)const
{
    if(!bMissionEnabled)return true;
    for(const auto& E:MissionEdges)if(E.bOptional&&
        ((E.From==Pieces[A].MissionId&&E.To==Pieces[B].MissionId)||(E.From==Pieces[B].MissionId&&E.To==Pieces[A].MissionId)))return true;
    return false;
}

bool MeasureMissionBudget()
{
    CorridorTotal=0;LongestRouteEstimate=0;RouteEstimates.Reset();RouteLengthDetails.Reset();TMap<FString,double> Lengths;
    if(bThemedRoutes)RouteBudget=0;
    TArray<double> PieceLengths;
    for(int32 I=0;I<Pieces.Num();++I)
    {
        const auto& P=Pieces[I];const auto& M=Modules[P.Module];double Length=AuthoredWalk(P.Module);
        const bool Connector=P.Module==Transit||P.Module==Threshold||P.Module==TreasureLink||P.Module==Elbow||P.Module==StairDrop||P.Module==BossApproach||IsThemeRamp(P.Module);
        if(Length<0)
        {
            if(Connector&&M.Ports.Num()==2)Length=P.Module==Elbow?400.:(M.Ports[0].P-M.Ports[1].P).Size();
            else if(Combat.Contains(P.Module)&&P.ActivePorts.Num()==2)
            {
                // Estimate the selected through-route, not the entire shell's
                // width + length (which includes unused wings/closed doorways).
                // This remains a rectilinear estimate, not a navigation distance.
                const FVector Delta=M.Ports[P.ActivePorts[0]].P-M.Ports[P.ActivePorts[1]].P;
                Length=FMath::Abs(Delta.X)+FMath::Abs(Delta.Y)+FMath::Abs(Delta.Z);
            }
            else Length=M.Bounds.GetSize().X+M.Bounds.GetSize().Y;
        }
        Length*=P.Transform.GetScale3D().Y;
        PieceLengths.Add(Length);
        if(Connector)CorridorTotal+=Length;
        Lengths.FindOrAdd(P.Route)+=Length;
    }
    if(bCompactBoss)
    {
        // Trace each mandatory branch through its real sockets. Summing route
        // labels charged the early fork for the later approach rooms and charged
        // the upper stair sleeve twice (once in RouteN, once in terminal_walk).
        // Optional loops/treasures cannot shorten this design progression path.
        const auto Graph=PieceGraph(false);
        int32 Entry=INDEX_NONE,Boss=INDEX_NONE;
        for(int32 I=0;I<Pieces.Num();++I)
        {
            if(Pieces[I].Route==TEXT("Approach")&&Entry==INDEX_NONE)Entry=I;
            if(Pieces[I].Module==BossRoom)Boss=I;
        }
        if(Entry==INDEX_NONE||Boss==INDEX_NONE)return false;
        auto SharedDoor=[&](int32 A,int32 B,FVector& Position)
        {
            for(int32 AP:OpenPorts(A))for(int32 BP:OpenPorts(B))
            {
                const auto AS=Socket(A,AP),BS=Socket(B,BP);
                if(AS.P.Equals(BS.P,1.)&&FVector::DotProduct(AS.N,BS.N)<-.999&&
                   FMath::Abs(AS.Width-BS.Width)<1.&&FMath::Abs(AS.Height-BS.Height)<1.)
                {Position=AS.P;return true;}
            }
            return false;
        };
        bool RoutesWithinBudget=true;
        for(int32 R=1;R<=3;++R)
        {
            const FString Route=FString::Printf(TEXT("Route%d"),R);
            auto Allowed=[&](int32 I)
            {
                const auto& Tag=Pieces[I].Route;
                return Tag==TEXT("Approach")||Tag==TEXT("Junction")||Tag==TEXT("JunctionEarly")||
                    Tag==Route||Tag==Route+TEXT("_Closure")||Tag==Route+TEXT("_Confluence")||
                    Tag==TEXT("BossDescent")||Tag==TEXT("BossLowerLink")||Tag==TEXT("BossConfluence")||
                    Tag==TEXT("BossApproach")||Tag==TEXT("BossTerminal")||Tag==TEXT("Archive")||Tag==TEXT("ArchiveLink");
            };
            TArray<int32> Parent;Parent.Init(INDEX_NONE,Pieces.Num());Parent[Entry]=Entry;
            TArray<int32> Queue{Entry};
            for(int32 Head=0;Head<Queue.Num()&&Parent[Boss]==INDEX_NONE;++Head)
                for(int32 Next:Graph[Queue[Head]])if(Parent[Next]==INDEX_NONE&&Allowed(Next))
                {Parent[Next]=Queue[Head];Queue.Add(Next);}
            if(Parent[Boss]==INDEX_NONE)return false;
            TArray<int32> Path;
            for(int32 At=Boss;;At=Parent[At]){Path.Add(At);if(At==Entry)break;}
            double Walk=0;
            FMissionRouteLength Detail;
            for(int32 I=0;I<Path.Num();++I)
            {
                const int32 At=Path[I],Module=Pieces[At].Module;
                double Length=PieceLengths[At];
                if((Module==Junction||Module==ForkLeft||Module==ForkRight||Module==BossConfluence)&&
                   I>0&&I+1<Path.Num())
                {
                    FVector In,Out;
                    if(!SharedDoor(At,Path[I-1],In)||!SharedDoor(At,Path[I+1],Out))return false;
                    const FVector Delta=In-Out;
                    Length=FMath::Abs(Delta.X)+FMath::Abs(Delta.Y)+FMath::Abs(Delta.Z);
                }
                Walk+=Length;
                // The descent, boss approach and two shared terminal sleeves
                // are fixed authored geometry, not a solver-created detour.
                const bool VariableLink=(Module==Transit||Module==Threshold||Module==Elbow||IsThemeRamp(Module))&&
                    Pieces[At].Route!=TEXT("BossLowerLink")&&Pieces[At].Route!=TEXT("ArchiveLink");
                if(VariableLink)Detail.Links+=Length;else Detail.FixedWalk+=Length;
            }
            if(bThemedRoutes)
            {
                // Approach: entry -> A rooms -> fork (A+1 joins).
                // Branch: fork -> R rooms -> descent (R+1 joins).
                // Count doorway links, never their tessellated mesh pieces.
                Detail.LinkLimit=(Counts[0]+Counts[R]+2)*ShortLinkLimit;
                if(bThemeBridgeSearch)Detail.LinkLimit+=ThemeBridgeLimit-ShortLinkLimit;
                if(FMath::Abs(ThemeCoreLevels.FindRef(Route))>.1)
                    Detail.LinkLimit+=2.*(ThemeRampLinkLimit-ShortLinkLimit);
                RoutesWithinBudget&=Detail.Links<=Detail.LinkLimit+.1;
                RouteBudget=FMath::Max(RouteBudget,Detail.FixedWalk+Detail.LinkLimit);
            }
            else
            {
                Detail.LinkLimit=RouteBudget-Detail.FixedWalk;
                RoutesWithinBudget&=Walk<=RouteBudget;
            }
            RouteLengthDetails.Add(Detail);
            RouteEstimates.Add(Walk);LongestRouteEstimate=FMath::Max(LongestRouteEstimate,Walk);
        }
        return !bMissionEnabled||(CorridorTotal<=CorridorBudget&&RoutesWithinBudget);
    }
    for(int32 R=1;R<=3;++R)
    {
        double Path=Lengths.FindRef(TEXT("Approach"))+Lengths.FindRef(TEXT("Junction"))+Lengths.FindRef(TEXT("JunctionEarly"));
        const FString Prefix=FString::Printf(TEXT("Route%d"),R);
        for(const auto& Pair:Lengths)if(Pair.Key==Prefix||Pair.Key==Prefix+TEXT("_Confluence")||Pair.Key==Prefix+TEXT("_Closure"))Path+=Pair.Value;
        double Terminal=0;for(double Walk:TerminalWalkLengths)Terminal=FMath::Max(Terminal,Walk);
        Path+=Terminal+Lengths.FindRef(TEXT("BossTerminal"));
        RouteEstimates.Add(Path);
        LongestRouteEstimate=FMath::Max(LongestRouteEstimate,Path);
    }
    return !bMissionEnabled||(CorridorTotal<=CorridorBudget&&LongestRouteEstimate<=RouteBudget);
}

TArray<TSharedPtr<FJsonValue>> MissionRouteLengthsJson()const
{
    TArray<TSharedPtr<FJsonValue>> Result;
    for(int32 I=0;I<RouteLengthDetails.Num();++I)
    {
        const auto& D=RouteLengthDetails[I];auto Value=MakeShared<FJsonObject>();
        Value->SetStringField(TEXT("route"),FString::Printf(TEXT("Route%d"),I+1));
        Value->SetNumberField(TEXT("authored_walk_cm"),D.FixedWalk);
        Value->SetNumberField(TEXT("link_walk_cm"),D.Links);
        Value->SetNumberField(TEXT("link_budget_cm"),D.LinkLimit);
        Value->SetNumberField(TEXT("total_walk_cm"),D.FixedWalk+D.Links);
        Value->SetNumberField(TEXT("total_budget_cm"),D.FixedWalk+D.LinkLimit);
        Result.Add(MakeShared<FJsonValueObject>(Value));
    }
    return Result;
}

bool FinalizeMissionLayout(const FSocket& Start)
{
    if(!bMissionEnabled)return true;
    BindMainMissions(Start);
    if(!ThemeLayoutMatches()){CompactFailure=TEXT("主题房顺序不完整，放弃该方案");return false;}
    const auto PhysicalGraph=PieceGraph(false);
    for(const auto& Edge:MissionEdges)if(!Edge.bOptional)
    {
        if(Edge.To==TEXT("reward.final"))
        {if(!Modules[BossRoom].Data->HasField(TEXT("reward_exit")))return false;continue;}
        int32 From=Edge.From==TEXT("entry")?EntryPiece(Start):INDEX_NONE,To=INDEX_NONE;
        for(int32 I=0;I<Pieces.Num();++I)
        {if(Pieces[I].MissionId==Edge.From)From=I;if(Pieces[I].MissionId==Edge.To)To=I;}
        if(From<0||To<0)return false;
        TSet<int32> Seen{From};TArray<int32> Queue{From};
        for(int32 Head=0;Head<Queue.Num()&&!Seen.Contains(To);++Head)for(int32 Next:PhysicalGraph[Queue[Head]])
            if(!Seen.Contains(Next)&&(Next==To||Pieces[Next].MissionId.IsEmpty())){Seen.Add(Next);Queue.Add(Next);}
        if(!Seen.Contains(To))return false;
    }
    if(!MeasureMissionBudget())
    {
        if(CorridorTotal>CorridorBudget)
            CompactFailure=FString::Printf(TEXT("完整布局通道总量超出预算：%.0f/%.0f cm"),CorridorTotal,CorridorBudget);
        else
        {
            CompactFailure=TEXT("完整布局的入口至首领路径无法计量");
            for(int32 I=0;I<RouteLengthDetails.Num();++I)
            {
                const auto& D=RouteLengthDetails[I];if(D.Links<=D.LinkLimit+.1)continue;
                CompactFailure=FString::Printf(TEXT("路线 %d 连接距离超出预算：%.0f/%.0f cm；房间与终点固定路程 %.0f cm"),
                    I+1,D.Links,D.LinkLimit,D.FixedWalk);break;
            }
        }
        return false;
    }
    const auto Base=Pieces;
    AddRouteLoops(Start);
    if(!MeasureMissionBudget()){Pieces=Base;LoopConnections.Reset();MeasureMissionBudget();}
    for(auto& Edge:MissionEdges)
    {
        Edge.bRealized=!Edge.bOptional;
        if(Edge.bOptional)for(const auto& Loop:LoopConnections)
            if((Edge.From==Pieces[Loop.From].MissionId&&Edge.To==Pieces[Loop.To].MissionId)||
               (Edge.To==Pieces[Loop.From].MissionId&&Edge.From==Pieces[Loop.To].MissionId))Edge.bRealized=true;
    }
    return CompleteSocketGraph(Start);
}

void BindRewardMissions(const FSocket& Start)
{
    if(!bMissionEnabled){MeasureMissionBudget();return;}
    for(int32 I=0;I<Pieces.Num();++I)
    {
        auto& P=Pieces[I];if(P.Module!=Treasure||!P.MissionId.IsEmpty())continue;
        for(int32 Parent=0;Parent<I;++Parent)if(!Pieces[Parent].MissionId.IsEmpty()&&
            P.Route==Pieces[Parent].Route+FString::Printf(TEXT("_Treasure%d"),Parent))
        {P.MissionId=Pieces[Parent].MissionId+TEXT(".treasure");P.RewardMultiplier=Pieces[Parent].RewardMultiplier;P.MissionDepth=Pieces[Parent].MissionDepth+1;break;}
    }
    MeasureMissionBudget();
}
