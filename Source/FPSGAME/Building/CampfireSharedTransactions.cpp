#include "SmeltingSystem.h"
#include "CampfireSharedTypes.h"
#include "ColdSteelCampfire.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Items/FoodSpoilage.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

namespace
{
    FString JournalSlot(const AVoxelBuildWorld* W){return W->SaveSlotName()+TEXT("_CampfireTransaction");}
    bool DeductCampfire(FColdSteelProfile& P,const FString& Def,int64 Count,
        TArray<FColdSteelItem>* Paid=nullptr,const FFoodClockSample* Clock=nullptr)
    {
        for(int32 Place:{0,5,4})for(int32 N=P.Items.Num()-1;N>=0&&Count>0;--N)
        {
            auto& I=P.Items[N];if(I.Definition!=Def||I.Place!=Place||(Place==4&&!I.Container.IsEmpty()))continue;
            if(Clock&&ColdSteelFood::IsExpired(I,*Clock))continue;
            const int64 Take=FMath::Min(Count,I.Count);
            if(Paid)
            {
                auto Portion=I;Portion.Count=Take;
                if(Take<I.Count)Portion.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
                if(Clock)ColdSteelFood::Rebase(Portion,*Clock);
                Paid->Add(MoveTemp(Portion));
            }
            I.Count-=Take;Count-=Take;
            if(I.Count==0)P.Items.RemoveAt(N);
        }
        return Count==0; // P is only a proposal; a partial deduction is never committed.
    }
    bool GrantCampfire(UColdSteelStatusModel* M,FColdSteelProfile& P,const FString& Id,int64 Count)
    {
        if(Count<=0)return true;
        const auto Item=M->CreateItem(Id,Count);
        return !Item.Data.IsEmpty()&&ColdSteelInventory::Insert(P.Items,Item);
    }
    bool ReturnCampfireItem(FColdSteelProfile& P,const FColdSteelItem& Item)
    {
        return Item.Count>0&&!Item.Data.IsEmpty()&&ColdSteelInventory::Insert(P.Items,Item);
    }
}

int64 UColdSteelSmeltingSystem::FreshCampfireCount(const UColdSteelStatusModel* Operator,const FString& Definition)
{
    if(!Operator)return 0;
    const auto Clock=ColdSteelFood::Clock(Operator);
    if(!Clock.Id.IsValid())return 0;
    int64 Count=0;
    for(const auto& Item:Operator->Items())
        if(Item.Definition==Definition&&Item.Count>0
            &&(Item.Place==0||Item.Place==5||(Item.Place==4&&Item.Container.IsEmpty()))
            &&!ColdSteelFood::IsExpired(Item,Clock))Count+=Item.Count;
    return Count;
}

