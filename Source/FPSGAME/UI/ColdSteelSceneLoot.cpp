#include "ColdSteelSceneLoot.h"
#include "ColdSteelSceneContainer.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Crc.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
struct FSearchEntry { FString Id; int32 Weight=0; };
struct FSearchPool { TArray<int32> CountWeights; TArray<FSearchEntry> Entries; };
struct FSearchTable { TMap<FString,FSearchPool> Pools; TMap<FString,FString> Bindings; bool Valid=false; };

bool ReadInteger(const TSharedPtr<FJsonValue>& Value,int32 Min,int32 Max,int32& Out)
{
    double Number=0;
    if(!Value||!Value->TryGetNumber(Number)||!FMath::IsFinite(Number)||Number<Min||Number>Max||Number!=FMath::FloorToDouble(Number))return false;
    Out=int32(Number);return true;
}
bool ParseTable(const FString& Text,FSearchTable& Out)
{
    TSharedPtr<FJsonObject> Root;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return false;
    int32 Version=0;
    if(!ReadInteger(Root->TryGetField(TEXT("version")),1,1,Version))return false;
    const TArray<TSharedPtr<FJsonValue>>* Pools=nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Bindings=nullptr;
    if(!Root->TryGetArrayField(TEXT("pools"),Pools)||!Root->TryGetArrayField(TEXT("bindings"),Bindings))return false;
    FSearchTable Result;
    for(const auto& Value:*Pools)
    {
        const TSharedPtr<FJsonObject>* Object=nullptr;
        if(!Value||!Value->TryGetObject(Object)||!Object->IsValid())return false;
        FString Id;const TArray<TSharedPtr<FJsonValue>>* Counts=nullptr;const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
        if(!(*Object)->TryGetStringField(TEXT("id"),Id)||Id.IsEmpty()||Result.Pools.Contains(Id)
            ||!(*Object)->TryGetArrayField(TEXT("count_weights"),Counts)||Counts->IsEmpty()||Counts->Num()>4
            ||!(*Object)->TryGetArrayField(TEXT("entries"),Entries)||Entries->IsEmpty()||Entries->Num()>64)return false;
        FSearchPool Pool;int32 Sum=0;TSet<FString> Ids;
        for(const auto& Count:*Counts)
        {int32 Weight=0;if(!ReadInteger(Count,0,10000,Weight))return false;Pool.CountWeights.Add(Weight);Sum+=Weight;}
        if(Sum!=100)return false;
        for(const auto& EntryValue:*Entries)
        {
            const TSharedPtr<FJsonObject>* Entry=nullptr;FSearchEntry Row;
            if(!EntryValue||!EntryValue->TryGetObject(Entry)||!Entry->IsValid()
                ||!(*Entry)->TryGetStringField(TEXT("id"),Row.Id)||Row.Id.IsEmpty()||Ids.Contains(Row.Id)
                ||!ReadInteger((*Entry)->TryGetField(TEXT("weight")),1,10000,Row.Weight))return false;
            Ids.Add(Row.Id);Pool.Entries.Add(MoveTemp(Row));
        }
        if(Pool.CountWeights.Num()-1>Pool.Entries.Num())return false;
        Result.Pools.Add(Id,MoveTemp(Pool));
    }
    for(const auto& Value:*Bindings)
    {
        const TSharedPtr<FJsonObject>* Object=nullptr;FString Id,Pool;
        if(!Value||!Value->TryGetObject(Object)||!Object->IsValid()
            ||!(*Object)->TryGetStringField(TEXT("container_id"),Id)||Id.IsEmpty()||Result.Bindings.Contains(Id)
            ||!(*Object)->TryGetStringField(TEXT("pool"),Pool)||!Result.Pools.Contains(Pool))return false;
        Result.Bindings.Add(Id,Pool);
    }
    if(Result.Bindings.IsEmpty())return false;
    Result.Valid=true;Out=MoveTemp(Result);return true;
}
const FSearchTable& Table()
{
    // Loaded once per process; no file reads from tick, highlighting or HUD refresh.
    static const FSearchTable Cached=[]
    {
        FSearchTable Result;FString Text;
        if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/scene_search_loot.json")))||!ParseTable(Text,Result))
            UE_LOG(LogTemp,Error,TEXT("[SceneSearchLoot] Invalid scene_search_loot.json; search rewards were not consumed."));
        return Result;
    }();
    return Cached;
}

