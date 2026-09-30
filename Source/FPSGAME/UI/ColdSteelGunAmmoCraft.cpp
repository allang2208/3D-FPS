#include "ColdSteelGunAssemblyWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Building/CraftingSystem.h"
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
    AmmoChoice=WidgetTree->ConstructWidget<UComboBoxString>();
    AmmoChoice->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::GenerateRecipeOption);
    int32 MaxRows=0;
    if(Crafting&&Model)for(const auto& Recipe:Crafting->AmmoCatalog())
    {
        const auto* Type=Model->AmmoType(Recipe.Output);if(!Type||!Type->Enabled)continue;
        AmmoRecipeIds.Add(Recipe.Id);AmmoChoice->AddOption(Model->AmmoLabel(Type->Id)+(Type->TierName.IsEmpty()?FString():TEXT(" · ")+Type->TierName));
        MaxRows=FMath::Max(MaxRows,Recipe.Inputs.Num());
    }
    if(!AmmoRecipeIds.IsEmpty()){SelectedAmmoRecipe=AmmoRecipeIds[0];AmmoChoice->SetSelectedIndex(0);}
    AmmoChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleAmmoSelected);
    auto* ChoiceSize=WidgetTree->ConstructWidget<USizeBox>();ChoiceSize->SetContent(AmmoChoice);ButtonSizes.Add(ChoiceSize);
    Space(Column->AddChildToVerticalBox(ChoiceSize),FMargin(0,0,0,8));
    AmmoStock=Text(TEXT(""),16,true);Space(Column->AddChildToVerticalBox(AmmoStock),FMargin(0,0,0,8));
    auto* Source=Text(TEXT("材料来源 · 背包 + 主仓库"),12);Source->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    Space(Column->AddChildToVerticalBox(Source),FMargin(0,0,0,4));
    auto* Grid=WidgetTree->ConstructWidget<UGridPanel>();Grid->SetColumnFill(0,1.f);
    Space(Column->AddChildToVerticalBox(Grid),FMargin(0,0,0,8));
    auto Cell=[&](UWidget* Widget,int32 Row,int32 Col)
    {
        auto* Slot=Grid->AddChildToGrid(Widget,Row,Col);Slot->SetHorizontalAlignment(Col==0?HAlign_Fill:HAlign_Right);Slot->SetVerticalAlignment(VAlign_Center);
        Slot->SetPadding(FMargin(Col==0?0.f:12.f/FMath::Max(.1f,Scale),4.f/FMath::Max(.1f,Scale),0,4.f/FMath::Max(.1f,Scale)));MaterialCellSlots.Add(Slot);
    };
    const TCHAR* Headers[]={TEXT("材料"),TEXT("持有 / 需要"),TEXT("状态")};
    for(int32 I=0;I<3;++I){auto* Label=Text(Headers[I],12);Label->SetColorAndOpacity(ColdSteelUI::TextSecondary);Cell(Label,0,I);}
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
    AmmoStatus=Text(TEXT(""),14);AmmoStatus->SetColorAndOpacity(ColdSteelUI::TextSecondary);
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
    AmmoChoice->SetIsEnabled(bInputReady&&!AmmoRecipeIds.IsEmpty());
    FString Reason;
    bool Can=Available;
    for(int32 I=0;I<AmmoMaterialRows.Num();++I)
    {
        const auto& Row=AmmoMaterialRows[I];const bool Show=Available&&R->Inputs.IsValidIndex(I);
        for(UWidget* W:{static_cast<UWidget*>(Row.Name.Get()),static_cast<UWidget*>(Row.Amount.Get()),static_cast<UWidget*>(Row.State.Get())})W->SetVisibility(Show?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(!Show)continue;
        const auto& Cost=R->Inputs[I];const int64 Have=Model->CountMaterial(Cost.Item);
        const FString Name=ColdSteelInventory::Text(Model->CreateItem(Cost.Item),TEXT("name"));
        Set(Row.Name.Get(),Name);Set(Row.Owned.Get(),FString::Printf(TEXT("%lld"),Have));Set(Row.Required.Get(),FString::Printf(TEXT("%lld"),Cost.Count));
        Row.Owned->SetColorAndOpacity(Have>=Cost.Count?ColdSteelUI::Success:ColdSteelUI::Danger);
        Set(Row.State.Get(),Have>=Cost.Count?TEXT("充足"):TEXT("不足"));
        if(Have<Cost.Count){Can=false;if(Reason.IsEmpty())Reason=FString::Printf(TEXT("还缺 %lld 个%s"),Cost.Count-Have,*Name);}
    }
    if(Available)
    {
        const int64 Have=Model->PouchCount(R->Output);
        if(Have>ColdSteelAmmo::MaxCount-R->OutputCount){Can=false;Reason=TEXT("弹药袋数量已达上限");}
        Set(AmmoStock,FString::Printf(TEXT("弹药袋 %lld 发 · 每次制作 %lld 发"),Have,R->OutputCount));
        Set(AmmoActionLabel,FString::Printf(TEXT("制作 %lld 发"),R->OutputCount));
    }
    else{Set(AmmoStock,TEXT("暂无可制作弹药"));Set(AmmoActionLabel,TEXT("制作弹药"));Reason=TEXT("弹药配方未就绪");}
    AmmoAction->SetIsEnabled(bInputReady&&Can);
    Set(AmmoStatus,!AmmoNotice.IsEmpty()?AmmoNotice:!Reason.IsEmpty()?Reason:TEXT("材料充足 · 点击即可制作"));
}
void UColdSteelGunAssemblyWidget::HandleAmmoSelected(FString Option,ESelectInfo::Type SelectionType)
{
    if(!bInputReady||!bAmmoPage||SelectionType==ESelectInfo::Direct)return;
    const int32 Index=AmmoChoice->GetSelectedIndex();if(!AmmoRecipeIds.IsValidIndex(Index))return;
    SelectedAmmoRecipe=AmmoRecipeIds[Index];AmmoNotice.Reset();bAmmoDirty=true;RefreshAmmoCard();
}
void UColdSteelGunAssemblyWidget::HandleAmmoCraft()
{
    if(!bInputReady||!bAmmoPage||!HUD||!HUD->IsWorkbenchOpen()||!Crafting||!Model)return;
    const auto* R=Crafting->Find(SelectedAmmoRecipe);if(!R)return;
    AmmoNotice.Reset();
    if(Crafting->Craft(R->Id,1,AmmoNotice))AmmoNotice=FString::Printf(TEXT("已制作 %lld 发 %s · 已存入弹药袋"),R->OutputCount,*Model->AmmoLabel(R->Output));
    bAmmoDirty=true;bMaterialsDirty=true;Refresh();
}
