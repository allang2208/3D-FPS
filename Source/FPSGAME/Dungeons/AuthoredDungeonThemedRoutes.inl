// Mandatory themed sequences are drawn once, before spatial backtracking.
// INDEX_NONE slots accept only facility transitions; never split a themed core.
bool bThemedRoutes=false;
int32 SharedArchive=INDEX_NONE;
TMap<FString,TArray<int32>> ThemeSlots;
TMap<FString,FString> RouteThemes;
TSet<FString> TransitionFamilies;
TSet<int32> ForwardOnlyModules;
static constexpr double ThemeBridgeLimit=2400.;
static constexpr int32 ThemeBridgeMaxTurns=4;
static constexpr double ThemeRampLinkLimit=4600.;
bool bThemeBridgeSearch=false;
TArray<int32> ThemeRamps;
TMap<FString,double> ThemeCoreLevels;
double ThemeFloorZ=0.;

bool ConfigureThemedRoutes(int32 Seed,const JObject& Catalog)
{
    const JObject* Rules=nullptr;
    bThemedRoutes=Catalog->TryGetObjectField(TEXT("themed_routes"),Rules)&&Rules->IsValid();
    if(!bThemedRoutes)return true;
    ThemeRamps.Reset();
    for(int32 I=0;I<Modules.Num();++I)
    {
        bool Ramp=false;Modules[I].Data->TryGetBoolField(TEXT("split_level_ramp"),Ramp);
        if(Ramp&&Modules[I].Ports.Num()==2)ThemeRamps.Add(I);
    }
    if(!bCompactBoss||!bBossTerminal){CompactFailure=TEXT("主题路线需要地下汇流终点");return false;}
    SharedArchive=Find((*Rules)->GetStringField(TEXT("shared_archive")));
    if(!Combat.Contains(SharedArchive)){CompactFailure=TEXT("缺少共用数据档案中心");return false;}
    auto& Archive=Modules[SharedArchive];Archive.bRunEligible=true;Archive.SelectionRoute=TEXT("Archive");Archive.MaxPerRun=1;
    for(const auto& V:(*Rules)->GetArrayField(TEXT("transition_families")))TransitionFamilies.Add(V->AsString());
    const auto& Cores=(*Rules)->GetArrayField(TEXT("routes"));
    if(Cores.Num()<3||TransitionFamilies.IsEmpty()){CompactFailure=TEXT("主题路线至少需要三个完整组合与过渡房池");return false;}
    FRandomStream Draw(int32(HashCombineFast(uint32(Seed),0x5448454Du)));
    TArray<int32> Order;
    for(int32 I=0;I<Cores.Num();++I)Order.Add(I);
    for(int32 I=Order.Num()-1;I>0;--I)Order.Swap(I,Draw.RandRange(0,I));
    TopologyCounts[0]=Draw.RandRange(1,2);
    ThemeSlots.Add(TEXT("Approach"),{});
    for(int32 I=0;I<TopologyCounts[0];++I)ThemeSlots[TEXT("Approach")].Add(INDEX_NONE);
    for(int32 R=1;R<=3;++R)
    {
        const FString Route=FString::Printf(TEXT("Route%d"),R);
        const auto Core=Cores[Order[R-1]]->AsObject();TArray<int32> Slots;
        const int32 Before=Draw.RandRange(1,2),After=Draw.RandRange(1,2);
        for(int32 I=0;I<Before;++I)Slots.Add(INDEX_NONE);
        for(const auto& V:Core->GetArrayField(TEXT("sequence")))
        {
            const int32 M=Find(V->AsString());
            if(!Combat.Contains(M)){CompactFailure=TEXT("主题组合缺少房间：")+V->AsString();return false;}
            Modules[M].bRunEligible=true;Modules[M].SelectionRoute.Empty();Slots.Add(M);
        }
        for(int32 I=0;I<After;++I)Slots.Add(INDEX_NONE);
        TopologyCounts[R]=Slots.Num();ThemeSlots.Add(Route,MoveTemp(Slots));
        RouteThemes.Add(Route,Core->GetStringField(TEXT("id")));
    }
    for(const auto& V:(*Rules)->GetArrayField(TEXT("forward_only")))ForwardOnlyModules.Add(Find(V->AsString()));
    // Cross-route shortcuts would bypass mandatory room pairs and freight gates.
    LoopGoal=0;TopologyRecipe=TEXT("three_fixed_theme_routes");
    return true;
}

int32 ThemeRequirement(const FString& Route,int32 Ordinal)const
{
    const auto* Slots=ThemeSlots.Find(Route);
    return Slots&&Slots->IsValidIndex(Ordinal)?(*Slots)[Ordinal]:INDEX_NONE;
}

