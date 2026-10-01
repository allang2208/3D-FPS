#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelDungeonLoot.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Async/Async.h"
#include "Engine/Texture2D.h"
#include "ImageCore.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SToolTip.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SGridPanel.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Text/STextBlock.h"

TSharedRef<SWidget> UColdSteelExpeditionWidget::Section(const FString& Title,const FString& Text)
{
    return SNew(SBorder).BorderImage(&HeroBrush).Padding(16)
        [SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Label(Title,16,ColdSteelUI::TextPrimary)]
            +SVerticalBox::Slot().AutoHeight()[Label(Text,14,ColdSteelUI::TextSecondary)]];
}

void UColdSteelExpeditionWidget::RefreshDetail()
{
    UpdateSelectionStyles();
    if(!DetailRows)return;
    DetailRows->ClearChildren();
    const auto* Entry=Selection();
    if(!Entry)
    {
        DetailRows->AddSlot().AutoHeight()[Section(TEXT("尚未选择目的地"),TEXT("从左侧选择目的地，查看路线、奖励与出征规则。"))];
        return;
    }
    if(DetailTab==1){AddRewards();return;}
    if(DetailTab==2)
    {
        DetailRows->AddSlot().AutoHeight().Padding(0,0,0,12)[Label(TEXT("出征规则"),16,ColdSteelUI::TextPrimary)];
        for(const auto& Rule:Entry->Rules)
            DetailRows->AddSlot().AutoHeight().Padding(0,0,0,10)[Section(Rule.Title,Rule.Text)];
        if(Entry->Rules.IsEmpty())DetailRows->AddSlot().AutoHeight()[Section(TEXT("暂无规则情报"),TEXT("此目的地尚未提供详细规则。"))];
        return;
    }
    DetailRows->AddSlot().AutoHeight().Padding(0,0,0,16)[Label(Entry->Description,14,ColdSteelUI::TextSecondary)];
    TArray<FColdSteelExpeditionSection> Facts={{TEXT("探索规模"),Entry->Scale},{TEXT("威胁情报"),Entry->Threat}};
    if(!Entry->RecommendedLevel.IsEmpty())Facts.Add({TEXT("推荐等级"),Entry->RecommendedLevel});
    auto Grid=SNew(SGridPanel);
    const int32 Columns=bSingleColumnFacts?1:2;
    for(int32 I=0;I<Facts.Num();++I)
    {
        Grid->SetColumnFill(I%Columns,1.f);
        Grid->AddSlot(I%Columns,I/Columns).Padding(0,0,I%Columns+1<Columns?8:0,8)[Section(Facts[I].Title,Facts[I].Text)];
    }
    DetailRows->AddSlot().AutoHeight()[Grid];
    if(!Entry->Routes.IsEmpty())
    {
        DetailRows->AddSlot().AutoHeight().Padding(0,12,0,6)[Label(TEXT("路线情报"),16,ColdSteelUI::TextPrimary)];
        DetailRows->AddSlot().AutoHeight().Padding(0,0,0,12)
            [Label(TEXT("每条路线：随机设施房 1–2 间 → 主题房 3 间 → 随机设施房 1–2 间"),14,ColdSteelUI::TextSecondary)];
        for(const auto& Route:Entry->Routes)
            DetailRows->AddSlot().AutoHeight().Padding(0,0,0,8)[Section(Route.Title,Route.Text)];
        DetailRows->AddSlot().AutoHeight().Padding(0,4,0,12)
            [Label(TEXT("路线顺序固定，过渡房与空间布局随机。此处为结构情报，不是本局地图。"),12,ColdSteelUI::TextTertiary)];
    }
    if(!Entry->Completion.IsEmpty())DetailRows->AddSlot().AutoHeight().Padding(0,0,0,10)
        [Section(TEXT("共同目标 · 数据档案中心 → 首领区域"),Entry->Completion)];
    if(Entry->bDungeonLoot)DetailRows->AddSlot().AutoHeight()
        [Label(TEXT("全图 18–25 间主要房间；选择一路通关约经过 8–11 间。包含公共前段、档案中心与首领房，不含连接走廊、前厅及奖励侧室。"),12,ColdSteelUI::TextTertiary)];
}

