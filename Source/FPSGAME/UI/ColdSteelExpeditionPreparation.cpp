#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/CombatItemFormula.h"
#include "../Items/FoodSpoilage.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"

namespace
{
    struct FCarriedSupply
    {
        FString Name;
        int64 Count=0,Uses=0;
        bool bExpired=false;
    };

    double Number(const FJsonObject* Data,const TCHAR* Field,double Default=0.)
    {
        double Value=Default;
        return Data&&Data->TryGetNumberField(Field,Value)?Value:Default;
    }
}

void UColdSteelExpeditionWidget::RefreshPreparationData()
{
    // Inventory transactions can broadcast while the expedition is suspended.
    // The return path explicitly refreshes the preserved panel once it is visible.
    if(GetVisibility()!=ESlateVisibility::Collapsed)RefreshPreparation();
}

void UColdSteelExpeditionWidget::RefreshPreparation()
{
    if(!PreparationRows)return;
    auto* Model=Profile();
    if(!Model)
    {
        PreparationRows->ClearChildren();PreparationKey.Reset();
        PreparationRows->AddSlot().AutoHeight()[Section(TEXT("物资暂不可用"),TEXT("角色资料载入后显示携带物资。"))];
        return;
    }
    TArray<FCarriedSupply> Groups[3];
    int64 Usable[3]={0,0,0};
    for(const auto& Item:Model->Items())
    {
        if((Item.Place!=0&&Item.Place!=ColdSteelInventory::ColdSteelCompartment::Place)||Item.Count<=0)continue;
        const auto Data=CombatItemFormula::ReadOnly(Item);
        const TSharedPtr<FJsonObject>* Effect=nullptr;
        if(!Data||!Data->TryGetObjectField(TEXT("useEffect"),Effect)||!Effect||!Effect->IsValid())continue;
        const auto Positive=[&](const TCHAR* Key){return Number(Effect->Get(),Key)>0.;};
        const bool Food=Positive(TEXT("hunger"))||Positive(TEXT("maxHungerPercent"));
        const bool Water=Positive(TEXT("hydration"))||Positive(TEXT("maxHydrationPercent"));
        const bool Potion=Item.Definition.Contains(TEXT("potion"))||Positive(TEXT("hp"))||Positive(TEXT("maxHpPercent"))||Positive(TEXT("mp"))||Positive(TEXT("maxMpPercent"));
        const int32 Group=Food?0:Water?1:Potion?2:INDEX_NONE;
        if(Group==INDEX_NONE)continue;
        const FString Name=ColdSteelInventory::Text(Item,TEXT("name"));
        const bool Expired=ColdSteelFood::LifetimeDays(Item)>0.&&Model->FoodRemainingDays(Item)<=0.;
        const int32 MaxUses=FMath::Max(1,int32(Number(Data.Get(),TEXT("maxUses"),1.)));
        const int32 Remaining=FMath::Clamp(int32(Number(Data.Get(),TEXT("remainingUses"),MaxUses)),0,MaxUses);
        auto* Supply=Groups[Group].FindByPredicate([&](const auto& Row){return Row.Name==Name&&Row.bExpired==Expired;});
        if(!Supply){FCarriedSupply Row;Row.Name=Name;Row.bExpired=Expired;Supply=&Groups[Group].Add_GetRef(MoveTemp(Row));}
        Supply->Count+=Item.Count;Supply->Uses+=Item.Count*Remaining;
        if(!Expired)Usable[Group]+=Group==1?Item.Count*Remaining:Item.Count;
    }
    FString Key;
    for(auto& Group:Groups)
    {
        Group.Sort([](const auto& A,const auto& B){return A.Name==B.Name?A.bExpired<B.bExpired:A.Name<B.Name;});
        for(const auto& Supply:Group)
            Key+=FString::Printf(TEXT("|%s:%lld:%lld:%d"),*Supply.Name,Supply.Count,Supply.Uses,Supply.bExpired);
        Key+=TEXT(";");
    }
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn());
    const auto* Weapon=Model->Equipped();
    if(!Weapon)Weapon=Model->ActiveFirearm();
    if(!Weapon)Weapon=Model->ActiveKukriWeapon();
    TArray<const FColdSteelItem*> Weapons;
    if(Weapon)
    {
        Weapons.Add(Weapon);
        if((Weapon->Cell==6||Weapon->Cell==9)&&(ColdSteelInventory::IsDualPistol(*Weapon)||ColdSteelStaff::IsStaff(*Weapon)))
            if(const auto* Offhand=Model->Equipped(Weapon->Cell==6?8:11);Offhand&&ColdSteelInventory::IsDualPistol(*Offhand))Weapons.Add(Offhand);
    }
    struct FWeaponSummary {FString Name,Ammo;int64 Reserve=0;bool bInfinite=false,bStaff=false;};
    TArray<FWeaponSummary> WeaponSummaries;
    TArray<FString> Warnings;
    if(Weapons.IsEmpty())Warnings.Add(TEXT("尚未装备武器"));
    for(const auto* Equipped:Weapons)
    {
        FWeaponSummary Summary;
        Summary.Name=ColdSteelInventory::Text(*Equipped,TEXT("name"));
        Summary.bStaff=ColdSteelStaff::IsStaff(*Equipped);
        Summary.Ammo=Summary.bStaff||ColdSteelInventory::IsMeleeWeapon(*Equipped)?FString():Model->AmmoDefinitionFor(*Equipped);
        Summary.bInfinite=!Summary.Ammo.IsEmpty()&&Character&&Character->HasInfiniteReserveAmmoFor(Summary.Ammo);
        Summary.Reserve=Summary.Ammo.IsEmpty()?0:Model->PouchCount(Summary.Ammo);
        Key+=FString::Printf(TEXT("|%s:%s:%lld:%d:%d:%d"),*Summary.Name,*Summary.Ammo,Summary.Reserve,Summary.bInfinite,Summary.bStaff,Model->HasInfiniteMana());
        if(!Summary.Ammo.IsEmpty()&&!Summary.bInfinite&&Summary.Reserve==0)Warnings.AddUnique(TEXT("当前弹种没有备弹"));
        WeaponSummaries.Add(MoveTemp(Summary));
    }
    if(PreparationKey==Key&&PreparationRows->NumSlots()>0)return;
    PreparationKey=Key;PreparationRows->ClearChildren();
    auto WeaponRows=SNew(SVerticalBox);
    WeaponRows->AddSlot().AutoHeight().Padding(0,0,0,10)[Label(TEXT("当前武器"),16,ColdSteelUI::HUDGold)];
    if(WeaponSummaries.IsEmpty())WeaponRows->AddSlot().AutoHeight()[Label(TEXT("未装备武器"),14,ColdSteelUI::TextSecondary)];
    for(const auto& Summary:WeaponSummaries)
    {
        WeaponRows->AddSlot().AutoHeight().Padding(0,4,0,4)[Label(Summary.Name,16,ColdSteelUI::TextPrimary)];
        if(!Summary.Ammo.IsEmpty())
        {
            WeaponRows->AddSlot().AutoHeight()[Row(TEXT("备弹"),Summary.bInfinite?TEXT("∞"):FString::Printf(TEXT("%lld"),Summary.Reserve),true)];
            WeaponRows->AddSlot().AutoHeight()[Label(Model->AmmoLabel(Summary.Ammo),12,ColdSteelUI::TextSecondary)];
        }
        else WeaponRows->AddSlot().AutoHeight()[Label(Summary.bStaff?(Model->HasInfiniteMana()?TEXT("消耗魔法 · 无限魔法已启用"):TEXT("消耗魔法，无需备弹")):TEXT("无需备弹"),12,ColdSteelUI::TextSecondary)];
    }
    // Natural section heights keep long carried-item lists scrollable without overlap.
    const auto AddGroup=[this](TSharedRef<SWidget> Content)
    {
        auto SectionRows=SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,14)[Content]
            +SVerticalBox::Slot().AutoHeight()[Divider()];
        PreparationRows->AddSlot().AutoHeight().Padding(0,6)[SectionRows];
    };
    AddGroup(WeaponRows);
    const TCHAR* Titles[]={TEXT("食物"),TEXT("水与饮品"),TEXT("补给品 · 药水")};
    for(int32 Group=0;Group<3;++Group)
    {
        auto Rows=SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1)[Label(Titles[Group],16,ColdSteelUI::HUDGold,false,false)]
                    +SHorizontalBox::Slot().AutoWidth()[Label(FString::Printf(TEXT("%lld %s"),Usable[Group],Group==1?TEXT("次"):TEXT("件")),14,ColdSteelUI::TextPrimary,false,false)]];
        if(Groups[Group].IsEmpty())Rows->AddSlot().AutoHeight().Padding(0,6)[Label(TEXT("未携带"),14,ColdSteelUI::TextSecondary)];
        for(const auto& Supply:Groups[Group])
        {
            const FString Name=Supply.Name+(Supply.bExpired?TEXT("（已变质）"):TEXT(""));
            const FString Amount=Group==1?FString::Printf(TEXT("%lld 件 · 可饮用 %lld 次"),Supply.Count,Supply.bExpired?0:Supply.Uses):FString::Printf(TEXT("× %lld"),Supply.Count);
            Rows->AddSlot().AutoHeight().Padding(0,5)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,12,0)
                        [Label(Name,14,Supply.bExpired?ColdSteelUI::TextTertiary:ColdSteelUI::TextPrimary)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Label(Amount,14,ColdSteelUI::TextPrimary,false,false)]];
        }
        AddGroup(Rows);
    }
    if(Usable[0]==0)Warnings.Add(TEXT("未携带可用食物"));
    if(Usable[1]==0)Warnings.Add(TEXT("未携带饮水"));
    if(Usable[2]==0)Warnings.Add(TEXT("未携带药水"));
    if(!Warnings.IsEmpty())PreparationRows->AddSlot().AutoHeight().Padding(0,12,0,4)
        [Label(FString::Join(Warnings,TEXT(" · ")),12,ColdSteelUI::Warning)];
    PreparationRows->AddSlot().AutoHeight().Padding(0,8,0,4)
        [Label(TEXT("统计背包与夹层；备弹来自弹药袋，未计入弹匣。缺少补给仍可出征。"),12,ColdSteelUI::TextTertiary)];
}
