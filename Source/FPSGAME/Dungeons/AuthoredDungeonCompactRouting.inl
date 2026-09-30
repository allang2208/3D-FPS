// Pure-data terminal placement. No actors/assets are accessed by the layout worker.
bool bCompactBoss=false;
int32 StairDrop=-1;
double BossDepth=1080,TerminalWalkLimit=6500;
int32 CompactBudget=0;
double SpineLinkLimit=ShortLinkLimit;
bool bCompactLaneHint=true,bForwardTerminalHint=true;
bool bExtendedSpineHint=false;
TArray<double> TerminalWalkLengths;
TArray<FSocket> CompactLeads;
FString CompactFailure;
int32 LastBridgeDepth=0;
double LastBridgeDistance=0;
bool bLayoutProbe=false;
int32 ProbeDepth=-1;
TArray<FPlaced> ProbePieces;
FSocket ProbeLead,ProbeTop;
FString ProbeRoute;
FVector LaneCenter=FVector::ZeroVector,LaneForward=FVector::ForwardVector,LaneRight=FVector::RightVector;
bool InCompactLane(const TArray<FBox>& Cells,const FString& Route)const
{
    if(!bCompactLaneHint)return true;
    const int32 Lane=Route.StartsWith(TEXT("Route1"))?0:Route.StartsWith(TEXT("Route2"))?-1:Route.StartsWith(TEXT("Route3"))?1:2;
    if(Lane==2)return true;
    for(const FBox& Cell:Cells)for(double X:{Cell.Min.X,Cell.Max.X})for(double Y:{Cell.Min.Y,Cell.Max.Y})
    {
        const FVector D=FVector(X,Y,LaneCenter.Z)-LaneCenter;
        if(FVector::DotProduct(D,LaneForward)<=400)continue;
        const double Side=FVector::DotProduct(D,LaneRight);
        if(Lane==0){if(FMath::Abs(Side)>2400)return false;}
        else if(Lane<0){if(Side>400)return false;}
        else if(Side<-400)return false;
    }
    return true;
}

bool JoinedWallSeam(int32 Module,const FTransform& Transform,int32 Other,const FBox& Intersection,const TArray<int32>& ActivePorts)const
{
    // A connected wall face may share its thickness, never an entire owner's volume.
    for(int32 Port=0;Port<Modules[Module].Ports.Num();++Port)if(ActivePorts.IsEmpty()||ActivePorts.Contains(Port))for(int32 J:OpenPorts(Other))
    {
        const FPort& P=Modules[Module].Ports[Port];
        const FSocket S=Socket(Other,J);const FVector At=Transform.TransformPosition(P.P);
        const FVector N=Transform.TransformVectorNoScale(P.N);
        if(!At.Equals(S.P,1)||FVector::DotProduct(N,S.N)>-.999)continue;
        if(FMath::Abs(P.Width-S.Width)>=1||FMath::Abs(P.Height-S.Height)>=1)continue;
        const int32 Axis=FMath::Abs(N.X)>.5?0:1;
        const int32 SideAxis=1-Axis;
        const double JoinDepth=Module==Treasure||Pieces[Other].Module==Treasure?45.:25.;
        // Occupancy cells include room height (and the full stair drop), so Z is
        // verified by the matched floor datum rather than clipped to lintel height.
        const double HalfWidth=P.Width*.5+30.;
        if(Intersection.Min[Axis]>=At[Axis]-JoinDepth&&Intersection.Max[Axis]<=At[Axis]+JoinDepth&&
           Intersection.Min[SideAxis]>=At[SideAxis]-HalfWidth&&Intersection.Max[SideAxis]<=At[SideAxis]+HalfWidth)return true;
    }
    return false;
}

double AuthoredWalk(int32 Module)const
{
    const TArray<TSharedPtr<FJsonValue>>* Points=nullptr;
    if(!Modules[Module].Data->TryGetArrayField(TEXT("walk_polyline"),Points))return -1;
    double Length=0;FVector Previous=FVector::ZeroVector;
    for(int32 I=0;I<Points->Num();++I)
    {
        const auto& P=(*Points)[I]->AsArray();const FVector At(P[0]->AsNumber(),P[1]->AsNumber(),P[2]->AsNumber());
        if(I)Length+=(At-Previous).Size();Previous=At;
    }
    return Length;
}

