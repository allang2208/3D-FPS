#include "ChapelDialogueComponent.h"
#include "VillageArtisanMerchant.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Tasks/BlacksmithApprenticeship.h"
#include "../Tasks/CarpenterApprenticeship.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

void UChapelDialogueComponent::BeginPlay()
{
    Super::BeginPlay();
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(PC&&PC->IsLocalController())
        if(auto* Tracking=GetWorld()->GetSubsystem<UTaskTrackingSubsystem>())Tracking->RegisterSource(this);
}

int32 UChapelDialogueComponent::SmithTrainingStage() const
{
    const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    return Model?BlacksmithApprenticeship::LessonStep(BlacksmithApprenticeship::Stage(Model->ProfileView())):0;
}

bool UChapelDialogueComponent::CanCollectTrainingSupplies() const
{
    const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model)return false;
    const auto& Profile=Model->ProfileView();
    if(IsCarpenter())return CarpenterApprenticeship::NeedsSupplies(Profile);
    return IsBlacksmith() && BlacksmithApprenticeship::NeedsSupplies(Profile);
}

void UChapelDialogueComponent::RequestSmithTraining()
{
    if(IsBlacksmith())RequestArtisanTask();
}

int32 UChapelDialogueComponent::CarpenterTrainingStage() const
{
    const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    return Model?int32(CarpenterApprenticeship::Stage(Model->ProfileView())):0;
}

void UChapelDialogueComponent::RequestCarpenterTraining()
{
    if(IsCarpenter())RequestArtisanTask();
}

void UChapelDialogueComponent::RequestArtisanTask()
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!Screen||!PC||!PC->IsLocalController()||bPending||!CanCollectTrainingSupplies())return;
    bPending=true;
    Message=IsBlacksmith() && SmithTrainingStage()==2 ? TEXT("正在交付铁矿石…") : TEXT("正在领取任务材料…");
    OnChanged.Broadcast();
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();
        if(!PS||!PS->RequestArtisanLesson(Cast<AVillageArtisanMerchant>(LocalMerchant.Get()),LocalSession))
            FinishArtisanInventoryRequest(LocalSession,false,TEXT("背包尚在同步，请稍后再领。"));
        return;
    }
    AcceptArtisanTraining(LocalSession,IsCarpenter()?TEXT("carpenter.training"):TEXT("smith.training"));
}

void UChapelDialogueComponent::FinishArtisanInventoryRequest(uint32 Session,bool Success,const FString& Reason)
{
    ClientResult_Implementation(Session,Success,Reason);
}

bool UChapelDialogueComponent::CanAcceptArtisanTask(uint32 Session,const AVillageArtisanMerchant* Teacher) const
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    return PC&&PC->HasAuthority()&&Session!=0&&Session==AuthoritySession&&IsValid(Teacher)
        &&Teacher==AuthorityMerchant.Get()&&PC->GetPawn()==AuthorityConversationPawn.Get()&&InReach(Teacher);
}

void UChapelDialogueComponent::AcceptArtisanTraining(uint32 Session,FName Action)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    const bool bCarpenter=Action==TEXT("carpenter.training");
    auto* Artisan=Cast<AVillageArtisanMerchant>(AuthorityMerchant.Get());
    if(!PC||!PC->IsLocalController()||!CanAcceptArtisanTask(Session,Artisan)||Artisan->IsCarpenterMerchant()!=bCarpenter)
    {
        ClientResult(Session,false,bCarpenter?TEXT("交谈已结束，请回到木匠身边。"):TEXT("交谈已结束，请回到铁匠身边。"));
        return;
    }
    auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||Model->RuntimePawn()!=PC->GetPawn()){ClientResult(Session,false,TEXT("角色档案正在同步，请稍后再试。"));return;}
    FString Reason;
    const bool Success=bCarpenter?CarpenterApprenticeship::Accept(Model,FString(),Reason)
                                :BlacksmithApprenticeship::Accept(Model,FString(),Reason);
    ClientResult(Session,Success,Reason);
}

