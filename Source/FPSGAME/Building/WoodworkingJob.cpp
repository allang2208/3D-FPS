#include "WoodworkingSystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "WoodworkingQuality.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelStationNetwork.h"
#include "Engine/GameInstance.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/MemoryReader.h"
#include "HAL/PlatformTime.h"

UColdSteelStatusModel* UWoodworkingSystem::Model() const
{return NetworkModel?NetworkModel.Get():ColdSteelAuthority::Model(this);}

const FColdSteelWoodworkingJob& UWoodworkingSystem::Job() const
{static const FColdSteelWoodworkingJob Empty;const auto* M=Model();return M?M->WoodworkingJob():Empty;}

bool UWoodworkingSystem::PayForJob()
{
    auto* M=Model();const auto* P=Pattern();
    const auto* Recipe=P?GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>()->Find(P->CraftRecipe):nullptr;
    if(!M||!Recipe||HasPendingJob())return false;
    M->SyncRuntime();auto Next=M->Snapshot();
    for(const auto& Input:Recipe->Inputs)
    {
        int64 Left=Input.Count;
        for(int32 Place:{0,5,4})for(int32 Index=Next.Items.Num()-1;Index>=0&&Left>0;--Index)
        {
            auto& Item=Next.Items[Index];
            if(Item.Place!=Place||(Place==4&&!Item.Container.IsEmpty())||Item.Definition!=Input.Item)continue;
            const int64 Taken=FMath::Min(Item.Count,Left);Item.Count-=Taken;Left-=Taken;
            if(Item.Count==0)Next.Items.RemoveAt(Index);
        }
        if(Left>0){Notice=TEXT("材料已变化，请重新准备工件");return false;}
    }
    auto& Pending=Next.WoodworkingJob;Pending={};
    Pending.Id=FGuid::NewGuid().ToString(EGuidFormats::Digits);Pending.Pattern=P->Id;
    Pending.Recipe=Recipe->Id;Pending.Name=P->Name;Pending.Item=M->CreateItem(Recipe->Output,Recipe->OutputCount);
    if(Pending.Item.Data.IsEmpty()){Notice=TEXT("成品数据尚未就绪，未扣除材料");return false;}
    for(const auto& Input:Recipe->Inputs)Pending.PaidMaterials.FindOrAdd(Input.Item)+=Input.Count;
    FString Error;if(!Board.Initialize(Rules,P->Outline,P->Connections,Error)){Notice=Error;return false;}
    FrozenElapsed=0;bCheckpointReady=true;WriteCheckpoint(Pending.Mask);
    if(!M->CommitState(MoveTemp(Next))){Notice=M->ResultMessage();return false;}
    AcceptedRecipe=*Recipe;return true;
}

void UWoodworkingSystem::BeginPaidRun()
{
    const auto* P=Pattern();if(!P)return;
    FString Error;if(!Board.Initialize(Rules,P->Outline,P->Connections,Error)){Notice=Error;return;}
    SessionMode=EWoodworkingMode::Craft;bPractice=false;bFeeding=bUndoPose=false;
    FrozenElapsed=0;StartedAt=FPlatformTime::Seconds();Phase=EWoodworkingPhase::Running;bMotorOn=false;bCheckpointReady=true;
    NextCheckpointAt=StartedAt+5;
    Notice=TEXT("材料已投入 · 先调整木板方向，按空格进入切割；加工结束后返回工作面板结算。");
}

bool UWoodworkingSystem::SaveResult()
{
    if(ColdSteelStationNet::IsClient(this))return true;
    auto* M=Model();if(!M||!HasPendingJob())return false;
    if(Job().bFinished)return true;
    const auto Metrics=Board.Metrics();const FString Summary=ResultSummary();const double Score=Quality();
    M->SyncRuntime();auto Next=M->Snapshot();auto& Pending=Next.WoodworkingJob;
    Pending.bFinished=true;Pending.bPassed=Phase==EWoodworkingPhase::Complete;
    Pending.Elapsed=FrozenElapsed;Pending.Quality=Score;Pending.Clearance=Metrics.Clearance;
    Pending.Integrity=Metrics.Integrity;Pending.EdgeFit=Metrics.EdgeFit;Pending.Result=Summary;
    if(Pending.bPassed&&!ColdSteelWoodQuality::Apply(Pending.Item,Score))
    {Notice=TEXT("工艺属性写入失败，工件保留，请重试结算");return false;}
    if(Pending.bPassed&&ColdSteelWoodQuality::Channel(Pending.Item)!=ColdSteelWoodQuality::EChannel::None)
        Pending.Result+=FString::Printf(TEXT("\n木工评分 %.1f / 100 · %s %+.1f%%"),Score,*ColdSteelWoodQuality::StatLabel(Pending.Item),(ColdSteelWoodQuality::FromScore(Score)-1)*100);
    WriteCheckpoint(Pending.Mask);
    if(!M->CommitState(MoveTemp(Next))){Notice=M->ResultMessage()+TEXT(" · 工件保留，请重试结算");return false;}
    return true;
}

