#include "AlchemySystem.h"
#include "AlchemyInteractionAssets.h"
#include "AlchemyWorkbenchLayout.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildWorld.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelStationNetwork.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/Controller.h"
#include "GameFramework/GameStateBase.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "HAL/PlatformTime.h"

namespace
{
double AlchemyNumber(const FJsonObject& J,const TCHAR* Key,double Default)
{double N=Default;J.TryGetNumberField(Key,N);return FMath::IsFinite(N)?N:Default;}
FString AlchemyString(const FJsonObject& J,const TCHAR* Key)
{FString S;J.TryGetStringField(Key,S);return S;}
bool AlchemyMaterialPlace(const FColdSteelItem& I)
{return I.Place==0||I.Place==5||(I.Place==4&&I.Container.IsEmpty());}
}

bool UColdSteelAlchemySystem::DecodeRecipe(const FString& Raw,FAlchemyRecipe& R)
{
    TSharedPtr<FJsonObject> J;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),J)||!J)return false;
    R={};R.Raw=Raw;R.Id=FName(*AlchemyString(*J,TEXT("id")));R.Name=AlchemyString(*J,TEXT("name"));
    R.Output=AlchemyString(*J,TEXT("output"));R.Description=AlchemyString(*J,TEXT("description"));
    R.Version=int32(AlchemyNumber(*J,TEXT("version"),1));
    J->TryGetBoolField(TEXT("autoBase"),R.AutoBase);J->TryGetBoolField(TEXT("freeBrewing"),R.FreeBrewing);
    R.BottleHeat=FMath::Clamp(float(AlchemyNumber(*J,TEXT("bottleHeat"),40)),30.f,65.f);
    R.BaseCount=FMath::Clamp(int32(AlchemyNumber(*J,TEXT("count"),2)),1,8);
    R.BonusCount=FMath::Clamp(int32(AlchemyNumber(*J,TEXT("bonus"),1)),0,2);
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(J->TryGetArrayField(TEXT("color"),Rows)&&Rows->Num()==3)
        R.Color=FLinearColor(float((*Rows)[0]->AsNumber()),float((*Rows)[1]->AsNumber()),float((*Rows)[2]->AsNumber()));
    if(J->TryGetArrayField(TEXT("inputs"),Rows))for(const auto& V:*Rows)
    {
        const auto O=V->AsObject();if(!O)return false;
        FAlchemyInput I;I.Item=AlchemyString(*O,TEXT("item"));I.Count=int32(AlchemyNumber(*O,TEXT("count"),1));
        if(I.Item.IsEmpty()||I.Count<1||I.Count>16)return false;
        R.Inputs.Add(I);
    }
    if(J->TryGetArrayField(TEXT("steps"),Rows))for(const auto& V:*Rows)
    {
        const auto O=V->AsObject();if(!O)return false;
        FAlchemyStep S;S.Id=AlchemyString(*O,TEXT("id"));S.Action=AlchemyString(*O,TEXT("action"));
        S.Item=AlchemyString(*O,TEXT("item"));S.Text=AlchemyString(*O,TEXT("text"));
        S.Amount=float(AlchemyNumber(*O,TEXT("amount"),1));S.MinHeat=float(AlchemyNumber(*O,TEXT("minHeat"),0));
        S.MaxHeat=float(AlchemyNumber(*O,TEXT("maxHeat"),100));S.Direction=int32(AlchemyNumber(*O,TEXT("direction"),1));
        if(S.Amount<=0||S.Amount>120||S.MinHeat<0||S.MaxHeat>100||S.MinHeat>S.MaxHeat||
            !(S.Action==TEXT("pour")||S.Action==TEXT("grind")||S.Action==TEXT("heat")||S.Action==TEXT("stir")||S.Action==TEXT("cool")))return false;
        R.Steps.Add(S);
    }
    return !R.Id.IsNone()&&!R.Output.IsEmpty()&&R.Inputs.Num()>0&&R.Inputs.Num()<=6&&R.Steps.Num()>0&&R.Steps.Num()<=24;
}
void UColdSteelAlchemySystem::Initialize(FSubsystemCollectionBase& C)
{
    Super::Initialize(C);FString Raw;TSharedPtr<FJsonObject> J;
    if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/alchemy-recipes.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),J)||!J){Notice=TEXT("炼药配方未就绪");return;}
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(J->TryGetArrayField(TEXT("recipes"),Rows))for(const auto& V:*Rows)
    {
        if(!V->AsObject())continue;FString Row;FJsonSerializer::Serialize(V->AsObject().ToSharedRef(),TJsonWriterFactory<>::Create(&Row));
        FAlchemyRecipe R;if(DecodeRecipe(Row,R)&&!Find(R.Id))Catalog.Add(MoveTemp(R));
    }
}
void UColdSteelAlchemySystem::Deinitialize(){Suspend();Release();Super::Deinitialize();}
UColdSteelAlchemySystem* UColdSteelAlchemySystem::CreateNetworkSession(UColdSteelStatusModel* M,const FString& GuestSaveSlot)
{
    auto* Session=NewObject<UColdSteelAlchemySystem>(GetGameInstance());
    Session->Catalog=Catalog;Session->NetworkModel=M;Session->NetworkSaveSlot=GuestSaveSlot;return Session;
}
UColdSteelStatusModel* UColdSteelAlchemySystem::Model() const
{return NetworkModel?NetworkModel.Get():ColdSteelAuthority::Model(this);}
bool UColdSteelAlchemySystem::Saving() const
{const auto* M=Model();return bSaveRetry||(M&&M->HasUnconfirmedTransactionSave());}
const FAlchemyRecipe* UColdSteelAlchemySystem::Find(FName Id) const
{return Catalog.FindByPredicate([Id](const auto& R){return R.Id==Id;});}
const FColdSteelAlchemyJob& UColdSteelAlchemySystem::Job() const
{
    static const FColdSteelAlchemyJob Empty;const auto* M=Model();if(!M)return Empty;
    const auto& Saved=M->AlchemyJob();
    return !Working.Id.IsEmpty()&&Working.Id==Saved.Id&&Working.Revision>=Saved.Revision?Working:Saved;
}
const FAlchemyRecipe* UColdSteelAlchemySystem::Recipe() const
{return HasJob()&&RestoredId==Job().Id&&Accepted.Id==Job().Recipe?&Accepted:nullptr;}
bool UColdSteelAlchemySystem::LoadJob()
{
    auto* M=Model();if(!M)return false;
    const auto Saved=M->AlchemyJob();
    if(Saved.Id.IsEmpty()){Working={};RestoredId.Reset();Accepted={};return true;}
    if(Saved.Id!=RestoredId||Saved.Revision>Working.Revision)
    {
        FAlchemyRecipe R;
        if(!DecodeRecipe(Saved.RecipeSnapshot,R)){Notice=TEXT("配方快照无法读取，批次仍保留，可按面板说明作废退料");Working=Saved;Accepted={};RestoredId.Reset();return false;}
        Accepted=MoveTemp(R);Working=Saved;RestoredId=Saved.Id;
    }
    if(Working.Progress.Num()!=Accepted.Steps.Num()){Notice=TEXT("本炉工序记录不完整，原批次与材料保留");return false;}
    return true;
}
int32 UColdSteelAlchemySystem::StepIndex() const
{
    const auto* R=Recipe();if(!R)return INDEX_NONE;
    for(int32 I=0;I<R->Steps.Num();++I)
        if(!Job().Progress.IsValidIndex(I)||Job().Progress[I]+.001f<R->Steps[I].Amount)return I;
    return R->Steps.Num();
}
bool UColdSteelAlchemySystem::CanGrind(int32 Ingredient) const
{
    const auto* R=Recipe();if(!R||!R->Inputs.IsValidIndex(Ingredient))return false;
    const FString& Id=R->Inputs[Ingredient].Item;
    if(Job().Poured.FindRef(Id)>=Reserved(Id))return false;
    for(int32 I=0;I<R->Steps.Num();++I)if(R->Steps[I].Action==TEXT("grind")&&R->Steps[I].Item==Id&&
        (R->FreeBrewing||(Job().Progress.IsValidIndex(I)&&Job().Progress[I]<R->Steps[I].Amount)))return true;
    return false;
}
float UColdSteelAlchemySystem::Infusion() const
{
    const auto* R=Recipe();if(!R)return 0;float Total=0,Done=0;
    for(int32 I=0;I<R->Steps.Num();++I)if(R->Steps[I].Action==TEXT("stir")||R->Steps[I].Action==TEXT("heat"))
    {Total+=1;if(Job().Progress.IsValidIndex(I))Done+=FMath::Clamp(Job().Progress[I]/R->Steps[I].Amount,0.f,1.f);}
    return Total>0?Done/Total:0;
}
FString UColdSteelAlchemySystem::Observation() const
{
    const auto* R=Recipe();if(!R)return TEXT("配方未就绪");
    if(const auto* B=Bench.Get();B&&B->AlchemyPresentation().Tool==uint8(EAlchemyOp::Grind))
    {
        const int32 Ingredient=B->AlchemyPresentation().Ingredient;
        if(R->Inputs.IsValidIndex(Ingredient))for(int32 I=0;I<R->Steps.Num();++I)
            if(R->Steps[I].Action==TEXT("grind")&&R->Steps[I].Item==R->Inputs[Ingredient].Item&&Job().Progress.IsValidIndex(I))
                return Job().Progress[I]+.001f<R->Steps[I].Amount?TEXT("研钵中仍有粗颗粒"):TEXT("研钵中的粉末已细碎");
    }
    if(Job().ScorchSeconds>3)return TEXT("药液泛褐，出现焦味");
    bool Added=false;for(const auto& I:R->Inputs)if(I.Item!=TEXT("alchemy_pure_base_fluid")&&Job().Poured.FindRef(I.Item)>0)Added=true;
    if(!Added)return Job().Poured.IsEmpty()?TEXT("坩埚尚未加入基液"):TEXT("基液清澈");
    const float Blend=Infusion();const FString Color=Blend<.15f?TEXT("药材浮散，颜色不均"):Blend<.999f?TEXT("药色逐渐融合"):TEXT("药液色泽均匀");
    return Color+(Job().Temperature>80?TEXT("\n药液剧烈翻滚"):Job().Temperature>=55?TEXT("\n药液轻沸"):TEXT(""));
}
bool UColdSteelAlchemySystem::Open(AActor* S,APawn* Pawn)
{
    auto* Piece=Cast<AVoxelBuildPrefabActor>(S);
    if(!Piece||Piece->PrefabId()!=FName(TEXT("potion_workbench"))||!Pawn)return false;
    if(bActive&&(Bench.Get()!=Piece||WorkingPawn.Get()!=Pawn))return false;
    Bench=Piece;WorkingPawn=Pawn;
    if(!Reachable())return false;
    LoadJob();return true;
}
bool UColdSteelAlchemySystem::Reachable() const
{
    const auto* B=Bench.Get();const auto* P=WorkingPawn.Get();
    if(!B||!P||B->GetWorld()!=GetWorld()||B->GetWorld()!=P->GetWorld()||B->IsFalling()||!P->GetController()||P->GetController()->GetPawn()!=P)return false;
    const auto* W=Cast<AVoxelBuildWorld>(B->GetOwner());if(!W||!W->HasPrefabAt(B->AnchorCell())||W->PrefabActorAt(B->AnchorCell())!=B)return false;
    if(const auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return false;
    const FVector Near=B->Body()->Bounds.GetBox().GetClosestPointTo(P->GetPawnViewLocation());
    if(FVector::DistSquared(Near,P->GetPawnViewLocation())>FMath::Square(350.f))return false;
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(AlchemyReach),false,P);
    return !GetWorld()->LineTraceSingleByChannel(Hit,P->GetPawnViewLocation(),Near,ECC_Visibility,Q)||Hit.GetActor()==B;
}
bool UColdSteelAlchemySystem::CanStart(FName Id,FString& Reason) const
{
    const auto* R=Find(Id);auto* M=Model();
    if(!R||!M){Reason=TEXT("配方尚未就绪");return false;}
    if(M->IsCampfireInventoryPending()){Reason=TEXT("背包正在同步，请稍候再开炉");return false;}
    if(Saving()){Reason=M->ResultMessage();if(Reason.IsEmpty())Reason=TEXT("本炉保存尚未确认，请稍候");return false;}
    if(HasJob()||bPending){Reason=TEXT("请先处理本炉或等待操作完成");return false;}
    for(const auto& I:R->Inputs)if(M->CountMaterial(I.Item)<I.Count){Reason=TEXT("材料不足");return false;}
    if(!Reachable()){Reason=TEXT("请靠近有效的药水工作台");return false;}
    if(const auto* B=Bench.Get();B&&B->AlchemyPresentation().Operator&&B->AlchemyPresentation().Operator!=WorkingPawn.Get())
    {Reason=TEXT("另一名玩家正在使用坩埚");return false;}
    Reason.Reset();return true;
}
bool UColdSteelAlchemySystem::CanResume(FString& Reason) const
{
    const auto* M=Model();const auto* R=Recipe();
    if(!M||bPending||M->IsCampfireInventoryPending()){Reason=TEXT("本炉或背包正在同步，请稍候");return false;}
    if(Saving()){Reason=TEXT("本炉保存尚未确认，请稍候");return false;}
    if(bActive){Reason=TEXT("本炉已在炼制中");return false;}
    if(!HasJob()||Job().bFinished){Reason=TEXT("本炉已变化，请先领取或作废成品");return false;}
    if(!R||Job().Progress.Num()!=R->Steps.Num()){Reason=TEXT("本炉配方或工序记录不可用，原批次保留");return false;}
    if(!Reachable()){Reason=TEXT("请靠近有效的药水工作台");return false;}
    if(const auto* B=Bench.Get();B&&B->AlchemyPresentation().Operator&&B->AlchemyPresentation().Operator!=WorkingPawn.Get())
    {Reason=TEXT("另一名玩家正在使用坩埚");return false;}
    // This is an already-paid batch. Inventory quantities are deliberately not
    // checked again; Resume must never route through Pay.
    Reason.Reset();return true;
}
bool UColdSteelAlchemySystem::Acquire()
{
    if(!Reachable()){Notice=TEXT("药水工作台已不可操作");return false;}
    auto S=Bench->AlchemyPresentation();
    if(IsValid(S.Operator)&&S.Operator!=WorkingPawn.Get()){Notice=TEXT("另一名玩家正在使用坩埚");return false;}
    S.Operator=WorkingPawn.Get();Bench->SetAlchemyPresentation(S);return true;
}
void UColdSteelAlchemySystem::Release()
{
    if(auto* B=Bench.Get();B&&B->HasAuthority())
    {
        const auto& State=B->AlchemyPresentation();
        const bool OwnsLiveOperator=WorkingPawn.IsValid()&&State.Operator==WorkingPawn.Get();
        // Logout may destroy the pawn before this session is suspended. Its
        // weak pointer is then empty, while the replicated bench still retains
        // that dead operator. Match the paid batch only when no live owner is
        // present, so a late cleanup cannot release a newly acquired bench.
        const bool OwnsExpiredBatch=!IsValid(State.Operator)&&!Working.Id.IsEmpty()&&State.JobId==Working.Id;
        if(OwnsLiveOperator||OwnsExpiredBatch)B->SetAlchemyPresentation(FAlchemyBenchState{});
    }
}
bool UColdSteelAlchemySystem::Request(const FString& Operation,FName Id)
{
    if(bPending)return false;
    if(!ColdSteelStationNet::Request(this,Operation,Id,1,Bench.Get(),Bench.IsValid()?Bench->AnchorCell():FIntVector::ZeroValue))
    {Notice=TEXT("炼药请求暂未发出，库存可能正在同步，请稍后重试");return false;}
    bPending=true;RequestPawn=WorkingPawn;RequestStateSerial=NetworkStateSerial;RequestInventoryRevision=Model()->InventoryRevision();Notice=TEXT("正在等待服务器保存本炉");return true;
}
bool UColdSteelAlchemySystem::Pay(FName Id)
{
    if(!CanStart(Id,Notice))return false;
    const auto* R=Find(Id);auto* M=Model();M->SyncRuntime();auto Next=M->Snapshot();
    FColdSteelAlchemyJob J;J.Id=FGuid::NewGuid().ToString(EGuidFormats::Digits);J.Recipe=R->Id;J.Name=R->Name;
    J.RecipeSnapshot=R->Raw;J.Revision=1;J.Progress.Init(0,R->Steps.Num());J.Product=M->CreateItem(R->Output,1);
    if(J.Product.Data.IsEmpty()){Notice=TEXT("成品数据未就绪，未扣料");return false;}
    for(const auto& Input:R->Inputs)
    {
        int64 Left=Input.Count;
        for(int32 Place:{0,5,4})for(int32 I=Next.Items.Num()-1;I>=0&&Left>0;--I)
        {
            auto& Item=Next.Items[I];if(Item.Place!=Place||!AlchemyMaterialPlace(Item)||Item.Definition!=Input.Item)continue;
            const int64 Count=FMath::Min(Left,Item.Count);auto Paid=Item;Paid.Count=Count;
            Paid.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);Paid.Place=0;Paid.Cell=-1;Paid.Container.Reset();
            J.Escrow.Add(Paid);Item.Count-=Count;Left-=Count;if(Item.Count==0)Next.Items.RemoveAt(I);
        }
        if(Left){Notice=TEXT("材料已变化，请重新备料");return false;}
    }
    if(R->AutoBase)for(const auto& I:R->Inputs)if(I.Item==TEXT("alchemy_pure_base_fluid"))
    {J.Poured.Add(I.Item,I.Count);J.Opened.Add(I.Item,I.Count);}
    Next.AlchemyJob=J;if(!M->CommitState(MoveTemp(Next))){Notice=M->ResultMessage();return false;}
    Working=J;Accepted=*R;RestoredId=J.Id;return true;
}
bool UColdSteelAlchemySystem::Start(FName Id)
{
    if(bActive||bPending||Saving()||HasJob()){Notice=TEXT("请先处理当前批次");return false;}
    if(ColdSteelStationNet::IsClient(this))return CanStart(Id,Notice)&&Request(TEXT("alchemy.start"),Id);
    if(!Acquire())return false;
    if(!Pay(Id)){Release();return false;}
    bActive=true;bBottling=bTimerRunning=false;HeatLevel=0;HeldTool=EAlchemyOp::Stop;NextActionAt=FPlatformTime::Seconds();NextSaveAt=NextActionAt+5;
    BookPage=0;bHourglassInverted=false;TimerFraction=1;TimerElapsed=0;StirDirection=StirPhase=0;
    Notice=Accepted.AutoBase?TEXT("基液已入锅 · 配方记在手册中"):TEXT("备料已保存 · 配方记在手册中");Publish();return true;
}
bool UColdSteelAlchemySystem::Resume()
{
    if(bActive||bPending||Saving()||!LoadJob()||!CanResume(Notice))return false;
    if(ColdSteelStationNet::IsClient(this))return Request(TEXT("alchemy.resume"));
    if(!Acquire())return false;bActive=true;bBottling=bTimerRunning=false;HeatLevel=0;HeldTool=EAlchemyOp::Stop;
    BookPage=0;bHourglassInverted=false;StirDirection=StirPhase=0;TimerElapsed=0;const int32 Current=StepIndex();
    TimerFraction=!Accepted.FreeBrewing&&Accepted.Steps.IsValidIndex(Current)&&Accepted.Steps[Current].Action==TEXT("heat")&&Working.Progress[Current]>0?Working.Progress[Current]/Accepted.Steps[Current].Amount:1.f;
    NextActionAt=FPlatformTime::Seconds();NextSaveAt=NextActionAt+5;Notice=TEXT("已恢复本炉 · 火力已关闭，无需再次备料");Publish();return true;
}
bool UColdSteelAlchemySystem::ToolBusy() const
{return bBottling||(bActive&&FPlatformTime::Seconds()<NextActionAt);}
bool UColdSteelStatusModel::CommitAlchemyProgress(const FColdSteelAlchemyJob& J,const FString& GuestSaveSlot)
{
    if(J.Id.IsEmpty()||J.Id!=Current.AlchemyJob.Id||J.Revision<Current.AlchemyJob.Revision)return false;
    if(bNetShadowProfile&&GuestSaveSlot.IsEmpty())return false;
    // Guest checkpoints must reach the same host slot as payment, before publishing the progress.
    TGuardValue<FString> SlotGuard(CampfireGuestSaveSlot,GuestSaveSlot);
    TGuardValue<bool> TransactionGuard(bSavingTransaction,true);
    SyncRuntime();auto Next=Snapshot();Next.AlchemyJob=J;return PersistState(MoveTemp(Next),false);
}
void UColdSteelStatusModel::MirrorAlchemyProgress(const FColdSteelAlchemyJob& J)
{
    if(bNetShadowProfile||!GetWorld()||GetWorld()->GetNetMode()!=NM_Client||J.Id.IsEmpty()||J.Id!=Current.AlchemyJob.Id)return;
    if(J.Revision<Current.AlchemyJob.Revision||J.Elapsed+1e-3<Current.AlchemyJob.Elapsed)return;
    // Keep the confirmed station checkpoint without touching inventory, pawn state,
    // training dirty flags or starting a disk write for every progress packet.
    Current.AlchemyJob=J;
}
bool UColdSteelAlchemySystem::Save()
{
    if(ColdSteelStationNet::IsClient(this)||Working.Id.IsEmpty())return true;
    ++Working.Revision;
    if(!Model()||!Model()->CommitAlchemyProgress(Working,NetworkSaveSlot))
    {
        bSaveRetry=true;bActive=false;bBottling=bTimerRunning=false;HeatLevel=0;HeldTool=EAlchemyOp::Stop;InputUntil=0;StirDirection=0;Release();
        Notice=Model()&&Model()->HasUnconfirmedTransactionSave()?Model()->ResultMessage():TEXT("本炉保存未完成，状态保留，正在重试");
        NextSaveAt=FPlatformTime::Seconds()+2;return false;
    }
    if(bSaveRetry)Notice=Working.bFinished?Working.Result:TEXT("本炉已保存，可继续炼制");
    bSaveRetry=false;NextSaveAt=FPlatformTime::Seconds()+5;return true;
}
bool UColdSteelAlchemySystem::Suspend()
{
    if(ColdSteelStationNet::IsClient(this))
    {
        // Keep the active lease until an authority snapshot/receipt confirms the pause.
        if(bPending)return false;
        if(!Reachable())
        {
            // A dead/replaced pawn or removed bench cannot keep a local menu alive.
            // The authority independently suspends its pawn-bound session in Tick.
            bActive=bBottling=bTimerRunning=false;HeatLevel=0;HeldTool=EAlchemyOp::Stop;
            if(HasJob()&&!Job().bFinished)Request(TEXT("alchemy.suspend"));
            return !bPending;
        }
        if(!bActive||!HasJob()||Job().bFinished)return true;
        return Request(TEXT("alchemy.suspend"));
    }
    bBottling=bTimerRunning=false;
    const bool WasActive=bActive;
    bActive=false;HeatLevel=0;HeldTool=EAlchemyOp::Stop;InputUntil=0;
    const bool Ok=!WasActive&&!bSaveRetry?true:Save();Release();
    if(Ok&&HasJob()&&!Job().bFinished)Notice=TEXT("本炉已收火暂存 · 过程和备料已保留");
    return Ok;
}
int64 UColdSteelAlchemySystem::Reserved(const FString& Id) const
{int64 N=0;for(const auto& I:Job().Escrow)if(I.Definition==Id)N+=I.Count;return N;}
void UColdSteelAlchemySystem::OpenUnits(const FString& Id,int32 N)
{Working.Opened.FindOrAdd(Id)=FMath::Min<int64>(Reserved(Id),FMath::Max<int64>(Working.Opened.FindRef(Id),N));}
void UColdSteelAlchemySystem::Fault(const FString& Text,float Points)
{
    Working.Penalty=FMath::Clamp(Working.Penalty+Points,0.f,100.f);
    if(!Working.Faults.Contains(Text)&&Working.Faults.Num()<16)Working.Faults.Add(Text);
}
bool UColdSteelAlchemySystem::Input(EAlchemyOp Op,int32 Index,float Value)
{
    if(!bActive||bPending||bSaveRetry||!FMath::IsFinite(Value))return false;
    // Reject malformed page requests on both owner and authority. Clamping a
    // negative/overflow value would turn the shared book to an unrelated page.
    if(Op==EAlchemyOp::Book&&(Index<0||Index>7))return false;
    if(const auto* M=Model();!M||M->HasUnconfirmedTransactionSave())return false;
    if(ColdSteelStationNet::IsClient(this))
    {
        if(Op!=EAlchemyOp::Stop&&(!Bench.IsValid()||Bench->AlchemyPresentation().Operator!=WorkingPawn.Get()||Bench->AlchemyPresentation().JobId!=Job().Id))return false;
        ColdSteelStationNet::Input(this,TEXT("alchemy"),uint8(Op),NAME_None,Index,FVector2D(Value,0));return true;
    }
    return ProcessInput(Op,Index,Value);
}
bool UColdSteelAlchemySystem::ProcessInput(EAlchemyOp Op,int32 Index,float Value)
{
    if(!bActive||bBottling||!FMath::IsFinite(Value)||!Reachable()||Bench->AlchemyPresentation().Operator!=WorkingPawn.Get()||!LoadJob()||Working.bFinished)return false;
    const double Now=FPlatformTime::Seconds();
    if(Op==EAlchemyOp::Timer)
    {
        if(Now<NextActionAt)return false;
        if(Accepted.FreeBrewing)
        {
            bHourglassInverted=!bHourglassInverted;TimerElapsed=TimerFraction=0;bTimerRunning=true;
            HeldTool=Op;InputUntil=NextActionAt=Now+.9;TimerStartsAt=NextActionAt;
            Notice=TEXT("沙漏计时 · 一轮十秒");++Serial;ActionAt=GetWorld()->GetTimeSeconds();Publish();return true;
        }
        const int32 Current=StepIndex();if(!Accepted.Steps.IsValidIndex(Current)||Accepted.Steps[Current].Action!=TEXT("heat"))return false;
        if(bTimerRunning)Working.Progress[Current]=0;
        bHourglassInverted=!bHourglassInverted;TimerFraction=Working.Progress[Current]/Accepted.Steps[Current].Amount;
        bTimerRunning=true;HeldTool=EAlchemyOp::Timer;InputUntil=NextActionAt=Now+.9;
        TimerStartsAt=NextActionAt;
        Notice=TEXT("沙漏已翻转 · 保持手册指定温区");++Serial;ActionAt=GetWorld()->GetTimeSeconds();
        const bool Ok=Save();Publish();return Ok;
    }
    if(Op==EAlchemyOp::Stop){if((HeldTool==EAlchemyOp::Pour||HeldTool==EAlchemyOp::Timer)&&Now<NextActionAt)return false;HeldTool=Op;InputUntil=0;StirDirection=0;Publish();return true;}
    if(Op==EAlchemyOp::Heat)
    {
        // Relative clicks are resolved against authority state, so rapid client clicks cannot lose a level.
        if(Index<0||Index>5)return false;
        HeatLevel=FMath::Clamp(Index==4?HeatLevel+1:Index==5?HeatLevel-1:Index,0,3);
        static const TCHAR* Names[]={TEXT("关闭"),TEXT("低火"),TEXT("中火"),TEXT("高火")};Notice=FString::Printf(TEXT("火力：%s"),Names[HeatLevel]);Publish();return true;
    }
    if(Op==EAlchemyOp::Book){BookPage=Index;Publish();return true;}
    if(Now<NextActionAt)return false;
    if(!Accepted.Inputs.IsValidIndex(Index)&&Op!=EAlchemyOp::Stir)return false;
    if(Op==EAlchemyOp::Pour)
    {
        if(Now<NextActionAt)return false;
        const FString Id=Accepted.Inputs[Index].Item;
        if(Working.Poured.FindRef(Id)>=Reserved(Id)){Notice=TEXT("该原料已全部投入");return false;}
        const int32 Current=StepIndex();int32 PourStep=INDEX_NONE;
        for(int32 I=0;I<Accepted.Steps.Num();++I)
            if(Accepted.Steps[I].Action==TEXT("pour")&&Accepted.Steps[I].Item==Id&&Working.Progress[I]<Accepted.Steps[I].Amount){PourStep=I;break;}
        if(PourStep==INDEX_NONE)return false;
        if(PourStep!=Current)Fault(TEXT("原料加入顺序偏离手册"),8);
        for(int32 I=0;I<Accepted.Steps.Num();++I)
            if(Accepted.Steps[I].Action==TEXT("grind")&&Accepted.Steps[I].Item==Id&&Working.Progress[I]<Accepted.Steps[I].Amount)
            {Fault(TEXT("结晶未充分研磨"),15);Working.Progress[I]=Accepted.Steps[I].Amount;}
        const auto& S=Accepted.Steps[PourStep];
        if(Working.Temperature<S.MinHeat||Working.Temperature>S.MaxHeat)Fault(TEXT("投料时热度偏离配方"),8);
        ++Working.Poured.FindOrAdd(Id);OpenUnits(Id,int32(Working.Poured.FindRef(Id)));
        Working.Progress[PourStep]+=1;HeldTool=Op;ToolIndex=Index;ActionAt=GetWorld()->GetTimeSeconds();++Serial;
        NextActionAt=Now+AlchemyInteraction::PourSeconds;InputUntil=NextActionAt;Notice=TEXT("原料已投入");
        const bool Ok=Save();Publish();return Ok;
    }
    if(Op!=EAlchemyOp::Grind&&Op!=EAlchemyOp::Stir)return false;
    if(Op==EAlchemyOp::Stir)
    {
        if(Working.Poured.IsEmpty())return false;
        Index=0; // Ingredient selection cannot restart a held spoon's pickup clock.
    }
    if(Op==EAlchemyOp::Grind)
    {
        const FString Id=Accepted.Inputs[Index].Item;
        if(!CanGrind(Index)){Notice=TEXT("研钵中没有可处理的原料");return false;}
        const int64 Before=Working.Opened.FindRef(Id);OpenUnits(Id,int32(Reserved(Id)));
        if(Working.Opened.FindRef(Id)!=Before&&!Save())return false;
    }
    if(HeldTool!=Op||ToolIndex!=Index){++Serial;ActionAt=GetWorld()->GetTimeSeconds();}
    HeldTool=Op;ToolIndex=Index;StirDirection=FMath::Clamp(Value,-1.f,1.f);InputUntil=Now+.4;Publish();return true;
}
void UColdSteelAlchemySystem::Advance(float Dt)
{
    Working.Elapsed+=Dt;
    const float Target[]={20,45,65,94};
    Working.Temperature=FMath::FInterpConstantTo(Working.Temperature,Target[HeatLevel],Dt,HeatLevel?8.f:5.f);
    const double Now=FPlatformTime::Seconds();
    if(bBottling){if(Now>=NextActionAt){bBottling=false;Finish();}return;}
    if(Accepted.FreeBrewing&&bTimerRunning&&Now>=TimerStartsAt)
    {TimerElapsed=FMath::Min(10.f,TimerElapsed+Dt);TimerFraction=TimerElapsed/10.f;if(TimerElapsed>=10)bTimerRunning=false;}
    if(Now>InputUntil){HeldTool=EAlchemyOp::Stop;StirDirection=0;}
    if(HeldTool==EAlchemyOp::Stir&&GetWorld()->GetTimeSeconds()-ActionAt>=AlchemyLayout::StirPickupSeconds)
        StirPhase=FMath::Fmod(StirPhase+Dt*StirDirection*1.5f*PI,2.f*PI);
    const int32 Current=StepIndex();
    if(HeldTool==EAlchemyOp::Grind&&Accepted.Inputs.IsValidIndex(ToolIndex))
    {
        const FString Id=Accepted.Inputs[ToolIndex].Item;
        for(int32 I=0;I<Accepted.Steps.Num();++I)if(Accepted.Steps[I].Action==TEXT("grind")&&Accepted.Steps[I].Item==Id&&Working.Progress[I]<Accepted.Steps[I].Amount)
        {
            Working.Progress[I]=FMath::Min(Accepted.Steps[I].Amount,Working.Progress[I]+Dt);
            if(Working.Progress[I]>=Accepted.Steps[I].Amount){Notice=TEXT("研钵中的粉末已细碎");if(!Save())return;}
            break;
        }
    }
    if(Accepted.Steps.IsValidIndex(Current))
    {
        const auto& S=Accepted.Steps[Current];
        const bool InHeat=Working.Temperature>=S.MinHeat&&Working.Temperature<=S.MaxHeat;
        const float Before=Working.Progress[Current];
        if(S.Action==TEXT("heat")&&(Accepted.FreeBrewing||(bTimerRunning&&Now>=TimerStartsAt)))
        {
            if(InHeat)Working.Progress[Current]=FMath::Min(S.Amount,Before+Dt);
            else if(Before>0&&Working.Temperature>S.MaxHeat+2)Fault(TEXT("熬煮超过目标温区"),Dt*.7f);
            if(!Accepted.FreeBrewing)TimerFraction=Working.Progress[Current]/S.Amount;
        }
        if(S.Action==TEXT("cool")&&HeatLevel==0&&Working.Temperature<=S.MaxHeat)
            Working.Progress[Current]=Accepted.FreeBrewing?S.Amount:FMath::Min(S.Amount,Before+Dt);
        if(S.Action==TEXT("stir")&&HeldTool==EAlchemyOp::Stir&&GetWorld()->GetTimeSeconds()-ActionAt>=AlchemyLayout::StirPickupSeconds)
        {
            if((S.Direction==0&&FMath::Abs(StirDirection)>.1f)||StirDirection*S.Direction>.1f)
            {
                if(!Accepted.FreeBrewing||InHeat)Working.Progress[Current]=FMath::Min(S.Amount,Before+Dt*.75f*FMath::Abs(StirDirection));
                if(!InHeat)Fault(TEXT("搅拌时热度偏离配方"),Dt*.5f);
            }
            else if(FMath::Abs(StirDirection)>.1f)Fault(TEXT("搅拌方向错误"),Dt*2.f);
        }
        if(Before<S.Amount&&Working.Progress[Current]>=S.Amount)
        {if(!Accepted.FreeBrewing)bTimerRunning=false;Notice=Observation();if(!Save())return;}
    }
    if(Working.Temperature>90&&!Working.Poured.IsEmpty())Working.ScorchSeconds+=Dt;
    if(Working.ScorchSeconds>10&&!Working.bFinished)
    {Fault(TEXT("持续高温导致药液焦化"),100);Finish();}
}
bool UColdSteelAlchemySystem::Finish()
{
    if(Working.Id.IsEmpty()||Working.bFinished)return false;
    const bool Steps=StepIndex()==Accepted.Steps.Num();
    if(!Steps)Fault(TEXT("药材未充分融合或熬制不足"),100);
    Working.bFinished=true;Working.bPassed=Steps&&Working.Penalty<=40;
    Working.OutputCount=Working.bPassed?Accepted.BaseCount+(Working.Penalty<=10?Accepted.BonusCount:0):0;
    Working.Result=Working.bPassed?FString::Printf(TEXT("炼制完成 · 工艺 %.0f / 100 · %d 瓶"),100-Working.Penalty,Working.OutputCount):
        TEXT("本炉失败 · 可作废退回一半材料（逐项向下取整）");
    bActive=false;bBottling=bTimerRunning=false;HeatLevel=0;HeldTool=EAlchemyOp::Stop;Notice=Working.Result;
    const bool Ok=Save();Release();return Ok;
}
bool UColdSteelAlchemySystem::Bottle()
{
    if(!bActive||bPending||Saving()||ToolBusy()||!Reachable())return false;
    if(Job().Poured.IsEmpty()){Notice=TEXT("锅中没有可灌装的药液");return false;}
    if(Job().Temperature>Accepted.BottleHeat){Notice=FString::Printf(TEXT("药液过热 · 低于 %.0f °C 才能安全灌装"),Accepted.BottleHeat);return false;}
    if(!Accepted.FreeBrewing&&StepIndex()!=Accepted.Steps.Num()){Notice=TEXT("旧批次仍需按原手册完成工序");return false;}
    if(ColdSteelStationNet::IsClient(this))return Request(TEXT("alchemy.bottle"));
    if(!LoadJob()||Working.bFinished||Bench->AlchemyPresentation().Operator!=WorkingPawn.Get())return false;
    if(const auto* M=Model();!M||M->HasUnconfirmedTransactionSave())return false;
    if(Accepted.FreeBrewing)
    {
        const int32 Current=StepIndex();
        if(Accepted.Steps.IsValidIndex(Current)&&Accepted.Steps[Current].Action==TEXT("cool")&&Working.Temperature<=Accepted.Steps[Current].MaxHeat)
            Working.Progress[Current]=Accepted.Steps[Current].Amount;
    }
    bBottling=true;bTimerRunning=false;HeatLevel=0;HeldTool=EAlchemyOp::Bottle;ActionAt=GetWorld()->GetTimeSeconds();++Serial;
    NextActionAt=FPlatformTime::Seconds()+AlchemyInteraction::BottleSeconds;Notice=TEXT("正在舀取药液、装瓶并放回器具");Publish();return true;
}
bool UColdSteelAlchemySystem::Claim()
{
    if(bActive||bPending||Saving()||!LoadJob()||!HasJob()||!Job().bFinished||!Job().bPassed)return false;
    if(ColdSteelStationNet::IsClient(this))return Request(TEXT("alchemy.claim"));
    auto* M=Model();M->SyncRuntime();auto Next=M->Snapshot();
    for(int32 I=0;I<Job().OutputCount;++I)
    {
        auto Item=Job().Product;Item.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Item.Count=1;Item.Place=0;Item.Cell=-1;Item.Container.Reset();
        if(!ColdSteelInventory::Insert(Next.Items,Item)){Notice=TEXT("背包放不下全部药水，本炉保留待领");return false;}
    }
    Next.AlchemyJob={};if(!M->CommitState(MoveTemp(Next))){Notice=M->ResultMessage();return false;}
    Working={};RestoredId.Reset();bSaveRetry=false;Notice=TEXT("药水已领取");return true;
}
TArray<FColdSteelItem> UColdSteelAlchemySystem::DiscardRefund() const
{
    const auto& J=Job();auto Used=J.Opened;
    if(J.bFinished)
    {
        // Round once per material, after combining all originally paid stacks.
        Used.Reset();
        for(const auto& Item:J.Escrow)Used.FindOrAdd(Item.Definition)+=Item.Count;
        for(auto& Entry:Used)Entry.Value-=Entry.Value/2;
    }
    TArray<FColdSteelItem> Refund;
    for(auto Item:J.Escrow)
    {
        const int64 Taken=FMath::Min(Item.Count,Used.FindRef(Item.Definition));Used.FindOrAdd(Item.Definition)-=Taken;Item.Count-=Taken;
        if(Item.Count<=0)continue;Item.Place=0;Item.Cell=-1;Item.Container.Reset();
        Refund.Add(MoveTemp(Item));
    }
    return Refund;
}
bool UColdSteelAlchemySystem::Discard()
{
    if(bActive||bPending||Saving()||!HasJob())return false;
    if(ColdSteelStationNet::IsClient(this))return Request(TEXT("alchemy.discard"));
    auto* M=Model();M->SyncRuntime();auto Next=M->Snapshot();
    const bool Finished=Job().bFinished;const auto Refund=DiscardRefund();
    for(const auto& Item:Refund)
    {
        if(!ColdSteelInventory::Insert(Next.Items,Item)){Notice=TEXT("背包放不下全部退料，本炉保留");return false;}
    }
    Next.AlchemyJob={};if(!M->CommitState(MoveTemp(Next))){Notice=M->ResultMessage();return false;}
    Working={};RestoredId.Reset();bSaveRetry=false;Release();
    Notice=Finished?(Refund.IsEmpty()?TEXT("本炉已作废 · 按半数取整后无可退材料"):TEXT("本炉已作废 · 一半投入材料已返还背包（逐项向下取整）")):
        TEXT("本炉已废弃 · 未开封备料已返还");return true;
}
bool UColdSteelAlchemySystem::Transaction(const FString& Op,FName Id,AActor* S,APawn* P,FString& Reason)
{
    bAuthorityTransactionPrepared=false;const auto Before=Job();
    if(Op!=TEXT("alchemy.suspend")&&!Open(S,P)){Reason=TEXT("药水工作台不可用");return false;}
    bool Ok=false;
    if(Op==TEXT("alchemy.start"))Ok=Start(Id);
    else if(Op==TEXT("alchemy.resume"))Ok=Resume();
    else if(Op==TEXT("alchemy.suspend"))Ok=Suspend();
    else if(Op==TEXT("alchemy.bottle"))Ok=Bottle();
    else if(Op==TEXT("alchemy.claim"))Ok=Claim();
    else if(Op==TEXT("alchemy.discard"))Ok=Discard();
    if(Ok){TransactionBefore=Before;bAuthorityTransactionPrepared=true;}
    Reason=Notice;return Ok;
}
void UColdSteelAlchemySystem::AuthorityTransactionFinished(bool Committed,const FString& Reason)
{
    if(!bAuthorityTransactionPrepared)return;bAuthorityTransactionPrepared=false;
    if(!Committed)
    {
        // WorldAction only stages the profile. A failed outer commit must also roll back
        // this subsystem's cached batch, heat and public lease.
        bActive=bBottling=bTimerRunning=false;HeatLevel=0;HeldTool=EAlchemyOp::Stop;InputUntil=0;Release();
        Working=TransactionBefore;RestoredId=Working.Id;Accepted={};
        if(!Working.Id.IsEmpty())DecodeRecipe(Working.RecipeSnapshot,Accepted);
        const auto* M=Model();
        bSaveRetry=M&&!Working.Id.IsEmpty()&&Working.Id==M->AlchemyJob().Id&&
            !FColdSteelAlchemyJob::StaticStruct()->CompareScriptStruct(&Working,&M->AlchemyJob(),0);
        NextSaveAt=FPlatformTime::Seconds()+2;
        Notice=Reason+TEXT(" · 本炉已收火，原批次保留");
    }
    TransactionBefore={};
}
void UColdSteelAlchemySystem::Tick(float Delta)
{
    if(ColdSteelStationNet::IsClient(this)){ApplyDeferredState();return;}
    const double Now=FPlatformTime::Seconds();
    if(bSaveRetry){if(Now>=NextSaveAt)Save();return;}
    if(!bActive)return;
    if(Model()&&Model()->HasUnconfirmedTransactionSave()){Suspend();return;}
    if(!Reachable()||Bench->AlchemyPresentation().Operator!=WorkingPawn.Get()){Suspend();return;}
    // Bound integration steps; a hitch advances real elapsed heat without changing input rate.
    float Left=FMath::Min(Delta,2.f);
    while(Left>0&&bActive){const float Step=FMath::Min(Left,.05f);Advance(Step);Left-=Step;}
    if(bActive&&Now>=NextSaveAt)Save();
    if(Now>=NextPublishAt){Publish();NextPublishAt=Now+.1;}
}
void UColdSteelAlchemySystem::Publish()
{
    auto* B=Bench.Get();if(!B||!B->HasAuthority()||!bActive)return;
    FAlchemyBenchState S;S.Operator=WorkingPawn.Get();S.JobId=Working.Id;S.Recipe=Accepted.Id;S.Temperature=Working.Temperature;
    int64 Paid=0,Poured=0;for(const auto& I:Accepted.Inputs){Paid+=I.Count;Poured+=Working.Poured.FindRef(I.Item);}
    S.Fill=Paid?FMath::Clamp(.85f*float(Poured)/float(Paid),0.f,.85f):0.f;
    const float Concentration=Accepted.Inputs.Num()>1?FMath::Clamp(float(Working.Poured.FindRef(Accepted.Inputs[1].Item))/Accepted.Inputs[1].Count,0.f,1.f):1.f;
    S.Color=FMath::Lerp(FLinearColor(.13f,.19f,.16f),Accepted.Color,Concentration*(.3f+.7f*Infusion()));
    if(Working.ScorchSeconds>0)S.Color=FMath::Lerp(S.Color,FLinearColor(.12f,.045f,.012f),FMath::Clamp(Working.ScorchSeconds/10.f,0.f,1.f));
    S.Heat=uint8(HeatLevel);S.Tool=uint8(HeldTool);
    S.Ingredient=ToolIndex;S.ActionSerial=Serial;S.ActionTime=ActionAt;S.Stir=StirDirection;S.BookPage=BookPage;
    S.StirPhase=StirPhase;S.SampleTime=GetWorld()->GetTimeSeconds();
    S.InputEndTime=S.SampleTime+float(FMath::Max(0.,InputUntil-FPlatformTime::Seconds()));
    S.TimerRunning=bTimerRunning;S.TimerFraction=TimerFraction;S.HourglassInverted=bHourglassInverted;
    B->SetAlchemyPresentation(S);
}
FColdSteelAlchemyNetState UColdSteelAlchemySystem::NetworkState() const
{
    FColdSteelAlchemyNetState S;const auto& J=Job();S.JobId=J.Id;S.Revision=J.Revision;S.InventoryRevision=Model()?Model()->InventoryRevision():0;
    S.Progress=J.Progress;
    for(const auto& Pair:J.Opened){auto& Entry=S.Opened.AddDefaulted_GetRef();Entry.Key=Pair.Key;Entry.Value=Pair.Value;}
    for(const auto& Pair:J.Poured){auto& Entry=S.Poured.AddDefaulted_GetRef();Entry.Key=Pair.Key;Entry.Value=Pair.Value;}
    S.Faults=J.Faults;S.Temperature=J.Temperature;
    S.Penalty=J.Penalty;S.ScorchSeconds=J.ScorchSeconds;S.Result=J.Result;S.Saving=Saving();
    S.Elapsed=J.Elapsed;S.Active=bActive;S.Finished=J.bFinished;S.Passed=J.bPassed;
    S.Bottling=bBottling;S.TimerRunning=bTimerRunning;S.ActionRemaining=bActive?float(FMath::Max(0.,NextActionAt-FPlatformTime::Seconds())):0.f;
    S.ServerTime=GetWorld()->GetTimeSeconds();
    S.OutputCount=J.OutputCount;S.Heat=uint8(HeatLevel);S.Notice=Notice;return S;
}
void UColdSteelAlchemySystem::ApplyNetworkState(const FColdSteelAlchemyNetState& S)
{
    auto* M=Model();if(!M||!ColdSteelStationNet::IsClient(this))return;
    // Unrelated inventory receipts may advance the baseline after a final pause
    // packet. Keep that same-job state if its job revision/time is still current.
    if(S.InventoryRevision<M->InventoryRevision()&&S.JobId!=M->AlchemyJob().Id)return;
    if(S.InventoryRevision>M->InventoryRevision())
    {
        // The small state RPC can overtake a chunked payment/claim receipt. Keep
        // its final pause/finish state until that inventory baseline is installed.
        if(!bHasDeferredState||S.InventoryRevision>=DeferredState.InventoryRevision)
        {DeferredState=S;bHasDeferredState=true;}
        return;
    }
    if(bHasDeferredState&&S.InventoryRevision>=DeferredState.InventoryRevision)
    {DeferredState={};bHasDeferredState=false;}
    if(S.JobId!=M->AlchemyJob().Id||!LoadJob())return;
    if(S.Revision<Working.Revision||S.Elapsed+1e-3<Working.Elapsed)return;
    Working.Revision=S.Revision;Working.Progress=S.Progress;
    Working.Opened.Reset();Working.Poured.Reset();
    for(const auto& Entry:S.Opened)Working.Opened.Add(Entry.Key,Entry.Value);
    for(const auto& Entry:S.Poured)Working.Poured.Add(Entry.Key,Entry.Value);
    Working.Faults=S.Faults;
    Working.Temperature=S.Temperature;Working.Penalty=S.Penalty;Working.Elapsed=S.Elapsed;Working.ScorchSeconds=S.ScorchSeconds;Working.Result=S.Result;
    Working.bFinished=S.Finished;Working.bPassed=S.Passed;Working.OutputCount=S.OutputCount;
    bActive=S.Active&&Reachable();bBottling=S.Bottling;bTimerRunning=S.TimerRunning;bSaveRetry=S.Saving;HeatLevel=S.Heat;Notice=S.Notice;
    const auto* GS=GetWorld()->GetGameState();
    const float PacketAge=GS?FMath::Max(0.f,float(GS->GetServerWorldTimeSeconds())-S.ServerTime):0.f;
    NextActionAt=FPlatformTime::Seconds()+FMath::Max(0.f,S.ActionRemaining-PacketAge);
    LastNetworkInventoryRevision=S.InventoryRevision;++NetworkStateSerial;if(!S.Saving)M->MirrorAlchemyProgress(Working);
}
void UColdSteelAlchemySystem::ApplyDeferredState()
{
    const auto* M=Model();if(!bHasDeferredState||!M||M->InventoryRevision()<DeferredState.InventoryRevision)return;
    auto State=MoveTemp(DeferredState);DeferredState={};bHasDeferredState=false;
    ApplyNetworkState(State);
}
void UColdSteelAlchemySystem::NetworkFinished(const FString& Op,bool Success,const FString& Reason)
{
    if(!bPending)return;bPending=false;
    const bool SamePawn=RequestPawn==WorkingPawn;RequestPawn.Reset();
    if(!SamePawn)return;
    ApplyDeferredState();Notice=Reason;if(!Success){if(!Reachable())bActive=bBottling=bTimerRunning=false;return;}
    if(!LoadJob()){bActive=bBottling=bTimerRunning=false;return;}
    if(Op==TEXT("alchemy.suspend")||Op==TEXT("alchemy.claim")||Op==TEXT("alchemy.discard"))bActive=false;
    else if(NetworkStateSerial==RequestStateSerial||LastNetworkInventoryRevision<=RequestInventoryRevision)
    {
        bActive=!Job().bFinished&&(Op==TEXT("alchemy.start")||Op==TEXT("alchemy.resume")||Op==TEXT("alchemy.bottle"));
        if(Op==TEXT("alchemy.bottle")&&bActive){bBottling=true;NextActionAt=FPlatformTime::Seconds()+AlchemyInteraction::BottleSeconds;}
        else if(bActive){bBottling=bTimerRunning=false;HeatLevel=0;NextActionAt=FPlatformTime::Seconds();}
    }
    if(!Reachable())bActive=bBottling=bTimerRunning=false;
    if(!bActive){bBottling=bTimerRunning=false;HeatLevel=0;}
    if(!HasJob()){Working={};RestoredId.Reset();bActive=false;}
}
void UColdSteelAlchemySystem::NetworkEnded()
{bActive=bPending=bBottling=bTimerRunning=bSaveRetry=bHasDeferredState=false;DeferredState={};RequestPawn.Reset();NetworkStateSerial=RequestStateSerial=0;LastNetworkInventoryRevision=RequestInventoryRevision=-1;HeatLevel=0;StirPhase=0;HeldTool=EAlchemyOp::Stop;Bench.Reset();WorkingPawn.Reset();Working={};RestoredId.Reset();}
