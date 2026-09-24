// Pure-data terminal placement. No actors/assets are accessed by the layout worker.
bool bCompactBoss=false;
int32 StairDrop=-1;
double BossDepth=1080,TerminalWalkLimit=6500;
int32 CompactBudget=0;
TArray<double> TerminalWalkLengths;
FString CompactFailure;
int32 LastBridgeDepth=0;
double LastBridgeDistance=0;
FVector LaneCenter=FVector::ZeroVector,LaneForward=FVector::ForwardVector,LaneRight=FVector::RightVector;
bool InCompactLane(const TArray<FBox>& Cells,const FString& Route)const
{
    const int32 Lane=Route.StartsWith(TEXT("Route1"))?0:Route.StartsWith(TEXT("Route2"))?-1:Route.StartsWith(TEXT("Route3"))?1:2;
    if(Lane==2)return true;
    for(const FBox& Cell:Cells)for(double X:{Cell.Min.X,Cell.Max.X})for(double Y:{Cell.Min.Y,Cell.Max.Y})
    {
        const FVector D=FVector(X,Y,LaneCenter.Z)-LaneCenter;
        if(FVector::DotProduct(D,LaneForward)<=1200)continue;
        const double Side=FVector::DotProduct(D,LaneRight);
        if(Lane==0?FMath::Abs(Side)>1600:Lane<0?Side>-1600:Side<1600)return false;
    }
    return true;
}