const FString* BoundPool(const FString& ContainerId)
{
    const auto& Bindings=Table().Bindings;
    if(const auto* Pool=Bindings.Find(ContainerId))return Pool;
    // Ward boxes retain their full historical identity for storage and RNG.
    // Only this authored family resolves to a shared pool, never a shared inventory.
    if(ContainerId.StartsWith(TEXT("Hospital.Bedside.DGN_"),ESearchCase::CaseSensitive))
    {
        const int32 SeedAt=ContainerId.Find(TEXT(".Seed"),ESearchCase::CaseSensitive);
        int32 At=SeedAt+5;
        if(SeedAt<0)return nullptr;
        if(ContainerId.IsValidIndex(At)&&ContainerId[At]==TEXT('-'))++At;
        const int32 Start=At;
        while(ContainerId.IsValidIndex(At)&&FChar::IsDigit(ContainerId[At]))++At;
        int32 LastDot=INDEX_NONE;
        if(At==Start||!ContainerId.IsValidIndex(At)||ContainerId[At]!=TEXT('.')
            ||!ContainerId.FindLastChar(TEXT('.'),LastDot)||LastDot<=At+1)return nullptr;
        if(LastDot+1>=ContainerId.Len())return nullptr;
        for(int32 I=LastDot+1;I<ContainerId.Len();++I)if(!FChar::IsDigit(ContainerId[I]))return nullptr;
        return Bindings.Find(TEXT("Hospital.Bedside"));
    }
    // Runtime freight furniture prefixes the authored identity with its seed and
    // node. Only pool lookup strips that prefix; rolls, claims and storage keep it.
    if(!ContainerId.StartsWith(TEXT("Run"),ESearchCase::CaseSensitive))return nullptr;
    int32 At=3;
    if(ContainerId.IsValidIndex(At)&&ContainerId[At]==TEXT('-'))++At;
    const int32 SeedStart=At;
    while(ContainerId.IsValidIndex(At)&&FChar::IsDigit(ContainerId[At]))++At;
    if(At==SeedStart||ContainerId.Mid(At,5)!=TEXT(".Node"))return nullptr;
    At+=5;const int32 NodeStart=At;
    while(ContainerId.IsValidIndex(At)&&FChar::IsDigit(ContainerId[At]))++At;
    if(At==NodeStart||!ContainerId.IsValidIndex(At)||ContainerId[At]!=TEXT('.'))return nullptr;
    return Bindings.Find(ContainerId.Mid(At+1));
}
}

bool ColdSteelSceneLoot::IsBound(const AColdSteelSceneContainer* Container)
{
    return IsValid(Container)&&UGameplayStatics::GetCurrentLevelName(Container,true)==TEXT("L_Dungeon_Randomized")
        &&BoundPool(Container->ContainerId)!=nullptr;
}
FName ColdSteelSceneLoot::Claim(const FString& ContainerId)
{return FName(*(TEXT("SceneSearch.")+ContainerId));}

bool ColdSteelSceneLoot::Roll(const FString& ContainerId,int32 RunSeed,TArray<TPair<FString,int64>>& OutLoot)
{
    OutLoot.Reset();const auto& Data=Table();const auto* PoolId=BoundPool(ContainerId);
    const auto* Pool=PoolId?Data.Pools.Find(*PoolId):nullptr;if(!Data.Valid||!Pool)return false;
    FRandomStream Random(int32(uint32(RunSeed)^FCrc::StrCrc32(*ContainerId)^0x534C5431u));
    int32 Ticket=Random.RandRange(0,99),Draws=0;
    for(;Draws<Pool->CountWeights.Num();++Draws){Ticket-=Pool->CountWeights[Draws];if(Ticket<0)break;}
    auto Remaining=Pool->Entries;
    for(int32 Draw=0;Draw<Draws;++Draw)
    {
        int32 Total=0;for(const auto& Entry:Remaining)Total+=Entry.Weight;
        Ticket=Random.RandRange(0,Total-1);
        for(int32 I=0;I<Remaining.Num();++I)
        {
            Ticket-=Remaining[I].Weight;if(Ticket>=0)continue;
            OutLoot.Emplace(Remaining[I].Id,1);Remaining.RemoveAt(I);break;
        }
    }
    return true; // The authored zero-count weight is 0: fresh searches yield 1-3 entries.
}

