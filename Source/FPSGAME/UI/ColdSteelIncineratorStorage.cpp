#include "ColdSteelIncineratorStorage.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
#include "ColdSteelIncineration.h"
#include "ColdSteelWorldInteraction.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "JsonObjectConverter.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"

namespace ColdSteelIncineratorStorage
{
namespace
{
    constexpr int64 Limit=9007199254740991ll;
    bool Integer(const FJsonObject& Object,const TCHAR* Key,int64& Out)
    {
        double N=0;
        if(!Object.TryGetNumberField(Key,N)||!FMath::IsFinite(N)||N<1||N>double(Limit)||FMath::FloorToDouble(N)!=N)return false;
        Out=int64(N);return true;
    }
    FString Name(const FColdSteelItem& Item)
    {const FString N=ColdSteelInventory::Text(Item,TEXT("name"));return N.IsEmpty()?Item.Definition:N;}
    bool InContainer(const FColdSteelItem& I,const FString& Key)
    {return I.Place==4&&IsContainer(I.Container)&&(Key.IsEmpty()||I.Container==Key);}
    void ClearReferences(FColdSteelProfile& P,const FString& Id)
    {
        for(auto& B:P.QuickBindings)if(B.ItemId==Id)B=FColdSteelQuickBinding();
        for(int32 N=0;N<P.Hotbar.Num();++N)if(P.Hotbar[N]==Id){P.Hotbar[N].Reset();if(P.HotbarDefinitions.IsValidIndex(N))P.HotbarDefinitions[N].Reset();}
        if(P.ActiveProductionTool==Id)P.ActiveProductionTool.Reset();
    }
    TSharedPtr<FJsonValue> CanonicalValue(const TSharedPtr<FJsonValue>& Value)
    {
        if(!Value)return MakeShared<FJsonValueNull>();
        if(Value->Type==EJson::Object)
        {
            const auto Source=Value->AsObject();auto Sorted=MakeShared<FJsonObject>();
            TArray<FJsonObject::FStringType> Keys;Source->Values.GetKeys(Keys);
            Keys.Sort([](const auto& A,const auto& B){return MakeStringView(A).Compare(MakeStringView(B),ESearchCase::CaseSensitive)<0;});
            for(const auto& Key:Keys)Sorted->SetField(MakeStringView(Key),CanonicalValue(Source->Values.FindChecked(Key)));
            return MakeShared<FJsonValueObject>(Sorted);
        }
        if(Value->Type==EJson::Array)
        {
            TArray<TSharedPtr<FJsonValue>> Array;
            for(const auto& Entry:Value->AsArray())Array.Add(CanonicalValue(Entry));
            return MakeShared<FJsonValueArray>(Array);
        }
        return Value;
    }
}
FRules ParseRules(const FString& Json)
{
    FRules R;R.Signature=FMD5::HashAnsiString(*Json);R.Error=TEXT("焚化产出配置无效，请检查规则文件");
    TSharedPtr<FJsonObject> Root;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root)return R;
    int64 Version=0;if(!Integer(*Root,TEXT("version"),Version)||Version!=1)return R;
    if(!Root->TryGetBoolField(TEXT("allowUnconfiguredDestruction"),R.bAllowUnconfigured))return R;
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(!Root->TryGetArrayField(TEXT("recipes"),Rows)||Rows->Num()>10000)return R;
    TSet<FString> Seen;
    for(const auto& V:*Rows)
    {
        const auto O=V->AsObject();FRecipe Recipe;
        if(!O||!O->TryGetStringField(TEXT("input"),Recipe.Input)||Recipe.Input.IsEmpty()||Seen.Contains(Recipe.Input)||!Integer(*O,TEXT("inputCount"),Recipe.InputCount))return R;
        Seen.Add(Recipe.Input);
        const TArray<TSharedPtr<FJsonValue>>* Outputs=nullptr;
        if(!O->TryGetArrayField(TEXT("outputs"),Outputs)||Outputs->Num()>256)return R;
        for(const auto& Value:*Outputs)
        {
            const auto Output=Value->AsObject();FProduct Product;
            if(!Output||!Output->TryGetStringField(TEXT("item"),Product.Item)||Product.Item.IsEmpty()||!Integer(*Output,TEXT("count"),Product.Count))return R;
            Recipe.Outputs.Add(MoveTemp(Product));
        }
        R.Recipes.Add(MoveTemp(Recipe));
    }
    R.bValid=true;R.Error.Reset();return R;
}
FRules LoadRules()
{
    FString Json;
    if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/incinerator-recipes.json"))))
    {FRules R;R.Error=TEXT("焚化产出配置文件缺失；物品仍保留在投入区");return R;}
    return ParseRules(Json);
}
bool HasInputs(const FColdSteelProfile& State,const FString& Container)
{return State.Items.ContainsByPredicate([&](const auto& I){return InContainer(I,Container);});}
FQuote Quote(const FColdSteelProfile& State,const FString& Container,const FRules& Rules)
{
    FQuote Q;Q.Generation=State.Generation;Q.Container=Container;Q.RuleSignature=Rules.Signature;
    if(!IsContainer(Container)){Q.Reason=TEXT("焚化容器无效");return Q;}
    if(!Rules.bValid){Q.Reason=Rules.Error;return Q;}
    TMap<FString,int64> Totals;
    for(const auto& I:State.Items)if(InContainer(I,Container))
    {
        if(I.Count<=0||I.Count>Limit||Totals.FindRef(I.Definition)>Limit-I.Count){Q.Reason=TEXT("投入数量超出可计算范围");return Q;}
        Q.Inputs.Add(I);Totals.FindOrAdd(I.Definition)+=I.Count;
    }
    if(Q.Inputs.IsEmpty()){Q.Reason=TEXT("从右侧背包拖入物品，或右键投入");return Q;}
    TMap<FString,int64> Products;
    for(const auto& Entry:Totals)
    {
        const auto* Recipe=Rules.Recipes.FindByPredicate([&](const auto& R){return R.Input==Entry.Key;});
        if(!Recipe){Q.Unconfigured.Add(Entry.Key);continue;}
        if(Recipe->InputCount<=0||Entry.Value%Recipe->InputCount!=0)
        {Q.Reason=TEXT("投入数量不是配方批量的整数倍，请先拆分取回余量");return Q;}
        const int64 Batches=Entry.Value/Recipe->InputCount;
        for(const auto& Product:Recipe->Outputs)
        {
            if(Product.Count<=0||Batches>Limit/Product.Count||Products.FindRef(Product.Item)>Limit-Batches*Product.Count)
            {Q.Reason=TEXT("预计产出数量超出可存储范围");return Q;}
            Products.FindOrAdd(Product.Item)+=Batches*Product.Count;
        }
    }
    TArray<FString> Keys;Products.GetKeys(Keys);Keys.Sort();
    for(const auto& Key:Keys)Q.Products.Add({Key,Products[Key]});
    Q.Unconfigured.Sort();
    if(!Q.Unconfigured.IsEmpty()&&!Rules.bAllowUnconfigured)
    {Q.Reason=TEXT("产出未配置；当前规则禁止无产出焚化，物品可随时取回");return Q;}
    Q.bValid=true;return Q;
}
bool Prepare(UColdSteelStatusModel& Model,const FQuote& Q,const FRules& Rules,FColdSteelProfile& Next,FString& Reason)
{
    const auto State=Model.Snapshot();
    if(!Q.bValid||Q.Generation!=State.Generation||Q.RuleSignature!=Rules.Signature)
    {Reason=TEXT("物品或产出规则已变化，请重新确认");return false;}
    const auto Current=Quote(State,Q.Container,Rules);
    if(!Current.bValid){Reason=Current.Reason;return false;}
    if(Current.Inputs.Num()!=Q.Inputs.Num()){Reason=TEXT("投入物品已变化，请重新确认");return false;}
    for(const auto& I:Q.Inputs)
    {
        const auto* Found=Current.Inputs.FindByPredicate([&](const auto& V){return V.InstanceId==I.InstanceId;});
        if(!Found||!FColdSteelItem::StaticStruct()->CompareScriptStruct(&I,Found,0))
        {Reason=TEXT("投入物品内容或数量已变化，请重新确认");return false;}
    }
    auto Candidate=State;
    for(const auto& I:Current.Inputs)
    {Candidate.Items.RemoveAll([&](const auto& V){return V.InstanceId==I.InstanceId;});ClearReferences(Candidate,I.InstanceId);}
    for(const auto& Product:Current.Products)
    {
        if(const auto* Ammo=Model.AmmoType(Product.Item))
        {
            if(!Ammo->Enabled||!Model.AddAmmoToState(Candidate,Product.Item,Product.Count))
            {Reason=TEXT("产物弹药不可用或弹药袋已满；投入物品未销毁");return false;}
        }
        else
        {
            auto Item=Model.CreateItem(Product.Item,Product.Count);
            if(Item.Data.IsEmpty()){Reason=TEXT("产出规则引用了不存在的物品：")+Product.Item;return false;}
            if(!ColdSteelInventory::Insert(Candidate.Items,Item))
            {Reason=TEXT("背包放不下预计收获；请整理背包后再焚化");return false;}
        }
    }
    if(!ColdSteelInventory::Validate(Candidate,Reason))return false;
    Next=MoveTemp(Candidate);Reason.Reset();return true;
}
FString InputSignature(const UColdSteelStatusModel& Model,const FQuote& Q)
{
    auto Inputs=Q.Inputs;
    Inputs.Sort([](const auto& A,const auto& B){return A.InstanceId<B.InstanceId;});
    FString Text=Q.Container+TEXT("\n");
    for(auto I:Inputs)
    {
        // Use the same catalog normalization as profile uploads. Compare JSON values,
        // not whitespace/key order introduced by server sanitization of Item.Data.
        if(Model.GetWorld()&&Model.GetWorld()->GetNetMode()!=NM_Standalone&&!Model.SanitizeNetworkItem(I))return {};
        I.Cooldown=0.f;FString Json;TSharedPtr<FJsonObject> Object,Data;
        if(!FJsonObjectConverter::UStructToJsonObjectString(I,Json)
            ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Object)
            ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data))return {};
        Object->SetObjectField(TEXT("data"),Data);
        const auto Sorted=CanonicalValue(MakeShared<FJsonValueObject>(Object))->AsObject();
        Json.Reset();FJsonSerializer::Serialize(Sorted.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Json));
        Text+=Json+TEXT("\n");
    }
    FTCHARToUTF8 Bytes(*Text);FSHAHash Hash;
    FSHA1::HashBuffer(Bytes.Get(),Bytes.Length(),Hash.Hash);return Hash.ToString();
}
bool CanReachStation(const APawn* Pawn,const AVoxelBuildPrefabActor* Piece,bool bCheckObstruction)
{
    if(!IsValid(Pawn)||!IsValid(Piece)||Pawn->GetWorld()!=Piece->GetWorld()||!Piece->Body())return false;
    const auto* Character=Cast<AFPSGAMECharacter>(Pawn);
    const FVector Eye=Character?Character->GetMeleeAimTransform().GetLocation():Pawn->GetPawnViewLocation();
    const FVector Near=Piece->Body()->Bounds.GetBox().GetClosestPointTo(Eye);
    if(FVector::DistSquared(Eye,Near)>FMath::Square(ColdSteelWorldInteraction::DefaultUseReach))return false;
    if(!bCheckObstruction)return true;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IncineratorReach),false,Pawn);
    return !Pawn->GetWorld()->LineTraceSingleByChannel(Hit,Eye,Near,ECC_Visibility,Query)||Hit.GetActor()==Piece;
}

