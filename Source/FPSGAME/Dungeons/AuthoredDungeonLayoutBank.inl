// Authored layout placements are a bounded fallback for the SAME drawn pairs.
// They never substitute room assets, reverse sequences, or skip fit/graph checks.
FString FacilityContractHash;
JObject FacilityLayoutBank;
FString LayoutSolver=TEXT("anchored_spine");

static void WriteContractJson(const TSharedPtr<FJsonValue>& Value,const TSharedRef<TJsonWriter<>>& Writer)
{
    switch(Value->Type)
    {
    case EJson::Object:
    {
        Writer->WriteObjectStart();const auto Object=Value->AsObject();TArray<FString> Keys;for(const auto& Field:Object->Values)Keys.Add(FString(Field.Key.ToView()));Keys.Sort();
        for(const auto& Key:Keys){Writer->WriteIdentifierPrefix(Key);WriteContractJson(Object->TryGetField(Key),Writer);}
        Writer->WriteObjectEnd();break;
    }
    case EJson::Array:Writer->WriteArrayStart();for(const auto& Item:Value->AsArray())WriteContractJson(Item,Writer);Writer->WriteArrayEnd();break;
    case EJson::String:Writer->WriteValue(Value->AsString());break;
    case EJson::Number:Writer->WriteValue(Value->AsNumber());break;
    case EJson::Boolean:Writer->WriteValue(Value->AsBool());break;
    default:Writer->WriteNull();break;
    }
}

void ConfigureFacilityBank(const JObject& Catalog)
{
    // Include authored geometry, ports, dressing revisions and all generation
    // rules. Exclude only this bank and explicit test/activation controls.
    auto Contract=MakeShared<FJsonObject>();Contract->Values=Catalog->Values;
    auto Flow=MakeShared<FJsonObject>();Flow->Values=FacilityFlowRules->Values;
    Flow->RemoveField(TEXT("layout_bank"));Flow->RemoveField(TEXT("probe_pair_order"));
    Flow->RemoveField(TEXT("joint_layout_version"));Contract->SetObjectField(TEXT("facility_flow"),Flow);
    FString Text;const auto Writer=TJsonWriterFactory<>::Create(&Text);
    WriteContractJson(MakeShared<FJsonValueObject>(Contract),Writer);Writer->Close();
    Text=TEXT("facility-layout-v1;rigid;12/48/46m;4turn;contact=8.001;")+Text;
    const FTCHARToUTF8 Bytes(*Text);uint8 Digest[20];FSHA1::HashBuffer(Bytes.Get(),Bytes.Length(),Digest);
    FacilityContractHash=BytesToHex(Digest,20).ToLower();
    const JObject* Bank=nullptr;
    if(FacilityFlowRules->TryGetObjectField(TEXT("layout_bank"),Bank))FacilityLayoutBank=*Bank;
}

FString FacilityPairKey()const
{
    TArray<FString> Keys;
    for(const auto& Pair:DrawnThemePairs)Keys.Add(FString::Join(Pair.Value,TEXT(">")));
    Keys.Sort();return FString::Join(Keys,TEXT("|"));
}