bool UWoodworkingSystem::RestoreJob()
{
    if(!HasPendingJob())return false;
    const auto Saved=Job();Selected=Saved.Pattern;FrozenElapsed=Saved.Elapsed;
    SessionMode=EWoodworkingMode::Craft;bPractice=false;bMotorOn=bFeeding=false;
    bCheckpointReady=false;ResetBoardPose();
    if(const auto* P=Pattern())
    {
        Rules.Seconds=P->Seconds;Rules.RequiredClearance=P->RequiredClearance;Rules.MaximumDamage=P->MaximumDamage;
        FString Error;bCheckpointReady=Board.Initialize(Rules,P->Outline,P->Connections,Error);
        if(bCheckpointReady&&!Saved.Mask.IsEmpty())bCheckpointReady=ReadCheckpoint(Saved.Mask);
    }
    Phase=!Saved.bFinished?EWoodworkingPhase::Preview:Saved.bPassed?EWoodworkingPhase::Complete:EWoodworkingPhase::Failed;
    Notice=!Saved.bFinished?(bCheckpointReady?TEXT("加工已暂停 · 可继续加工，无需再次投入材料。"):TEXT("工件进度无法读取，已保留投入记录，可废弃返还一半材料。")):
        Saved.bPassed?TEXT("工件已完成 · 领取成品，或废弃返还一半材料。"):TEXT("工件未达标 · 可废弃返还一半投入材料。");
    return true;
}

// Keep checkpoints in the existing job payload; old raw masks remain readable.
void UWoodworkingSystem::WriteCheckpoint(TArray<uint8>& Bytes)
{
    Bytes.Reset();FMemoryWriter Writer(Bytes);uint32 Magic=0x57574B32,Version=1;
    bool StrokeChanged=bFeeding&&StrokeRevision!=Board.Revision();
    Writer<<Magic<<Version<<BoardPose.Offset<<BoardPose.Angle<<UndoPose.Offset<<UndoPose.Angle
        <<StrokePose.Offset<<StrokePose.Angle<<bUndoPose<<StrokeChanged;
    Board.SerializeNetwork(Writer);
}
bool UWoodworkingSystem::ReadCheckpoint(const TArray<uint8>& Bytes)
{
    if(Bytes.Num()<int32(sizeof(uint32)))return false;
    FMemoryReader Reader(Bytes);uint32 Magic=0,Version=0;Reader<<Magic;
    if(Magic!=0x57574B32)return Board.RestoreNetwork(Bytes);
    bool StrokeChanged=false;Reader<<Version;if(Version!=1)return false;
    Reader<<BoardPose.Offset<<BoardPose.Angle<<UndoPose.Offset<<UndoPose.Angle
        <<StrokePose.Offset<<StrokePose.Angle<<bUndoPose<<StrokeChanged;
    if(Reader.IsError()||BoardPose.Offset.ContainsNaN()||!FMath::IsFinite(BoardPose.Angle)
        ||UndoPose.Offset.ContainsNaN()||!FMath::IsFinite(UndoPose.Angle)
        ||StrokePose.Offset.ContainsNaN()||!FMath::IsFinite(StrokePose.Angle))return false;
    TArray<uint8> Mask;Mask.Append(Bytes.GetData()+Reader.Tell(),Bytes.Num()-Reader.Tell());
    if(!Board.RestoreNetwork(Mask))return false;
    Board.EndStroke();
    if(StrokeChanged){UndoPose=StrokePose;bUndoPose=true;}
    return true;
}
bool UColdSteelStatusModel::CommitWoodworkingProgress(const FColdSteelWoodworkingJob& SavedJob)
{
    if(SavedJob.Id.IsEmpty()||SavedJob.Id!=Current.WoodworkingJob.Id||Current.WoodworkingJob.bFinished)return false;
    SyncRuntime();auto Next=Snapshot();Next.WoodworkingJob=SavedJob;
    // A progress checkpoint must not re-equip the pawn or interrupt other actions.
    return PersistState(MoveTemp(Next),false);
}
bool UWoodworkingSystem::SaveCheckpoint()
{
    if(!HasPendingJob()||Job().bFinished)return true;
    if(Phase==EWoodworkingPhase::Complete||Phase==EWoodworkingPhase::Failed)return SaveResult();
    if(ColdSteelStationNet::IsClient(this))return true;
    if(!bCheckpointReady)return false;
    auto Saved=Job();const auto Metrics=Board.Metrics();Saved.Elapsed=Elapsed();Saved.Quality=Quality();
    Saved.Clearance=Metrics.Clearance;Saved.Integrity=Metrics.Integrity;Saved.EdgeFit=Metrics.EdgeFit;
    WriteCheckpoint(Saved.Mask);
    if(Saved.Elapsed==Job().Elapsed&&Saved.Mask==Job().Mask)return true;
    if(!Model()->CommitWoodworkingProgress(Saved)){Notice=TEXT("加工进度保存失败，当前工件仍保留，请重试暂停保存");return false;}
    NextCheckpointAt=FPlatformTime::Seconds()+5;return true;
}
bool UWoodworkingSystem::CanResume() const
{return bOpen&&HasPendingJob()&&!Job().bFinished&&!bClaiming&&Phase==EWoodworkingPhase::Preview&&bCheckpointReady;}
bool UWoodworkingSystem::Resume()
{
    if(!CanResume())return false;
    if(ColdSteelStationNet::IsClient(this))
    {if(!ColdSteelStationNet::Request(this,TEXT("wood.resume")))return false;bClaiming=true;Notice=TEXT("等待服务器恢复工件");return true;}
    Phase=EWoodworkingPhase::Running;bMotorOn=bFeeding=false;StartedAt=FPlatformTime::Seconds();NextCheckpointAt=StartedAt+5;
    CheckDamage();
    if(Phase==EWoodworkingPhase::Running&&((Rules.bCheckConnections&&!Board.ConnectionsIntact())||Remaining()<=0))Evaluate(Remaining()<=0);
    if(Phase==EWoodworkingPhase::Running)Notice=TEXT("已恢复工件 · 先调整方向，按空格继续切割；材料无需再次投入。");
    return true;
}
bool UWoodworkingSystem::Suspend()
{
    ColdSteelStationNet::FInputScope Scope;if(Scope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),13);
    EndStroke();FrozenElapsed=Elapsed();bMotorOn=bFeeding=false;
    const bool Saved=SaveCheckpoint();
    if(Phase==EWoodworkingPhase::Running)Phase=EWoodworkingPhase::Preview;
    if(Saved&&HasPendingJob()&&!Job().bFinished)Notice=TEXT("加工已暂停 · 进度已保留，可继续加工或废弃返还一半材料。");
    return Saved;
}
void UWoodworkingSystem::NetworkSessionEnded()
{
    // The owning PlayerState channel is gone. Its pending receipt cannot complete here.
    bClaiming=false;bOpen=false;FrozenElapsed=Elapsed();bMotorOn=bFeeding=false;
    Phase=EWoodworkingPhase::Abandoned;Notice=TEXT("联机连接已结束，重新进入工作台后同步工件状态。");
}

