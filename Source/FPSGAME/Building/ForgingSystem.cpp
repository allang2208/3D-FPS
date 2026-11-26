#include "ForgingSystem.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelStationNetwork.h"
#include "../FPSGAMECharacter.h"
#include "../Tasks/BlacksmithApprenticeship.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void UColdSteelStatusModel::StageForgeContact(const FString& JobId,bool bHit)
{
    if(Current.ForgeJob.Id!=JobId||Current.ForgeJob.bFinished)return;
    Current.ForgeJob.bHammeredBlank=true;
    if(bHit)Current.ForgeJob.Hits=FMath::Min(Current.ForgeJob.Hits+1,UColdSteelForgingSystem::TargetCount);
    bTrainingDirty=true;
}

UColdSteelStatusModel* UColdSteelForgingSystem::Model() const
{return NetworkModel?NetworkModel.Get():ColdSteelAuthority::Model(this);}
const FColdSteelForgeJob& UColdSteelForgingSystem::Job() const
{static const FColdSteelForgeJob Empty;const auto* M=Model();return M?M->ForgeJob():Empty;}
const FColdSteelForgeRecipe* UColdSteelForgingSystem::Find(FName Id) const
{return Recipes.FindByPredicate([Id](const auto& R){return R.Id==Id;});}
const FColdSteelForgeMetal* UColdSteelForgingSystem::FindMetal(FName Id) const
{return MetalOptions.FindByPredicate([Id](const auto& M){return M.Item==Id;});}
bool UColdSteelForgingSystem::InputsFor(FName Recipe,FName Metal,TArray<FColdSteelCraftingInput>& Out) const
{
    Out.Reset();const auto* R=Find(Recipe);
    if(!R||!FindMetal(Metal)||R->MetalCount<=0)return false;
    Out=R->Inputs;Out.Add({Metal.ToString(),R->MetalCount});return true;
}

void UColdSteelForgingSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);Collection.InitializeDependency<UColdSteelStatusModel>();
    FString BlankText;TSharedPtr<FJsonObject> BlankRoot;
    if(!FFileHelper::LoadFileToString(BlankText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/forge-blanks.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(BlankText),BlankRoot)||!BlankRoot)return;
    auto Read2=[](const TSharedPtr<FJsonObject>& O,const TCHAR* Key,FVector2D& Out)
    {const TArray<TSharedPtr<FJsonValue>>* A=nullptr;if(O->TryGetArrayField(Key,A)&&A->Num()==2)Out=FVector2D((*A)[0]->AsNumber(),(*A)[1]->AsNumber());};
    auto Read3=[](const TSharedPtr<FJsonObject>& O,const TCHAR* Key,FVector& Out)
    {const TArray<TSharedPtr<FJsonValue>>* A=nullptr;if(O->TryGetArrayField(Key,A)&&A->Num()==3)Out=FVector((*A)[0]->AsNumber(),(*A)[1]->AsNumber(),(*A)[2]->AsNumber());};
    const TSharedPtr<FJsonObject>* Profiles=nullptr;
    if(!BlankRoot->TryGetObjectField(TEXT("profiles"),Profiles)||!*Profiles)return;
    for(const auto& Entry:(*Profiles)->Values)
    {
        const auto O=Entry.Value->AsObject();if(!O)continue;
        FColdSteelForgeBlank B;B.Id=FName(*Entry.Key);O->TryGetStringField(TEXT("label"),B.Label);
        Read2(O,TEXT("crown"),B.Crown);Read2(O,TEXT("eye_center_cm"),B.EyeCenter);Read2(O,TEXT("eye_radius_cm"),B.EyeRadius);
        Read2(O,TEXT("aim_min"),B.AimMin);Read2(O,TEXT("aim_max"),B.AimMax);Read2(O,TEXT("heat_span_cm"),B.HeatSpan);
        Read3(O,TEXT("grip_cm"),B.Grip);Read3(O,TEXT("quench_tip_cm"),B.QuenchTip);Read3(O,TEXT("quench_heel_cm"),B.QuenchHeel);
        Read3(O,TEXT("heat_center_cm"),B.HeatCenter);Read3(O,TEXT("veil_scale"),B.VeilScale);
        double Drop=B.QuenchDrop;if(O->TryGetNumberField(TEXT("quench_drop_cm"),Drop))B.QuenchDrop=float(Drop);
        double Radius=B.StrikeRadius;if(O->TryGetNumberField(TEXT("strike_radius_cm"),Radius)&&Radius>0)B.StrikeRadius=float(Radius);
        const TArray<TSharedPtr<FJsonValue>> *Stages=nullptr,*Points=nullptr;
        if(!O->TryGetArrayField(TEXT("stages"),Stages)||Stages->Num()!=3||!O->TryGetArrayField(TEXT("points"),Points))continue;
        bool Valid=true;
        for(const auto& StageValue:*Stages)
        {
            const auto S=StageValue->AsObject();FColdSteelForgeBlankStage Stage;
            const TArray<TSharedPtr<FJsonValue>>* Sections=nullptr;
            if(!S||!S->TryGetStringField(TEXT("mesh"),Stage.Mesh)||!S->TryGetArrayField(TEXT("sections"),Sections)){Valid=false;break;}
            for(const auto& SectionValue:*Sections)
            {
                const auto& A=SectionValue->AsArray();if(A.Num()!=5){Valid=false;break;}
                FColdSteelForgeBlankSection Section{A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber(),A[3]->AsNumber(),A[4]->AsNumber()};
                if(Section.MaxY<=Section.MinY||(!Stage.Sections.IsEmpty()&&Section.X<=Stage.Sections.Last().X)){Valid=false;break;}
                Stage.Sections.Add(Section);
            }
            if(!Valid||Stage.Sections.Num()<2){Valid=false;break;}B.Stages.Add(MoveTemp(Stage));
        }
        for(const auto& P:*Points)
        {
            const auto& A=P->AsArray();if(A.Num()!=2){Valid=false;break;}
            B.Points.Emplace(A[0]->AsNumber(),A[1]->AsNumber());
        }
        if(Valid&&B.Points.Num()>1)Blanks.Add(B.Id,MoveTemp(B));
    }
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/forging-recipes.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return;
    const TArray<TSharedPtr<FJsonValue>>* Metals=nullptr;
    if(Root->TryGetArrayField(TEXT("metals"),Metals))for(const auto& Value:*Metals)
    {
        const auto O=Value->AsObject();FString Item;double Bonus=0;
        if(!O||!O->TryGetStringField(TEXT("item"),Item)||Item.IsEmpty()
            ||!O->TryGetNumberField(TEXT("damage_bonus"),Bonus)||!FMath::IsFinite(Bonus)
            ||Bonus<0||Bonus>ColdSteelForgeQuality::MaxMaterialBonus||FindMetal(FName(*Item)))continue;
        MetalOptions.Add({FName(*Item),Bonus});
    }
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
        FString BlankId;if(O->TryGetStringField(TEXT("blank"),BlankId))R.Blank=FName(*BlankId);
        const auto* Profile=FindBlank(R.Blank);if(!Profile)continue;
        const TArray<TSharedPtr<FJsonValue>>* Inputs=nullptr;const TArray<TSharedPtr<FJsonValue>>* Points=nullptr;
        if(!O->TryGetArrayField(TEXT("inputs"),Inputs))continue;
        double MetalCount=0;
        if(!O->TryGetNumberField(TEXT("metal_count"),MetalCount)||MetalCount<1||MetalCount>9999
            ||MetalCount!=FMath::FloorToDouble(MetalCount))continue;
        R.MetalCount=int64(MetalCount);
        if(!O->TryGetArrayField(TEXT("points"),Points)&&R.Blank==FName(TEXT("sword")))Points=SwordPoints;
        bool Valid=true;TSet<FString> Seen;
        for(const auto& I:*Inputs)
        {
            const auto In=I->AsObject();FColdSteelCraftingInput Cost;double Count=0;
            if(!In||!In->TryGetStringField(TEXT("item"),Cost.Item)||!In->TryGetNumberField(TEXT("count"),Count)
                ||Count<1||Count>9999||Count!=FMath::FloorToDouble(Count)||Seen.Contains(Cost.Item)){Valid=false;break;}
            Cost.Count=int64(Count);Seen.Add(Cost.Item);R.Inputs.Add(Cost);
        }
        // Kept only for old saves that predate actual-payment snapshots.
        const TArray<TSharedPtr<FJsonValue>>* Legacy=nullptr;
        if(O->TryGetArrayField(TEXT("legacy_inputs"),Legacy))for(const auto& Value:*Legacy)
        {
            const auto In=Value->AsObject();FColdSteelCraftingInput Cost;double Count=0;
            if(In&&In->TryGetStringField(TEXT("item"),Cost.Item)&&In->TryGetNumberField(TEXT("count"),Count)
                &&Count>=1&&Count<=9999&&Count==FMath::FloorToDouble(Count))
            {Cost.Count=int64(Count);R.LegacyInputs.Add(Cost);}
        }
        if(!Points)R.Points=Profile->Points;
        else for(const auto& P:*Points)
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
bool UColdSteelForgingSystem::CanStart(FName Id,FString& Reason,FName Metal) const
{
    const auto* M=Model();const auto* R=Find(Id);
    if(!M||!R){Reason=TEXT("配方未就绪");return false;}
    if(!GetWorld()){Reason=TEXT("锻造仅支持单人模式");return false;}
    if(bActive||!Job().Id.IsEmpty()){Reason=TEXT("先领取或废弃上一把成品");return false;}
    if(M->CreateItem(R->Output).Data.IsEmpty()){Reason=TEXT("成品未加入物品目录");return false;}
    TArray<FColdSteelCraftingInput> Inputs;
    if(!InputsFor(Id,Metal,Inputs)){Reason=TEXT("请选择一种可用金属锭");return false;}
    for(const auto& In:Inputs)if(M->CreateItem(In.Item).Data.IsEmpty())
    {Reason=TEXT("锻造材料未加入物品目录");return false;}
    const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(M);
    if(!Free)for(const auto& In:Inputs)if(M->CountMaterial(In.Item)<In.Count)
    {
        Reason=FString::Printf(TEXT("缺少 %lld 个%s"),In.Count-M->CountMaterial(In.Item),
            *ColdSteelInventory::Text(M->CreateItem(In.Item),TEXT("name")));return false;
    }
    Reason=Free?TEXT("免材料制作 · 每轮制作一把"):TEXT("材料充足 · 每轮制作一把");return true;
}
bool UColdSteelForgingSystem::Start(FName Id,FString& Reason,FName Metal,AActor* Station)
{
    if(ColdSteelStationNet::IsClient(this)){SetStation(Station);Reason=TEXT("等待服务器处理");return ColdSteelStationNet::Request(this,TEXT("forge.start"),Id,1,Station,FIntVector::ZeroValue,Metal);}
    if(!CanStart(Id,Reason,Metal))return false;
    auto* M=Model();const auto* R=Find(Id);M->SyncRuntime();auto P=M->Snapshot();
    TArray<FColdSteelCraftingInput> Inputs;InputsFor(Id,Metal,Inputs);
    const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(M);
    if(!Free)for(const auto& In:Inputs)
    {
        int64 Left=In.Count;
        for(int32 Place:{0,5,4})for(int32 I=P.Items.Num()-1;I>=0&&Left>0;--I)
        {
            auto& Item=P.Items[I];if(Item.Place!=Place||(Place==4&&!Item.Container.IsEmpty())||Item.Definition!=In.Item)continue;
            const int64 Take=FMath::Min(Item.Count,Left);Item.Count-=Take;Left-=Take;if(Item.Count==0)P.Items.RemoveAt(I);
        }
        if(Left>0){Reason=TEXT("材料已变化，请重新开始");return false;}
    }
    P.ForgeJob={};P.ForgeJob.Id=FGuid::NewGuid().ToString(EGuidFormats::Digits);P.ForgeJob.Recipe=Id;
    P.ForgeJob.Item=M->CreateItem(R->Output);const FString NewId=P.ForgeJob.Id;
    P.ForgeJob.bMaterialsWaived=Free;
    P.ForgeJob.QualityVersion=ColdSteelForgeQuality::Version;P.ForgeJob.Metal=Metal;
    P.ForgeJob.MaterialName=ColdSteelInventory::Text(M->CreateItem(Metal.ToString()),TEXT("name"));
    P.ForgeJob.MaterialBonus=FindMetal(Metal)->Bonus;
    if(!ColdSteelForgeQuality::Apply(P.ForgeJob.Item,P.ForgeJob))
    {Reason=TEXT("工件数据不可读，未消耗材料");return false;}
    if(!Free)for(const auto& In:Inputs)P.ForgeJob.PaidMaterials.Add(In.Item,In.Count);
    BlacksmithApprenticeship::WorkpieceUpdated(P);
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
bool UColdSteelForgingSystem::BeginStrike(int32 ShownIndex,double ContactDelay,double RecoveryDelay,const FVector2D& SurfaceUV)
{
    if(!bActive||bStrikePending||ShownIndex==INDEX_NONE||ShownIndex!=TargetIndex())return false;
    FVector2D Point;float Life=0;if(!Target(Point,Life))return false;
    ColdSteelStationNet::Input(this,TEXT("forge"),0,NAME_None,ShownIndex,FVector2D(ContactDelay,RecoveryDelay),SurfaceUV);
    // Judge the player's reaction at input time, without charging the hammer's travel time.
    StrikeTargetLife=Life;
    bStrikePending=true;StrikeContactAt=FPlatformTime::Seconds()+FMath::Max(0.,ContactDelay);
    RecoveryAfterContact=FMath::Max(0.,RecoveryDelay);return true;
}
void UColdSteelForgingSystem::ResolveTarget(double Now)
{
    ++CompletedTargets;bTargetOpen=false;bStrikePending=false;StrikeTargetLife=0;
    // Sample once per resolved point, never during HUD refresh. A random gap
    // cannot end before the hammer's recovery and interaction buffer have elapsed.
    const double Gap=FMath::FRandRange(float(TargetGapMin),float(TargetGapMax));
    PhaseEndsAt=Now+FMath::Max(Gap,RecoveryAfterContact);RecoveryAfterContact=0;
}
void UColdSteelForgingSystem::AdvanceTargets(double Now)
{
    if(bTargetOpen&&!bStrikePending&&Now>=PhaseEndsAt)ResolveTarget(Now);
    if(!bTargetOpen&&CompletedTargets<TargetCount&&Now>=PhaseEndsAt)
    {bTargetOpen=true;TargetOpenedAt=Now;PhaseEndsAt=Now+FMath::FRandRange(float(HitWindowMin),float(HitWindowMax));}
}
bool UColdSteelForgingSystem::Strike(int32 ShownIndex,const FVector2D& UV,const FVector2D& RadiusUV)
{
    if(ColdSteelStationNet::IsClient(this))
    {ColdSteelStationNet::Input(this,TEXT("forge"),1,NAME_None,ShownIndex,UV,RadiusUV);return true;}
    const double Now=FPlatformTime::Seconds();FVector2D Point;float Life=0;
    if(ShownIndex==INDEX_NONE||ShownIndex!=TargetIndex()||!Target(Point,Life)
        ||RadiusUV.X<=0||RadiusUV.Y<=0||Job().Id!=ActiveId||(bStrikePending&&Now+.08<StrikeContactAt))return false;
    const FVector2D Delta((UV.X-Point.X)/RadiusUV.X,(UV.Y-Point.Y)/RadiusUV.Y);
    const bool bHit=Delta.SizeSquared()<=Life*Life;
    if(bHit||(UV.X>=0.&&UV.X<=1.&&UV.Y>=0.&&UV.Y<=1.))Model()->StageForgeContact(ActiveId,bHit);
    ResolveTarget(Now);return bHit;
}
void UColdSteelForgingSystem::Tick(float DeltaTime)
{
    if(ColdSteelStationNet::IsClient(this))return;
    if(Job().Id!=ActiveId){bActive=false;return;}
    const double Now=FPlatformTime::Seconds();AdvanceTargets(Now);
    if(CompletedTargets>=TargetCount&&Now>=PhaseEndsAt&&Now>=RetryAt)
    {FString Reason;if(!Finish(Reason)){LastError=Reason;RetryAt=FPlatformTime::Seconds()+2.;}}
}
bool UColdSteelForgingSystem::Finish(FString& Reason)
{
    if(ColdSteelStationNet::IsClient(this)){Reason=TEXT("等待服务器处理");return ColdSteelStationNet::Request(this,TEXT("forge.finish"),NAME_None,1,BoundStation.Get());}
    auto* M=Model();if(!M)return false;
    if(Job().Id.IsEmpty()||Job().bFinished){bActive=false;return true;}
    M->SyncRuntime();auto P=M->Snapshot();auto& J=P.ForgeJob;
    if(!ColdSteelForgeQuality::Apply(J.Item,J))
    {Reason=TEXT("工件数据不可读，保留待处理记录");return false;}
    J.bFinished=true;
    BlacksmithApprenticeship::WorkpieceUpdated(P);
    const auto* Pawn=NetworkModel?M->RuntimePawn():nullptr;
    const auto* Owner=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(!M->CommitWorkshopCheckpoint(MoveTemp(P),Owner?Owner->CampfireGuestSlot():FString()))
    {Reason=M->ResultMessage();LastError=Reason;return false;}
    bActive=false;ActiveId.Reset();LastError.Reset();Reason=TEXT("锻造完成 · 领取或废弃后可开始下一轮");return true;
}
bool UColdSteelForgingSystem::Claim(FString& Reason)
{
    if(ColdSteelStationNet::IsClient(this)){Reason=TEXT("等待服务器处理");return ColdSteelStationNet::Request(this,TEXT("forge.claim"),NAME_None,1,BoundStation.Get());}
    auto* M=Model();if(!M||bActive||Job().Id.IsEmpty()||!Job().bFinished){Reason=TEXT("还没有可领取的成品");return false;}
    M->SyncRuntime();auto P=M->Snapshot();
    if(!ColdSteelInventory::Insert(P.Items,P.ForgeJob.Item)){Reason=TEXT("背包空间不足，成品保留待领");return false;}
    const auto LessonStage = BlacksmithApprenticeship::Stage(P);
    const bool UnworkedLessonBlade = P.ForgeJob.Recipe == BlacksmithApprenticeship::TargetRecipe
        && LessonStage != BlacksmithApprenticeship::EStage::NotStarted
        && LessonStage != BlacksmithApprenticeship::EStage::Complete
        && !P.ForgeJob.bHammeredBlank && P.ForgeJob.Hits == 0;
    BlacksmithApprenticeship::WorkpieceRemoved(P,true);
    P.ForgeJob={};if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    LastError.Reset();
    Reason=UnworkedLessonBlade ? TEXT("锻钢双手剑已放入背包。这炉没有敲到剑坯，打铁修炼仍在进行。") : TEXT("成品已放入背包");
    return true;
}
bool UColdSteelForgingSystem::GetPaidMaterials(TMap<FString,int64>& Paid) const
{
    Paid.Reset();
    if(Job().Id.IsEmpty())return false;
    if(Job().bMaterialsWaived)return true;
    Paid=Job().PaidMaterials;
    if(!Paid.IsEmpty())return true;
    if(Job().QualityVersion>=ColdSteelForgeQuality::Version)return false;
    // Keep old-save fallback identical for the materials display and discard quote.
    const auto* Recipe=Find(Job().Recipe);
    if(!Recipe||Recipe->LegacyInputs.IsEmpty())return false;
    // Jobs predating paid-material snapshots never paid the new search inputs.
    for(const auto& In:Recipe->LegacyInputs)if(!In.Item.StartsWith(TEXT("search_")))Paid.Add(In.Item,In.Count);
    return true;
}
bool UColdSteelForgingSystem::GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const
{
    Refund.Reset();Reason.Reset();
    if(!Model()||bActive||Job().Id.IsEmpty()||!Job().bFinished)
    {Reason=TEXT("只有已完成、尚未领取的成品可以废弃");return false;}
    if(!GetWorld())
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
    if(ColdSteelStationNet::IsClient(this)){Reason=TEXT("等待服务器处理");return ColdSteelStationNet::Request(this,TEXT("forge.discard"),NAME_None,1,BoundStation.Get());}
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
    const bool Free=P.ForgeJob.bMaterialsWaived;
    BlacksmithApprenticeship::WorkpieceRemoved(P,false);
    P.ForgeJob={};
    if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    LastError.Reset();
    Reason=Free?TEXT("成品已废弃 · 免材料制作，无材料返还"):Returned.IsEmpty()?TEXT("成品已废弃，各项材料折半不足 1 个，无可返还材料")
        :TEXT("成品已废弃，已返还背包：")+FString::Join(Returned,TEXT("、"));
    return true;
}

UColdSteelForgingSystem* UColdSteelForgingSystem::CreateNetworkSession(UColdSteelStatusModel* M)
{auto* Session=NewObject<UColdSteelForgingSystem>(GetGameInstance());Session->Recipes=Recipes;Session->MetalOptions=MetalOptions;Session->Blanks=Blanks;Session->NetworkModel=M;if(!M->ForgeJob().Id.IsEmpty()&&!M->ForgeJob().bFinished){FString Why;Session->Finish(Why);}return Session;}

FColdSteelForgeNetState UColdSteelForgingSystem::NetworkState() const
{
    FColdSteelForgeNetState S;const auto& CurrentJob=Job();S.JobId=CurrentJob.Id;S.Hits=CurrentJob.Hits;S.Finished=CurrentJob.bFinished;
    S.bHammeredBlank=CurrentJob.bHammeredBlank;
    S.Points=Sequence;S.Active=bActive;S.Open=bTargetOpen;S.Pending=bStrikePending;
    S.Completed=CompletedTargets;const double Now=FPlatformTime::Seconds();S.Elapsed=Now-StartedAt;
    S.Remaining=PhaseEndsAt-Now;S.ContactRemaining=StrikeContactAt-Now;S.Window=PhaseEndsAt-TargetOpenedAt;S.Life=StrikeTargetLife;return S;
}
void UColdSteelForgingSystem::NetworkSessionEnded()
{
    BoundStation.Reset();
    bActive=bTargetOpen=bStrikePending=false;ActiveId.Reset();Sequence.Reset();
    CompletedTargets=0;StrikeTargetLife=0;StartedAt=RetryAt=0.;
    TargetOpenedAt=PhaseEndsAt=StrikeContactAt=RecoveryAfterContact=0.;
}
void UColdSteelForgingSystem::ApplyNetworkState(const FColdSteelForgeNetState& S)
{
    if(!ColdSteelStationNet::IsClient(this))return;
    Sequence=S.Points;bActive=S.Active;bTargetOpen=S.Open;bStrikePending=S.Pending;CompletedTargets=S.Completed;
    ActiveId=S.JobId;const double Now=FPlatformTime::Seconds();StartedAt=Now-S.Elapsed;PhaseEndsAt=Now+S.Remaining;
    TargetOpenedAt=PhaseEndsAt-S.Window;StrikeContactAt=Now+S.ContactRemaining;StrikeTargetLife=S.Life;
}