void UColdSteelExpeditionWidget::BuildRewardPreview()
{
    auto* Model=Profile();
    if(bRewardsLoaded||!Model)return;
    bRewardsLoaded=true;
    for(const auto& Candidate:FColdSteelDungeonLoot::PreviewItems())
    {
        FColdSteelExpeditionReward Row;
        const auto* Ammo=Model->AmmoType(Candidate.Definition);
        if(Ammo)
        {
            Row.Content.Name=Ammo->Name;Row.Content.Description=Ammo->Description;
            Row.Content.Type=TEXT("弹药");Row.Content.Icon=Ammo->Icon;Row.Content.Rarity=TEXT("common");
        }
        else
        {
            const auto Item=Model->CreateItem(Candidate.Definition);
            Row.Content=BuildColdSteelItemTooltip(Item,Model,nullptr);
        }
        if(Row.Content.Name.IsEmpty())continue;
        Row.Group=Candidate.Definition.StartsWith(TEXT("enchant_scroll_"))?2:
            (Ammo||Candidate.Definition==TEXT("gold")||Candidate.Definition.StartsWith(TEXT("hp_potion"))||Candidate.Definition.StartsWith(TEXT("mp_potion")))?0:1;
        Row.Availability=Candidate.MinimumDepth<=0?TEXT("起始区域可出现"):Candidate.MinimumDepth<8?TEXT("深入设施后可出现"):TEXT("深层区域可出现");
        if(Candidate.bInFinalTier)Row.Availability+=TEXT(" · 最终宝箱候选");
        if(!Row.Content.Icon.IsEmpty())Row.IconPath=FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Row.Content.Icon;
        Row.Brush=MakeShared<FSlateBrush>();
        Row.Brush->DrawAs=ESlateBrushDrawType::Image;
        RewardPreview.Add(MoveTemp(Row));
    }
}

void UColdSteelExpeditionWidget::LoadNextRewardIcon()
{
    if(bClosing||bRewardIconLoading||DetailTab!=1||!IsInViewport())return;
    while(RewardPreview.IsValidIndex(NextRewardIcon)&&RewardPreview[NextRewardIcon].IconPath.IsEmpty())++NextRewardIcon;
    if(!RewardPreview.IsValidIndex(NextRewardIcon))return;
    const int32 Index=NextRewardIcon++;
    const FString Filename=RewardPreview[Index].IconPath;
    bRewardIconLoading=true;
    const TWeakObjectPtr<UColdSteelExpeditionWidget> Weak(this);
    // One bounded decode at a time; full-resolution source PNGs never become UI textures.
    Async(EAsyncExecution::ThreadPool,[Weak,Index,Filename]()
    {
        auto Thumbnail=MakeShared<FImage,ESPMode::ThreadSafe>();FImage Source;
        bool Loaded=FImageUtils::LoadImage(*Filename,Source);
        if(Loaded)
        {
            const float Scale=FMath::Min(1.f,192.f/FMath::Max(Source.SizeX,Source.SizeY));
            FImageCore::ResizeImageAllocDest(Source,*Thumbnail,FMath::Max(1,FMath::RoundToInt(Source.SizeX*Scale)),
                FMath::Max(1,FMath::RoundToInt(Source.SizeY*Scale)),ERawImageFormat::BGRA8,EGammaSpace::sRGB);
        }
        AsyncTask(ENamedThreads::GameThread,[Weak,Index,Thumbnail,Loaded]()
        {
            auto* Self=Weak.Get();if(!Self||Self->bClosing)return;
            Self->bRewardIconLoading=false;
            if(Loaded)if(auto* Texture=FImageUtils::CreateTexture2DFromImage(*Thumbnail))
            {
                Self->RewardTextures.Add(Texture);
                auto& Row=Self->RewardPreview[Index];Row.Brush->SetResourceObject(Texture);
                Row.Brush->ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());
                if(auto Image=Row.Image.Pin()){Image->SetImage(Row.Brush.Get());Image->Invalidate(EInvalidateWidgetReason::Layout);}
            }
            Self->LoadNextRewardIcon();
        });
    });
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::RewardCard(FColdSteelExpeditionReward& Reward)
{
    const auto Brush=Reward.Brush;
    auto Details=SNew(SVerticalBox);
    Details->AddSlot().AutoHeight().Padding(0,0,0,8)[Label(Reward.Content.Name,20,ColdSteelUI::ItemTooltipText)];
    Details->AddSlot().AutoHeight().Padding(0,0,0,8)
        [Label(ColdSteelUI::RarityLabel(Reward.Content.Rarity)+TEXT(" · ")+Reward.Content.Type,12,ColdSteelUI::ItemTooltipGold)];
    if(!Reward.Content.Description.IsEmpty())Details->AddSlot().AutoHeight().Padding(0,0,0,10)
        [Label(Reward.Content.Description,14,ColdSteelUI::ItemTooltipText)];
    for(const auto& Stat:Reward.Content.Summary)
        Details->AddSlot().AutoHeight().Padding(0,0,0,5)[Label(Stat.Label+TEXT("  ")+Stat.Value,14,ColdSteelUI::ItemTooltipText)];
    Details->AddSlot().AutoHeight().Padding(0,8,0,0)[Label(Reward.Availability+TEXT("\n可能获得 · 不保证掉落"),12,ColdSteelUI::ItemTooltipSecondary)];
    auto Tip=SNew(SToolTip).BorderImage(&RewardTooltipBrush).TextMargin(16)
        [SNew(SBox).WidthOverride_Lambda([this]() { return BodyHost?FMath::Min(340.f,FMath::Max(120.f,BodyHost->GetCachedGeometry().GetLocalSize().X-48.f)):340.f; })[Details]];
    TSharedPtr<SImage> Image;
    auto CardContent=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,12,0)
            [SNew(SBox).WidthOverride(48).HeightOverride(48)
                [SNew(SOverlay)
                    +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(Reward.Content.Name.Left(1)))
                            .Font(ColdSteelUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::TextSecondary)
                            .Visibility_Lambda([Brush](){return Brush->GetResourceObject()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})]
                    +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
                        [SAssignNew(Image,SImage).Image(Brush.Get()).Visibility_Lambda([Brush]() { return Brush->GetResourceObject()?EVisibility::HitTestInvisible:EVisibility::Collapsed; })]]]]
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(Reward.Content.Name,14,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[Label(ColdSteelUI::RarityLabel(Reward.Content.Rarity),12,ColdSteelUI::RarityColor(Reward.Content.Rarity))]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Label(TEXT("可能获得"),12,ColdSteelUI::TextTertiary)]];
    Reward.Image=Image;
    return SNew(SBorder).BorderImage(&HeroBrush).Padding(12).ToolTip(Tip)
        [SNew(SBox).MinDesiredHeight(80)[CardContent]];
}

