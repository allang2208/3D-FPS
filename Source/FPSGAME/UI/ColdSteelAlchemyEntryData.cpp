#include "ColdSteelAlchemyWidget.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "ColdSteelForgeBoard.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelCraftingResultStyle.h"
#include "../Building/AlchemySystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "Blueprint/WidgetTree.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Components/WrapBox.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"

void UColdSteelAlchemyWidget::RefreshEntry(bool DataChanged)
{
    bEntryDirty|=DataChanged;if(bWorld||bBook||!System||!Model)return;
    const auto Set=[](UTextBlock* Label,const FString& Value){if(Label&&Label->GetText().ToString()!=Value)Label->SetText(FText::FromString(Value));};
    const auto* R=Recipe();const auto& J=System->Job();const bool Pending=System->HasJob();
    const bool Free=Pending?J.bMaterialsWaived:UDevelopmentTuningSubsystem::IsFreeCrafting(Model);
    if(bEntryDirty)
    {
        const int32 Index=R?System->Recipes().IndexOfByPredicate([R](const auto& Recipe){return Recipe.Id==R->Id;}):INDEX_NONE;
        if(Choice->GetSelectedIndex()!=Index)Choice->SetSelectedIndex(Index);
        Set(EntryRecipeTitle,R?FString::Printf(TEXT("%d / %d · %s"),Index+1,System->Recipes().Num(),*R->Name):TEXT("配方未就绪"));
        TArray<TPair<FString,int64>> Inputs;
        if(Pending)
        {
            TMap<FString,int64> Paid;for(const auto& Item:J.Escrow)Paid.FindOrAdd(Item.Definition)+=Item.Count;
            if(R)for(const auto& Input:R->Inputs)if(const auto* Count=Paid.Find(Input.Item)){Inputs.Emplace(Input.Item,*Count);Paid.Remove(Input.Item);}
            TArray<FString> Extra;Paid.GetKeys(Extra);Extra.Sort();for(const auto& Id:Extra)Inputs.Emplace(Id,Paid[Id]);
        }
        else if(R)for(const auto& Input:R->Inputs)Inputs.Emplace(Input.Item,Input.Count);
        Set(Materials,Free?TEXT("免材料制作"):Pending?TEXT("本炉已备材料"):TEXT("所需材料"));
        Set(EntryMaterialSource,Free?TEXT("本炉免费备料 · 不扣材料，废弃不返料"):Pending?(J.Escrow.IsEmpty()?TEXT("本炉材料记录不可用"):TEXT("本炉材料已扣除")):R?TEXT("材料来源 · 背包 + 主仓库"):TEXT("暂无可用配方"));
        Set(EntryQuantityHeader,Pending?TEXT("已备料数量"):Free?TEXT("持有 / 本次消耗"):TEXT("持有 / 需要"));EnsureEntryMaterialRows(Inputs.Num());
        for(int32 I=0;I<EntryMaterialRows.Num();++I)
        {
            const auto& Row=EntryMaterialRows[I];const bool Visible=Inputs.IsValidIndex(I);
            const auto RowVisibility=Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
            Row.Name->SetVisibility(RowVisibility);Row.Amount->SetVisibility(RowVisibility);Row.State->SetVisibility(RowVisibility);if(!Visible)continue;
            const auto& Input=Inputs[I];const int64 Owned=Pending?Input.Value:Model->CountMaterial(Input.Key);
            Set(Row.Name.Get(),ColdSteelInventory::Text(Model->CreateItem(Input.Key),TEXT("name")));
            Set(Row.Owned.Get(),FString::Printf(TEXT("%lld"),Owned));Set(Row.Required.Get(),FString::Printf(TEXT("%lld"),Free?int64(0):Input.Value));
            Row.Separator->SetVisibility(Pending?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            Row.Required->SetVisibility(Pending?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            const bool Enough=Free||Owned>=Input.Value;const FLinearColor Color=Pending?ColdSteelUI::TextPrimary:Enough?ColdSteelUI::Success:ColdSteelUI::Danger;
            Row.Owned->SetColorAndOpacity(Color);Row.State->SetColorAndOpacity(Pending?ColdSteelUI::TextSecondary:Color);
            Set(Row.State.Get(),Free?(Pending?TEXT("免费备料"):TEXT("免消耗")):Pending?TEXT("已备料"):Enough?TEXT("已满足"):FString::Printf(TEXT("缺 %lld"),Input.Value-Owned));
        }
        const FColdSteelItem Product=Pending?J.Product:R?Model->CreateItem(R->Output):FColdSteelItem{};
        const auto Info=Product.Data.IsEmpty()?FColdSteelTooltipContent{}:BuildColdSteelItemTooltip(Product,Model,GetGameInstance()->GetSubsystem<UGunsmithSystem>());
        Set(EntryPreviewName,Info.Name.IsEmpty()?TEXT("暂无成品参数"):Info.Name);Set(EntryPreviewStage,Pending&&J.bFinished?TEXT("成品实际参数"):TEXT("配方基础参数"));
        FString Scope=Info.ValueScope;if(R&&!R->Description.IsEmpty()){if(!Scope.IsEmpty())Scope+=TEXT("\n");Scope+=R->Description;}Set(ProductInfo,Scope);
        while(EntryParameterRows.Num()<Info.Summary.Num())
        {
            const int32 I=EntryParameterRows.Num();auto* Name=Text(TEXT(""),14);Name->SetColorAndOpacity(ColdSteelUI::TextSecondary);
            auto* Value=Text(TEXT(""),14,false,true);Value->SetJustification(ETextJustify::Right);
            for(int32 C=0;C<2;++C)
            {
                auto* ParameterCellSlot=EntryParameterGrid->AddChildToGrid(C==0?Name:Value,I,C);ParameterCellSlot->SetVerticalAlignment(VAlign_Center);ParameterCellSlot->SetHorizontalAlignment(HAlign_Fill);
                ParameterCellSlot->SetPadding(FMargin(C==0?0.f:12.f/Scale,6.f/Scale,0,6.f/Scale));EntryParameterSlots.Add(ParameterCellSlot);
            }
            EntryParameterRows.Add({Name,Value});
        }
        for(int32 I=0;I<EntryParameterRows.Num();++I)
        {
            const auto& Row=EntryParameterRows[I];const bool Visible=Info.Summary.IsValidIndex(I);
            Row.Name->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);Row.Value->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
            if(Visible){Set(Row.Name.Get(),Info.Summary[I].Label);Set(Row.Value.Get(),Info.Summary[I].Value);}
        }
        EntryPreview->Configure(nullptr,Images.FindRef(ColdSteelInventory::Text(Product,TEXT("ue_icon"))));
        bEntryDirty=false;
    }
    Refund->SetVisibility(Pending?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    const bool Finished=Pending&&J.bFinished;
    const float Score=FMath::Clamp(100.f-J.Penalty,0.f,100.f);
    const FLinearColor QualityColor=ColdSteelCraftingResultStyle::ScoreColor(Score);
    Set(EntryStage,Pending?(J.bFinished?(J.bPassed?TEXT("交付成品 · 炼制完成"):TEXT("炼制失败 · 无可领取成品")):TEXT("本炉已暂存 · 可继续炼制")):TEXT("选择配方 · 准备炼药"));
    EntryStage->SetColorAndOpacity(Finished?(J.bPassed?QualityColor:ColdSteelUI::Danger):ColdSteelUI::TextPrimary);
    EntryStats->SetVisibility(Finished?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    EntryResultMetrics->SetVisibility(Finished?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    EntryYieldDelta->SetVisibility(Finished?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    EntryTimer->SetFillColorAndOpacity(Finished?(J.bPassed?QualityColor:ColdSteelUI::Danger):ColdSteelUI::Accent);
    if(Finished)
    {
        Set(EntryScoreValue,FString::Printf(TEXT("%.0f 分"),Score));EntryScoreValue->SetColorAndOpacity(QualityColor);
        Set(EntryOutputValue,FString::Printf(TEXT("成品 %d 瓶"),J.OutputCount));EntryOutputValue->SetColorAndOpacity(J.bPassed?ColdSteelUI::TextPrimary:ColdSteelUI::Danger);
        Set(EntryFaultValue,FString::Printf(TEXT("偏差 %d 项"),J.Faults.Num()));EntryFaultValue->SetColorAndOpacity(J.Faults.IsEmpty()?ColdSteelUI::TextTertiary:ColdSteelUI::Danger);
        Set(EntryLegend,R?FString::Printf(TEXT("本炉基础产量 %d 瓶"),R->BaseCount):TEXT("本炉配方记录不可用"));
        if(R&&R->BaseCount>0)ColdSteelCraftingResultStyle::SetBonus(EntryYieldDelta,TEXT("产量修正"),double(J.OutputCount)/R->BaseCount-1);
        else {Set(EntryYieldDelta,TEXT("产量基准不可用"));EntryYieldDelta->SetColorAndOpacity(ColdSteelUI::TextTertiary);}
        EntryTimer->SetPercent(1);
    }
    else if(Pending)
    {
        int64 Poured=0,Paid=0;for(const auto& Pair:J.Poured)Poured+=Pair.Value;for(const auto& Item:J.Escrow)Paid+=Item.Count;
        Set(EntryStats,FString::Printf(TEXT("%.1f °C   ·   %lld 份   ·   %lld 份"),J.Temperature,Poured,Paid));
        Set(EntryLegend,TEXT("药液温度   /   已投入   /   已备料"));EntryTimer->SetPercent(Paid>0?FMath::Clamp(float(Poured)/Paid,0.f,1.f):0.f);
    }
    else
    {
        Set(EntryStats,R?FString::Printf(TEXT("%d 瓶   ·   +%d 瓶   ·   ≤%.0f °C"),R->BaseCount,R->BonusCount,R->BottleHeat):TEXT("—"));
        Set(EntryLegend,TEXT("基础产量   /   精制加成   /   装瓶上限"));EntryTimer->SetPercent(0);
    }
    EntryStats->SetColorAndOpacity(Pending?ColdSteelUI::TextPrimary:ColdSteelUI::TextSecondary);
}