bool ReplayFacilityLayout(const FSocket& Start)
{
    if(!FacilityLayoutBank.IsValid()||!CanSearch())return false;
    FString Hash;
    if(!FacilityLayoutBank->TryGetStringField(TEXT("contract_sha1"),Hash)||Hash!=FacilityContractHash)
    {if(bLayoutProbe)++ProbeRejects.FindOrAdd(TEXT("bank/stale_contract"));return false;}
    const JObject* Entries=nullptr;const JObject* Entry=nullptr;const JObject* Pairs=nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Layout=nullptr;const TArray<TSharedPtr<FJsonValue>>* Levels=nullptr;
    if(!FacilityLayoutBank->TryGetObjectField(TEXT("entries"),Entries)||
       !(*Entries)->TryGetObjectField(FacilityPairKey(),Entry)||
       !(*Entry)->TryGetObjectField(TEXT("route_pairs"),Pairs)||
       !(*Entry)->TryGetArrayField(TEXT("pieces"),Layout)||Layout->IsEmpty()||Layout->Num()>1024||
       !(*Entry)->TryGetArrayField(TEXT("levels_cm"),Levels)||Levels->Num()!=3)return false;
    bool Matches=false;
    for(int32 Arrangement=0;Arrangement<6&&!Matches;++Arrangement)
    {
        if(!SelectFacilityArrangement(Arrangement))return false;
        Matches=true;
        for(int32 R=1;R<=3;++R)
        {
            const FString Route=FString::Printf(TEXT("Route%d"),R);const TArray<TSharedPtr<FJsonValue>>* Pair=nullptr;
            if(!(*Pairs)->TryGetArrayField(Route,Pair)||Pair->Num()!=2){Matches=false;break;}
            for(int32 I=0;I<2;++I)if((*Pair)[I]->AsString()!=RouteThemePairs[Route][I])Matches=false;
        }
    }
    if(!Matches)return false;
    Pieces.Reset();Counts=TopologyCounts;TerminalWalkLengths.Reset();LoopConnections.Reset();
    bCompactLaneHint=false;bThemeBridgeSearch=false;(*Entry)->TryGetBoolField(TEXT("theme_bridges_enabled"),bThemeBridgeSearch);
    ThemeFloorZ=Start.P.Z;ThemeCoreLevels.Reset();
    for(int32 R=1;R<=3;++R)ThemeCoreLevels.Add(FString::Printf(TEXT("Route%d"),R),(*Levels)[R-1]->AsNumber());
    TArray<FSocket> Leads;if(!BuildMissionPrefix(Start,Leads,0))return false;
    const auto Prefix=Pieces;Pieces.Reset();
    for(const auto& Value:*Layout)
    {
        if(!CanSearch()){Pieces.Reset();return false;}
        const auto Item=Value->AsObject();const int32 M=Find(Item->GetStringField(TEXT("module")));
        if(M<0){Pieces.Reset();return false;}
        const auto T=FTransform(FRotator(0,Item->GetNumberField(TEXT("yaw")),0),Vec(Item,TEXT("origin")),Vec(Item,TEXT("scale")));
        TArray<int32> Ports;
        for(const auto& Port:Item->GetArrayField(TEXT("active_ports")))
        {const int32 P=int32(Port->AsNumber());if(!Modules[M].Ports.IsValidIndex(P)){Pieces.Reset();return false;}Ports.Add(P);}
        const int32 Index=Pieces.Num();
        if(!Place(M,T,Item->GetStringField(TEXT("route")),-2,Index==0?-1:-2,{}, {},-2,Ports))
        {Pieces.Reset();if(bLayoutProbe)++ProbeRejects.FindOrAdd(TEXT("bank/placement_rejected"));return false;}
        auto& Placed=Pieces.Last();Placed.LinkLength=Item->GetNumberField(TEXT("link_cm"));
        Placed.LinkTurns=int32(Item->GetNumberField(TEXT("link_turns")));Placed.bThemeBridge=Item->GetBoolField(TEXT("theme_bridge"));
        if(Index<Prefix.Num())
        {
            if(M!=Prefix[Index].Module||!T.Equals(Prefix[Index].Transform,.01)){Pieces.Reset();return false;}
            Placed.MissionId=Prefix[Index].MissionId;
        }
    }
    if(!CompleteSocketGraph(Start)||!FinalizeMissionLayout(Start)){Pieces.Reset();return false;}
    // Restore the rigid shared-terminal walk metrics using its current geometry.
    for(const auto& Placed:Pieces)if(Placed.Module==BossConfluence)
    {
        const auto& Hub=Modules[BossConfluence];
        const double ArchiveWalk=FMath::Max(0.,AuthoredWalk(SharedArchive))+ExitLeadLength;
        for(int32 Port:{0,2,3})TerminalWalkLengths.Add(AuthoredWalk(StairDrop)+2*ExitLeadLength+
            (Hub.Ports[Port].P-FVector(0,-600,0)).Size()+(Hub.Ports[1].P-FVector(0,-600,0)).Size()+
            (Modules[BossApproach].Ports[0].P-Modules[BossApproach].Ports[1].P).Size()+ArchiveWalk);
        break;
    }
    LayoutSolver=TEXT("verified_pair_fallback_v1");CompactFailure.Empty();return true;
}

bool BuildFacility(int32 Seed,const FSocket& Start)
{
    if(bLayoutProbe&&FParse::Param(FCommandLine::Get(),TEXT("DungeonLayoutBankProbe")))
    {
        const bool Replayed=ReplayFacilityLayout(Start);
        if(!Replayed)CompactFailure=TEXT("对应抽签组合没有可用且通过当前接口检查的后备布局");
        return Replayed;
    }
    LayoutSolver=TEXT("joint_facility_v1");
    // Keep part of the existing 12 s window for validating a fallback, even if
    // candidate search meets its time bound on a slow machine.
    const double FullDeadline=PlanningDeadline;
    PlanningDeadline=FMath::Min(FullDeadline,FPlatformTime::Seconds()+8.);
    const bool Generated=BuildJointFacility(Seed,Start);
    PlanningDeadline=FullDeadline;bSearchExpired=false;
    if(Generated)return true;
    if(ReplayFacilityLayout(Start))return true;
    if(!CanSearch())return false;
    LayoutSolver=TEXT("anchored_spine_recovery");
    return BuildCompact(Seed,Start,FullDeadline);
}