bool ReserveCompactTerminal(FSocket Entry,TArray<FSocket>& Tops)
{
    Entry.P.Z-=BossDepth;
    if(!Place(BossConfluence,Fit(BossConfluence,0,Entry),TEXT("BossConfluence")))return false;
    const int32 Hub=Pieces.Num()-1;
    FSocket Door=Socket(Hub,1);
    if(!Place(BossApproach,Fit(BossApproach,0,Door),TEXT("BossApproach"),-2,Hub))return false;
    Door=Socket(Pieces.Num()-1,1);
    if(!Place(BossRoom,Fit(BossRoom,0,Door),TEXT("BossTerminal"),-2,Door.Owner))return false;
    const double StairLength=AuthoredWalk(StairDrop);
    if(StairLength<=0)return false;
    Tops.Reset();TerminalWalkLengths.Reset();
    for(int32 Port:{0,2,3})
    {
        FSocket S=Socket(Hub,Port);const FVector At=S.P;
        if(!Corridor(1,S,TEXT("BossLowerLink"),Threshold))return false;
        const double LowerLength=(S.P-At).Size();
        if(!Place(StairDrop,Fit(StairDrop,1,S),TEXT("BossDescent"),-2,S.Owner))return false;
        const FSocket Top=Socket(Pieces.Num()-1,0);
        if(FMath::Abs(Top.P.Z-(Entry.P.Z+BossDepth))>1)return false;
        Tops.Add(Top);
        // Junction's empty central crossing is authored as two perpendicular axes.
        const FVector Center=Pieces[Hub].Transform.TransformPosition(FVector(0,-600,0));
        const double HallWalk=(At-Center).Size()+(Socket(Hub,1).P-Center).Size();
        const double Approach=(Modules[BossApproach].Ports[0].P-Modules[BossApproach].Ports[1].P).Size();
        const double UpperLength=(Modules[Threshold].Ports[0].P-Modules[Threshold].Ports[1].P).Size();
        const double Total=StairLength+LowerLength+HallWalk+Approach+UpperLength;
        if(Total>TerminalWalkLimit||LowerLength+HallWalk+Approach+UpperLength>2800)return false;
        TerminalWalkLengths.Add(Total);
    }
    return true;
}

struct FCompactBeam {TArray<FPlaced> Layout;FSocket End;double Score=0;double JoinCost=0;};