// Door-to-door spans of the actual remaining slots, not the smallest room in
// the whole catalog. The lower value is a search hint, never a fit constraint;
// the upper sum is an optimistic reach bound (rooms may rotate and fold).
FVector2D ThemeSpanRange(const FString& Route,int32 First,int32 Count,int32 Step=1)const
{
    FVector2D Total=FVector2D::ZeroVector;
    for(int32 I=0;I<Count;++I)
    {
        const int32 Required=ThemeRequirement(Route,First+I*Step);
        double Minimum=DBL_MAX,Maximum=0.;
        for(int32 M:Combat)
        {
            const auto& Room=Modules[M];
            if(Required>=0?M!=Required:!TransitionFamilies.Contains(Room.Family))continue;
            if(!Room.bRunEligible||(!Room.SelectionRoute.IsEmpty()&&Room.SelectionRoute!=Route))continue;
            for(const auto& Pair:Room.PortPairs)
            {
                const double Span=(Room.Ports[Pair.X].P-Room.Ports[Pair.Y].P).Size();
                Minimum=FMath::Min(Minimum,Span);Maximum=FMath::Max(Maximum,Span);
            }
        }
        if(Minimum<DBL_MAX)Total+=FVector2D(Minimum,Maximum);
    }
    return Total;
}

double ThemeDistanceCost(double Distance,double RemainingSpan,int32 RemainingRooms)const
{
    // Retain space for compulsory large rooms without requiring a straight
    // chain. Previously every early layer raced towards the goal and discarded
    // the outward poses needed to fit the 66 m isolation ward later on.
    const double Target=RemainingSpan*.65+RemainingRooms*PreferredLinkLength*.5;
    return FMath::Abs(Distance-Target);
}

bool ThemeGapAllowsBridge(const FString& Route,int32 A,int32 B)const
{
    // A connector can precede/follow a core or join its transition rooms, but
    // never insert a detour inside the three mandatory themed rooms.
    return bThemedRoutes&&bThemeBridgeSearch&&ThemeSlots.Contains(Route)&&
        (ThemeRequirement(Route,A)<0||ThemeRequirement(Route,B)<0);
}

bool CloseThemedGap(const FSocket& Start,const FSocket& Goal,const FString& Route,bool AllowBridge)
{
    if(FMath::Abs(Start.P.Z-Goal.P.Z)>.1)
        return AllowBridge&&CloseSplitLevelGap(Start,Goal,Route);
    if(ShortRouteTo(Start,Goal,Route+TEXT("_Closure")))return true;
    if(!AllowBridge||CompactBudget<=0||!CanSearch())return false;
    const double Limit=ThemeBridgeLimit-Start.ReservedLead-Goal.ReservedLead;
    if((Start.P-Goal.P).Size()>Limit||FMath::Abs(Start.P.Z-Goal.P.Z)>.1||
       FMath::Abs(Start.Width-Goal.Width)>=1.||FMath::Abs(Start.Height-Goal.Height)>=1.)return false;
    const int32 Before=Pieces.Num(),Available=CompactBudget,Allowance=FMath::Min(Available,2200);
    CompactBudget=Allowance;
    // Route around occupied cells with real corridor/elbow modules. StraightTo
    // emits <=4 m pieces even when a complete connecting corridor is longer.
    const bool Connected=RouteTo(Start,Goal,Route+TEXT("_Closure"),Limit,Limit,1800);
    CompactBudget=Available-(Allowance-FMath::Max(0,CompactBudget));
    int32 Turns=0;
    for(int32 I=Before;I<Pieces.Num();++I)if(Pieces[I].Module==Elbow)++Turns;
    if(!Connected||Turns>ThemeBridgeMaxTurns){Pieces.SetNum(Before);return false;}
    for(int32 I=Before;I<Pieces.Num();++I)Pieces[I].bThemeBridge=true;
    return true;
}

bool IsFreightPair(const FString& Route,int32 A,int32 B)const
{
    const int32 MA=ThemeRequirement(Route,A),MB=ThemeRequirement(Route,B);
    if(MA<0||MB<0)return false;
    const FString& X=Modules[MA].Id;const FString& Y=Modules[MB].Id;
    return (X==TEXT("FreightTransfer_WarehouseLink")&&Y==TEXT("AbandonedCargoWarehouse"))||
           (Y==TEXT("FreightTransfer_WarehouseLink")&&X==TEXT("AbandonedCargoWarehouse"));
}

void FilterThemedLinks(TArray<FShortLink>& Links,const FString& Route,int32 Ordinal,int32 Step)const
{
    if(bThemedRoutes&&IsFreightPair(Route,Ordinal-Step,Ordinal))
        Links.RemoveAll([](const FShortLink& L){return L.Turns!=0||L.Length>80.1;});
}

bool ThemeLayoutMatches()const
{
    if(!bThemedRoutes)return true;
    for(const auto& Pair:ThemeSlots)for(int32 I=0;I<Pair.Value.Num();++I)
    {
        const FString Id=MissionRoom(Pair.Key,I);
        const FPlaced* P=Pieces.FindByPredicate([&](const FPlaced& V){return V.MissionId==Id;});
        if(!P||(Pair.Value[I]>=0?P->Module!=Pair.Value[I]:!TransitionFamilies.Contains(Modules[P->Module].Family)))return false;
    }
    int32 Archives=0;for(const auto& P:Pieces)if(P.Module==SharedArchive)++Archives;
    return Archives==1;
}
