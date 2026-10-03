#include "ForgingSystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void UColdSteelStatusModel::StageForgeHit(const FString& JobId,int32 Hits)
{
    if(Current.ForgeJob.Id!=JobId||Current.ForgeJob.bFinished)return;
    Current.ForgeJob.Hits=FMath::Clamp(Hits,Current.ForgeJob.Hits,UColdSteelForgingSystem::TargetCount);
    bTrainingDirty=true;
}

UColdSteelStatusModel* UColdSteelForgingSystem::Model() const
{return GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
const FColdSteelForgeJob& UColdSteelForgingSystem::Job() const
{static const FColdSteelForgeJob Empty;const auto* M=Model();return M?M->ForgeJob():Empty;}
const FColdSteelForgeRecipe* UColdSteelForgingSystem::Find(FName Id) const
{return Recipes.FindByPredicate([Id](const auto& R){return R.Id==Id;});}

void UColdSteelForgingSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);Collection.InitializeDependency<UColdSteelStatusModel>();
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/forging-recipes.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return;
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;if(!Root->TryGetArrayField(TEXT("recipes"),Rows))return;
    // Sword recipes share the accepted blank's strike regions. Per-recipe points remain readable.
    const TSharedPtr<FJsonObject>* SwordBlank=nullptr;
    const TArray<TSharedPtr<FJsonValue>>* SwordPoints=nullptr;
    if(Root->TryGetObjectField(TEXT("sword_blank"),SwordBlank)&&*SwordBlank)
        (*SwordBlank)->TryGetArrayField(TEXT("points"),SwordPoints);
    for(const auto& V:*Rows)
    {
        const auto O=V->AsObject();if(!O)continue;
        FColdSteelForgeRecipe R;FString Id;
        if(!O->TryGetStringField(TEXT("id"),Id)||Id.IsEmpty()||!O->TryGetStringField(TEXT("output"),R.Output)
            ||!O->TryGetStringField(TEXT("mold"),R.Mold))continue;
        R.Id=FName(*Id);if(Find(R.Id))continue;
        const TArray<TSharedPtr<FJsonValue>>* Inputs=nullptr;const TArray<TSharedPtr<FJsonValue>>* Points=nullptr;
        if(!O->TryGetArrayField(TEXT("inputs"),Inputs))continue;
        if(!O->TryGetArrayField(TEXT("points"),Points))Points=SwordPoints;
        if(!Points)continue;
        bool Valid=true;TSet<FString> Seen;
        for(const auto& I:*Inputs)
        {
            const auto In=I->AsObject();FColdSteelCraftingInput Cost;double Count=0;
            if(!In||!In->TryGetStringField(TEXT("item"),Cost.Item)||!In->TryGetNumberField(TEXT("count"),Count)
                ||Count<1||Count>9999||Count!=FMath::FloorToDouble(Count)||Seen.Contains(Cost.Item)){Valid=false;break;}
            Cost.Count=int64(Count);Seen.Add(Cost.Item);R.Inputs.Add(Cost);
        }
        for(const auto& P:*Points)
        {
            const auto& A=P->AsArray();if(A.Num()!=2){Valid=false;break;}
            FVector2D Point(A[0]->AsNumber(),A[1]->AsNumber());
            if(Point.X<0||Point.X>1||Point.Y<0||Point.Y>1){Valid=false;break;}R.Points.Add(Point);
        }
        if(Valid&&!R.Inputs.IsEmpty()&&R.Points.Num()>1)Recipes.Add(MoveTemp(R));
    }
}
void UColdSteelForgingSystem::Deinitialize()
{if(bActive){FString Reason;Finish(Reason);}Super::Deinitialize();}
FString UColdSteelForgingSystem::Quality(int32 Hits)
{
    if(Hits>=20)return TEXT("完美");if(Hits>=18)return TEXT("精工");if(Hits>=14)return TEXT("精良");
    if(Hits>=10)return TEXT("合格");if(Hits>=5)return TEXT("普通");return TEXT("粗制");
}
bool UColdSteelForgingSystem::CanStart(FName Id,FString& Reason) const
{
    const auto* M=Model();const auto* R=Find(Id);
    if(!M||!R){Reason=TEXT("配方未就绪");return false;}
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client){Reason=TEXT("锻造仅支持单人模式");return false;}
    if(bActive||!Job().Id.IsEmpty()){Reason=TEXT("先领取或废弃上一把成品");return false;}
    if(M->CreateItem(R->Output).Data.IsEmpty()){Reason=TEXT("成品未加入物品目录");return false;}
    for(const auto& In:R->Inputs)if(M->CountMaterial(In.Item)<In.Count)
    {
        Reason=FString::Printf(TEXT("缺少 %lld 个%s"),In.Count-M->CountMaterial(In.Item),
            *ColdSteelInventory::Text(M->CreateItem(In.Item),TEXT("name")));return false;
    }
    Reason=TEXT("材料充足 · 每轮制作一把");return true;
}
bool UColdSteelForgingSystem::Start(FName Id,FString& Reason)
{
    if(!CanStart(Id,Reason))return false;
    auto* M=Model();const auto* R=Find(Id);M->SyncRuntime();auto P=M->Snapshot();
    for(const auto& In:R->Inputs)
    {
        int64 Left=In.Count;
        for(int32 Place:{0,4})for(int32 I=P.Items.Num()-1;I>=0&&Left>0;--I)
        {
            auto& Item=P.Items[I];if(Item.Place!=Place||!Item.Container.IsEmpty()||Item.Definition!=In.Item)continue;
            const int64 Take=FMath::Min(Item.Count,Left);Item.Count-=Take;Left-=Take;if(Item.Count==0)P.Items.RemoveAt(I);
        }
        if(Left>0){Reason=TEXT("材料已变化，请重新开始");return false;}
    }
    P.ForgeJob={};P.ForgeJob.Id=FGuid::NewGuid().ToString(EGuidFormats::Digits);P.ForgeJob.Recipe=Id;
    P.ForgeJob.Item=M->CreateItem(R->Output);const FString NewId=P.ForgeJob.Id;
    for(const auto& In:R->Inputs)P.ForgeJob.PaidMaterials.Add(In.Item,In.Count);
    if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    Sequence.Reset();FRandomStream Random(FMath::Rand());int32 Last=INDEX_NONE;
    for(int32 I=0;I<TargetCount;++I)
    {
        TArray<int32> Candidates;
        for(int32 N=0;N<R->Points.Num();++N)
            if(Last==INDEX_NONE||FVector2D::Distance(R->Points[N],R->Points[Last])>=.18)Candidates.Add(N);
        if(Candidates.IsEmpty())for(int32 N=0;N<R->Points.Num();++N)if(N!=Last)Candidates.Add(N);
        Last=Candidates[Random.RandRange(0,Candidates.Num()-1)];Sequence.Add(R->Points[Last]);
    }
    ActiveId=NewId;StartedAt=FPlatformTime::Seconds();CompletedTargets=0;
    bTargetOpen=false;bStrikePending=false;TargetOpenedAt=0;PhaseEndsAt=StartedAt+Preparation;
    RecoveryAfterContact=0;StrikeContactAt=0;StrikeTargetLife=0;
    LastError.Reset();RetryAt=0;bActive=true;Reason=TEXT("准备锻打");return true;
}
double UColdSteelForgingSystem::Elapsed() const
{return StartedAt>0?FPlatformTime::Seconds()-StartedAt-Preparation:0;}
double UColdSteelForgingSystem::PhaseRemaining() const
{
    if(!bActive)return 0;
    const double Now=FPlatformTime::Seconds();
    if(bStrikePending)return FMath::Max(0.,StrikeContactAt-Now);
    return FMath::Max(0.,PhaseEndsAt-Now);
}
int32 UColdSteelForgingSystem::TargetIndex() const
{
    return bActive&&bTargetOpen&&(bStrikePending||FPlatformTime::Seconds()<PhaseEndsAt)
        ?CompletedTargets:INDEX_NONE;
}
bool UColdSteelForgingSystem::Target(FVector2D& UV,float& Life) const
{
    const int32 I=TargetIndex();if(!Sequence.IsValidIndex(I))return false;
    UV=Sequence[I];
    Life=bStrikePending?StrikeTargetLife:float(FMath::Clamp((PhaseEndsAt-FPlatformTime::Seconds())/FMath::Max(PhaseEndsAt-TargetOpenedAt,.001),0.,1.));
    return Life>0;
}
bool UColdSteelForgingSystem::BeginStrike(int32 ShownIndex,double ContactDelay,double RecoveryDelay)
{
    if(!bActive||bStrikePending||ShownIndex==INDEX_NONE||ShownIndex!=TargetIndex())return false;
    FVector2D Point;float Life=0;if(!Target(Point,Life))return false;
    // Judge the player's reaction at input time, without charging the hammer's travel time.
    StrikeTargetLife=Life;
    bStrikePending=true;StrikeContactAt=FPlatformTime::Seconds()+FMath::Max(0.,ContactDelay);
    RecoveryAfterContact=FMath::Max(0.,RecoveryDelay);return true;
}
void UColdSteelForgingSystem::ResolveTarget(bool bHit,double Now)
{
    if(bHit)Model()->StageForgeHit(ActiveId,Job().Hits+1);
    ++CompletedTargets;bTargetOpen=false;bStrikePending=false;StrikeTargetLife=0;
    // Sample once per resolved point, never during HUD refresh. A random gap
    // cannot end before the hammer's recovery and interaction buffer have elapsed.
    const double Gap=FMath::FRandRange(float(TargetGapMin),float(TargetGapMax));
    PhaseEndsAt=Now+FMath::Max(Gap,RecoveryAfterContact);RecoveryAfterContact=0;
}
void UColdSteelForgingSystem::AdvanceTargets(double Now)
{
    if(bTargetOpen&&!bStrikePending&&Now>=PhaseEndsAt)ResolveTarget(false,Now);
    if(!bTargetOpen&&CompletedTargets<TargetCount&&Now>=PhaseEndsAt)
    {bTargetOpen=true;TargetOpenedAt=Now;PhaseEndsAt=Now+FMath::FRandRange(float(HitWindowMin),float(HitWindowMax));}
}
bool UColdSteelForgingSystem::Strike(int32 ShownIndex,const FVector2D& UV,const FVector2D& RadiusUV)
{
    const double Now=FPlatformTime::Seconds();FVector2D Point;float Life=0;
    if(ShownIndex==INDEX_NONE||ShownIndex!=TargetIndex()||!Target(Point,Life)
        ||RadiusUV.X<=0||RadiusUV.Y<=0||Job().Id!=ActiveId||(bStrikePending&&Now<StrikeContactAt))return false;
    const FVector2D Delta((UV.X-Point.X)/RadiusUV.X,(UV.Y-Point.Y)/RadiusUV.Y);
    const bool bHit=Delta.SizeSquared()<=Life*Life;ResolveTarget(bHit,Now);return bHit;
}
void UColdSteelForgingSystem::Tick(float DeltaTime)
{
    if(Job().Id!=ActiveId){bActive=false;return;}
    const double Now=FPlatformTime::Seconds();AdvanceTargets(Now);
    if(CompletedTargets>=TargetCount&&Now>=PhaseEndsAt&&Now>=RetryAt)
    {FString Reason;if(!Finish(Reason)){LastError=Reason;RetryAt=FPlatformTime::Seconds()+2.;}}
}
bool UColdSteelForgingSystem::Finish(FString& Reason)
{
    auto* M=Model();if(!M)return false;
    if(Job().Id.IsEmpty()||Job().bFinished){bActive=false;return true;}
    M->SyncRuntime();auto P=M->Snapshot();auto& J=P.ForgeJob;
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(J.Item.Data),Data)||!Data)
    {Reason=TEXT("工件数据不可读，保留待处理记录");return false;}
    auto Q=MakeShared<FJsonObject>();Q->SetNumberField(TEXT("hits"),J.Hits);Q->SetNumberField(TEXT("total"),TargetCount);
    Q->SetNumberField(TEXT("multiplier"),Multiplier(J.Hits));Q->SetStringField(TEXT("label"),Quality(J.Hits));
    Data->SetObjectField(TEXT("_forgeQuality"),Q);
    FString Serialized;FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Serialized));
    J.Item.Data=MoveTemp(Serialized);J.bFinished=true;
    if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();LastError=Reason;return false;}
    bActive=false;ActiveId.Reset();LastError.Reset();Reason=TEXT("锻造完成 · 领取或废弃后可开始下一轮");return true;
}
bool UColdSteelForgingSystem::Claim(FString& Reason)
{
    auto* M=Model();if(!M||bActive||Job().Id.IsEmpty()||!Job().bFinished){Reason=TEXT("还没有可领取的成品");return false;}
    M->SyncRuntime();auto P=M->Snapshot();
    if(!ColdSteelInventory::Insert(P.Items,P.ForgeJob.Item)){Reason=TEXT("背包空间不足，成品保留待领");return false;}
    P.ForgeJob={};if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    LastError.Reset();Reason=TEXT("成品已放入背包");return true;
}
bool UColdSteelForgingSystem::GetPaidMaterials(TMap<FString,int64>& Paid) const
{
    Paid.Reset();
    if(Job().Id.IsEmpty())return false;
    Paid=Job().PaidMaterials;
    if(!Paid.IsEmpty())return true;
    // Keep old-save fallback identical for the materials display and discard quote.
    const auto* Recipe=Find(Job().Recipe);
    if(!Recipe)return false;
    for(const auto& In:Recipe->Inputs)Paid.Add(In.Item,In.Count);
    return true;
}
bool UColdSteelForgingSystem::GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const
{
    Refund.Reset();Reason.Reset();
    if(!Model()||bActive||Job().Id.IsEmpty()||!Job().bFinished)
    {Reason=TEXT("只有已完成、尚未领取的成品可以废弃");return false;}
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client)
    {Reason=TEXT("锻造仅支持单人模式");return false;}
    TMap<FString,int64> Paid;
    if(!GetPaidMaterials(Paid)){Reason=TEXT("无法读取返还材料，成品保留待领");return false;}
    TArray<FString> Definitions;Paid.GetKeys(Definitions);Definitions.Sort();
    for(const auto& Definition:Definitions)
    {
        const int64 Count=Paid[Definition]/2;
        if(Count>0)Refund.Add({Definition,Count});
    }
    return true;
}
bool UColdSteelForgingSystem::Discard(FString& Reason)
{
    TArray<FColdSteelCraftingInput> Refund;
    if(!GetDiscardRefund(Refund,Reason))return false;
    auto* M=Model();M->SyncRuntime();auto P=M->Snapshot();
    TArray<FString> Returned;
    for(const auto& In:Refund)
    {
        const auto Material=M->CreateItem(In.Item,In.Count);
        if(Material.Data.IsEmpty()){Reason=TEXT("返还材料尚未就绪，成品保留待领");return false;}
        if(!ColdSteelInventory::Insert(P.Items,Material))
        {Reason=TEXT("背包空间不足，无法容纳全部返还材料；成品保留待领");return false;}
        Returned.Add(FString::Printf(TEXT("%s × %lld"),*ColdSteelInventory::Text(Material,TEXT("name")),In.Count));
    }
    // Refund and consumption of the pending result share one saved transaction.
    P.ForgeJob={};
    if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    LastError.Reset();
    Reason=Returned.IsEmpty()?TEXT("成品已废弃，各项材料折半不足 1 个，无可返还材料")
        :TEXT("成品已废弃，已返还背包：")+FString::Join(Returned,TEXT("、"));
    return true;
}