bool GrowCompactRooms(int32 Count,FSocket Start,const FSocket& Goal,const FString& Route,
                      TArray<FCompactBeam>& Beam,bool AnchorTerminal=false,TFunction<bool()> Complete={})
{
    LastBridgeDepth=0;LastBridgeDistance=(Start.P-Goal.P).Size();
    const TArray<FPlaced> Base=Pieces;
    Beam.Reset();Beam.Add({Pieces,Start,0,0});
    double MaxRoomSpan=0.,MinRoomSpan=DBL_MAX;
    for(int32 M:Combat)if(RoomAllowed(M,Route))for(const auto& Pair:Modules[M].PortPairs)
    {
        MaxRoomSpan=FMath::Max(MaxRoomSpan,(Modules[M].Ports[Pair.X].P-Modules[M].Ports[Pair.Y].P).Size());
        MinRoomSpan=FMath::Min(MinRoomSpan,(Modules[M].Ports[Pair.X].P-Modules[M].Ports[Pair.Y].P).Size());
    }
    for(int32 Depth=0;Depth<Count;++Depth)
    {
        if(!CanSearch()){Pieces=Base;return false;}
        TArray<FCompactBeam> Next;
        // A beam layer must not spend the entire branch budget before the next
        // room is considered. Allocate work across states AND remaining depths.
        // Interior/port variants made the former exhaustive 24-state expansion
        // exhaust every attempt at depth 2, discarding already valid successors.
        const int32 StateLimit=FMath::Max(1,FMath::Min(AnchorTerminal?128:256,
            CompactBudget/FMath::Max(1,(Count-Depth)*Beam.Num())));
        for(const FCompactBeam& State:Beam)
        {
            const int32 StateStartBudget=CompactBudget;
            Pieces=State.Layout;
            const auto Choices=RoomChoices(Route);
            TMap<FString,double> FamilyJitter;
            for(int32 M:Combat)if(RoomAllowed(M,Route)&&!FamilyJitter.Contains(Modules[M].Family))FamilyJitter.Add(Modules[M].Family,Random.FRand()*180.);
            int32 ChoiceRank=0;
            auto Links=RoomLinks(State.End);
            if(AnchorTerminal)Links.RemoveAll([&](const FShortLink& Link){return Link.Length+State.End.ReservedLead>SpineLinkLimit+.1;});
            const int32 Remaining=Count-Depth-1;
            for(const auto& Choice:Choices)
            {
                if(StateStartBudget-CompactBudget>=StateLimit)break;
                Pieces=State.Layout;
                ++ChoiceRank;
                // Reserve trials for every room/door choice. A blocked first
                // choice must not consume the whole state's placement budget.
                const int32 ChoiceStartBudget=CompactBudget;
                const int32 ChoiceLimit=FMath::Max(1,
                    (StateLimit-(StateStartBudget-CompactBudget))/FMath::Max(1,Choices.Num()-ChoiceRank+1));
                auto Ranked=Links;
                if(Remaining==0&&!AnchorTerminal)
                {
                    AddTargetRoomLinks(Ranked,Choice.Key,Choice.Value,State.End,Goal,Choice.Exit);
                    // Reject impossible last-room closures before they consume
                    // placement budget or displace a joinable beam candidate.
                    Ranked.RemoveAll([&](const FShortLink& Link)
                    {
                        const FTransform T=Fit(Choice.Key,Choice.Value,Link.End);
                        const auto& P=Modules[Choice.Key].Ports[Choice.Exit];
                        const FVector N=T.TransformVectorNoScale(P.N);
                        const FSocket Out{T.TransformPosition(P.P)+N*ExitLeadLength,N,-2,P.Width,P.Height,ExitLeadLength};
                        return !(Out.P.Equals(Goal.P,.1)&&FVector::DotProduct(Out.N,Goal.N)<-.999)&&LinksBetween(Out,Goal).IsEmpty();
                    });
                }
                Ranked.StableSort([&](const FShortLink& A,const FShortLink& B)
                {
                    if(AnchorTerminal)return LinkChoiceCost(A,State.End,Route)<LinkChoiceCost(B,State.End,Route);
                    return LinkGoalCost(A,Choice.Key,Choice.Value,Goal,Remaining,Choice.Exit)-LinkCost(A)+LinkChoiceCost(A,State.End,Route)*.25<
                           LinkGoalCost(B,Choice.Key,Choice.Value,Goal,Remaining,Choice.Exit)-LinkCost(B)+LinkChoiceCost(B,State.End,Route)*.25;
                });
                int32 Accepted=0;
                for(const auto& Link:Ranked)
                {
                    if(StateStartBudget-CompactBudget>=StateLimit||ChoiceStartBudget-CompactBudget>=ChoiceLimit)break;
                    if(--CompactBudget<0||!CanSearch()){Pieces=Base;return false;}
                    const FTransform Candidate=Fit(Choice.Key,Choice.Value,Link.End);
                    const auto& ExitPort=Modules[Choice.Key].Ports[Choice.Exit];
                    const FVector ExitNormal=Candidate.TransformVectorNoScale(ExitPort.N);
                    const double SpineFacing=FVector::DotProduct(ExitNormal,LaneForward);
                    // Intermediate rooms may fold the spine back within its
                    // collision-checked lane. Forbidding a backwards exit made
                    // the terminal too distant for legitimate short side routes.
                    // Early attempts keep a forward terminal; later attempts
                    // may rotate the same rigid terminal with the final exit.
                    if(AnchorTerminal&&Remaining==0&&bForwardTerminalHint&&SpineFacing<.999)continue;
                    if(!AnchorTerminal)
                    {
                        const FVector ExitPosition=Candidate.TransformPosition(ExitPort.P)+ExitNormal*ExitLeadLength;
                        // Optimistic upper reach, never a relaxed collision/length rule.
                        if((ExitPosition-Goal.P).Size()>Remaining*(MaxRoomSpan+ShortLinkLimit)+ShortLinkLimit+.1)continue;
                    }
                    Pieces=State.Layout;FSocket S;
                    const double Repetition=RoomRepetitionCost(Choice.Key,Route);
                    const double CandidateJoinCost=LinkChoiceCost(Link,State.End,Route);
                    if(!AttachRoom(Choice.Key,Choice.Value,State.End,Link,Route,S,{},{},Choice.Exit))continue;
                    const double Distance=(S.P-Goal.P).Size();
                    const double Facing=Remaining==0?300*(1+FVector::DotProduct(S.N,Goal.N)):0;
                    // Accumulate connector cost across the branch, rather than
                    // making every locally attractive detour free at the next depth.
                    const double JoinCost=State.JoinCost+CandidateJoinCost;
                    // The middle branch anchors all three stairs. Prefer a
                    // compact forward span: the outer branches must also pay
                    // for the lateral approach and the confluence's offset.
                    const double Forward=FVector::DotProduct(S.P-LaneCenter,LaneForward);
                    const double SpinePosition=bExtendedSpineHint?
                        FMath::Abs(Forward-(Depth+1)*(MinRoomSpan+PreferredLinkLength*.5)):
                        FMath::Max(0.,Forward)*2.;
                    const double PositionCost=AnchorTerminal?
                        FMath::Abs(FVector::DotProduct(S.P-LaneCenter,LaneRight))*(bCompactLaneHint?1.2:.1)+
                            SpinePosition:
                        Distance+Facing;
                    const double VarietyWeight=AnchorTerminal?1.:.15;
                    double Score=PositionCost+(Repetition+FamilyJitter[Modules[Choice.Key].Family])*VarietyWeight+ChoiceRank*.25+JoinCost*(AnchorTerminal?1.:.25);
                    if(Remaining==0&&!AnchorTerminal)
                    {
                        // A close-looking exit is not necessarily joinable with
                        // real 4 m elbows. Close it before pruning the beam.
                        if(!ShortRouteTo(S,Goal,Route+TEXT("_Closure")))continue;
                        // A sibling route can reject this complete chain too,
                        // not only its reserved end room or solve direction.
                        if(Complete&&!Complete())continue;
                        TArray<FCompactBeam> Completed;Completed.Add({Pieces,S,Score,JoinCost});
                        Beam=MoveTemp(Completed);Pieces=Base;LastBridgeDepth=Count;LastBridgeDistance=0;return true;
                    }
                    if(AnchorTerminal&&Remaining==0)
                    {
                        // The stairs and boss hub must fit before the beam drops
                        // alternatives. A short spine can overlap its own terminal.
                        const int32 BeforeTerminal=Pieces.Num();TArray<FSocket> Tops;
                        const bool TerminalFits=AnchorCompactTerminal(S,Tops);
                        Pieces.SetNum(BeforeTerminal);TerminalWalkLengths.Reset();
                        if(!TerminalFits)continue;
                        // Rank the whole terminal by its hardest remaining
                        // branch, not just the middle exit's forward distance.
                        // A compact sideways spine can strand the opposite side.
                        double Reach=0;
                        for(int32 I=1;I<3;++I)Reach=FMath::Max(Reach,(Tops[I].P-CompactLeads[I].P).Size()/Counts[I+1]);
                        const double ReachCost=bExtendedSpineHint?FMath::Abs(Reach-(MinRoomSpan+PreferredLinkLength)):Reach;
                        Score=ReachCost*4.+JoinCost*.15+(Repetition+FamilyJitter[Modules[Choice.Key].Family])*.15;
                    }
                    Next.Add({Pieces,S,Score,JoinCost});
                    if(++Accepted==3)break;
                }
            }
        }
        if(Next.IsEmpty()){Pieces=Base;return false;}
        LastBridgeDepth=Depth+1;
        LastBridgeDistance=DBL_MAX;
        for(const auto& Candidate:Next)LastBridgeDistance=FMath::Min(LastBridgeDistance,(Candidate.End.P-Goal.P).Size());
        Next.StableSort([](const FCompactBeam& A,const FCompactBeam& B){return A.Score<B.Score;});
        // Keep different positions/headings, rather than sixteen nearly identical rooms.
        Beam.Reset();TSet<FIntVector> Buckets;
        for(FCompactBeam& Candidate:Next)
        {
            const FIntVector Key(FMath::RoundToInt(Candidate.End.P.X/350.),FMath::RoundToInt(Candidate.End.P.Y/350.),
                                 FMath::RoundToInt(Candidate.End.N.Rotation().Yaw/90.));
            if(Buckets.Contains(Key))continue;
            // The last room has an exact two-sided solve. Preserve more of its
            // potential starting sockets instead of pruning them by distance.
            const int32 BeamLimit=!AnchorTerminal&&Depth+2==Count?128:24;
            Buckets.Add(Key);Beam.Add(MoveTemp(Candidate));if(Beam.Num()==BeamLimit)break;
        }
    }
    Pieces=Base;return !Beam.IsEmpty();
}

