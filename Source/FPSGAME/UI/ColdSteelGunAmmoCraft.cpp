#include "ColdSteelGunAssemblyWidget.h"
#include "DevelopmentItemPicker.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Building/CraftingSystem.h"
#include "../Building/GunAssemblySystem.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Button.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"

void UColdSteelGunAssemblyWidget::BuildAmmoCard(UVerticalBox* Parent,UVerticalBox* ActionParent)
{
    auto* Column=Card(Parent);
    Space(Column->AddChildToVerticalBox(Text(TEXT("弹药制造"),16,false,true)),FMargin(0,0,0,8));
    auto* Description=Text(TEXT("选择弹药后直接制作，成品自动收纳至弹药袋。"),12);
    Description->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(Column->AddChildToVerticalBox(Description),FMargin(0,0,0,8));
    AmmoChoice=WidgetTree->ConstructWidget<UDevelopmentItemPicker>();
    AmmoChoice->SetPhysicalFontSizes(true);
    TArray<FColdSteelCatalogEntry> Options;
    int32 MaxRows=0;
    if(Crafting&&Model)for(const auto& Recipe:Crafting->AmmoCatalog())
    {
        const auto* Type=Model->AmmoType(Recipe.Output);if(!Type||!Type->Enabled)continue;
        AmmoRecipeIds.Add(Recipe.Id);FColdSteelCatalogEntry Entry;
        Entry.Definition=Recipe.Id.ToString();Entry.Name=Type->Name+(Type->TierName.IsEmpty()?FString():TEXT(" · ")+Type->TierName);
        Entry.Group=Type->GroupName;Entry.GroupOrder=Type->Order;
        Options.Add(MoveTemp(Entry));
        MaxRows=FMath::Max(MaxRows,Recipe.Inputs.Num());
    }
    Options.StableSort([](const auto& A,const auto& B){return A.GroupOrder<B.GroupOrder;});
    if(!Options.IsEmpty())SelectedAmmoRecipe=FName(*Options[0].Definition);
    AmmoChoice->SetOptions(Options,SelectedAmmoRecipe.ToString(),true);
    AmmoChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleAmmoSelected);
    auto* ChoiceSize=WidgetTree->ConstructWidget<USizeBox>();ChoiceSize->SetContent(AmmoChoice);ButtonSizes.Add(ChoiceSize);
    Space(Column->AddChildToVerticalBox(ChoiceSize),FMargin(0,0,0,8));
    AmmoDescription=Text(TEXT(""),14);AmmoDescription->SetAutoWrapText(true);
    Space(Column->AddChildToVerticalBox(AmmoDescription),FMargin(0,0,0,8));
    AmmoEffects=Text(TEXT(""),14);AmmoEffects->SetAutoWrapText(true);AmmoEffects->SetColorAndOpacity(ColdSteelUI::Success);
    Space(Column->AddChildToVerticalBox(AmmoEffects),FMargin(0,0,0,8));
    AmmoCompatibility=Text(TEXT(""),12);AmmoCompatibility->SetAutoWrapText(true);AmmoCompatibility->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Space(Column->AddChildToVerticalBox(AmmoCompatibility),FMargin(0,0,0,12));
    // The assembly catalog and ammo compatibility map are immutable for this session.
    for(const auto& Recipe:System->Catalog())
    {
        const auto Item=Model->CreateItem(Recipe.Output);const FString Group=Model->AmmoGroupFor(Item);
        if(Group.IsEmpty())continue;
        FString& Names=AmmoCompatibleWeapons.FindOrAdd(Group);if(!Names.IsEmpty())Names+=TEXT("、");
        Names+=ColdSteelInventory::Text(Item,TEXT("name"));
    }
    AmmoStock=Text(TEXT(""),16,true);Space(Column->AddChildToVerticalBox(AmmoStock),FMargin(0,0,0,8));
    AmmoStock->SetAutoWrapText(true);
    AmmoCapacity=Text(TEXT(""),12);AmmoCapacity->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Space(Column->AddChildToVerticalBox(AmmoCapacity),FMargin(0,0,0,8));
    auto* BatchRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    Space(Column->AddChildToVerticalBox(BatchRow),FMargin(0,0,0,12));
    auto AddBatchButton=[&](const TCHAR* Label)
    {
        UTextBlock* Caption=nullptr;auto* Entry=Button(Label,Caption);
        auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetContent(Entry);ButtonSizes.Add(Size);
        auto* Slot=BatchRow->AddChildToHorizontalBox(Size);Slot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        return Entry;
    };
    AmmoMinus=AddBatchButton(TEXT("−"));AmmoMinus->OnClicked.AddDynamic(this,&ThisClass::HandleAmmoMinus);
    AmmoBatchText=Text(TEXT("1 份"),14,true);AmmoBatchText->SetJustification(ETextJustify::Center);
    auto* BatchSlot=BatchRow->AddChildToHorizontalBox(AmmoBatchText);BatchSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));BatchSlot->SetVerticalAlignment(VAlign_Center);
    AmmoPlus=AddBatchButton(TEXT("+"));AmmoPlus->OnClicked.AddDynamic(this,&ThisClass::HandleAmmoPlus);
    AmmoMax=AddBatchButton(TEXT("最大"));AmmoMax->OnClicked.AddDynamic(this,&ThisClass::HandleAmmoMax);
    auto* Source=Text(TEXT("材料来源 · 背包 + 主仓库"),12);Source->SetColorAndOpacity(ColdSteelUI::TextTertiary);AmmoMaterialSource=Source;
    Space(Column->AddChildToVerticalBox(Source),FMargin(0,0,0,4));
    auto* Grid=WidgetTree->ConstructWidget<UGridPanel>();Grid->SetColumnFill(0,1.f);
    Space(Column->AddChildToVerticalBox(Grid),FMargin(0,0,0,8));
    auto Cell=[&](UWidget* Widget,int32 Row,int32 Col)
    {
        auto* Slot=Grid->AddChildToGrid(Widget,Row,Col);Slot->SetHorizontalAlignment(Col==0?HAlign_Fill:HAlign_Right);Slot->SetVerticalAlignment(VAlign_Center);
        Slot->SetPadding(FMargin(Col==0?0.f:12.f/FMath::Max(.1f,Scale),4.f/FMath::Max(.1f,Scale),0,4.f/FMath::Max(.1f,Scale)));MaterialCellSlots.Add(Slot);
    };
    const TCHAR* Headers[]={TEXT("材料"),TEXT("持有 / 需要"),TEXT("状态")};
    for(int32 I=0;I<3;++I){auto* Label=Text(Headers[I],12);Label->SetColorAndOpacity(ColdSteelUI::TextSecondary);Cell(Label,0,I);if(I==1)AmmoMaterialQuantityHeader=Label;}
    for(int32 I=0;I<MaxRows;++I)
    {
        FMaterialRow Row;auto* Name=Text(TEXT(""),14);Row.Name=Name;
        auto* Amount=WidgetTree->ConstructWidget<UHorizontalBox>();Row.Amount=Amount;
        auto* Owned=Text(TEXT(""),14,true);Row.Owned=Owned;
        auto* Separator=Text(TEXT(" / "),14,true);Row.Separator=Separator;
        auto* Required=Text(TEXT(""),14,true);Row.Required=Required;
        Separator->SetColorAndOpacity(ColdSteelUI::TextSecondary);Required->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        for(auto* Number:{Owned,Separator,Required}){Number->SetAutoWrapText(false);Amount->AddChildToHorizontalBox(Number)->SetVerticalAlignment(VAlign_Center);}
        auto* State=Text(TEXT(""),14);Row.State=State;State->SetAutoWrapText(false);
        Cell(Name,I+1,0);Cell(Amount,I+1,1);Cell(State,I+1,2);AmmoMaterialRows.Add(Row);
    }
    UTextBlock* Caption=nullptr;AmmoAction=Button(TEXT("制作弹药"),Caption);AmmoActionLabel=Caption;
    AmmoAction->OnClicked.AddDynamic(this,&ThisClass::HandleAmmoCraft);
    auto* ActionSize=WidgetTree->ConstructWidget<USizeBox>();ActionSize->SetContent(AmmoAction);ButtonSizes.Add(ActionSize);
    AmmoStatus=Text(TEXT(""),14);AmmoStatus->SetAutoWrapText(true);AmmoStatus->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Space(ActionParent->AddChildToVerticalBox(AmmoStatus),FMargin(0,0,0,8));
    ActionParent->AddChildToVerticalBox(ActionSize);
}