bool UColdSteelStatusModel::AppendSceneSearchLoot(FColdSteelProfile& State,const AColdSteelSceneContainer* Scene,FString& Reason) const
{
    const auto* Run=Scene?UDungeonRunSubsystem::Get(Scene->GetWorld()):nullptr;
    if(!ColdSteelSceneLoot::IsBound(Scene)||Scene->GetNetMode()==NM_Client||!Run||!Run->IsRunActive()
        ||Run->RunId().IsEmpty()||State.DungeonRun.RunId!=Run->RunId())
    {Reason=TEXT("搜索物品尚未就绪");return false;}
    const FName Claim=ColdSteelSceneLoot::Claim(Scene->ContainerId);
    if(State.DungeonRun.Claimed.Contains(Claim))return true;
    const FString Key=Scene->StorageKey(),Legacy=Scene->LegacyStorageKey();
    auto Staged=State;
    // Random furniture changes seed/node prefixes between runs. Retire only
    // bound search storage from old runs, including those prior generated IDs.
    auto PreviousRunStorage=[&](const FString& Storage)
    {
        const FString Base=TEXT("SceneSearch.L_Dungeon_Randomized.");
        if(!Storage.StartsWith(Base,ESearchCase::CaseSensitive))return false;
        const int32 Marker=Storage.Find(TEXT(".Run."),ESearchCase::CaseSensitive,ESearchDir::FromEnd);
        return Marker>=Base.Len() && Storage.Mid(Marker+5)!=Run->RunId()
            && BoundPool(Storage.Mid(Base.Len(),Marker-Base.Len()))!=nullptr;
    };
    Staged.Items.RemoveAll([&](const auto& I){return I.Place==ColdSteelWarehouse::Place&&PreviousRunStorage(I.Container);});
    for(auto It=Staged.StoragePages.CreateIterator();It;++It)
        if(PreviousRunStorage(It.Key()))It.RemoveCurrent();
    bool HasExisting=false;
    for(auto& Item:Staged.Items)
        if(Item.Place==ColdSteelWarehouse::Place&&(Item.Container==Legacy||Item.Container==Key))
        {Item.Container=Key;HasExisting=true;}
    Staged.StoragePages.Remove(Legacy);
    const int32 Pages=FMath::Clamp(Scene->StoragePages,1,8);Staged.StoragePages.Add(Key,Pages);
    if(!HasExisting)
    {
        TArray<TPair<FString,int64>> Loot;
        if(!ColdSteelSceneLoot::Roll(Scene->ContainerId,Run->RunSeed(),Loot))
        {Reason=TEXT("搜索池配置不可用");return false;}
        for(const auto& Entry:Loot)
        {
            if(!Definitions.Contains(Entry.Key)){Reason=TEXT("搜索物品定义缺失");return false;}
            auto Item=CreateItem(Entry.Key,Entry.Value);Item.Place=ColdSteelWarehouse::Place;Item.Container=Key;
            if(!ColdSteelWarehouse::Insert(Staged.Items,Item,Pages*ColdSteelWarehouse::CellsPerPage))
            {Reason=TEXT("搜索容器空间不足");return false;}
        }
    }
    Staged.DungeonRun.Claimed.Add(Claim);State=MoveTemp(Staged);return true;
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSceneSearchPoolTest,"FPSGAME.SceneSearch.Pools",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSceneSearchPoolTest::RunTest(const FString& Parameters)
{
    const auto& Data=Table();if(!TestTrue(TEXT("valid production table"),Data.Valid))return false;
    TestEqual(TEXT("212 prior, 67 staff living and two drainage toolbox bindings"),Data.Bindings.Num(),281);
    TestEqual(TEXT("31 prior and eight staff living profiles"),Data.Pools.Num(),39);
    TArray<TPair<FString,int64>> Unknown;
    TestFalse(TEXT("outside scope has no roll"),ColdSteelSceneLoot::Roll(TEXT("FacilityTransit.Unknown"),7,Unknown));
    TestFalse(TEXT("unknown generated identity has no roll"),ColdSteelSceneLoot::Roll(TEXT("Run7.Node3.StationWorkshop.Unknown"),7,Unknown));
    TestFalse(TEXT("malformed generated prefix has no roll"),ColdSteelSceneLoot::Roll(TEXT("RunX.Node3.StationWorkshop.Tools"),7,Unknown));
    TArray<TPair<FString,int64>> Freight,RepeatedFreight;
    TestTrue(TEXT("generated freight identity resolves its authored pool"),ColdSteelSceneLoot::Roll(TEXT("Run7.Node3.StationWorkshop.Tools"),7,Freight));
    ColdSteelSceneLoot::Roll(TEXT("Run7.Node3.StationWorkshop.Tools"),7,RepeatedFreight);
    TestTrue(TEXT("generated freight roll is deterministic and yields one item"),Freight==RepeatedFreight&&Freight.Num()==1);
    TestTrue(TEXT("separate room instances keep separate claims"),ColdSteelSceneLoot::Claim(TEXT("Run7.Node3.StationWorkshop.Tools"))
        !=ColdSteelSceneLoot::Claim(TEXT("Run7.Node4.StationWorkshop.Tools")));
    TSet<FString> Items;
    for(const auto& Binding:Data.Bindings)
    {
        TArray<TPair<FString,int64>> A,B;
        TestTrue(TEXT("every binding rolls"),ColdSteelSceneLoot::Roll(Binding.Key,417,A));
        ColdSteelSceneLoot::Roll(Binding.Key,417,B);
        TestTrue(TEXT("reopening seed is independent of player/order"),A==B);
    }
    for(const auto& Pair:Data.Pools)
    {
        FString Id;for(const auto& Binding:Data.Bindings)if(Binding.Value==Pair.Key){Id=Binding.Key;break;}
        if(!TestEqual(TEXT("zero through three count weights"),Pair.Value.CountWeights.Num(),4))return false;
        TestEqual(TEXT("no empty initial searches"),Pair.Value.CountWeights[0],0);
        int32 Counts[4]={0,0,0,0};TMap<FString,int32> Hits;constexpr int32 Samples=100000;
        for(const auto& Entry:Pair.Value.Entries)Items.Add(Entry.Id);
        for(int32 Seed=0;Seed<Samples;++Seed)
        {
            TArray<TPair<FString,int64>> Loot;ColdSteelSceneLoot::Roll(Id,Seed,Loot);
            if(Loot.Num()<1||Loot.Num()>3){AddError(TEXT("initial search must yield one to three entries"));return false;}
            ++Counts[Loot.Num()];TSet<FString> Seen;
            for(const auto& Entry:Loot)
            {
                if(Seen.Contains(Entry.Key)||Entry.Value!=1){AddError(TEXT("duplicate entry or invalid quantity"));return false;}
                Seen.Add(Entry.Key);++Hits.FindOrAdd(Entry.Key);
            }
        }
        for(int32 N=0;N<4;++N)
            TestTrue(*FString::Printf(TEXT("%s count %d frequency"),*Pair.Key,N),FMath::Abs(double(Counts[N])/Samples-Pair.Value.CountWeights[N]/100.)<.005);
        double Total=0;for(const auto& Entry:Pair.Value.Entries)Total+=Entry.Weight;
        for(const auto& Entry:Pair.Value.Entries)
        {
            double Twice=Entry.Weight/Total;
            for(const auto& Other:Pair.Value.Entries)if(Other.Id!=Entry.Id)Twice+=(Other.Weight/Total)*(Entry.Weight/(Total-Other.Weight));
            double Thrice=Twice;
            for(const auto& First:Pair.Value.Entries)if(First.Id!=Entry.Id)
                for(const auto& Second:Pair.Value.Entries)if(Second.Id!=Entry.Id&&Second.Id!=First.Id)
                    Thrice+=(First.Weight/Total)*(Second.Weight/(Total-First.Weight))*(Entry.Weight/(Total-First.Weight-Second.Weight));
            const double Expected=Pair.Value.CountWeights[1]/100.*Entry.Weight/Total+Pair.Value.CountWeights[2]/100.*Twice+Pair.Value.CountWeights[3]/100.*Thrice;
            TestTrue(*(Pair.Key+TEXT(" ")+Entry.Id+TEXT(" marginal probability")),FMath::Abs(double(Hits.FindRef(Entry.Id))/Samples-Expected)<.005);
        }
    }
    TestEqual(TEXT("42 prior items, four living collectibles and four existing raw foods"),Items.Num(),50);
    FSearchTable Bad;
    TestFalse(TEXT("missing pools rejected"),ParseTable(TEXT("{\"version\":1}"),Bad));
    TestFalse(TEXT("unknown schema rejected"),ParseTable(TEXT("{\"version\":2,\"pools\":[],\"bindings\":[]}"),Bad));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSceneSearchSharedSaveTest,"FPSGAME.SceneSearch.SharedSaveAndRevision",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSceneSearchSharedSaveTest::RunTest(const FString& Parameters)
{
    // Memory-only serialization, no player profile, map travel or disk save slot.
    auto* Save=NewObject<UColdSteelSharedInventorySave>();
    auto& Empty=Save->Data.Containers.Add(TEXT("empty"));Empty.bSeeded=true;Empty.bSceneLootResolved=true;Empty.Revision=4;
    auto& Full=Save->Data.Containers.Add(TEXT("full"));Full.bSeeded=true;Full.bSceneLootResolved=true;Full.Revision=10;
    FColdSteelItem Card;Card.InstanceId=TEXT("shared-card");Card.Definition=TEXT("search_graphics_card");
    Card.Place=4;Card.Container=TEXT("full");Card.Width=2;Card.Height=1;Full.Items.Add(Card);
    FColdSteelSharedContainer Legacy;Legacy.bSeeded=true;
    TestFalse(TEXT("cannot mutate before search"),FColdSteelSharedContainer().CanMutate(0,true));
    TestFalse(TEXT("old empty cabinet needs new loot resolution"),Legacy.CanMutate(0,true));
    TestTrue(TEXT("ordinary containers retain prior behavior"),Legacy.CanMutate(0,false));
    TestTrue(TEXT("first competing request accepted"),Full.CanMutate(10,true));
    const auto Transfer=ColdSteelWarehouse::Transfer(Full.Items,Card.InstanceId,0,-1,216,0,-1,TEXT("full"));
    if(TestTrue(TEXT("GPU fits normal backpack with 2x1 footprint"),Transfer.bValid))
    {
        Full.Items.Reset();++Full.Revision;
        TestFalse(TEXT("second request with previous revision rejected"),Full.CanMutate(10,true));
        TestTrue(TEXT("refresh uses new revision"),Full.CanMutate(11,true));
    }
    TArray<uint8> Blob;TestTrue(TEXT("serialize shared empty result"),ColdSteelProfileTransfer::SaveToBlob(Save,Blob));
    auto* Restored=NewObject<UColdSteelSharedInventorySave>();
    TestTrue(TEXT("restore shared state"),ColdSteelProfileTransfer::BlobToSaveObject(Blob,Restored));
    const auto* Stored=Restored->Data.Containers.Find(TEXT("empty"));
    TestTrue(TEXT("empty claim survives reload without reroll"),Stored&&Stored->bSeeded&&Stored->bSceneLootResolved&&Stored->Items.IsEmpty()&&Stored->Revision==4);
    const auto* Taken=Restored->Data.Containers.Find(TEXT("full"));
    TestTrue(TEXT("taken item stays absent after reload"),Taken&&Taken->bSceneLootResolved&&Taken->Items.IsEmpty()&&Taken->Revision==11);
    return true;
}
#endif