bool JoinedWallSeam(int32 Module,const FTransform& Transform,int32 Other,const FBox& Intersection)const
{
    // A connected wall face may share its thickness, never an entire owner's volume.
    for(const FPort& P:Modules[Module].Ports)for(int32 J=0;J<PortCount(Other);++J)
    {
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
                      TArray<FCompactBeam>& Beam,bool AnchorTerminal=false)
{
    LastBridgeDepth=0;LastBridgeDistance=(Start.P-Goal.P).Size();
    const TArray<FPlaced> Base=Pieces;
    Beam.Reset();Beam.Add({Pieces,Start,0,0});
    for(int32 Depth=0;Depth<Count;++Depth)
    {
        TArray<FCompactBeam> Next;
        for(const FCompactBeam& State:Beam)
        {
            Pieces=State.Layout;
            const auto Choices=RoomChoices(Route);
            TMap<FString,double> FamilyJitter;
            for(int32 M:Combat)if(!FamilyJitter.Contains(Modules[M].Family))FamilyJitter.Add(Modules[M].Family,Random.FRand()*180.);
            int32 ChoiceRank=0;
            const auto Links=RoomLinks(State.End);
            const int32 Remaining=Count-Depth-1;
            for(const auto& Choice:Choices)
            {
                ++ChoiceRank;
                auto Ranked=Links;
                if(Remaining==0&&!AnchorTerminal)AddTargetRoomLinks(Ranked,Choice.Key,Choice.Value,State.End,Goal);
                Ranked.StableSort([&](const FShortLink& A,const FShortLink& B)
                {
                    if(AnchorTerminal)return LinkCost(A,State.End.ReservedLead)<LinkCost(B,State.End.ReservedLead);
                    return LinkGoalCost(A,Choice.Key,Choice.Value,Goal,Remaining)<LinkGoalCost(B,Choice.Key,Choice.Value,Goal,Remaining);
                });
                int32 Accepted=0;
                for(const auto& Link:Ranked)
                {
                    if(--CompactBudget<0){Pieces=Base;return false;}
                    Pieces=State.Layout;FSocket S;
                    const double Repetition=RoomRepetitionCost(Choice.Key,Route);
                    if(!AttachRoom(Choice.Key,Choice.Value,State.End,Link,Route,S))continue;
                    if(AnchorTerminal&&Remaining==0&&FVector::DotProduct(S.N,LaneForward)<.999)continue;
                    const double Distance=(S.P-Goal.P).Size();
                    const double Facing=Remaining==0?300*(1+FVector::DotProduct(S.N,Goal.N)):0;
                    // Accumulate connector cost across the branch, rather than
                    // making every locally attractive detour free at the next depth.
                    const double JoinCost=State.JoinCost+LinkCost(Link,State.End.ReservedLead);
                    // The middle branch is constructed in full before placing
                    // the terminal. It has no estimated endpoint to squeeze into.
                    const double PositionCost=AnchorTerminal?
                        FMath::Abs(FVector::DotProduct(S.P-LaneCenter,LaneRight))*.35:
                        Distance/(1.+Remaining*.6)+Facing;
                    const double Score=PositionCost+Repetition+FamilyJitter[Modules[Choice.Key].Family]+ChoiceRank*.25+JoinCost;
                    if(Remaining==0&&!AnchorTerminal)
                    {
                        // A close-looking exit is not necessarily joinable with
                        // real 4 m elbows. Close it before pruning the beam.
                        if(!ShortRouteTo(S,Goal,Route+TEXT("_Closure")))continue;
                        TArray<FCompactBeam> Completed;Completed.Add({Pieces,S,Score,JoinCost});
                        Beam=MoveTemp(Completed);Pieces=Base;LastBridgeDepth=Count;LastBridgeDistance=0;return true;
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
            Buckets.Add(Key);Beam.Add(MoveTemp(Candidate));if(Beam.Num()==24)break;
        }
    }
    Pieces=Base;return !Beam.IsEmpty();
}

bool BridgeRooms(int32 Count,const FSocket& Start,const FSocket& Goal,const FString& Route)
{
    if(Count==0)return ShortRouteTo(Start,Goal,Route+TEXT("_Closure"));
    TArray<FCompactBeam> Beam;
    if(!GrowCompactRooms(Count,Start,Goal,Route,Beam))return false;
    Pieces=MoveTemp(Beam[0].Layout);return true;
}

TArray<FCompactBeam> CompactEndRooms(const FSocket& Top,const FSocket& Lead,const FString& Route,int32 Remaining)
{
    const TArray<FPlaced> Base=Pieces;
    const auto Tails=RoomChoices(Route);
    TMap<FString,double> FamilyJitter;
    for(int32 M:Combat)if(!FamilyJitter.Contains(Modules[M].Family))FamilyJitter.Add(Modules[M].Family,Random.FRand()*900.);
    TArray<FCompactBeam> Options;
    double RoomSpan=DBL_MAX;
    for(int32 M:Combat)RoomSpan=FMath::Min(RoomSpan,(Modules[M].Ports[0].P-Modules[M].Ports[1].P).Size());
    auto Links=RoomLinks(Top);
    // The last room-to-stair sleeve is part of the existing terminal walking
    // budget (80 cm). Flexibility belongs upstream, not in a longer boss lead.
    if(Pieces.IsValidIndex(Top.Owner)&&Pieces[Top.Owner].Module==StairDrop)
        Links.RemoveAll([](const FShortLink& Link){return Link.Turns!=0||!FMath::IsNearlyEqual(Link.Length,ExitLeadLength,.1);});
    for(const auto& Tail:Tails)
    {
        auto Ranked=Links;
        Ranked.StableSort([&](const FShortLink& A,const FShortLink& B)
        {return LinkGoalCost(A,Tail.Key,Tail.Value,Lead,1)<LinkGoalCost(B,Tail.Key,Tail.Value,Lead,1);});
        int32 Accepted=0;
        for(const auto& Link:Ranked)
        {
            if(--CompactBudget<0)break;
            Pieces=Base;FSocket Back;
            const double Repetition=RoomRepetitionCost(Tail.Key,Route);
            if(!AttachRoom(Tail.Key,Tail.Value,Top,Link,Route,Back))continue;
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

bool ConnectCompactBranch(int32 Count,const FSocket& Lead,const FSocket& Top,const FString& Route)
{
    LastBridgeDepth=0;LastBridgeDistance=(Lead.P-Top.P).Size();
    const TArray<FPlaced> Base=Pieces;
    auto Ends=CompactEndRooms(Top,Lead,Route,Count-1);
    // Retain end-room alternatives. A failed middle chain must be able to
    // release the endpoint, not repeat the same greedy reservation six times.
    for(auto& EndRoom:Ends)
    {
        if(CompactBudget<=0)break;
        Pieces=MoveTemp(EndRoom.Layout);
        const int32 Available=CompactBudget,TrialBudget=FMath::Min(Available,16000);
        CompactBudget=TrialBudget;
        const bool Connected=BridgeRooms(Count-1,Lead,EndRoom.End,Route);
        CompactBudget=Available-(TrialBudget-FMath::Max(0,CompactBudget));
        if(Connected)return true;
    }
    Pieces=Base;return false;
}

bool AnchorCompactTerminal(const FSocket& Exit,TArray<FSocket>& Tops)
{
    if(FVector::DotProduct(Exit.N,LaneForward)<.999)return false;
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

bool BuildCompact(int32 Seed,const FSocket& Start)
{
    int32 Prefixes=0,Terminals=0,MostBranches=0;
    for(int32 Attempt=0;Attempt<80;++Attempt)
    {
        Pieces.Reset();Counts.Reset();TerminalWalkLengths.Reset();
        bool LoggedFailure=false;
        Random.Initialize(Seed+Attempt*7919);SearchBudget=2500;CompactBudget=50000;
        Counts.Add(Random.RandRange(MinRooms,MaxRooms));
        for(int32 I=0;I<3;++I)Counts.Add(Random.RandRange(MinRooms,MaxRooms));
        // Outer routes also need lateral travel. Keep all three drawn counts,
        // but assign the shortest one to the direct middle route so a five-room
        // spine cannot force a three-room side route to make up missing distance.
        int32 Shortest=1;
        for(int32 I=2;I<4;++I)if(Counts[I]<Counts[Shortest])Shortest=I;
        Counts.Swap(1,Shortest);
        FSocket S=Start;
        if(!Chain(Counts[0],S,TEXT("Approach"))||!Corridor(1,S,TEXT("Approach")))continue;
        if(!Place(Junction,Fit(Junction,0,S),TEXT("Junction"),-2,S.Owner))continue;
        const int32 Hub=Pieces.Num()-1;
        const FVector Center=Pieces[Hub].Bounds.GetCenter();
        const FVector Forward=Socket(Hub,1).N,Right(-Forward.Y,Forward.X,0);
        LaneCenter=Center;LaneForward=Forward;LaneRight=Right;
        TArray<FSocket> Leads;bool Good=true;
        for(int32 Port=1;Port<4;++Port)
        {FSocket Lead=Socket(Hub,Port);if(!Corridor(1,Lead,FString::Printf(TEXT("Route%d"),Port))){Good=false;break;}Leads.Add(Lead);}
        if(!Good)continue;
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
            // Left and right keep their own lanes. Both room count and endpoint
            // are solved together; there is no separately frozen first room.
            for(int32 Order=0;Order<2;++Order)
            {
                if(CompactBudget<=0)break;
                Pieces=Terminal;Good=true;
                for(int32 Step=0;Step<2;++Step)
                {
                    const int32 I=1+(Step+Order)%2;
                    if(!ConnectCompactBranch(Counts[I+1],Leads[I],Tops[I],FString::Printf(TEXT("Route%d"),I+1)))
                    {
                        if(!LoggedFailure)
                        {
                            UE_LOG(LogTemp,Display,TEXT("Compact anchored branch: attempt=%d route=%d rooms=%d depth=%d nearest=%.0f budget=%d start=%s top=%s"),
                                Attempt,I+1,Counts[I+1],LastBridgeDepth,LastBridgeDistance,CompactBudget,
                                *Leads[I].P.ToCompactString(),*Tops[I].P.ToCompactString());
                            LoggedFailure=true;
                        }
                        Good=false;break;
                    }
                    MostBranches=FMath::Max(MostBranches,Step+2);
                }
                if(Good&&CompleteSocketGraph(Start)){CompactFailure.Empty();return true;}
            }
        }
        Pieces=Prefix;
    }
    CompactFailure=FString::Printf(TEXT("地下终点短连接未完成；前段=%d，按中路出口定位终点=%d，最多连接支路=%d；保留原场景"),Prefixes,Terminals,MostBranches);return false;
}
