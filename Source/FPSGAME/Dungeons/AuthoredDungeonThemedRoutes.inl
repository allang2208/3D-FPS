// Mandatory themed sequences are drawn once, before spatial backtracking.
// INDEX_NONE slots accept only facility transitions; never split a themed core.
bool bThemedRoutes=false;
bool bPairedFacility=false;
bool bUseJointFacilityLayout=false;
int32 FacilityEntrance=INDEX_NONE,FacilityReception=INDEX_NONE;
TMap<FString,TArray<FString>> RouteThemePairs;
int32 SharedArchive=INDEX_NONE;
TMap<FString,TArray<int32>> ThemeSlots;
TMap<FString,FString> RouteThemes;
TSet<FString> TransitionFamilies;
TSet<int32> ForwardOnlyModules;
double ThemeBridgeLimit=2400.;
static constexpr int32 ThemeBridgeMaxTurns=4;
static constexpr double ThemeRampLinkLimit=4600.;
bool bThemeBridgeSearch=false;
TArray<int32> ThemeRamps;
TMap<FString,double> ThemeCoreLevels;
double ThemeFloorZ=0.;
TMap<FString,TArray<int32>> DrawnThemeSlots;
TMap<FString,TArray<FString>> DrawnThemePairs;
JObject FacilityHubBase,FacilityFlowRules;

bool SelectFacilityArrangement(int32 Arrangement)
{
    if(!bPairedFacility)return true;
    static const int32 Orders[6][3]={{0,1,2},{1,0,2},{2,1,0},{0,2,1},{1,2,0},{2,0,1}};
    // Move whole drawn pairs among the three physical doors. Never redraw a
    // theme, reverse its authored sequence, or keep signage from another pose.
    const JObject* Variants=nullptr;
    if(!FacilityFlowRules->TryGetObjectField(TEXT("route_portal_variants"),Variants))
    {CompactFailure=TEXT("分流大厅缺少主题门厅构件");return false;}
    JObject Hall=MakeShared<FJsonObject>();Hall->Values=FacilityHubBase->Values;
    auto Parts=Hall->GetArrayField(TEXT("parts"));
    for(int32 R=1;R<=3;++R)
    {
        const FString Route=FString::Printf(TEXT("Route%d"),R);
        const FString Drawn=FString::Printf(TEXT("Route%d"),Orders[Arrangement%6][R-1]+1);
        ThemeSlots.FindChecked(Route)=DrawnThemeSlots.FindChecked(Drawn);
        RouteThemePairs.FindChecked(Route)=DrawnThemePairs.FindChecked(Drawn);
        const auto& Pair=RouteThemePairs.FindChecked(Route);
        RouteThemes.FindChecked(Route)=Pair[0];
        const JObject* RouteVariants=nullptr;const TArray<TSharedPtr<FJsonValue>>* Kit=nullptr;
        if(!(*Variants)->TryGetObjectField(Route,RouteVariants)||
           !(*RouteVariants)->TryGetArrayField(Pair[0],Kit)||Kit->IsEmpty())
        {CompactFailure=TEXT("主题门厅构件不完整：")+Route;return false;}
        Parts.Append(*Kit);
        const JObject* PairSigns=nullptr;const JObject* RouteSigns=nullptr;const TArray<TSharedPtr<FJsonValue>>* Sign=nullptr;
        if(!FacilityFlowRules->TryGetObjectField(TEXT("route_pair_signs"),PairSigns)||
           !(*PairSigns)->TryGetObjectField(Route,RouteSigns)||
           !(*RouteSigns)->TryGetArrayField(Pair[0]+TEXT("__")+Pair[1],Sign))
        {CompactFailure=TEXT("分流大厅缺少双主题顺序牌：")+Route;return false;}
        Parts.Append(*Sign);
    }
    Hall->SetArrayField(TEXT("parts"),Parts);Modules[Junction].Data=Hall;return true;
}