bool BridgeRooms(int32 Count,const FSocket& Start,const FSocket& Goal,const FString& Route,TFunction<bool()> Complete={})
{
    if(Count==0)return ShortRouteTo(Start,Goal,Route+TEXT("_Closure"))&&(!Complete||Complete());
    TArray<FCompactBeam> Beam;
    if(!GrowCompactRooms(Count,Start,Goal,Route,Beam,false,Complete))return false;
    Pieces=MoveTemp(Beam[0].Layout);return true;
}

TArray<FCompactBeam> CompactEndRooms(const FSocket& Top,const FSocket& Lead,const FString& Route,int32 Remaining)
{
    const TArray<FPlaced> Base=Pieces;
    const auto Tails=RoomChoices(Route);
    TMap<FString,double> FamilyJitter;
    for(int32 M:Combat)if(RoomAllowed(M,Route)&&!FamilyJitter.Contains(Modules[M].Family))FamilyJitter.Add(Modules[M].Family,Random.FRand()*900.);
    TArray<FCompactBeam> Options;
    double RoomSpan=DBL_MAX;
    for(int32 M:Combat)if(RoomAllowed(M,Route))RoomSpan=FMath::Min(RoomSpan,(Modules[M].Ports[0].P-Modules[M].Ports[1].P).Size());
    auto Links=RoomLinks(Top);
    // The last room-to-stair sleeve is part of the existing terminal walking
    // budget (80 cm). Flexibility belongs upstream, not in a longer boss lead.
    if(Pieces.IsValidIndex(Top.Owner)&&Pieces[Top.Owner].Module==StairDrop)
        Links.RemoveAll([](const FShortLink& Link){return Link.Turns!=0||!FMath::IsNearlyEqual(Link.Length,ExitLeadLength,.1);});
    for(const auto& Tail:Tails)
    {
        auto Ranked=Links;
        Ranked.StableSort([&](const FShortLink& A,const FShortLink& B)
        {return LinkGoalCost(A,Tail.Key,Tail.Value,Lead,1,Tail.Exit)<LinkGoalCost(B,Tail.Key,Tail.Value,Lead,1,Tail.Exit);});
        int32 Accepted=0;
        for(const auto& Link:Ranked)
        {
            if(--CompactBudget<0||!CanSearch())break;
            Pieces=Base;FSocket Back;
            const double Repetition=RoomRepetitionCost(Tail.Key,Route);
            if(!AttachRoom(Tail.Key,Tail.Value,Top,Link,Route,Back,{},{},Tail.Exit))continue;
            const double Distance=(Back.P-Lead.P).Size();
            const double Crowding=FMath::Max(0.,Remaining*RoomSpan-Distance)*2.;
            Options.Add({Pieces,Back,Distance/(1.+Remaining*.6)+Crowding+Repetition+FamilyJitter[Modules[Tail.Key].Family]+LinkCost(Link,Top.ReservedLead),0});
            if(++Accepted==2)break;
        }
        if(CompactBudget<=0)break;
    }
    Options.StableSort([](const FCompactBeam& A,const FCompactBeam& B){return A.Score<B.Score;});
    Pieces=Base;return Options;
}