bool UWoodworkingSystem::Settle()
{
    ColdSteelStationNet::FInputScope Scope;
    if(Scope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),12);
    if(!HasPendingJob()||bClaiming)return false;
    EndStroke();
    if(Phase==EWoodworkingPhase::Running)Evaluate(false);
    return SaveResult();
}

bool UWoodworkingSystem::GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const
{
    Refund.Reset();
    if(!HasPendingJob()||Phase==EWoodworkingPhase::Running||bClaiming)
    {Reason=TEXT("请先结束加工并结算工件");return false;}
    TArray<FString> Materials;Job().PaidMaterials.GetKeys(Materials);Materials.Sort();
    for(const auto& Material:Materials)
    {const int64 Count=Job().PaidMaterials.FindRef(Material)/2;if(Count>0)Refund.Add({Material,Count});}
    Reason.Reset();return true;
}

bool UWoodworkingSystem::Discard()
{
    TArray<FColdSteelCraftingInput> Refund;if(!GetDiscardRefund(Refund,Notice))return false;
    if(ColdSteelStationNet::IsClient(this))
    {
        if(!ColdSteelStationNet::Request(this,TEXT("wood.discard")))return false;
        bClaiming=true;Notice=TEXT("等待服务器返还材料");return true;
    }
    auto* M=Model();if(!M)return false;M->SyncRuntime();auto Next=M->Snapshot();
    for(const auto& Input:Refund)
    {
        auto Material=M->CreateItem(Input.Item,Input.Count);
        if(Material.Data.IsEmpty()||!ColdSteelInventory::Insert(Next.Items,Material))
        {Notice=TEXT("背包无法容纳全部返还材料，工件保留待处理");return false;}
    }
    Next.WoodworkingJob={};
    if(!M->CommitState(MoveTemp(Next))){Notice=M->ResultMessage();return false;}
    Phase=EWoodworkingPhase::Delivered;Notice=TEXT("工件已废弃 · 一半投入材料已返还背包（逐项向下取整）");return true;
}

void UWoodworkingSystem::NetworkTransactionFinished(const FString& Operation,bool Success,const FString& Reason)
{
    bClaiming=false;Notice=Reason;
    if(!Success)return;
    if(Operation==TEXT("wood.start")||Operation==TEXT("wood.resume"))
    {
        if(bOpen&&HasPendingJob()&&!Job().bFinished)
        {RestoreJob();if(bCheckpointReady){Phase=EWoodworkingPhase::Running;StartedAt=FPlatformTime::Seconds();}}
        else if(!bOpen)Close(); // A late receipt must leave the server's paid job paused too.
    }
    else if(Operation==TEXT("wood.claim")||Operation==TEXT("wood.discard"))
    {Phase=EWoodworkingPhase::Delivered;bMotorOn=bFeeding=false;}
}
