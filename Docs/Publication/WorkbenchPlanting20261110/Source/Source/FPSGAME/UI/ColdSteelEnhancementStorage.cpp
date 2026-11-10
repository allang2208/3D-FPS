#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelStatusModel.h"
#include "../FPSGAMEPlayerController.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

const FColdSteelItem* UColdSteelEnhancementSystem::BenchItem() const
{
    const auto* Model=ColdSteelAuthority::Model(this);
    return Model&&!Model->EnhancementItem().InstanceId.IsEmpty()?&Model->EnhancementItem():nullptr;
}
bool UColdSteelStatusModel::CommitEnhancementState(FColdSteelProfile State)
{
    // A write with an uncertain durable outcome must freeze further transfers,
    // just like paid workstation/container transactions.
    TGuardValue<bool> Guard(bSavingTransaction,true);
    return CommitState(MoveTemp(State));
}
bool UColdSteelEnhancementSystem::Transfer(const FString& ItemId,FString& Message)
{
    if(Pending()){Message=TEXT("操作正在处理，请等待服务器确认");return false;}
    auto* PC=Cast<AFPSGAMEPlayerController>(UGameplayStatics::GetPlayerController(this,0));
    if(!PC||!PC->IsEnhancementSessionValid())
    {Message=TEXT("请靠近有效的奥术工作台后操作");return false;}
    const auto* Stored=BenchItem();const FString Expected=Stored?Stored->InstanceId:FString();
    if(GetWorld()->GetNetMode()!=NM_Standalone)
    {
        auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();
        FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Workstation;
        R.Mode=ItemId.IsEmpty()?TEXT("enhancement.retrieve"):TEXT("enhancement.place");
        R.Item=ItemId.IsEmpty()?Expected:ItemId;R.ExpectedBenchId=Expected;
        R.Target=PC->GetEnhancementStation();
        bNetworkPending=true;LastNetworkMessage.Reset();
        const bool Sent=PS&&PS->RequestInventoryAction(R);
        if(!Sent)bNetworkPending=false;
        Message=!Sent?TEXT("背包正在同步，请稍后重试"):bNetworkPending?TEXT("正在保存暂存操作，请稍候"):LastNetworkMessage;
        return Sent&&(bNetworkPending||bLastNetworkSuccess);
    }
    return TransferAuthority(ItemId,Expected,Message);
}
bool UColdSteelEnhancementSystem::TransferAuthority(const FString& ItemId,const FString& ExpectedBenchId,FString& Message)
{
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client){Message=TEXT("等待服务器确认");return false;}
    auto* Model=ColdSteelAuthority::Model(this);if(!Model)return false;
    if(Model->EnhancementItem().InstanceId!=ExpectedBenchId)
    {Message=TEXT("工作台物品已变化，请同步后重试");return false;}
    Model->SyncRuntime();const auto Before=Model->Snapshot();auto Next=Before;
    if(!ItemId.IsEmpty())
    {
        const int32 Source=Next.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==ItemId;});
        if(Source<0||!Supports(Next.Items[Source]))
        {Message=TEXT("请选择背包或装备栏中可加工的装备");return false;}
        auto Incoming=Next.Items[Source];Next.Items.RemoveAt(Source);
        const int32 Preferred=Incoming.Place==0?Incoming.Cell:Incoming.BackpackCell;
        const auto Previous=Next.EnhancementItem;
        if(!Previous.InstanceId.IsEmpty())
        {
            auto Return=Previous;Return.Container.Reset();
            bool Fits=ColdSteelInventory::Insert(Next.Items,Return,Preferred);
            if(!Fits&&ColdSteelInventory::CanRotate(Return))
            {ColdSteelInventory::ApplyOrientation(Return,Return.bRotated?0:1);Fits=ColdSteelInventory::Insert(Next.Items,Return,Preferred);}
            if(!Fits){Message=TEXT("背包没有连续空间放回原装备，两件装备均保持原处");return false;}
        }
        if(!ColdSteelInventory::ReconcileBagCapacity(Before.Items,Next.Items,Message))return false;
        if(Incoming.Place==0)Incoming.BackpackCell=Incoming.Cell;
        Incoming.Place=0;Incoming.Cell=-1;Incoming.Container.Reset();Incoming.Map.Reset();
        Incoming.Position=FVector::ZeroVector;Incoming.WorldRotation=FRotator::ZeroRotator;
        Next.EnhancementItem=MoveTemp(Incoming);
        // Stored equipment cannot still be activated through a quick binding/tool.
        for(auto& Binding:Next.QuickBindings)if(Binding.ItemId==ItemId)Binding={};
        for(int32 N=0;N<Next.Hotbar.Num();++N)if(Next.Hotbar[N]==ItemId)
        {Next.Hotbar[N].Reset();if(Next.HotbarDefinitions.IsValidIndex(N))Next.HotbarDefinitions[N].Reset();}
        if(Next.ActiveProductionTool==ItemId)Next.ActiveProductionTool.Reset();
        Message=Previous.InstanceId.IsEmpty()?TEXT("装备已放入工作台并保存"):TEXT("已替换暂存装备，原装备已返回背包");
    }
    else
    {
        if(Next.EnhancementItem.InstanceId.IsEmpty()){Message=TEXT("工作台暂无暂存装备");return false;}
        auto Return=Next.EnhancementItem;Return.Container.Reset();
        bool Fits=ColdSteelInventory::Insert(Next.Items,Return,Return.BackpackCell);
        if(!Fits&&ColdSteelInventory::CanRotate(Return))
        {ColdSteelInventory::ApplyOrientation(Return,Return.bRotated?0:1);Fits=ColdSteelInventory::Insert(Next.Items,Return,Return.BackpackCell);}
        if(!Fits){Message=TEXT("背包没有连续空间，装备仍安全保存在工作台");return false;}
        Next.EnhancementItem={};Message=TEXT("装备已取回背包并保存");
    }
    if(!Model->CommitEnhancementState(MoveTemp(Next))){Message=Model->ResultMessage();return false;}
    return true;
}