bool ConnectCompactBranch(int32 Count,const FSocket& Lead,const FSocket& Top,const FString& Route,
                          TFunction<bool()> Complete={})
{
    LastBridgeDepth=0;LastBridgeDistance=(Lead.P-Top.P).Size();
    const TArray<FPlaced> Base=Pieces;
    auto Ends=CompactEndRooms(Top,Lead,Route,Count-1);
    // Retain end-room alternatives. A failed middle chain must be able to
    // release the endpoint, not repeat the same greedy reservation six times.
    for(auto& EndRoom:Ends)
    {
        if(CompactBudget<=0)break;
        // Either end can be the constrained one. Give both directions a
        // bounded opportunity before moving to another endpoint reservation.
        for(int32 Direction=0;Direction<2;++Direction)
        {
            if(CompactBudget<=0)break;
            Pieces=EndRoom.Layout;
            const int32 Available=CompactBudget,TrialBudget=FMath::Min(Available,5000);
            CompactBudget=TrialBudget;
            int32 ContinuationSpent=0;
            auto Finish=[&]()
            {
                if(!Complete)return true;
                // Sibling search is charged to the shared budget, not the
                // current chain's reserved placement quota. It cannot silently
                // consume every alternative in this beam on the first failure.
                const int32 Left=CompactBudget,Spent=TrialBudget-Left;
                const int32 ContinuationBudget=FMath::Min(Available-Spent-ContinuationSpent,5000);
                if(ContinuationBudget<=0){CompactBudget=0;return false;}
                CompactBudget=ContinuationBudget;
                const bool Done=Complete();
                ContinuationSpent+=ContinuationBudget-FMath::Max(0,CompactBudget);
                CompactBudget=FMath::Min(Left,FMath::Max(0,Available-Spent-ContinuationSpent));
                return Done;
            };
            const bool Connected=Direction==0?BridgeRooms(Count-1,Lead,EndRoom.End,Route,Finish):BridgeRooms(Count-1,EndRoom.End,Lead,Route,Finish);
            CompactBudget=FMath::Max(0,Available-(TrialBudget-FMath::Max(0,CompactBudget))-ContinuationSpent);
            if(Connected)return true;
        }
    }
    Pieces=Base;return false;
}

