#include "ColdSteelIncineration.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "String/LexFromString.h"

namespace ColdSteelIncineration
{
bool Accessible(const FColdSteelItem& I)
{
    // Closed chests and world drops are not an extension of the player's workbench inventory.
    return I.Count>0&&I.Container.IsEmpty()&&(I.Place==0||I.Place==1||I.Place==4||I.Place==ColdSteelInventory::ColdSteelCompartment::Place);
}

bool ParseQuantity(const FString& Text,int64& Count)
{
    Count=0;
    if(Text.IsEmpty()||Text.Len()>16)return false;
    for(TCHAR C:Text)if(C<TEXT('0')||C>TEXT('9'))return false;
    return LexTryParseString(Count,*Text)&&Count>0&&Count<=ColdSteelAmmo::MaxCount;
}

FString Location(const FColdSteelItem& I)
{
    if(I.Place==1)return TEXT("已装备 · ")+(ColdSteelInventory::SlotNames().IsValidIndex(I.Cell)?ColdSteelInventory::SlotNames()[I.Cell]:TEXT("装备"));
    if(I.Place==4)return TEXT("主仓库");
    if(I.Place==ColdSteelInventory::ColdSteelCompartment::Place)return TEXT("背包夹层");
    return TEXT("背包");
}

static FString ItemName(const FColdSteelItem& I)
{
    const FString Name=ColdSteelInventory::Text(I,TEXT("name"));
    return Name.IsEmpty()?TEXT("未命名物品"):Name;
}

FColdSteelIncinerationQuote Quote(const FColdSteelProfile& State,const FString& Key,bool bAmmo,int64 Count)
{
    FColdSteelIncinerationQuote Q;Q.Key=Key;Q.bAmmo=bAmmo;Q.Count=Count;Q.Generation=State.Generation;
    if(Key.IsEmpty()||Count<=0||Count>ColdSteelAmmo::MaxCount){Q.Reason=TEXT("请输入有效的销毁数量");return Q;}
    if(bAmmo)
    {
        Q.Available=State.AmmoPouch.FindRef(Key);
        if(Q.Available<Count){Q.Reason=TEXT("弹药袋数量已变化，请重新选择");return Q;}
    }
    else
    {
        const auto* I=State.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Key;});
        if(!I||!Accessible(*I)){Q.Reason=TEXT("物品已移出可用范围；箱内物品请先取出");return Q;}
        Q.Before=*I;Q.Available=I->Count;
        if(I->Count<Count){Q.Reason=TEXT("物品数量已变化，请重新选择");return Q;}
        if(I->Place==1&&I->Cell==14)
        {
            TArray<FString> Blockers;
            for(const auto& V:State.Items)
                if(V.Count>0&&(V.Place==ColdSteelInventory::ColdSteelCompartment::Place
                    ||(V.Place==0&&V.Cell/18+V.Height>4)))
                    Blockers.Add(FString::Printf(TEXT("%s · %s × %lld"),*Location(V),*ItemName(V),V.Count));
            if(!Blockers.IsEmpty())
            {
                Q.Reason=TEXT("请先取出夹层及扩展格中的物品，再销毁背包；不会连带销毁：\n")+FString::Join(Blockers,TEXT("\n"));
                return Q;
            }
        }
    }
    Q.bValid=true;
    return Q;
}

static bool ValidateQuote(const FColdSteelProfile& State,const FColdSteelIncinerationQuote& Q,FString& Reason)
{
    if(!Q.bValid||Q.Generation!=State.Generation){Reason=TEXT("物品数据已变化，请重新查看销毁清单");return false;}
    const auto Current=Quote(State,Q.Key,Q.bAmmo,Q.Count);
    if(!Current.bValid){Reason=Current.Reason;return false;}
    if(Q.Available!=Current.Available||(!Q.bAmmo&&!FColdSteelItem::StaticStruct()->CompareScriptStruct(&Q.Before,&Current.Before,0)))
    {Reason=TEXT("物品内容或数量已变化，请重新查看销毁清单");return false;}
    return true;
}

static void DeductValidated(FColdSteelProfile& Candidate,const FColdSteelIncinerationQuote& Q)
{
    if(Q.bAmmo)
    {
        int64& Amount=Candidate.AmmoPouch.FindChecked(Q.Key);Amount-=Q.Count;
        if(Amount==0)Candidate.AmmoPouch.Remove(Q.Key);
    }
    else
    {
        const int32 Index=Candidate.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Q.Key;});
        Candidate.Items[Index].Count-=Q.Count;
        if(Candidate.Items[Index].Count==0)
        {
            Candidate.Items.RemoveAt(Index);
            // Clear exact-instance references; other stacks and their bindings remain untouched.
            for(auto& B:Candidate.QuickBindings)if(B.ItemId==Q.Key)B=FColdSteelQuickBinding();
            for(int32 N=0;N<Candidate.Hotbar.Num();++N)if(Candidate.Hotbar[N]==Q.Key)
            {Candidate.Hotbar[N].Reset();if(Candidate.HotbarDefinitions.IsValidIndex(N))Candidate.HotbarDefinitions[N].Reset();}
            if(Candidate.ActiveProductionTool==Q.Key)Candidate.ActiveProductionTool.Reset();
        }
    }
}

