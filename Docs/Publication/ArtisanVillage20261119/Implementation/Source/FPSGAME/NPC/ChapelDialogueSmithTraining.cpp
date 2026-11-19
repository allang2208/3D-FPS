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
    return Model?static_cast<int32>(BlacksmithApprenticeship::Stage(Model->ProfileView())):0;
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
    Message=TEXT("正在领取任务材料…");
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

void UChapelDialogueComponent::AppendTrackedTasks(const APawn* Viewer,TArray<FTrackedTaskView>& Out)
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!Viewer||!PC||!PC->IsLocalController()||Viewer!=PC->GetPawn())return;
    const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model)return;
    const FString ThisProfile=Model->ProfileSlot();
    if(LastTrackerProfile!=ThisProfile)
    {
        LastTrackerProfile=ThisProfile;
        SmithTracker={};
        CarpenterTracker={};
    }

    struct FLessonStep
    {
        FName Id;
        FText Objective, Stage, Hint;
    };
    static const FLessonStep SmithSteps[]={
        {TEXT("materials"),INVTEXT("在铸造台为唐刀开炉"),INVTEXT("第一步 · 开炉"),INVTEXT("选「唐刀」和铁锭，用铁匠给的锻造合金坯、木材和铁锭开始锻造。")},
        {TEXT("hammer"),INVTEXT("亲手在刀坯上落锤，锻出唐刀"),INVTEXT("第二步 · 锤炼"),INVTEXT("移动白圈，对准刀坯上的蓝圈后单击左键。打准的锤数越多，成品伤害越高。")},
        {TEXT("finish"),INVTEXT("领取亲手锻造的唐刀"),INVTEXT("第三步 · 取刀"),INVTEXT("在铸造台领取唐刀，武器放进背包即完成任务。废弃工件后可以重新开炉。")}
    };
    static const FLessonStep WoodSteps[]={
        {TEXT("materials"),INVTEXT("在木工台为学徒长杖开料"),INVTEXT("第一步 · 开料"),INVTEXT("到工坊一楼选「法杖 · 学徒长杖」和原木芯，用木匠给的材料开始加工。")},
        {TEXT("cut"),INVTEXT("沿轮廓锯出一把合格的学徒长杖"),INVTEXT("第二步 · 上锯"),INVTEXT("Q / E 转动木板，空格切换切割，按住左键拖动进料。保留浅色主体和连接处，清除外围废料。")},
        {TEXT("finish"),INVTEXT("领取亲手做成的学徒长杖"),INVTEXT("第三步 · 取杖"),INVTEXT("在工作面板领取合格的学徒长杖，武器放进背包即完成任务。")}
    };
    const auto Append=[&](int32 Stage,FLessonTrackerState& State,FName Id,const FText& Title,const FText& Area,TConstArrayView<FLessonStep> Steps)
    {
        if(Stage<=0){State={};return;}
        const bool Complete=Stage>Steps.Num();
        if(Complete)
        {
            const double Now=GetWorld()->GetRealTimeSeconds();
            if(State.bWasActive)State.ShowCompletionUntil=Now+5.;
            State.bWasActive=false;
            if(Now>=State.ShowCompletionUntil)return;
        }
        else State.bWasActive=true;

        auto& Task=Out.AddDefaulted_GetRef();
        Task.Id=Id;
        Task.InstanceId=ThisProfile.IsEmpty()?Id.ToString():ThisProfile;
        Task.Title=Title;
        Task.Area=Area;
        Task.Priority=40;
        Task.Stage=Complete?INVTEXT("修炼完成"):Steps[Stage-1].Stage;
        if(!Complete)Task.Hint=Steps[Stage-1].Hint;
        for(int32 Index=0;Index<FMath::Min(Stage,Steps.Num());++Index)
        {
            auto& Row=Task.Objectives.AddDefaulted_GetRef();
            Row.Id=Steps[Index].Id;
            Row.Text=Steps[Index].Objective;
            Row.State=Index+1<Stage?ETrackedObjectiveState::Completed:ETrackedObjectiveState::Active;
        }
    };
    const auto& Profile=Model->ProfileView();
    const auto SmithStage=BlacksmithApprenticeship::Stage(Profile);
    Append(int32(SmithStage),SmithTracker,TEXT("village.blacksmith.apprenticeship"),
        INVTEXT("打铁修炼"),INVTEXT("村庄铁匠铺"),SmithSteps);
    if(SmithStage==BlacksmithApprenticeship::EStage::Materials)
    {
        auto& Task=Out.Last();
        if(BlacksmithApprenticeship::NeedsSupplies(Profile))
            Task.Hint=INVTEXT("找铁匠选择「学习技能」，领取第一炉材料。");
        else if(!Profile.ForgeJob.Id.IsEmpty())
            Task.Hint=Profile.ForgeJob.Recipe==BlacksmithApprenticeship::TargetRecipe
                ?INVTEXT("上一炉还没落锤就结束了。先处理成品，再开炉亲手锻刀。")
                :INVTEXT("铸造台上有另一件工件，先处理它，再选择唐刀开炉。");
    }
    const auto WoodStage=CarpenterApprenticeship::Stage(Profile);
    Append(int32(WoodStage),CarpenterTracker,TEXT("village.carpenter.apprenticeship"),
        INVTEXT("木工修炼"),INVTEXT("村庄木工工坊"),WoodSteps);
    if(WoodStage==CarpenterApprenticeship::EStage::Materials)
    {
        auto& Task=Out.Last();
        if(CarpenterApprenticeship::NeedsSupplies(Profile))
            Task.Hint=INVTEXT("找木匠选择「学习技能」，领取木材和原木芯。");
        else if(!Profile.WoodworkingJob.Id.IsEmpty())
            Task.Hint=Profile.WoodworkingJob.Recipe==CarpenterApprenticeship::TargetRecipe
                ?INVTEXT("这把杖未达到图样要求。废弃工件可收回部分材料，备齐后再做一把。")
                :INVTEXT("台上还有另一件工件。先处理它，再选择学徒长杖的图样。");
    }
}