bool AnchorCompactTerminal(const FSocket& Exit,TArray<FSocket>& Tops)
{
    if(bForwardTerminalHint&&FVector::DotProduct(Exit.N,LaneForward)<.999)return false;
    // Fit the authored descent and lower sleeve to the completed middle route,
    // then derive the confluence entry. No guessed per-room distance is used.
    const FTransform Stair=Fit(StairDrop,0,Exit);
    const FPort& Bottom=Modules[StairDrop].Ports[1];
    const FSocket Lower{Stair.TransformPosition(Bottom.P),Stair.TransformVectorNoScale(Bottom.N),-2,Bottom.Width,Bottom.Height};
    const FTransform Sleeve=Fit(Threshold,0,Lower);
    const FPort& EndPort=Modules[Threshold].Ports[1];
    FSocket Entry{Sleeve.TransformPosition(EndPort.P),Sleeve.TransformVectorNoScale(EndPort.N),-2,EndPort.Width,EndPort.Height};
    Entry.P.Z+=BossDepth;
    const int32 Before=Pieces.Num();
    if(ReserveCompactTerminal(Entry,Tops)&&Tops[0].P.Equals(Exit.P,.1)&&FVector::DotProduct(Tops[0].N,Exit.N)<-.999)return true;
    Pieces.SetNum(Before);Tops.Reset();TerminalWalkLengths.Reset();return false;
}

