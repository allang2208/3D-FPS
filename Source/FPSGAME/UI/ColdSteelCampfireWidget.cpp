#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelSmeltingPresentation.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Building/ColdSteelCampfire.h"
#include "../Building/SmeltingSystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "GameFramework/PlayerController.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
#include "Components/Border.h"
#include "Components/ScrollBox.h"
#include "Components/HorizontalBox.h"
#include "Components/VerticalBox.h"
#include "Components/ProgressBar.h"

void UColdSteelSmeltingWidget::SetCampfire(AColdSteelCampfire* Fire)
{
    SetFurnace(nullptr,FIntVector::ZeroValue);Campfire=Fire;bCampfire=true;RowsSignature.Reset();
    StationTitle->SetText(FText::FromString(TEXT("篝火 · 共享烧烤")));
    ProgressTitle->SetText(FText::FromString(TEXT("公共队列与成品")));
    SectionTitle->SetText(FText::FromString(TEXT("可烧烤食材")));
    const bool HasRecipes=System&&System->Catalog().ContainsByPredicate([](const auto& R){return R.bCampfire;});
    RowsEmpty->SetText(FText::FromString(HasRecipes?TEXT("背包与仓库中没有可烧烤的食材")
        :TEXT("暂无已接入的烧烤菜谱；可添加木材取暖。")));
    StationFooter->SetText(FText::FromString(TEXT("Esc / × 关闭 · 材料由操作者支付，队列与成品全员共享\n燃烧时 5 米内饥饿与缺水自然消耗各减缓 50%，不叠加；木材离线也计时")));
    SetStatus(FString());RefreshRows();RefreshJob();
}
void UColdSteelSmeltingWidget::SubmitCampfire(uint8 Action)
{
    const auto* PC=GetOwningPlayer();auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(!PS||!Campfire.IsValid())return;
    PS->RequestCampfire(Campfire.Get(),Action,Action==1?SelectedRecipe:NAME_None,Action==1?Batch:1);
    SetStatus(PS->CampfireMessage());RefreshJob();
}
void UColdSteelSmeltingWidget::RefreshCampfireJob()
{
    const auto* Fire=Campfire.Get();if(!Fire||!System)return;
    const auto& S=Fire->SharedState();const auto& FC=System->FuelConfig();
    const auto* PC=GetOwningPlayer();const auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const bool Pending=PS&&PS->CampfireRequestPending();
    const bool Ready=Fire->IsAvailable()&&S.Revision>0&&!S.bSaveBlocked&&PS&&!Pending;
    const auto* R=System->Find(S.Recipe);const auto* Selected=System->Find(SelectedRecipe);
    auto Name=[&](const FString& Id)
    {
        if(const auto* Cached=CampfireNames.Find(Id))return *Cached;
        const FString N=Model?ColdSteelInventory::Text(Model->CreateItem(Id),TEXT("name")):FString();
        return CampfireNames.Add(Id,N.IsEmpty()?Id:N);
    };
    const double Fuel=Fire->DisplayFuel();
    int64 Stored=0;FString Products;
    for(const auto& P:S.Products){Stored+=P.Count;Products+=FString::Printf(TEXT("%s ×%lld  "),*Name(P.Item),P.Count);}
    const bool Blocked=R&&Stored+R->OutputCount>UColdSteelSmeltingSystem::CastingCapacity;
    const double Progress=R?FMath::Clamp(Fire->DisplayProgress(),0.0,R->Seconds):0;
    FString Queue;
    for(int32 I=0;I<S.Queue.Num();++I)
    {
        const auto& Q=S.Queue[I];const auto* QR=System->Find(Q.Recipe);
        Queue+=FString::Printf(TEXT("\n%d. %s ×%lld"),I+1,QR?*Name(QR->Output):*Q.Recipe.ToString(),Q.Batch);
    }
    JobTitle->SetText(FText::FromString(S.bSaveBlocked?TEXT("篝火保存待恢复")
        :Blocked?TEXT("成品已满 · 烧烤暂停"):R?(Fuel>0?TEXT("烧烤中"):TEXT("缺少燃料 · 进度保留"))
        :Fuel>0?TEXT("篝火燃烧中"):TEXT("篝火已熄灭")));
    JobTitle->SetColorAndOpacity(S.bSaveBlocked||Blocked?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    const FString Active=R?FString::Printf(TEXT("正在烧烤：%s · %lld / %lld 份\n"),*Name(R->Output),S.Produced,S.Batch):FString();
    JobDetail->SetText(FText::FromString(Active+FString::Printf(TEXT("成品 %lld / 60：%s\n等待队列 %d / 8%s"),Stored,
        Products.IsEmpty()?TEXT("暂无"):*Products,S.Queue.Num(),*Queue)));
    JobTime->SetText(FText::FromString(S.bSaveBlocked?TEXT("等待存档恢复"):R?FString::Printf(TEXT("本份剩余 %.1f 秒"),R->Seconds-Progress)
        :Fuel>0?TEXT("5 米内减耗生效"):TEXT("添柴后点燃")));
    AnimSmeltT=R?static_cast<float>(Progress/R->Seconds):0;bBurning=R&&Fuel>0&&!Blocked&&!S.bSaveBlocked;
    AnimFuelRatio=FC.Capacity>0?static_cast<float>(FMath::Clamp(Fuel/FC.Capacity,0.0,1.0)):0.f;bFuelAlive=Fuel>0&&!S.bSaveBlocked;
    ColdSteelSmeltingPresentation::RefreshProgressBars(SmeltBar,FuelBar,AnimSmeltT,AnimFuelRatio,bBurning,bFuelAlive);
    CdFuel=Fuel;CdNeed=R?FMath::Max(0.0,R->Seconds-Progress):0;CdStamp=FPlatformTime::Seconds();
    bCdRunning=R&&!Blocked;bCdBurning=Fuel>0&&!S.bSaveBlocked;PaintFuelLine();
    if(const auto* B=IconFor(FC.Item))FuelIcon->SetBrush(*B);
    UpgradeTab->SetVisibility(ESlateVisibility::Collapsed);bUpgradeOpen=false;
    Showcase->SetVisibility(ESlateVisibility::Collapsed);JobIcon->SetVisibility(ESlateVisibility::Collapsed);
    SmeltSection->SetVisibility(ESlateVisibility::Visible);FuelCard->SetVisibility(ESlateVisibility::Visible);
    RowsScroll->SetVisibility(ESlateVisibility::Visible);SectionTitle->SetVisibility(ESlateVisibility::Visible);
    BatchRow->SetVisibility(ESlateVisibility::Visible);StartButton->SetVisibility(ESlateVisibility::Visible);
    int64 MaxBatch=Selected&&Model?FMath::Clamp<int64>(Model->CountMaterial(Selected->Input)/Selected->InputCount,1,5):1;
    Batch=FMath::Clamp<int64>(Batch,1,MaxBatch);
    BatchText->SetText(FText::FromString(FString::Printf(TEXT("批量 ×%lld（最多 %lld）"),Batch,MaxBatch)));
    BatchMinus->SetIsEnabled(!Pending&&Batch>1);BatchPlus->SetIsEnabled(!Pending&&Batch<MaxBatch);
    if(auto* Caption=Cast<UTextBlock>(StartButton->GetContent()))Caption->SetText(FText::FromString(TEXT("加入烧烤队列")));
    StartButton->SetIsEnabled(Ready&&Selected&&Selected->bCampfire&&S.Queue.Num()<8&&Model&&Model->CountMaterial(Selected->Input)>=Selected->InputCount*Batch);
    AddFuelButton->SetIsEnabled(Ready&&Fuel+FC.SecondsPerUnit<=FC.Capacity+1e-6&&Model&&Model->CountMaterial(FC.Item)>0);
    CollectButton->SetVisibility(ESlateVisibility::Visible);CollectButton->SetIsEnabled(Ready&&Stored>0);
    if(auto* Caption=Cast<UTextBlock>(CollectButton->GetContent()))Caption->SetText(FText::FromString(TEXT("领取公共成品")));
    CollectGlow->SetVisibility(Stored>0?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    if(PS)SetStatus(Pending?TEXT("正在同步篝火操作…"):PS->CampfireMessage());
    RefreshRows();
}
