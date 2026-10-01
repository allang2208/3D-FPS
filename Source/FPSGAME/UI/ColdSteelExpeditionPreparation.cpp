#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/CombatItemFormula.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "Dom/JsonObject.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/Text/STextBlock.h"

void UColdSteelExpeditionWidget::RefreshPreparationData()
{
    if(auto* Model=Profile())PreparedMaxMana=Model->Derived(TEXT("maxMp"));
    if(auto* Pawn=GetOwningPlayerPawn())PlayerHealth=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    RefreshPreparation();
}

void UColdSteelExpeditionWidget::RefreshPreparation()
{
    if(!PreparationRows)return;
    auto* Model=Profile();const auto* Entry=Selection();
    if(!Model)
    {
        PreparationRows->ClearChildren();
        PreparationRows->AddSlot().AutoHeight()[Section(TEXT("角色信息暂不可用"),TEXT("角色资料载入后再查看行前准备。"))];return;
    }
    int64 HealthSupplies=0,ManaSupplies=0;
    const auto& Items=Model->Items();
    for(const auto& Item:Items)
    {
        if((Item.Place!=0&&Item.Place!=ColdSteelInventory::ColdSteelCompartment::Place)||Item.Count<=0)continue;
        const auto Data=CombatItemFormula::ReadOnly(Item);const TSharedPtr<FJsonObject>* Effect=nullptr;
        if(!Data||!Data->TryGetObjectField(TEXT("useEffect"),Effect))continue;
        const auto Positive=[&](const TCHAR* Field){double Amount=0;return (*Effect)->TryGetNumberField(Field,Amount)&&Amount>0;};
        if(Positive(TEXT("hp"))||Positive(TEXT("maxHpPercent")))HealthSupplies+=Item.Count;
        if(Positive(TEXT("mp"))||Positive(TEXT("maxMpPercent")))ManaSupplies+=Item.Count;
    }
    const int32 Capacity=18*ColdSteelInventory::BagRows(Items);
    int32 FreeCells=0;
    for(int32 Cell=0;Cell<Capacity;++Cell)if(ColdSteelInventory::Owner(Items,0,Cell)==INDEX_NONE)++FreeCells;
    const auto* Weapon=Model->Equipped();
    const FString WeaponName=Weapon?ColdSteelInventory::Text(*Weapon,TEXT("name")):TEXT("未装备");
    const bool Staff=Weapon&&ColdSteelStaff::IsStaff(*Weapon);
    const bool UsesAmmo=Weapon&&!Staff&&!ColdSteelInventory::IsMeleeWeapon(*Weapon);
    const FString Ammo=UsesAmmo?Model->AmmoDefinitionFor(*Weapon):FString();
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn());
    const bool Infinite=!Ammo.IsEmpty()&&Character&&Character->HasInfiniteReserveAmmoFor(Ammo);
    const FString Reserve=Infinite?TEXT("∞"):FString::Printf(TEXT("%lld"),Ammo.IsEmpty()?0:Model->PouchCount(Ammo));
    const FString Key=SelectedId.ToString()+Model->CharacterName+Model->CharacterClass+WeaponName+Ammo+Reserve+
        FString::Printf(TEXT("|%d|%lld|%lld|%d|%d|%d|%d"),Model->Level,HealthSupplies,ManaSupplies,FreeCells,Capacity,Staff,Model->HasInfiniteMana());
    if(PreparationKey==Key&&PreparationRows->NumSlots()>0)return;
    PreparationKey=Key;PreparationRows->ClearChildren();
    auto Identity=SNew(SVerticalBox);
    Identity->AddSlot().AutoHeight()[Label(Model->CharacterName,20,ColdSteelUI::TextPrimary)];
    Identity->AddSlot().AutoHeight().Padding(0,6,0,10)[Label(Model->CharacterClass,12,ColdSteelUI::TextSecondary)];
    Identity->AddSlot().AutoHeight()[Row(TEXT("等级"),FString::FromInt(Model->Level),true)];
    const auto Resource=[this](bool Mana)
    {
        auto Value=SNew(STextBlock).Font(ColdSteelUI::NumberFont(10.5f)).ColorAndOpacity(ColdSteelUI::TextPrimary)
            .Text_Lambda([this,Mana]()
            {
                const auto* ProfileModel=Profile();const auto* Health=PlayerHealth.Get();
                if(Mana&&ProfileModel)return FText::FromString(FString::Printf(TEXT("%.0f / %.0f"),ProfileModel->Mana(),PreparedMaxMana));
                return Health?FText::FromString(FString::Printf(TEXT("%.0f / %.0f"),Health->Health,Health->MaxHealth)):FText::FromString(TEXT("—"));
            });
        return SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,5)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1)[Label(Mana?TEXT("魔法"):TEXT("生命"),14,ColdSteelUI::TextSecondary)]
                    +SHorizontalBox::Slot().AutoWidth()[Value]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)
                [SNew(SBox).HeightOverride(4)[SNew(SProgressBar).Style(&ResourceStyle).FillColorAndOpacity(Mana?ColdSteelUI::Mana:ColdSteelUI::Health)
                    .Percent_Lambda([this,Mana]()->TOptional<float>
                    {
                        const auto* M=Profile();const auto* H=PlayerHealth.Get();
                        return Mana?(M&&PreparedMaxMana>0?FMath::Clamp(M->Mana()/PreparedMaxMana,0.f,1.f):0.f):
                            (H&&H->MaxHealth>0?FMath::Clamp(H->Health/H->MaxHealth,0.f,1.f):0.f);
                    })]];
    };
    Identity->AddSlot().AutoHeight()[Resource(false)];
    Identity->AddSlot().AutoHeight()[Resource(true)];
    Identity->AddSlot().AutoHeight()[Row(TEXT("当前武器"),WeaponName)];
    if(!Ammo.IsEmpty())
    {
        Identity->AddSlot().AutoHeight()[Row(TEXT("使用弹药"),Model->AmmoLabel(Ammo))];
        Identity->AddSlot().AutoHeight()[Row(TEXT("弹药袋备弹"),Reserve,true)];
    }
    else if(Staff)Identity->AddSlot().AutoHeight()[Label(Model->HasInfiniteMana()?TEXT("法杖 · 无限魔法已启用"):TEXT("法杖 · 留意魔法与恢复补给"),12,ColdSteelUI::TextSecondary)];
    PreparationRows->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(SBorder).BorderImage(&HeroBrush).Padding(14)[Identity]];
    auto Supplies=SNew(SVerticalBox);
    Supplies->AddSlot().AutoHeight().Padding(0,0,0,8)[Label(TEXT("携带补给"),16,ColdSteelUI::TextPrimary)];
    Supplies->AddSlot().AutoHeight()[Row(TEXT("生命恢复品"),FString::Printf(TEXT("%lld"),HealthSupplies),true)];
    Supplies->AddSlot().AutoHeight()[Row(TEXT("魔法恢复品"),FString::Printf(TEXT("%lld"),ManaSupplies),true)];
    Supplies->AddSlot().AutoHeight()[Row(TEXT("主背包空格"),FString::Printf(TEXT("%d / %d"),FreeCells,Capacity),true)];
    Supplies->AddSlot().AutoHeight().Padding(0,6,0,8)[Label(TEXT("恢复品统计背包与夹层；备弹取弹药袋。空格不保证大件能放入。"),12,ColdSteelUI::TextTertiary)];
    TArray<FString> Warnings;
    if(!Weapon)Warnings.Add(TEXT("尚未装备武器"));
    if(HealthSupplies==0)Warnings.Add(TEXT("未携带生命恢复品"));
    if(Staff&&ManaSupplies==0&&!Model->HasInfiniteMana())Warnings.Add(TEXT("未携带魔法恢复品"));
    if(!Ammo.IsEmpty()&&!Infinite&&Model->PouchCount(Ammo)==0)Warnings.Add(TEXT("当前弹种没有备弹"));
    if(FreeCells==0)Warnings.Add(TEXT("主背包已满"));
    if(!Warnings.IsEmpty())Supplies->AddSlot().AutoHeight().Padding(0,0,0,10)
        [Label(FString::Join(Warnings,TEXT("；"))+TEXT("。这些提醒不阻止出征。"),12,ColdSteelUI::Warning)];
    Supplies->AddSlot().AutoHeight()[Action(TEXT("整理装备"),[this](){if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->PrepareExpeditionEquipment();})];
    PreparationRows->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(SBorder).BorderImage(&HeroBrush).Padding(14)[Supplies]];
    PreparationRows->AddSlot().AutoHeight()
        [Section(TEXT("进入条件"),Entry?Entry->EntryCost:TEXT("尚未选择目的地"))];
}