bool BuildCompact(int32 Seed,const FSocket& Start,double Deadline)
{
    int32 Prefixes=0,Terminals=0,MostBranches=0;
    FString FinalReject;
    // Explore authored prefixes within the same bounded planning window.
    constexpr int32 CompactTries=64;
    NoteSearch(0,CompactTries);
    for(int32 Attempt=0;Attempt<CompactTries;++Attempt)
    {
        if(FPlatformTime::Seconds()>Deadline||!CanSearch())break;
        NoteSearch(Attempt+1,CompactTries);
        Pieces.Reset();Counts.Reset();TerminalWalkLengths.Reset();
        bool LoggedFailure=false;
        Random.Initialize(int32(uint32(Seed)+uint32(Attempt)*7919u));SearchBudget=2500;CompactBudget=40000;
        // Lanes and forward facing are search hints, not geometry contracts.
        // Retain the quick aligned attempt, then permit rigid folded layouts.
        bCompactLaneHint=Attempt==0;bForwardTerminalHint=Attempt<16;
        // Alternate a compact risk spine with the general short-link recipe.
        // A middle route that spends 12 m at each join can place the shared
        // terminal beyond what the shorter outside branches can actually span.
        SpineLinkLimit=Attempt%2==0?PreferredLinkLength:ShortLinkLimit;
        Counts=TopologyCounts;
        // Outer routes also need lateral travel. Keep all three drawn counts,
        // but assign the shortest one to the direct middle route so a five-room
        // spine cannot force a three-room side route to make up missing distance.
        int32 Shortest=1;
        for(int32 I=2;I<4;++I)if(Counts[I]<Counts[Shortest])Shortest=I;
        Counts.Swap(1,Shortest);
        // Long branches need room to fit their drawn room count. Always scoring
        // a terminal by the smallest distance folds a four/five-room spine into
        // the space needed by both side routes. Keep the compact fast attempts,
        // then also seek an extended, collision-checked spine for long routes.
        bExtendedSpineHint=Attempt>=8&&Counts[1]>=4;
        // Authored L-shaped rooms may rotate but cannot mirror. Give both side
        // count assignments the compact/long connector pair without redrawing
        // any count or changing the middle risk route.
        if(bExtendedSpineHint&&(Attempt/2)%2==1)Counts.Swap(2,3);
        // If the fixed assignment keeps failing, let a short outside branch
        // use the longer approach draw. Preserve the exact drawn multiset and
        // total room count; all segments retain their authored min/max limits.
        // The mission graph is rebuilt below, before any rooms are spawned.
        if(Attempt>=16&&Counts[0]>FMath::Max(Counts[2],Counts[3]))
            Counts.Swap(0,2+(Attempt/8)%2);
        TArray<FSocket> Leads;bool Good=true;
        if(!BuildMissionPrefix(Start,Leads,Attempt))continue;
        CompactLeads=Leads;
        ++Prefixes;
        const TArray<FPlaced> Prefix=Pieces;
        // Build every middle-route room first. The former fixed terminal offset
        // plus greedy first/last reservations left 8-16 m for 1-2 entire rooms
        // in seed 231395984. Increasing retries cannot make that space fit.
        TArray<FCompactBeam> Spines;
        if(!GrowCompactRooms(Counts[1],Leads[0],Leads[0],TEXT("Route1"),Spines,true))continue;
        for(auto& Spine:Spines)
        {
            if(CompactBudget<=0)break;
            Pieces=MoveTemp(Spine.Layout);TArray<FSocket> Tops;
            if(!AnchorCompactTerminal(Spine.End,Tops))continue;
            ++Terminals;
            MostBranches=FMath::Max(MostBranches,1);
            const TArray<FPlaced> Terminal=Pieces;
            // Solve the two side routes as one transaction. If the second
            // route fails, release the first and try its other endpoint choices.
            for(int32 Order=0;Order<2;++Order)
            {
                if(CompactBudget<=0)break;
                Pieces=Terminal;
                const int32 First=1+Order,Second=1+(1+Order)%2;
                auto RecordFailure=[&](int32 I)
                {
                    if(bLayoutProbe&&LastBridgeDepth>ProbeDepth)
                    {ProbeDepth=LastBridgeDepth;ProbePieces=Pieces;ProbeLead=Leads[I];ProbeTop=Tops[I];ProbeRoute=FString::Printf(TEXT("Route%d"),I+1);}
                    if(!LoggedFailure)
                    {
                        UE_LOG(LogTemp,Display,TEXT("Compact anchored branch: attempt=%d route=%d rooms=%d depth=%d nearest=%.0f budget=%d start=%s top=%s"),
                            Attempt,I+1,Counts[I+1],LastBridgeDepth,LastBridgeDistance,CompactBudget,
                            *Leads[I].P.ToCompactString(),*Tops[I].P.ToCompactString());
                        LoggedFailure=true;
                    }
                };
                Good=ConnectCompactBranch(Counts[First+1],Leads[First],Tops[First],FString::Printf(TEXT("Route%d"),First+1),[&]()
                {
                    MostBranches=FMath::Max(MostBranches,2);
                    if(!ConnectCompactBranch(Counts[Second+1],Leads[Second],Tops[Second],FString::Printf(TEXT("Route%d"),Second+1)))
                    {RecordFailure(Second);return false;}
                    MostBranches=3;return true;
                });
                if(!Good)RecordFailure(First);
                if(Good)
                {
                    if(CompleteSocketGraph(Start)&&FinalizeMissionLayout(Start)){CompactFailure.Empty();return true;}
                    FinalReject=CompactFailure;
                }
            }
        }
        Pieces=Prefix;
    }
    CompactFailure=FString::Printf(TEXT("地下终点短连接未完成；前段=%d，按中路出口定位终点=%d，最多连接支路=%d；%s保留原场景"),
        Prefixes,Terminals,MostBranches,FinalReject.IsEmpty()?TEXT(""):*(FinalReject+TEXT("；")));return false;
}