FColdSteelIncinerationBatch QuoteBatch(const FColdSteelProfile& State,const TArray<FColdSteelIncinerationSelection>& Selections)
{
    FColdSteelIncinerationBatch B;B.Generation=State.Generation;
    if(Selections.IsEmpty()){B.Reason=TEXT("请先勾选要销毁的物品。");return B;}
    TSet<FString> Seen;
    for(const auto& S:Selections)
    {
        const FString Identity=(S.bAmmo?TEXT("ammo:"):TEXT("item:"))+S.Key;
        if(Seen.Contains(Identity)){B.Reason=TEXT("清单包含重复条目，整批未执行。请重新勾选。");return B;}
        Seen.Add(Identity);
        auto Q=Quote(State,S.Key,S.bAmmo,S.Count);
        if(!Q.bValid){B.Reason=FString::Printf(TEXT("第 %d 项不可销毁，整批未执行：\n%s"),B.Entries.Num()+1,*Q.Reason);return B;}
        B.Entries.Add(MoveTemp(Q));
    }
    B.bValid=true;return B;
}

bool ApplyBatch(const FColdSteelProfile& State,const FColdSteelIncinerationBatch& B,FColdSteelProfile& Next,FString& Reason)
{
    if(!B.bValid||B.Entries.IsEmpty()||B.Generation!=State.Generation)
    {Reason=TEXT("清单已失效，整批未执行销毁。请重新勾选并确认。");return false;}
    TSet<FString> Seen;
    for(int32 N=0;N<B.Entries.Num();++N)
    {
        const auto& Q=B.Entries[N];const FString Identity=(Q.bAmmo?TEXT("ammo:"):TEXT("item:"))+Q.Key;
        if(Seen.Contains(Identity)){Reason=TEXT("清单存在重复条目，整批未执行销毁。");return false;}
        Seen.Add(Identity);
        FString Failure;
        // Every capacity/bag check uses the original state, even when its contents are selected too.
        if(!ValidateQuote(State,Q,Failure))
        {Reason=FString::Printf(TEXT("第 %d 项已变化，整批未执行销毁：\n%s"),N+1,*Failure);return false;}
    }
    auto Candidate=State;
    for(const auto& Q:B.Entries)DeductValidated(Candidate,Q);
    FString Failure;
    if(!ColdSteelInventory::Validate(Candidate,Failure)){Reason=TEXT("整批未执行销毁：")+Failure;return false;}
    Next=MoveTemp(Candidate);Reason.Reset();return true;
}

bool Apply(const FColdSteelProfile& State,const FColdSteelIncinerationQuote& Q,FColdSteelProfile& Next,FString& Reason)
{
    FColdSteelIncinerationBatch B;B.bValid=Q.bValid;B.Generation=Q.Generation;B.Entries.Add(Q);
    return ApplyBatch(State,B,Next,Reason);
}