namespace
{
    struct FLessonStep
    {
        FName Id;
        FText Objective, Stage, Hint;
    };
    static const FLessonStep SmithSteps[]={
        {TEXT("mine"),INVTEXT("采集并拾取十块铁矿石"),INVTEXT("采矿 · 露天铁矿脉"),INVTEXT("装备铁匠赠送的十字镐，前往地图上的露天铁矿脉。敲碎含铁岩块并拾取铁矿石。")},
        {TEXT("deliver_ore"),INVTEXT("回铁匠铺交付十块铁矿石"),INVTEXT("采矿 · 回店交付"),INVTEXT("随身带齐十块铁矿石，与铁匠交谈，选择「修炼技能」并交付。")},
        {TEXT("smelt"),INVTEXT("在高炉冶炼并领取三块金属锭"),INVTEXT("冶炼 · 炼矿取锭"),INVTEXT("到铁匠铺西门一侧的炉棚，给任一座高炉添木材。选择铁矿，数量设为 3，冶炼完成后领取铁锭。")},
        {TEXT("materials"),INVTEXT("在铸造台为锻钢双手剑开炉"),INVTEXT("打铁 · 备料开炉"),INVTEXT("回铁匠铺选「锻钢双手剑」，投入合金胚 ×1 和任选同种金属锭 ×3。")},
        {TEXT("hammer"),INVTEXT("亲手在剑坯上落锤，锻出锻钢双手剑"),INVTEXT("打铁 · 锤炼"),INVTEXT("移动白圈，对准剑坯上的蓝圈后单击左键。打准的锤数越多，成品伤害越高。")},
        {TEXT("finish"),INVTEXT("领取亲手锻造的锻钢双手剑"),INVTEXT("打铁 · 取剑"),INVTEXT("在铸造台领取锻钢双手剑，武器放进背包即完成任务。废弃工件后可以重新开炉。")}
    };
    static const FLessonStep WoodSteps[]={
        {TEXT("materials"),INVTEXT("在木工台为学徒长杖开料"),INVTEXT("第一步 · 开料"),INVTEXT("到工坊一楼选「法杖 · 学徒长杖」和原木芯，用木匠给的材料开始加工。")},
        {TEXT("cut"),INVTEXT("沿轮廓锯出一把合格的学徒长杖"),INVTEXT("第二步 · 上锯"),INVTEXT("Q / E 转动木板，空格切换切割，按住左键拖动进料。保留浅色主体和连接处，清除外围废料。")},
        {TEXT("finish"),INVTEXT("领取亲手做成的学徒长杖"),INVTEXT("第三步 · 取杖"),INVTEXT("在工作面板领取合格的学徒长杖，武器放进背包即完成任务。")}
    };
}

bool UChapelDialogueComponent::ReadJournalDetails(const APawn* Viewer, const FTrackedTaskView& Task, FTaskJournalDetails& Out) const
{
    const auto* PC = Cast<APlayerController>(GetOwner());
    if (!Viewer || !PC || PC->GetPawn() != Viewer) return false;
    const bool bSmith = Task.Id == BlacksmithApprenticeship::TaskId;
    if (!bSmith && Task.Id != CarpenterApprenticeship::TaskId) return false;

    Out.Introduction = bSmith
        ? INVTEXT("与铁匠交谈领取十字镐，按地图指引采回十块铁矿石。交付后，到西门一侧的炉棚学习冶炼。取出三块金属锭后，回铺用合金胚开炉，亲手锤炼并领取你的第一把锻钢双手剑。")
        : INVTEXT("木匠会给你木材和原木芯。去工坊一楼照着图样锯出杖身，做一把能交工的学徒长杖。");
    Out.Reward = bSmith
        ? INVTEXT("接取时获得十字镐 ×1。交矿后获得练习用铁矿 ×3、木材 ×1、合金胚 ×1。完成修炼可领取亲手锻造的锻钢双手剑 ×1。")
        : INVTEXT("学徒长杖 ×1。在木工台领取合格的成品，长杖进入背包。");
    const TConstArrayView<FLessonStep> Steps = bSmith ? MakeArrayView(SmithSteps) : MakeArrayView(WoodSteps);
    for (const FLessonStep& Step : Steps)
    {
        auto& Row = Out.Steps.AddDefaulted_GetRef();
        Row.Id = Step.Id;
        Row.Text = Step.Objective;
        Row.Hint = Step.Hint;
        const auto* Live = Task.Objectives.FindByPredicate([&](const auto& Goal) { return Goal.Id == Step.Id; });
        Row.State = Live ? Live->State : ETrackedObjectiveState::Pending;
        if (Live) { Row.Current = Live->Current; Row.Target = Live->Target; }
    }
    return true;
}

void UChapelDialogueComponent::AppendTrackedTasks(const APawn* Viewer,TArray<FTrackedTaskView>& Out)
{
    AppendLessons(Viewer, Out, ETaskViewPurpose::Tracker);
}

void UChapelDialogueComponent::AppendJournalTasks(const APawn* Viewer,TArray<FTrackedTaskView>& Out)
{
    AppendLessons(Viewer, Out, ETaskViewPurpose::Journal);
}

