// FPlan extension. Route intent is chosen before placement; optional loop edges
// are embedded using complete authored side-wall variants and real connectors.
TArray<int32> TopologyCounts;
FString TopologyRecipe;
int32 LoopGoal=0;
struct FLoopConnection {int32 From,To;double Length;};
TArray<FLoopConnection> LoopConnections;

void ConfigureTopology(int32 Seed)
{
    ConnectionSeed=HashCombineFast(uint32(Seed),0x4C494E4Bu);
    FRandomStream GraphRandom(int32(HashCombineFast(uint32(Seed),0x47524150u)));
    TopologyCounts.Reset();LoopConnections.Reset();
    for(int32 I=0;I<4;++I)TopologyCounts.Add(GraphRandom.RandRange(MinRooms,MaxRooms));
    // Keep the drawn total, but give symmetric draws different branch lengths.
    if(MaxRooms-MinRooms>=2&&TopologyCounts[1]==TopologyCounts[2]&&TopologyCounts[2]==TopologyCounts[3]&&
       TopologyCounts[1]>MinRooms&&TopologyCounts[1]<MaxRooms)
    {--TopologyCounts[1];++TopologyCounts[2+GraphRandom.RandRange(0,1)];}
    int32 Shortest=1;
    for(int32 I=2;I<4;++I)if(TopologyCounts[I]<TopologyCounts[Shortest])Shortest=I;
    TopologyCounts.Swap(1,Shortest);
    const int32 Recipe=GraphRandom.RandRange(0,2);
    TopologyRecipe=Recipe==0?TEXT("cross_route"):Recipe==1?TEXT("local_return"):TEXT("mixed_loops");
    LoopGoal=Recipe==2?2:1;
}

TArray<TArray<int32>> PieceGraph(bool bIncludeLoops=true)const
{
    TArray<TArray<int32>> Graph;Graph.SetNum(Pieces.Num());
    for(int32 I=0;I<Pieces.Num();++I)
    {
        if(!bIncludeLoops&&Pieces[I].Route.StartsWith(TEXT("Loop.")))continue;
        for(int32 J=0;J<I;++J)
        {
            if(!bIncludeLoops&&Pieces[J].Route.StartsWith(TEXT("Loop.")))continue;
            for(int32 A:OpenPorts(I))for(int32 B:OpenPorts(J))
            {
                const FSocket SA=Socket(I,A),SB=Socket(J,B);
                if(SA.P.Equals(SB.P,1.)&&FVector::DotProduct(SA.N,SB.N)<-.999&&
                   FMath::Abs(SA.Width-SB.Width)<1.&&FMath::Abs(SA.Height-SB.Height)<1.)
                {Graph[I].AddUnique(J);Graph[J].AddUnique(I);}
            }
        }
    }
    return Graph;
}

int32 EntryPiece(const FSocket& Start)const
{
    for(int32 I=0;I<Pieces.Num();++I)for(int32 P:OpenPorts(I))
    {
        const FSocket S=Socket(I,P);
        if(S.P.Equals(Start.P,1.)&&FVector::DotProduct(S.N,Start.N)<-.999)return I;
    }
    return INDEX_NONE;
}

TArray<int32> PieceDepths(int32 Root,const TArray<TArray<int32>>& Graph)const
{
    TArray<int32> Depth;Depth.Init(MAX_int32,Pieces.Num());
    if(!Pieces.IsValidIndex(Root))return Depth;
    TArray<int32> Queue{Root};Depth[Root]=Combat.Contains(Pieces[Root].Module)?1:0;
    for(int32 Head=0;Head<Queue.Num();++Head)for(int32 Next:Graph[Queue[Head]])
    {
        const int32 Module=Pieces[Next].Module;
        const bool Room=Combat.Contains(Module)||Module==Junction||Module==ForkLeft||Module==ForkRight||Module==Treasure||Module==BossConfluence||Module==BossRoom;
        const int32 Candidate=Depth[Queue[Head]]+(Room?1:0);
        // Relax distances: connectors have zero weight, so first-visit BFS is wrong.
        if(Candidate<Depth[Next]){Depth[Next]=Candidate;Queue.Add(Next);}
    }
    return Depth;
}

