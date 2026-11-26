// Included in FPlan. Clients assemble the authority's completed placement list;
// they never run a deadline-dependent search or choose another fallback layout.
bool ReadNetworkLayout(const FString& Json, const FString& CatalogHash, const FSocket& Start)
{
    JObject Root;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root) return false;
    int32 Version=0;
    FString Hash;
    if (!Root->TryGetNumberField(TEXT("network_plan_version"),Version) || Version!=1
        || !Root->TryGetStringField(TEXT("catalog_sha1"),Hash) || Hash!=CatalogHash)
    { CompactFailure=TEXT("服务器与客户端地牢目录版本不一致"); return false; }
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    if (!Root->TryGetArrayField(TEXT("plan_counts"),Values) || Values->Num()!=4) return false;
    Counts.Reset(); for (const auto& Value:*Values) Counts.Add(int32(Value->AsNumber()));
    if (bPairedFacility)
    {
        const TArray<TSharedPtr<FJsonValue>>* Routes=nullptr;
        if (!Root->TryGetArrayField(TEXT("themed_routes"),Routes) || Routes->Num()!=3) return false;
        bool Matched=false;
        for (int32 Arrangement=0;Arrangement<6&&!Matched;++Arrangement)
        {
            if (!SelectFacilityArrangement(Arrangement)) return false;
            Matched=true;
            for (const auto& Value:*Routes)
            {
                const auto Route=Value->AsObject();
                const auto* Pair=RouteThemePairs.Find(Route->GetStringField(TEXT("route")));
                const auto& Names=Route->GetArrayField(TEXT("themes"));
                if (!Pair || Names.Num()!=Pair->Num()) { Matched=false; break; }
                for (int32 I=0;I<Pair->Num();++I) Matched&=(*Pair)[I]==Names[I]->AsString();
            }
        }
        if (!Matched) return false;
    }
    Root->TryGetNumberField(TEXT("mission_grammar_requested"),RequestedGrammar);
    Root->TryGetNumberField(TEXT("mission_grammar_realized"),ActualGrammar);
    Root->TryGetNumberField(TEXT("split_after"),SplitAfter);
    Root->TryGetStringField(TEXT("topology_recipe"),TopologyRecipe);
    Root->TryGetStringField(TEXT("layout_solver"),LayoutSolver);
    Root->TryGetBoolField(TEXT("theme_bridges_enabled"),bThemeBridgeSearch);
    ThemeFloorZ=Start.P.Z;
    ThemeCoreLevels.Reset();
    const JObject* Levels=nullptr;
    if (Root->TryGetObjectField(TEXT("theme_core_elevations_cm"),Levels))
        for (const auto& Pair:(*Levels)->Values) ThemeCoreLevels.Add(FString(Pair.Key.ToView()),Pair.Value->AsNumber());
    if (!Root->TryGetArrayField(TEXT("nodes"),Values) || Values->IsEmpty() || Values->Num()>1024) return false;
    Pieces.Reset();
    for (const auto& Value:*Values)
    {
        const auto Node=Value->AsObject();
        const int32 M=Find(Node->GetStringField(TEXT("module")));
        if (M<0 || int32(Node->GetNumberField(TEXT("id")))!=Pieces.Num()) return false;
        const FTransform Transform(FRotator(0,Node->GetNumberField(TEXT("yaw")),0),Vec(Node,TEXT("origin")),Vec(Node,TEXT("scale")));
        if (Transform.ContainsNaN() || Transform.GetScale3D().GetMin()<=0) return false;
        FPlaced Piece{M,Transform,Modules[M].Bounds.TransformBy(Transform),Node->GetStringField(TEXT("route")),{}};
        for (const FBox& Cell:Modules[M].Cells) Piece.Cells.Add(Cell.TransformBy(Transform));
        Node->TryGetNumberField(TEXT("side_index"),Piece.Side);
        if (Piece.Side!=INDEX_NONE && !Modules[M].SideSockets.IsValidIndex(Piece.Side)) return false;
        for (const auto& Port:Node->GetArrayField(TEXT("active_ports")))
        {
            const int32 Index=int32(Port->AsNumber());
            if (!Modules[M].Ports.IsValidIndex(Index)) return false;
            Piece.ActivePorts.Add(Index);
        }
        Node->TryGetNumberField(TEXT("entry_link_turns"),Piece.LinkTurns);
        Node->TryGetNumberField(TEXT("entry_link_cm"),Piece.LinkLength);
        Node->TryGetBoolField(TEXT("theme_bridge"),Piece.bThemeBridge);
        Node->TryGetStringField(TEXT("mission_id"),Piece.MissionId);
        Node->TryGetStringField(TEXT("encounter_role"),Piece.EncounterRole);
        Node->TryGetNumberField(TEXT("threat_bonus"),Piece.ThreatBonus);
        Node->TryGetNumberField(TEXT("reward_multiplier"),Piece.RewardMultiplier);
        Node->TryGetNumberField(TEXT("progression_depth"),Piece.MissionDepth);
        Pieces.Add(MoveTemp(Piece));
    }
    MissionEdges.Reset();
    for (const auto& Value:Root->GetArrayField(TEXT("mission_edges")))
    {
        const auto Edge=Value->AsObject();
        MissionEdges.Add({Edge->GetStringField(TEXT("from")),Edge->GetStringField(TEXT("to")),Edge->GetStringField(TEXT("purpose")),
            Edge->GetBoolField(TEXT("optional")),Edge->GetBoolField(TEXT("realized"))});
    }
    LoopConnections.Reset();
    for (const auto& Value:Root->GetArrayField(TEXT("loop_connections")))
    {
        const auto Edge=Value->AsObject();
        LoopConnections.Add({int32(Edge->GetNumberField(TEXT("from"))),int32(Edge->GetNumberField(TEXT("to"))),Edge->GetNumberField(TEXT("length"))});
    }
    TerminalWalkLengths.Reset();
    for (const auto& Value:Root->GetArrayField(TEXT("terminal_walk_cm"))) TerminalWalkLengths.Add(Value->AsNumber());
    RouteLengthDetails.Reset();RouteEstimates.Reset();
    for (const auto& Value:Root->GetArrayField(TEXT("route_length_details")))
    {
        const auto Detail=Value->AsObject();
        RouteLengthDetails.Add({Detail->GetNumberField(TEXT("authored_walk_cm")),Detail->GetNumberField(TEXT("link_walk_cm")),Detail->GetNumberField(TEXT("link_budget_cm"))});
        RouteEstimates.Add(Detail->GetNumberField(TEXT("total_walk_cm")));
    }
    Root->TryGetNumberField(TEXT("loop_goal"),LoopGoal);
    Root->TryGetNumberField(TEXT("treasure_rooms"),TreasureCount);
    Root->TryGetNumberField(TEXT("corridor_total_cm"),CorridorTotal);
    Root->TryGetNumberField(TEXT("corridor_budget_cm"),CorridorBudget);
    Root->TryGetNumberField(TEXT("route_span_estimate_cm"),LongestRouteEstimate);
    Root->TryGetNumberField(TEXT("route_span_budget_cm"),RouteBudget);
    return CompleteSocketGraph(Start);
}