void UColdSteelExpeditionWidget::AddRewards()
{
    if(!Selection()||!Selection()->bDungeonLoot)
    {DetailRows->AddSlot().AutoHeight()[Section(TEXT("暂无奖励情报"),TEXT("此目的地尚未提供奖励列表。"))];return;}
    BuildRewardPreview();
    DetailRows->AddSlot().AutoHeight().Padding(0,0,0,12)
        [Section(TEXT("可能获得"),TEXT("奖励随探索推进变化。下列物品来自实际宝箱掉落池，每次只随机获得其中部分；悬停查看说明。"))];
    const TCHAR* Groups[]={TEXT("基础与进阶补给"),TEXT("材料与重铸"),TEXT("附魔卷轴")};
    for(int32 Group=0;Group<3;++Group)
    {
        auto Grid=SNew(SGridPanel);int32 Count=0;
        for(auto& Reward:RewardPreview)if(Reward.Group==Group)
        {
            const int32 Column=Count%RewardColumns;
            Grid->SetColumnFill(Column,1.f);
            Grid->AddSlot(Column,Count/RewardColumns).Padding(0,0,Column+1<RewardColumns?8:0,8)[RewardCard(Reward)];++Count;
        }
        if(!Count)continue;
        DetailRows->AddSlot().AutoHeight().Padding(0,8,0,10)[Label(Groups[Group],16,ColdSteelUI::TextPrimary)];
        DetailRows->AddSlot().AutoHeight()[Grid];
    }
    if(RewardPreview.IsEmpty())DetailRows->AddSlot().AutoHeight()[Section(TEXT("奖励情报暂不可用"),TEXT("未能读取奖励目录。出征不会因此扣除额外物品。"))];
    else DetailRows->AddSlot().AutoHeight().Padding(0,12,0,0)
        [Section(TEXT("首领后的最终宝箱"),FString::Printf(TEXT("击败首领后开放奖励区。最终宝箱使用最高档掉落池，抽中物品的基础数量按 %g 倍发放；不是获得所有候选物品。"),FColdSteelDungeonLoot::FinalQuantityMultiplier()))];
    LoadNextRewardIcon();
}