bool ExecuteAuthority(UColdSteelStatusModel& Model,AActor* Station,const FString& ExpectedInputs,const FString& ExpectedRules,const FString& GuestSlot,FString& Reason)
{
    auto* Piece=Cast<AVoxelBuildPrefabActor>(Station);
    auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    auto* Pawn=Model.RuntimePawn();const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Piece||!World||!Pawn||!Health||Health->IsDead()||!Piece->HasAuthority()||Piece->GetWorld()!=Pawn->GetWorld()
        ||Piece->IsFalling()||Piece->PrefabId()!=VoxelIncineratorId||World->PrefabActorAt(Piece->AnchorCell())!=Piece)
    {Reason=TEXT("焚化炉不可用或距离过远，请重新靠近并打开");return false;}
    if(!CanReachStation(Pawn,Piece,true))
    {Reason=TEXT("请靠近焚化炉未被遮挡的操作面");return false;}
    Model.SyncRuntime();const auto Rules=LoadRules();
    const auto Q=Quote(Model.Snapshot(),World->IncineratorContainerAt(Piece->AnchorCell()),Rules);
    if(!Q.bValid){Reason=Q.Reason;return false;}
    if(ExpectedInputs.IsEmpty()||ExpectedInputs!=InputSignature(Model,Q)||ExpectedRules!=Rules.Signature)
    {Reason=TEXT("投入物品或回收规则已变化，未执行焚化；请重新确认");return false;}
    FColdSteelProfile Next;if(!Prepare(Model,Q,Rules,Next,Reason))return false;
    // Destruction is irreversible even offline: uncertain disk writes must freeze
    // later saves instead of letting the old in-memory inventory overwrite them.
    const bool Saved=Model.CommitCampfireState(MoveTemp(Next),TEXT("Inventory"),GuestSlot);
    if(!Saved){Reason=Model.ResultMessage();return false;}
    Piece->PresentIncineration();
    Reason=Q.Products.IsEmpty()?TEXT("焚化已保存 · 无回收产物 · 炉体正在排烟"):TEXT("焚化已保存 · 产物已放入背包／弹药袋");return true;
}
bool NormalizeAmmoInput(const UColdSteelStatusModel& Model,FColdSteelItem& I)
{
    const auto* Ammo=Model.AmmoType(I.Definition);
    if(!I.bIncineratorAmmo||!Ammo||I.InstanceId.IsEmpty()||I.InstanceId.Len()>128
        ||I.Place!=4||!IsContainer(I.Container)||I.Container.Len()>256
        ||I.Count<=0||I.Count>ColdSteelAmmo::MaxCount||I.Width!=1||I.Height!=1
        ||I.Magazine!=0||I.Reserve!=0||I.VirtualMagazineAmmo!=0)return false;
    // Retain exact count and container/cell; rebuild only host-owned display data.
    I.StackMax=ColdSteelAmmo::MaxCount;I.Cooldown=0.f;I.bRotated=false;I.LoadedAmmoType.Reset();
    auto Data=MakeShared<FJsonObject>();Data->SetStringField(TEXT("name"),Model.AmmoLabel(I.Definition));
    Data->SetStringField(TEXT("category"),TEXT("ammo"));Data->SetNumberField(TEXT("grid_w"),1);Data->SetNumberField(TEXT("grid_h"),1);
    Data->SetNumberField(TEXT("maxStack"),double(ColdSteelAmmo::MaxCount));Data->SetStringField(TEXT("icon"),Ammo->Icon);
    I.Data.Reset();return FJsonSerializer::Serialize(Data,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&I.Data));
}
bool DepositAmmo(UColdSteelStatusModel& Model,const FString& Ammo,int64 Count,FString& Reason,int32 Cell)
{
    if(!Model.bIncineratorOpen||!IsContainer(Model.ActiveContainer)||!Model.AmmoType(Ammo))
    {Reason=TEXT("请先打开焚化炉投入区");return false;}
    Model.SyncRuntime();auto State=Model.Snapshot();
    if(Count<=0||Count>Limit||State.AmmoPouch.FindRef(Ammo)<Count)
    {Reason=TEXT("弹药袋数量不足或已变化");return false;}
    FColdSteelItem I;I.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);I.Definition=Ammo;
    I.Count=Count;I.StackMax=Limit;I.Place=4;I.Container=Model.ActiveContainer;I.bIncineratorAmmo=true;I.Magazine=I.Reserve=0;
    if(!NormalizeAmmoInput(Model,I)){Reason=TEXT("弹药暂存数据无效，弹药仍在弹药袋");return false;}
    if(Cell>=0)
    {
        const int32 Target=ColdSteelInventory::Owner(State.Items,4,Cell,I.Container);
        if(Target>=0)
        {
            auto& Existing=State.Items[Target];
            if(!ColdSteelInventory::Compatible(Existing,I)||Existing.StackMax-Existing.Count<Count)
            {Reason=TEXT("目标格不能容纳这些弹药，请选空格或减少数量");return false;}
            Existing.Count+=Count;
        }
        else
        {
            if(!ColdSteelWarehouse::Fits(State.Items,I,Cell,Model.OpenStorageCapacity()))
            {Reason=TEXT("目标格不可用；弹药仍在弹药袋");return false;}
            I.Cell=Cell;State.Items.Add(I);
        }
    }
    else if(!ColdSteelWarehouse::Insert(State.Items,I,Model.OpenStorageCapacity()))
    {Reason=TEXT("投入区没有空间；弹药仍在弹药袋");return false;}
    State.AmmoPouch.FindOrAdd(Ammo)-=Count;
    if(!Model.CommitState(MoveTemp(State))){Reason=Model.ResultMessage();return false;}
    Reason=FString::Printf(TEXT("已暂存 %lld 发／支弹药；可右键取回"),Count);return true;
}
bool Retrieve(UColdSteelStatusModel& Model,const FString& Container,FString& Reason)
{
    if(!Container.IsEmpty()&&!IsContainer(Container))return false;
    Model.SyncRuntime();auto State=Model.Snapshot();const auto Original=State.Items;int32 Moved=0,Blocked=0;
    for(const auto& I:Original)if(InContainer(I,Container))
    {
        if(I.bIncineratorAmmo)
        {
            if(!Model.AddAmmoToState(State,I.Definition,I.Count)){++Blocked;continue;}
            State.Items.RemoveAll([&](const auto& V){return V.InstanceId==I.InstanceId;});++Moved;
        }
        else
        {
            const int32 Capacity=FMath::Max(1,State.StoragePages.FindRef(I.Container))*ColdSteelWarehouse::CellsPerPage;
            auto R=ColdSteelWarehouse::Transfer(State.Items,I.InstanceId,0,-1,Capacity,0,-1,I.Container);
            if(!R.bValid){++Blocked;continue;}State.Items=MoveTemp(R.Items);++Moved;
        }
    }
    if(Moved&&!Model.CommitState(MoveTemp(State))){Reason=Model.ResultMessage();return false;}
    Reason=FString::Printf(TEXT("已取回 %d 件；%d 件因容量不足保留在暂存区"),Moved,Blocked);
    return Moved>0;
}
FString Describe(const FQuote& Q,const UColdSteelStatusModel& Model,bool Confirmation)
{
    TArray<FString> Lines;
    if(!Q.Unconfigured.IsEmpty())Lines.Add(FString::Printf(TEXT("%d 种投入物无回收产物，将直接销毁"),Q.Unconfigured.Num()));
    if(Q.Products.IsEmpty())Lines.Add(TEXT("预计收获：无物品"));
    for(const auto& P:Q.Products)Lines.Add(FString::Printf(TEXT("%s × %lld"),Model.AmmoType(P.Item)?*Model.AmmoLabel(P.Item):*Name(Model.CreateItem(P.Item)),P.Count));
    if(Confirmation)
    {
        Lines.Insert(FString::Printf(TEXT("本次焚化 %d 个条目"),Q.Inputs.Num()),0);
        Lines.Add(Q.Products.IsEmpty()?TEXT("本次不获得物品。确认后投入区内物品永久销毁。"):TEXT("确认后销毁投入区内物品，收获放入背包／弹药袋。"));
        Lines.Add(TEXT("改装、强化、附魔与枪内弹药随本体移除，不额外返还。"));
        for(const auto& Input:Q.Inputs)Lines.Add(FString::Printf(TEXT("%s × %lld"),*Name(Input),Input.Count));
    }
    if(!Q.Reason.IsEmpty())Lines.Add(Q.Reason);
    return FString::Join(Lines,TEXT("\n"));
}
bool FSession::Review(UColdSteelStatusModel& Model,const FString& Container,const FRules& Rules)
{Cancel();Model.SyncRuntime();Draft=Quote(Model.Snapshot(),Container,Rules);return Draft.bValid;}
bool FSession::Confirm(UColdSteelStatusModel& Model,const FRules& Rules,FString& Reason,AActor* Station)
{
    auto Q=MoveTemp(Draft);Cancel();
    if(!Model.bIncineratorOpen||Model.ActiveContainer!=Q.Container){Reason=TEXT("焚化会话已关闭，请重新打开");return false;}
    Model.SyncRuntime();FColdSteelProfile Next;
    if(!Prepare(Model,Q,Rules,Next,Reason))return false;
    if(!Model.IsAudit())
    {
        auto* Pawn=Model.RuntimePawn();
        if(Pawn&&Pawn->GetNetMode()!=NM_Standalone)
        {
            auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
            FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Incinerate;
            R.Target=Station;R.Item=InputSignature(Model,Q);R.Mode=Rules.Signature;
            const bool Sent=PS&&PS->RequestInventoryAction(R);
            Reason=Sent?(Pawn->HasAuthority()?TEXT("焚化请求已处理，请查看结果提示"):TEXT("焚化请求已提交，等待服务端确认")):TEXT("物品正在同步，请稍后重新确认");return Sent;
        }
        return ExecuteAuthority(Model,Station,InputSignature(Model,Q),Rules.Signature,FString(),Reason);
    }
    if(!Model.CommitState(MoveTemp(Next))){Reason=Model.ResultMessage();return false;}
    Reason=Q.Products.IsEmpty()?TEXT("已焚化投入物品；本次未获得物品"):TEXT("已焚化，收获已放入背包／弹药袋");return true;
}
}