bool ConfigureThemedRoutes(int32 Seed,const JObject& Catalog)
{
    const JObject* Rules=nullptr;
    bThemedRoutes=Catalog->TryGetObjectField(TEXT("themed_routes"),Rules)&&Rules->IsValid();
    if(!bThemedRoutes)return true;
    const JObject* Flow=nullptr;
    bPairedFacility=Catalog->TryGetObjectField(TEXT("facility_flow"),Flow)&&Flow->IsValid();
    // Six-room paired branches contain two full-size cores. Their inter-core
    // connector must clear both footprints; retain the old cap for single cores.
    ThemeBridgeLimit=bPairedFacility?4800.:2400.;
    if(bPairedFacility)
    {
        int32 JointVersion=0;(*Flow)->TryGetNumberField(TEXT("joint_layout_version"),JointVersion);
        bUseJointFacilityLayout=JointVersion==1;
        if(bLayoutProbe&&FParse::Param(FCommandLine::Get(),TEXT("DungeonJointLayoutProbe")))bUseJointFacilityLayout=true;
        FacilityEntrance=Find((*Flow)->GetStringField(TEXT("entrance")));
        FacilityReception=Find((*Flow)->GetStringField(TEXT("reception")));
        if(FacilityEntrance<0||FacilityReception<0||Modules[FacilityEntrance].Ports.Num()!=2||Modules[FacilityReception].Ports.Num()!=2)
        {CompactFailure=TEXT("设施入口通道或侧墙破洞接待厅缺少双端口");return false;}
    }
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
    if(bPairedFacility&&Cores.Num()!=6){CompactFailure=TEXT("双主题三路线需要六个主题");return false;}
    // Exhaustive pairing fixtures exist only in the explicit layout-only probe.
    // Runtime draws remain seed-driven and are never replaced during retries.
    if(bLayoutProbe&&bPairedFacility)
    {
        const TArray<TSharedPtr<FJsonValue>>* Fixture=nullptr;
        if((*Flow)->TryGetArrayField(TEXT("probe_pair_order"),Fixture))
        {
            TArray<int32> Fixed;TSet<int32> Used;
            for(const auto& Id:*Fixture)
            {
                int32 Match=INDEX_NONE;
                for(int32 I=0;I<Cores.Num();++I)if(Cores[I]->AsObject()->GetStringField(TEXT("id"))==Id->AsString())Match=I;
                if(Match<0||Used.Contains(Match)){CompactFailure=TEXT("组合测试包含无效或重复主题");return false;}
                Used.Add(Match);Fixed.Add(Match);
            }
            if(Fixed.Num()!=6){CompactFailure=TEXT("组合测试必须包含六个主题");return false;}
            Order=MoveTemp(Fixed);
        }
    }
    if(bPairedFacility)
    {
        // Pairing stays random. Try the shortest pair as the direct spine
        // first; spatial backtracking may move whole pairs to other doors.
        auto Span=[&](int32 Pair)
        {
            double Total=0;
            for(int32 B=0;B<2;++B)for(const auto& V:Cores[Order[Pair*2+B]]->AsObject()->GetArrayField(TEXT("sequence")))
            {
                const int32 M=Find(V->AsString());if(M<0)continue;
                double Best=DBL_MAX;
                for(const auto& P:Modules[M].PortPairs)Best=FMath::Min(Best,(Modules[M].Ports[P.X].P-Modules[M].Ports[P.Y].P).Size());
                if(Best<DBL_MAX)Total+=Best;
            }
            return Total;
        };
        int32 Shortest=0;for(int32 P=1;P<3;++P)if(Span(P)<Span(Shortest))Shortest=P;
        if(Shortest)for(int32 B=0;B<2;++B)Order.Swap(B,Shortest*2+B);
    }
    TopologyCounts[0]=bPairedFacility?0:Draw.RandRange(1,2);
    ThemeSlots.Add(TEXT("Approach"),{});
    for(int32 I=0;I<TopologyCounts[0];++I)ThemeSlots[TEXT("Approach")].Add(INDEX_NONE);
    TSet<FString> UsedThemes;TSet<int32> UsedCoreRooms;
    for(int32 R=1;R<=3;++R)
    {
        const FString Route=FString::Printf(TEXT("Route%d"),R);
        TArray<int32> Slots;TArray<FString> PairIds;
        const int32 Before=bPairedFacility?0:Draw.RandRange(1,2),After=bPairedFacility?0:Draw.RandRange(1,2);
        for(int32 I=0;I<Before;++I)Slots.Add(INDEX_NONE);
        for(int32 Block=0;Block<(bPairedFacility?2:1);++Block)
        {
            const auto Core=Cores[Order[bPairedFacility?(R-1)*2+Block:R-1]]->AsObject();
            const FString ThemeId=Core->GetStringField(TEXT("id"));
            const auto& Sequence=Core->GetArrayField(TEXT("sequence"));
            if(bPairedFacility&&(UsedThemes.Contains(ThemeId)||Sequence.Num()!=3))
            {CompactFailure=TEXT("主题重复或不满足三房序列：")+ThemeId;return false;}
            UsedThemes.Add(ThemeId);PairIds.Add(ThemeId);
            for(const auto& V:Sequence)
            {
                const int32 M=Find(V->AsString());
                if(!Combat.Contains(M)||(bPairedFacility&&UsedCoreRooms.Contains(M)))
                {CompactFailure=TEXT("主题组合缺少或重复房间：")+V->AsString();return false;}
                UsedCoreRooms.Add(M);Modules[M].bRunEligible=true;Modules[M].SelectionRoute.Empty();Slots.Add(M);
                if(bPairedFacility)ForwardOnlyModules.Add(M);
            }
        }
        for(int32 I=0;I<After;++I)Slots.Add(INDEX_NONE);
        TopologyCounts[R]=Slots.Num();ThemeSlots.Add(Route,MoveTemp(Slots));
        RouteThemes.Add(Route,PairIds[0]);RouteThemePairs.Add(Route,MoveTemp(PairIds));
    }
    if(bPairedFacility)
    {
        DrawnThemeSlots=ThemeSlots;DrawnThemePairs=RouteThemePairs;
        FacilityHubBase=Modules[Junction].Data;FacilityFlowRules=*Flow;
        ConfigureFacilityBank(Catalog);
        if(!SelectFacilityArrangement(0))return false;
    }
    for(const auto& V:(*Rules)->GetArrayField(TEXT("forward_only")))ForwardOnlyModules.Add(Find(V->AsString()));
    // Cross-route shortcuts would bypass mandatory room pairs and freight gates.
    LoopGoal=0;TopologyRecipe=bPairedFacility?TEXT("facility_three_paired_theme_routes"):TEXT("three_fixed_theme_routes");
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
        (ThemeRequirement(Route,A)<0||ThemeRequirement(Route,B)<0||
         (bPairedFacility&&A/3!=B/3));
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