void AddRouteLoops(const FSocket& Start)
{
    LoopConnections.Reset();
    if(LoopGoal<=0||(CancelRequested&&CancelRequested->Load()))return;
    // Optional work has a fixed 512-candidate budget. A nearly exhausted main
    // search deadline must not change the same seed's successfully placed loops.
    TGuardValue<double> DeadlineGuard(PlanningDeadline,DBL_MAX);
    TGuardValue<bool> DeadlineStateGuard(bSearchExpired,false);
    const int32 BaseCount=Pieces.Num();
    const auto Graph=PieceGraph();
    struct FCandidate {int32 A,ASide,B,BSide;double Score;};
    TArray<FCandidate> Candidates;
    FRandomStream LoopRandom(int32(HashCombineFast(ConnectionSeed,0x4C4F4F50u)));
    for(int32 A=0;A<BaseCount;++A)
    {
        if(!Combat.Contains(Pieces[A].Module)||Pieces[A].Side>=0)continue;
        const auto Distance=PieceDepths(A,Graph);
        const auto& AM=Modules[Pieces[A].Module];
        for(int32 B=A+1;B<BaseCount;++B)
        {
            if(!Combat.Contains(Pieces[B].Module)||Pieces[B].Side>=0||Distance[B]<3||Distance[B]==MAX_int32)continue;
            const bool SameRoute=Pieces[A].Route==Pieces[B].Route;
            const double IntentCost=(TopologyRecipe==TEXT("cross_route")?SameRoute:
                                    TopologyRecipe==TEXT("local_return")?!SameRoute:false)?500.:0.;
            const auto& BM=Modules[Pieces[B].Module];
            for(int32 AS=0;AS<AM.SideSockets.Num();++AS)for(int32 BS=0;BS<BM.SideSockets.Num();++BS)
            {
                if(!SideAvailable(A,AS)||!SideAvailable(B,BS)||!MissionAllowsLoop(A,B))continue;
                const FPort& AP=AM.SideSockets[AS].Port;const FPort& BP=BM.SideSockets[BS].Port;
                // Side doors become legal optional route ports only with their complete
                // replacement wall meshes; they never replace a primary room exit.
                if(!AM.SideSockets[AS].Data->HasField(TEXT("parts"))||!BM.SideSockets[BS].Data->HasField(TEXT("parts")))continue;
                const FVector PA=Pieces[A].Transform.TransformPosition(AP.P),PB=Pieces[B].Transform.TransformPosition(BP.P);
                const double Gap=(PA-PB).Size();
                if(Gap<ExitLeadLength||Gap>ShortLinkLimit||FMath::Abs(PA.Z-PB.Z)>.1)continue;
                if(FMath::Abs(AP.Width-BP.Width)>=1.||FMath::Abs(AP.Height-BP.Height)>=1.)continue;
                Candidates.Add({A,AS,B,BS,IntentCost+Gap*.25-FMath::Min(Distance[B],8)*40.+LoopRandom.FRand()*180.});
            }
        }
    }
    Candidates.StableSort([](const FCandidate& A,const FCandidate& B){return A.Score<B.Score;});
    const int32 PreviousBudget=CompactBudget;CompactBudget=512;
    for(const auto& C:Candidates)
    {
        if(LoopConnections.Num()>=LoopGoal||CompactBudget<=0||(CancelRequested&&CancelRequested->Load()))break;
        if(Pieces[C.A].Side>=0||Pieces[C.B].Side>=0)continue;
        const int32 Before=Pieces.Num();
        Pieces[C.A].Side=C.ASide;Pieces[C.B].Side=C.BSide;
        const FSocket A=Socket(C.A,OptionalPort(C.A,C.ASide));
        const FSocket B=Socket(C.B,OptionalPort(C.B,C.BSide));
        const FString Route=FString::Printf(TEXT("Loop.%d"),LoopConnections.Num());
        const auto Links=LinksBetween(A,B);
        bool Connected=false;
        for(const auto& Link:Links)
        {
            if(--CompactBudget<0||(CancelRequested&&CancelRequested->Load()))break;
            Pieces.SetNum(Before);
            if(PlaceRoutePolyline(A,B,Route,Link.Points,ShortLinkLimit,ShortLinkLimit)&&CompleteSocketGraph(Start))
            {LoopConnections.Add({C.A,C.B,Link.Length});Connected=true;break;}
        }
        if(!Connected){Pieces.SetNum(Before);Pieces[C.A].Side=-1;Pieces[C.B].Side=-1;}
    }
    CompactBudget=PreviousBudget;
    CompactFailure.Empty();
}