FString Describe(UColdSteelStatusModel& Model,const FColdSteelIncinerationQuote& Q)
{
    if(!Q.bValid)return Q.Reason;
    TArray<FString> Lines;
    Lines.Add(FString::Printf(TEXT("%s × %lld"),Q.bAmmo?*Model.AmmoLabel(Q.Key):*ItemName(Q.Before),Q.Count));
    Lines.Add(Q.bAmmo?TEXT("来源：弹药袋（仅扣除袋内计数）"):TEXT("来源：")+Location(Q.Before));
    if(!Q.bAmmo)
    {
        const auto& I=Q.Before;
        const FString Ammo=Model.AmmoDefinitionFor(I);
        if(Model.AmmoType(Ammo)&&I.Magazine>0)
        {
            const int32 Owned=FMath::Max(0,I.Magazine-I.VirtualMagazineAmmo);
            Lines.Add(FString::Printf(TEXT("一同销毁：已装填 %s × %d；不会退回弹药袋"),*Model.AmmoLabel(Ammo),Owned));
            if(I.VirtualMagazineAmmo>0)Lines.Add(TEXT("训练用虚拟弹药随本体移除，不计入拥有数量。"));
        }
        if(auto* GI=Model.GetGameInstance())
        {
            if(auto* G=GI->GetSubsystem<UGunsmithSystem>())
            {
                auto Parts=G->Installed(I);TArray<FString> Keys;Parts.GetKeys(Keys);Keys.Sort();
                for(const auto& Slot:Keys)
                {
                    const FString& Id=Parts.FindChecked(Slot);
                    if(Id==TEXT("false")||Id.IsEmpty())continue;
                    if(const auto* Part=G->Option(I.Definition,Slot,Id))
                        Lines.Add(TEXT("随本体移除：")+G->CategoryLabel(I.Definition,Slot)+TEXT(" · ")+Part->Name);
                    else Lines.Add(TEXT("随本体移除：")+G->CategoryLabel(I.Definition,Slot)+TEXT("的已保存改造"));
                }
            }
            if(auto* E=GI->GetSubsystem<UColdSteelEnhancementSystem>())
                for(const TCHAR* Slot:{TEXT("prefix"),TEXT("suffix")})
                {const FString Affix=E->Affix(I,Slot);if(!Affix.IsEmpty())Lines.Add(TEXT("随本体移除：附魔 · ")+Affix);}
        }
        const int32 Level=FMath::Max(ColdSteelInventory::Number(I,TEXT("enhanceLevel")),ColdSteelInventory::Number(I,TEXT("tool_enhance_level")));
        if(Level>0)Lines.Add(FString::Printf(TEXT("随本体移除：强化等级 +%d"),Level));
        Lines.Add(TEXT("该实例的全部改造、强化及附魔一并移除，不返还配件或材料。"));
    }
    Lines.Add(TEXT("此操作不可恢复。没有产出，也没有返还。"));
    return FString::Join(Lines,TEXT("\n\n"));
}
FString DescribeBatch(UColdSteelStatusModel& Model,const FColdSteelIncinerationBatch& B)
{
    if(!B.bValid)return B.Reason;
    TArray<FString> Lines;
    for(int32 N=0;N<B.Entries.Num();++N)
        Lines.Add(FString::Printf(TEXT("%d / %d\n"),N+1,B.Entries.Num())+Describe(Model,B.Entries[N]));
    return FString::Join(Lines,TEXT("\n\n────────────────────\n\n"));
}
}

bool FColdSteelIncinerationSession::Review(UColdSteelStatusModel& Model,const FString& Key,bool bAmmo,int64 Count)
{
    Cancel();if(bCommitting)return false;
    Model.SyncRuntime();Draft=ColdSteelIncineration::Quote(Model.Snapshot(),Key,bAmmo,Count);return Draft.bValid;
}
bool FColdSteelIncinerationSession::Confirm(UColdSteelStatusModel& Model,FString& Reason)
{
    if(bCommitting||!Draft.bValid){Reason=TEXT("请先选择物品并查看销毁清单");return false;}
    TGuardValue<bool> Guard(bCommitting,true);
    const auto Accepted=Draft;Cancel(); // Consume before synchronous saving or OnChanged callbacks.
    Model.SyncRuntime();FColdSteelProfile Next;
    if(!ColdSteelIncineration::Apply(Model.Snapshot(),Accepted,Next,Reason))return false;
    if(!Model.CommitState(MoveTemp(Next))){Reason=Model.ResultMessage();return false;}
    Reason=TEXT("已销毁并保存；无产出、无返还。");return true;
}

bool FColdSteelIncinerationBatchSession::Review(UColdSteelStatusModel& Model,const TArray<FColdSteelIncinerationSelection>& Selections)
{
    if(bCommitting)return false;
    Cancel();Model.SyncRuntime();Draft=ColdSteelIncineration::QuoteBatch(Model.Snapshot(),Selections);return Draft.bValid;
}
bool FColdSteelIncinerationBatchSession::Confirm(UColdSteelStatusModel& Model,FString& Reason)
{
    if(bCommitting||!Draft.bValid){Reason=TEXT("请先勾选物品并核对批量销毁清单。");return false;}
    TGuardValue<bool> Guard(bCommitting,true);const auto Accepted=Draft;Cancel();
    Model.SyncRuntime();FColdSteelProfile Next;
    if(!ColdSteelIncineration::ApplyBatch(Model.Snapshot(),Accepted,Next,Reason))return false;
    // Exactly one durable transaction for the whole batch; no per-entry save or intermediate publish.
    if(!Model.CommitState(MoveTemp(Next))){Reason=TEXT("保存失败，整批库存保持原样。请重新勾选。\n")+Model.ResultMessage();return false;}
    Reason=FString::Printf(TEXT("已一次性销毁并保存 %d 个条目；无产出、无返还。"),Accepted.Entries.Num());return true;
}