void UChapelDialogueComponent::AppendLessons(const APawn* Viewer,TArray<FTrackedTaskView>& Out,ETaskViewPurpose Purpose)
{
    const bool bJournal = Purpose == ETaskViewPurpose::Journal;
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!Viewer||!PC||!PC->IsLocalController()||Viewer!=PC->GetPawn())return;
    const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model)return;
    const FString ThisProfile=Model->ProfileSlot();
    if(!bJournal && LastTrackerProfile!=ThisProfile)
    {
        LastTrackerProfile=ThisProfile;
        SmithTracker={};
        CarpenterTracker={};
    }

    const auto& Profile=Model->ProfileView();
    const auto Append=[&](int32 Stage,FLessonTrackerState& State,FName Id,const FText& Title,const FText& Area,TConstArrayView<FLessonStep> Steps)
    {
        if(!bJournal && Stage<=0){State={};return;}
        const bool Complete=Stage>Steps.Num();
        if(!bJournal && Complete)
        {
            const double Now=GetWorld()->GetRealTimeSeconds();
            if(State.bWasActive)State.ShowCompletionUntil=Now+5.;
            State.bWasActive=false;
            if(Now>=State.ShowCompletionUntil)return;
        }
        else if(!bJournal) State.bWasActive=true;

        auto& Task=Out.AddDefaulted_GetRef();
        Task.Id=Id;
        Task.InstanceId=ThisProfile.IsEmpty()?Id.ToString():ThisProfile;
        if (const auto* Revision = Profile.CampfireWorldReceipts.Find(Id.ToString() + TEXT(".reset")))
            Task.InstanceId += FString::Printf(TEXT("/%lld"), *Revision);
        Task.Title=Title;
        Task.Area=bJournal ? FText::Format(INVTEXT("个人修炼 · {0}"),Area) : Area;
        Task.Priority=40;
        if (Stage <= 0)
        {
            Task.State=ETrackedTaskState::NotStarted;
            Task.Stage=INVTEXT("未领取");
            Task.Hint=FText::Format(Id==BlacksmithApprenticeship::TaskId ? INVTEXT("前往{0}，与铁匠交谈并选择「修炼技能」。") : INVTEXT("前往{0}，与店主交谈并选择「学习技能」。"),Area);
            return;
        }
        Task.State=Complete ? ETrackedTaskState::Completed : ETrackedTaskState::InProgress;
        Task.Stage=Complete?INVTEXT("修炼完成"):Steps[Stage-1].Stage;
        if (bJournal)
            Task.Stage = FText::Format(INVTEXT("{0} · 已完成 {1}/{2} 步"), Task.Stage,
                FMath::Min(Stage - 1, Steps.Num()), Steps.Num());
        if(!Complete)Task.Hint=Steps[Stage-1].Hint;
        for(int32 Index=0;Index<FMath::Min(Stage,Steps.Num());++Index)
        {
            auto& Row=Task.Objectives.AddDefaulted_GetRef();
            Row.Id=Steps[Index].Id;
            Row.Text=Steps[Index].Objective;
            Row.State=Index+1<Stage?ETrackedObjectiveState::Completed:ETrackedObjectiveState::Active;
        }
    };
    const auto SmithStage=BlacksmithApprenticeship::Stage(Profile);
    const int32 BeforeSmith = Out.Num();
    Append(BlacksmithApprenticeship::LessonStep(SmithStage),SmithTracker,BlacksmithApprenticeship::TaskId,
        INVTEXT("铁匠修炼 · 采矿、冶炼与打铁"),INVTEXT("村庄铁匠铺"),SmithSteps);
    if (Out.Num() > BeforeSmith && !Out.Last().Objectives.IsEmpty())
    {
        for (auto& Row:Out.Last().Objectives)
        {
            if (Row.Id==TEXT("mine"))
            {
                Row.Current=BlacksmithApprenticeship::OreCollected(SmithStage);
                Row.Target=BlacksmithApprenticeship::RequiredOre;
            }
            if (Row.Id==TEXT("smelt"))
            {
                Row.Current=BlacksmithApprenticeship::IngotsCollected(SmithStage);
                Row.Target=BlacksmithApprenticeship::RequiredIngots;
            }
        }
        if (SmithStage==BlacksmithApprenticeship::EStage::Smelting && BlacksmithApprenticeship::NeedsSupplies(Profile))
            Out.Last().Hint=INVTEXT("与铁匠交谈，选择「修炼技能」领取冶炼材料。");
    }
    if(SmithStage==BlacksmithApprenticeship::EStage::Materials)
    {
        auto& Task=Out.Last();
        if(!Profile.ForgeJob.Id.IsEmpty())
            Task.Hint=Profile.ForgeJob.Recipe==BlacksmithApprenticeship::TargetRecipe
                ?INVTEXT("先处理台上的旧工件，再开新炉，亲手锻出锻钢双手剑。")
                :INVTEXT("铸造台上有另一件工件，先处理它，再选择锻钢双手剑开炉。");
    }
    const auto WoodStage=CarpenterApprenticeship::Stage(Profile);
    Append(int32(WoodStage),CarpenterTracker,CarpenterApprenticeship::TaskId,
        INVTEXT("木工修炼"),INVTEXT("村庄木工工坊"),WoodSteps);
    if(WoodStage==CarpenterApprenticeship::EStage::Materials)
    {
        auto& Task=Out.Last();
        if(CarpenterApprenticeship::NeedsSupplies(Profile))
            Task.Hint=INVTEXT("找木匠选择「学习技能」，领取木材和原木芯。");
        else if(!Profile.WoodworkingJob.Id.IsEmpty())
            Task.Hint=Profile.WoodworkingJob.Recipe==CarpenterApprenticeship::TargetRecipe
                ?INVTEXT("先处理台上的旧工件，再开料做一把符合图样的学徒长杖。")
                :INVTEXT("台上还有另一件工件。先处理它，再选择学徒长杖的图样。");
    }
}