FGuid AVoxelBuildWorld::CampfireIdentity(FIntVector Cell) const
{
    const auto* Piece=Prefabs.FindByPredicate([Cell](const auto& P){return P.Cell==Cell&&P.Id==TEXT("campfire");});
    return Piece?Piece->InstanceId:FGuid();
}
void AVoxelBuildWorld::WriteCampfireState(FIntVector Cell,const FCampfireSharedState& S)
{
    if(!HasAuthority()||GetNetMode()==NM_Client||!IsCampfireAt(Cell))return;
    auto* J=FindSmeltingMutable(Cell);
    if(!J){J=&SmeltingJobs.AddDefaulted_GetRef();J->Cell=Cell;}
    J->Recipe=S.Recipe;J->ProgressSeconds=S.Progress;J->BurnStartTicks=S.BurnTicks;
    J->BatchCount=S.Batch;J->ProducedBatches=S.Produced;J->bCasting=false;
    J->FoodEscrowVersion=S.FoodEscrowVersion;J->Ingredients=S.Ingredients;
    J->FoodClockId=S.FoodClockId;J->FoodSampleDay=S.FoodSampleDay;J->FoodUtcTicks=S.FoodUtcTicks;
    J->bMaterialsWaived=S.bMaterialsWaived;
    J->Queue.Reset();for(const auto& Q:S.Queue)J->Queue.Add({Q.Recipe,Q.Batch,Q.Ingredients,Q.bMaterialsWaived});
    J->Products.Reset();for(const auto& P:S.Products)J->Products.Add({P.Item,P.Count,P.Payload});
    SetFuel(Cell,S.Fuel);SetFurnaceFireTicks(Cell,S.FireTicks);MarkSmeltingDirty();
}
FCampfireSharedState UColdSteelSmeltingSystem::CampfireState(const AVoxelBuildWorld* W,FIntVector Cell) const
{
    FCampfireSharedState S;if(!W)return S;
    const auto Clock=ColdSteelFood::Clock(W);
    auto Fresh=[&](const FColdSteelItem& Item)
    {
        const double Life=ColdSteelFood::LifetimeDays(Item);
        return Life>0.?FMath::Max(0.,Life-ColdSteelFood::AgeDays(Item,Clock)):-1.;
    };
    auto FreshList=[&](const TArray<FColdSteelItem>& Items)
    {
        double Days=-1.;
        for(const auto& Item:Items){const double D=Fresh(Item);if(D>=0.)Days=Days<0.?D:FMath::Min(Days,D);}
        return Days;
    };
    S.Fuel=W->FuelAt(Cell);S.FireTicks=W->FurnaceFireTicks(Cell);S.bSaveBlocked=IsCampfireSaveBlocked(W);
    if(const auto* J=W->FindSmelting(Cell))
    {
        S.Recipe=J->Recipe;S.Progress=J->ProgressSeconds;S.BurnTicks=J->BurnStartTicks;
        S.Batch=J->BatchCount;S.Produced=J->ProducedBatches;
        S.FoodEscrowVersion=J->FoodEscrowVersion;S.Ingredients=J->Ingredients;
        S.FoodClockId=J->FoodClockId;S.FoodSampleDay=J->FoodSampleDay;S.FoodUtcTicks=J->FoodUtcTicks;
        S.bMaterialsWaived=J->bMaterialsWaived;S.FreshDays=FreshList(J->Ingredients);
        for(const auto& Q:J->Queue){auto& R=S.Queue.AddDefaulted_GetRef();R.Recipe=Q.Recipe;R.Batch=Q.Batch;R.Ingredients=Q.Ingredients;R.bMaterialsWaived=Q.bMaterialsWaived;R.FreshDays=FreshList(Q.Ingredients);}
        for(const auto& P:J->Products){auto& R=S.Products.AddDefaulted_GetRef();R.Item=P.Item;R.Count=P.Count;R.Payload=P.Payload;R.FreshDays=Fresh(P.Payload);}
    }
    return S;
}
bool UColdSteelSmeltingSystem::IsCampfireSaveBlocked(const AVoxelBuildWorld* W) const
{
    return CampfireBlockedWorlds.Contains(const_cast<AVoxelBuildWorld*>(W));
}
void UColdSteelSmeltingSystem::RecoverCampfireJournal(AVoxelBuildWorld* W)
{
    if(!W||!W->HasAuthority()||W->GetNetMode()==NM_Client)return;
    const FString Slot=JournalSlot(W);
    if(!UGameplayStatics::DoesSaveGameExist(Slot,0))return;
    CampfireBlockedWorlds.Add(W);
    auto* J=Cast<UColdSteelCampfireJournal>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!J||J->WorldKey!=W->BuildingWorldKey()||J->InventoryRevision<=0)return; // Preserve unreadable evidence; no guessed rollback.
    int64 Revision=-1;
    if(J->bGuest)
    {
        if(!UGameplayStatics::DoesSaveGameExist(J->PlayerSlot,0))Revision=0;
        else if(auto* Save=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(J->PlayerSlot,0)))
            Revision=Save->Profile.CampfireWorldReceipts.FindRef(J->WorldKey);
    }
    else if(const auto* M=Model();M&&M->ProfileSlot()==J->PlayerSlot)Revision=M->Snapshot().CampfireWorldReceipts.FindRef(J->WorldKey);
    if(Revision<0)return;
    if(Revision>J->InventoryRevision)return; // A newer same-world receipt cannot precede clearing this journal.
    if(Revision==J->InventoryRevision)
    {
        // The durable player debit/credit committed. Redo the station side exactly once,
        // before cooking resumes; never write a player's profile from this journal.
        if(W->CampfireIdentity(J->Cell)==J->InstanceId)
        {W->WriteCampfireState(J->Cell,J->After);if(!W->FlushCampfirePersistence())return;}
    }
    if(!UGameplayStatics::DeleteGameInSlot(Slot,0))return;
    CampfireBlockedWorlds.Remove(W);
}