void UColdSteelGunAssemblyWidget::RefreshAmmoCard()
{
    if(!bAmmoDirty||!AmmoAction||!Model||!Crafting)return;bAmmoDirty=false;
    auto Set=[](UTextBlock* Label,const FString& Value){if(Label&&Label->GetText().ToString()!=Value)Label->SetText(FText::FromString(Value));};
    const auto* R=Crafting->Find(SelectedAmmoRecipe);
    const auto* Type=R?Model->AmmoType(R->Output):nullptr;
    const bool Available=R&&Type&&Type->Enabled;
    const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(Model);
    Set(AmmoMaterialQuantityHeader.Get(),Free?TEXT("持有 / 本次消耗"):TEXT("持有 / 需要"));
    Set(AmmoMaterialSource.Get(),Free?TEXT("免材料制作 · 不扣背包或仓库材料"):TEXT("材料来源 · 背包 + 主仓库"));
    AmmoChoice->SetIsEnabled(CanInteract()&&!AmmoRecipeIds.IsEmpty());
    AmmoMaxBatch=Available?Crafting->MaxCraftable(Model,*R):0;
    AmmoBatch=FMath::Clamp<int64>(AmmoBatch,1,FMath::Max<int64>(1,AmmoMaxBatch));
    Set(AmmoBatchText,FString::Printf(TEXT("%lld 份"),AmmoBatch));
    Set(AmmoCapacity,FString::Printf(TEXT("当前最多可制作 %lld 份 · 单次上限 99 份"),AmmoMaxBatch));
    AmmoMinus->SetIsEnabled(CanInteract()&&Available&&AmmoBatch>1);
    AmmoPlus->SetIsEnabled(CanInteract()&&Available&&AmmoBatch<AmmoMaxBatch);
    AmmoMax->SetIsEnabled(CanInteract()&&Available&&AmmoMaxBatch>0&&AmmoBatch!=AmmoMaxBatch);
    FString Reason;
    bool Can=Available;
    for(int32 I=0;I<AmmoMaterialRows.Num();++I)
    {
        const auto& Row=AmmoMaterialRows[I];const bool Show=Available&&R->Inputs.IsValidIndex(I);
        for(UWidget* W:{static_cast<UWidget*>(Row.Name.Get()),static_cast<UWidget*>(Row.Amount.Get()),static_cast<UWidget*>(Row.State.Get())})W->SetVisibility(Show?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(!Show)continue;
        const auto& Cost=R->Inputs[I];const int64 Have=Model->CountMaterial(Cost.Item),Need=Cost.Count*AmmoBatch;
        const FString Name=ColdSteelInventory::Text(Model->CreateItem(Cost.Item),TEXT("name"));
        Set(Row.Name.Get(),Name);Set(Row.Owned.Get(),FString::Printf(TEXT("%lld"),Have));Set(Row.Required.Get(),FString::Printf(TEXT("%lld"),Free?int64(0):Need));
        Row.Owned->SetColorAndOpacity(Free||Have>=Need?ColdSteelUI::Success:ColdSteelUI::Danger);
        Set(Row.State.Get(),Free?TEXT("免消耗"):Have>=Need?TEXT("充足"):TEXT("不足"));
    }
    if(Available)
    {
        const int64 Have=Model->PouchCount(R->Output);
        Can=Crafting->CanCraft(*R,AmmoBatch,Reason);
        Set(AmmoStock,FString::Printf(TEXT("弹药袋 %lld 发 · 每次制作 %lld 发"),Have,R->OutputCount));
        Set(AmmoActionLabel,FString::Printf(TEXT("制作 %lld 发"),R->OutputCount*AmmoBatch));
        Set(AmmoDescription,Type->Description);
        FString Effects=FString::Printf(TEXT("伤害倍率 ×%.2f · 物理护甲忽略 %.0f%%"),Type->DamageMultiplier,Type->PhysicalArmorPenetration*100.f);
        if(Type->ProjectileCount>0)Effects+=FString::Printf(TEXT("\n每发 %d 枚弹丸 · 射程倍率 ×%.2f"),Type->ProjectileCount,Type->RangeMultiplier);
        Set(AmmoEffects,Effects);
        const FString Names=AmmoCompatibleWeapons.FindRef(Type->Group);
        Set(AmmoCompatibility,TEXT("适配枪械：")+(Names.IsEmpty()?FString(TEXT("暂无已接入枪械")):Names));
    }
    else{Set(AmmoStock,TEXT("暂无可制作弹药"));Set(AmmoActionLabel,TEXT("制作弹药"));Set(AmmoDescription,TEXT(""));Set(AmmoEffects,TEXT(""));Set(AmmoCompatibility,TEXT(""));Reason=TEXT("弹药配方未就绪");}
    AmmoAction->SetIsEnabled(CanInteract()&&Can&&AmmoMaxBatch>0);
    Set(AmmoStatus,bTransactionPending?TEXT("等待服务器确认制作结果…"):!AmmoNotice.IsEmpty()?AmmoNotice:!Reason.IsEmpty()?Reason:Free?TEXT("免材料制作 · 点击即可制作"):TEXT("材料充足 · 点击即可制作"));
}
void UColdSteelGunAssemblyWidget::HandleAmmoSelected(const FString& RecipeId)
{
    const FName Id(*RecipeId);
    if(!CanInteract()||!bAmmoPage||!AmmoRecipeIds.Contains(Id)){AmmoChoice->SetSelectedOption(SelectedAmmoRecipe.ToString());return;}
    SelectedAmmoRecipe=Id;AmmoBatch=1;AmmoNotice.Reset();bAmmoDirty=true;RefreshAmmoCard();
}
void UColdSteelGunAssemblyWidget::HandleAmmoCraft()
{
    if(!CanInteract()||!bAmmoPage||!HUD||!HUD->IsWorkbenchOpen()||!HUD->GunAssemblyStation()||!Crafting||!Model)return;
    const auto* R=Crafting->Find(SelectedAmmoRecipe);if(!R)return;
    AmmoNotice.Reset();
    Crafting->Craft(R->Id,AmmoBatch,AmmoNotice,HUD->GunAssemblyStation());
    bAmmoDirty=true;bMaterialsDirty=true;Refresh();
}
void UColdSteelGunAssemblyWidget::SetAmmoBatch(int64 Batch)
{
    if(!CanInteract()||!bAmmoPage)return;
    AmmoBatch=FMath::Clamp<int64>(Batch,1,FMath::Max<int64>(1,AmmoMaxBatch));
    AmmoNotice.Reset();bAmmoDirty=true;RefreshAmmoCard();
}
void UColdSteelGunAssemblyWidget::HandleAmmoMinus(){SetAmmoBatch(AmmoBatch-1);}
void UColdSteelGunAssemblyWidget::HandleAmmoPlus(){SetAmmoBatch(AmmoBatch+1);}
void UColdSteelGunAssemblyWidget::HandleAmmoMax(){SetAmmoBatch(AmmoMaxBatch);}