bool UColdSteelSmeltingSystem::ExecuteCampfire(AVoxelBuildWorld* W,FIntVector Cell,UColdSteelStatusModel* Operator,
    AColdSteelPlayerState* Guest,uint8 Action,FName Recipe,int64 Batch,FString& Reason)
{
    if(!W||!W->HasAuthority()||!W->IsReady()||W->GetNetMode()==NM_Client||!W->IsCampfireAt(Cell)||!Operator||Action>3)
    {Reason=TEXT("篝火或操作者未就绪");return false;}
    if(IsCampfireSaveBlocked(W))
    {Reason=TEXT("篝火保存尚待恢复，请保留存档并重新进入主机世界");return false;}
    // Building removal already stages this operator and the complete building snapshot
    // in the shared inventory transaction. Do not nest a separate campfire journal.
    const bool bStagedTeardown=Action==3&&Operator->IsStagingNetworkContainer();
    const FString PlayerSlot=Guest?Guest->CampfireGuestSlot():Operator->ProfileSlot();
    if((!bStagedTeardown&&PlayerSlot.IsEmpty())||(Guest&&Guest->GetShadowModel()!=Operator))
    {Reason=TEXT("操作者档案未就绪");return false;}
    SettleCampfire(W,Cell);
    FCampfireSharedState After=CampfireState(W,Cell);
    const auto FoodClock=ColdSteelFood::Clock(W);
    if(!FoodClock.Id.IsValid()||(W->FindSmelting(Cell)&&After.FoodEscrowVersion!=1))
    {Reason=TEXT("篝火食物时间或旧档原料尚未就绪，物品仍保留");return false;}
    // A failed conversion deliberately leaves original evidence in the station.
    // Do not let collection/removal bypass that failure by returning expired raw food.
    auto Unsettled=[&](const FColdSteelItem& Item)
    {return ColdSteelFood::LifetimeDays(Item)>0.&&(Item.FoodVersion!=1||Item.FoodClockId!=FoodClock.Id||ColdSteelFood::IsExpired(Item,FoodClock));};
    if(After.Ingredients.ContainsByPredicate(Unsettled)
        ||After.Queue.ContainsByPredicate([&](const auto& Q){return Q.Ingredients.ContainsByPredicate(Unsettled);})
        ||After.Products.ContainsByPredicate([&](const auto& Product)
            {return Unsettled(Product.Payload)||Product.Item!=Product.Payload.Definition
                ||Product.Count!=Product.Payload.Count||Product.Payload.Data.IsEmpty();}))
    {Reason=TEXT("篝火食物腐败转换尚未完成，原物品保留，请稍后重试");return false;}
    After.FoodEscrowVersion=1;
    After.FoodClockId=FoodClock.Id;After.FoodSampleDay=FoodClock.Day;After.FoodUtcTicks=FDateTime::UtcNow().GetTicks();
    Operator->SyncRuntime();auto P=Operator->Snapshot();
    if(P.CampfireInventoryRevision==MAX_int64){Reason=TEXT("档案版本已达上限");return false;}
    for(const auto& Intent:P.SmeltIntents)
        if(Intent.WorldKey==W->BuildingWorldKey()&&FIntVector(Intent.X,Intent.Y,Intent.Z)==Cell)
        {Reason=TEXT("旧篝火操作尚待存档恢复");return false;}
    if(Action==0)
    {
        if(After.Fuel+Fuel.SecondsPerUnit>Fuel.Capacity+1e-6){Reason=TEXT("篝火燃料仓已满");return false;}
        if(!DeductCampfire(P,Fuel.Item,1)){Reason=TEXT("缺少木材（背包与仓库）");return false;}
        After.Fuel+=Fuel.SecondsPerUnit;After.FireTicks=FDateTime::UtcNow().GetTicks();
        Reason=TEXT("已添加 1 份木材，篝火燃料全员共享");
    }
    else if(Action==1)
    {
        const auto* R=Find(Recipe);
        if(!R||!R->bCampfire||Batch<1||Batch>5||R->InputCount>MAX_int64/Batch||R->OutputCount>CastingCapacity)
        {Reason=TEXT("菜谱或投料数量无效");return false;}
        if(After.Queue.Num()>=CastingQueueCapacity){Reason=TEXT("烧烤队列已满（8 项）");return false;}
        if(Operator->CreateItem(R->Input).Data.IsEmpty()||Operator->CreateItem(R->Output).Data.IsEmpty())
        {Reason=TEXT("菜谱食材或成品尚未接入");return false;}
        TArray<FColdSteelItem> Paid;
        const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(Operator);
        if(Free)
        {
            auto Item=Operator->CreateItem(R->Input,R->InputCount*Batch);
            ColdSteelFood::Stamp(Item,FoodClock);Paid.Add(MoveTemp(Item));
        }
        else if(!DeductCampfire(P,R->Input,R->InputCount*Batch,&Paid,&FoodClock))
        {Reason=TEXT("新鲜食材不足，腐败食物不能用于烹饪");return false;}
        if(After.Recipe.IsNone())
        {After.Recipe=Recipe;After.Batch=Batch;After.Progress=0;After.Produced=0;After.Ingredients=MoveTemp(Paid);After.bMaterialsWaived=Free;}
        else {auto& Q=After.Queue.AddDefaulted_GetRef();Q.Recipe=Recipe;Q.Batch=Batch;Q.Ingredients=MoveTemp(Paid);Q.bMaterialsWaived=Free;}
        Reason=Free?TEXT("已免食材加入公共队列；木材照常消耗，免费食材不退料"):TEXT("已加入公共烧烤队列；无燃料时保留进度");
    }
    else if(Action==2)
    {
        int64 Taken=0;
        for(auto& Product:After.Products)
        {
            const int64 Max=FMath::Min(Product.Count,CastingCapacity);
            for(int64 N=0;N<Max;++N)
            {
                auto Portion=Product.Payload;Portion.Count=1;
                if(Product.Count>1)Portion.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
                auto Trial=P;if(!ReturnCampfireItem(Trial,Portion))break;
                P=MoveTemp(Trial);--Product.Count;Product.Payload.Count=Product.Count;++Taken;
            }
        }
        After.Products.RemoveAll([](const auto& E){return E.Count<=0;});
        if(Taken==0){Reason=TEXT("暂无成品或背包空间不足，成品仍保留在篝火");return false;}
        Reason=FString::Printf(TEXT("已领取 %lld 份；剩余成品保留在公共篝火"),Taken);
    }
    else // validated building removal; never exposed by the campfire RPC
    {
        auto Known=[&](FName Id){const auto* R=Find(Id);return R&&R->bCampfire;};
        if((!After.Recipe.IsNone()&&!Known(After.Recipe))||After.Queue.ContainsByPredicate([&](const auto& Q){return !Known(Q.Recipe);}))
        {Reason=TEXT("篝火仍有缺失菜谱的订单，保留订单并恢复菜谱后再拆除");return false;}
        bool Ok=true;
        for(const auto& Product:After.Products)Ok=Ok&&ReturnCampfireItem(P,Product.Payload);
        if(!After.bMaterialsWaived)for(const auto& Ingredient:After.Ingredients)Ok=Ok&&ReturnCampfireItem(P,Ingredient);
        for(const auto& Q:After.Queue)if(!Q.bMaterialsWaived)for(const auto& Ingredient:Q.Ingredients)Ok=Ok&&ReturnCampfireItem(P,Ingredient);
        Ok=Ok&&GrantCampfire(Operator,P,Fuel.Item,FMath::FloorToInt64(After.Fuel/Fuel.SecondsPerUnit));
        if(!Ok){Reason=TEXT("背包放不下篝火退料，请先领取或整理");return false;}
        After=FCampfireSharedState();
    }
    if(bStagedTeardown)
    {
        // CommitState validates/publishes only while staging. The caller owns the
        // guest slot, durable receipt, building save and rollback as one operation.
        if(!Operator->CommitState(MoveTemp(P)))
        {Reason=Operator->ResultMessage();return false;}
        W->WriteCampfireState(Cell,After);
        return true;
    }
    if(After.Fuel>0&&!After.Recipe.IsNone())After.BurnTicks=FDateTime::UtcNow().GetTicks();
    auto* J=NewObject<UColdSteelCampfireJournal>();
    J->WorldKey=W->BuildingWorldKey();J->Cell=Cell;J->InstanceId=W->CampfireIdentity(Cell);
    J->PlayerSlot=PlayerSlot;J->bGuest=Guest!=nullptr;J->InventoryRevision=P.CampfireInventoryRevision+1;J->After=After;
    // Persist a new station's anchor before debiting a player: recovery needs its identity.
    if(!J->InstanceId.IsValid()||!W->FlushCampfirePersistence())
    {Reason=TEXT("篝火原状态未能保存，材料未转移");return false;}
    if(!UGameplayStatics::SaveGameToSlot(J,JournalSlot(W),0))
    {Reason=TEXT("交易日志保存失败，材料未转移");return false;}
    CampfireBlockedWorlds.Add(W);
    if(!Operator->CommitCampfireState(MoveTemp(P),W->BuildingWorldKey(),Guest?PlayerSlot:FString()))
    {Reason=TEXT("玩家保存未确认，篝火已暂停交易；重进世界后恢复");return false;}
    W->WriteCampfireState(Cell,After);
    if(!W->FlushCampfirePersistence()||!UGameplayStatics::DeleteGameInSlot(JournalSlot(W),0))
    {Reason=TEXT("材料已记账，篝火保存待恢复；重进世界后对账");return Action!=3;}
    CampfireBlockedWorlds.Remove(W);
    SettleCampfire(W,Cell);
    return true;
}
