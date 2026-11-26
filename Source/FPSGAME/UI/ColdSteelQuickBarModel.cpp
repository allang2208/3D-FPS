#include "ColdSteelStatusModel.h"
#include "../Weapons/PojunGrip.h"
#include "ColdSteelMagicQuickCast.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../Skills/FPSMagicArrowRainComponent.h"
#include "../Skills/FPSElementalArrowComponent.h"
#include "../Skills/FPSIlluminationArrowComponent.h"
#include "../Skills/FPSLightningComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/FPSHolyLightComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "GameFramework/PlayerController.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/OffhandKukriComponent.h"
#include "../Weapons/Staff/StaffOffhandMeleeComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

namespace ColdSteelQuickBar
{
const TCHAR* KeyLabel(int32 Index)
{
    static const TCHAR* Labels[]={TEXT(""),TEXT(""),TEXT(""),TEXT("1"),TEXT("2"),TEXT("3"),TEXT("4"),TEXT("5"),TEXT("6"),TEXT("7"),TEXT("8"),TEXT("9"),TEXT("0")};
    return Index>=0&&Index<Count?Labels[Index]:TEXT("");
}
FKey Key(int32 Index)
{
    static const FKey Keys[]={EKeys::Invalid,EKeys::Invalid,EKeys::Invalid,EKeys::One,EKeys::Two,EKeys::Three,EKeys::Four,EKeys::Five,EKeys::Six,EKeys::Seven,EKeys::Eight,EKeys::Nine,EKeys::Zero};
    return Index>=0&&Index<Count?Keys[Index]:EKeys::Invalid;
}
int32 KeyIndex(const FKey& Input)
{
    if(!Input.IsValid())return INDEX_NONE;
    for(int32 I=ItemOffset;I<Count;++I)if(Input==Key(I))return I;
    return INDEX_NONE;
}
void MirrorLegacy(FColdSteelProfile& P)
{
    if(P.QuickBarVersion!=Version||P.QuickBindings.Num()!=Count)return;
    P.Hotbar.SetNum(4);P.HotbarDefinitions.SetNum(4);
    for(int32 I=0;I<4;++I){P.Hotbar[I]=P.QuickBindings[I+ItemOffset].ItemId;P.HotbarDefinitions[I]=P.QuickBindings[I+ItemOffset].ItemDefinition;}
}
// Q/E/X retired (version 3): their bindings move to the first free number slot, otherwise they are dropped.
static void RetireLetterSlots(FColdSteelProfile& P)
{
    for(int32 I=0;I<ItemOffset&&I<P.QuickBindings.Num();++I)
    {
        if(P.QuickBindings[I].IsEmpty())continue;
        for(int32 J=ItemOffset;J<P.QuickBindings.Num();++J)if(P.QuickBindings[J].IsEmpty()){P.QuickBindings[J]=P.QuickBindings[I];break;}
        P.QuickBindings[I]=FColdSteelQuickBinding();
    }
}
bool Migrate(FColdSteelProfile& P)
{
    const bool MagicMigrated=ColdSteelMagicQuickCast::Migrate(P);
    if(P.QuickBarVersion==1&&P.QuickBindings.Num()==LegacyCount)
    {
        P.QuickBindings.SetNum(Count);RetireLetterSlots(P);P.QuickBarVersion=Version;MirrorLegacy(P);return true;
    }
    if(P.QuickBarVersion==2&&P.QuickBindings.Num()==Count){RetireLetterSlots(P);P.QuickBarVersion=Version;MirrorLegacy(P);return true;}
    if(P.QuickBarVersion!=0)return MagicMigrated;
    P.QuickBindings.SetNum(Count);P.QuickBindings[0].Skill=TEXT("fireball");
    TSet<FString> Seen;
    for(int32 I=0;I<4;++I)
    {
        if(!P.Hotbar.IsValidIndex(I)||!P.HotbarDefinitions.IsValidIndex(I)||P.HotbarDefinitions[I].IsEmpty())continue;
        if(!P.Hotbar[I].IsEmpty()&&Seen.Contains(P.Hotbar[I]))continue;
        auto& B=P.QuickBindings[I+ItemOffset];B.ItemId=P.Hotbar[I];B.ItemDefinition=P.HotbarDefinitions[I];Seen.Add(B.ItemId);
    }
    RetireLetterSlots(P);P.QuickBarVersion=Version;MirrorLegacy(P);return true;
}
bool Validate(const FColdSteelProfile& P,FString& Reason)
{
    if(!ColdSteelMagicQuickCast::Validate(P,Reason))return false;
    if(P.QuickBarVersion==0)return true;
    Reason=TEXT("快捷栏绑定无效，保留原存档");
    if(!((P.QuickBarVersion==1&&P.QuickBindings.Num()==LegacyCount)||
        ((P.QuickBarVersion==2||P.QuickBarVersion==Version)&&P.QuickBindings.Num()==Count)))return false;
    TSet<FName> Skills;TSet<FString> Items;
    for(const auto& B:P.QuickBindings)
    {
        if(!B.Skill.IsNone())
        {
            if((!ElectricMagic::IsSkill(B.Skill)&&!FireMagic::IsSkill(B.Skill)&&B.Skill!=TEXT("fireball")&&B.Skill!=TEXT("iceSpike")&&B.Skill!=TEXT("iceWall")&&B.Skill!=TEXT("blizzard")&&B.Skill!=TEXT("magicArrowRain")&&B.Skill!=TEXT("elementalArrow")&&B.Skill!=TEXT("illuminationArrow")&&B.Skill!=TEXT("lightningStrike")&&B.Skill!=TEXT("holyLight")&&B.Skill!=TEXT("lightningHaste")&&B.Skill!=TEXT("iceArmor")&&B.Skill!=TEXT("dodge")&&B.Skill!=TEXT("heavyStrike")&&B.Skill!=TEXT("quickCombat")&&B.Skill!=TEXT("whirlwind")&&B.Skill!=TEXT("swordUppercut")&&B.Skill!=TEXT("chainSlash")&&B.Skill!=TEXT("leapStrike")&&B.Skill!=TEXT("shadowStepSlash"))||!B.ItemId.IsEmpty()||!B.ItemDefinition.IsEmpty()||Skills.Contains(B.Skill))return false;
            Skills.Add(B.Skill);
        }
        else if(!B.ItemDefinition.IsEmpty())
        {
            if(!B.ItemId.IsEmpty()&&Items.Contains(B.ItemId))return false;
            if(!B.ItemId.IsEmpty())Items.Add(B.ItemId);
        }
        else if(!B.ItemId.IsEmpty())return false;
    }
    Reason.Reset();return true;
}
}

FColdSteelQuickBinding UColdSteelStatusModel::QuickBinding(int32 Index) const
{ return Current.QuickBindings.IsValidIndex(Index)?Current.QuickBindings[Index]:FColdSteelQuickBinding(); }
const FColdSteelSkillDefinition* UColdSteelStatusModel::QuickSkillDefinition(FName Id) const
{ if(Id==TEXT("illuminationArrow")||Id==TEXT("magicArrowRain")||Id==TEXT("elementalArrow"))return &MasteryDefinition(Id);if(Id==TEXT("leapStrike")||Id==TEXT("chainSlash")||Id==TEXT("shadowStepSlash")||Id==TEXT("swordUppercut"))return &MasteryDefinition(Id);if(ElectricMagic::IsSkill(Id))return &ElectricMagicDefinition(Id);if(Id==TEXT("blizzard"))return &BlizzardSkill;if(Id==TEXT("iceWall"))return &IceWallSkill;if(Id==TEXT("staffLight"))return &StaffLightSkill;if(FireMagic::IsSkill(Id))return &FireMagicDefinition(Id);if(Id==TEXT("holyLight"))return &HolyLightSkill;if(Id==TEXT("lightningHaste"))return &LightningHasteSkill;if(Id==TEXT("iceArmor"))return &IceArmorSkill;if(Id==TEXT("lightningStrike"))return &LightningSkill;if(Id==TEXT("iceSpike"))return &IceSpikeSkill;if(Id==TEXT("heavyStrike")||Id==TEXT("whirlwind"))return &MasteryDefinition(Id);if(Id==TEXT("quickCombat"))return &QuickCombatSkill;if(Id==TEXT("runeBlades"))return &RuneBladesSkill;return Id==TEXT("fireball")?&FireballSkill:Id==TEXT("dodge")?&DodgeSkill:nullptr; }
bool UColdSteelStatusModel::CanBindQuickSkill(FName Id) const
{ if(Id==TEXT("runeBlades")||Id==TEXT("staffLight"))return false;if(!IsSkillLearned(Id))return false;if(Id==TEXT("swordUppercut"))return true;const auto* P=Current.Skills.Find(Id);return QuickSkillDefinition(Id)&&P&&P->Level>0; }
const FColdSteelItem* UColdSteelStatusModel::ResolveQuickItem(int32 Index) const
{
    const auto B=QuickBinding(Index);if(!B.Skill.IsNone()||B.ItemDefinition.IsEmpty())return nullptr;
    // 背包与夹层的同类消耗品在快捷栏视为一体：显示合计（QuickItemCount），消耗优先背包那堆，
    // 背包堆耗尽（实例移除）后解析自然落到夹层堆上，绑定不因换堆而失效。
    const FColdSteelItem* CompartmentStack=nullptr;
    for(const auto& V:Current.Items)
    {
        if(V.Definition!=B.ItemDefinition||(V.Place!=0&&V.Place!=ColdSteelInventory::ColdSteelCompartment::Place)||ColdSteelInventory::Text(V,TEXT("category"))!=TEXT("consumable"))continue;
        if(V.Place==0)return &V;
        if(!CompartmentStack)CompartmentStack=&V;
    }
    return CompartmentStack;
}
int64 UColdSteelStatusModel::QuickItemCount(int32 Index) const
{
    const auto B=QuickBinding(Index);if(!B.Skill.IsNone()||B.ItemDefinition.IsEmpty())return 0;
    int64 Total=0;
    for(const auto& V:Current.Items)
        if(V.Definition==B.ItemDefinition&&(V.Place==0||V.Place==ColdSteelInventory::ColdSteelCompartment::Place)&&ColdSteelInventory::Text(V,TEXT("category"))==TEXT("consumable"))Total+=V.Count;
    return Total;
}
bool UColdSteelStatusModel::BindQuickSkill(int32 Index,FName Id)
{
    if(Index<ColdSteelQuickBar::ItemOffset||!Current.QuickBindings.IsValidIndex(Index)||!CanBindQuickSkill(Id))return false;
    const int32 Existing=Current.QuickBindings.IndexOfByPredicate([&](const auto& B){return B.Skill==Id;});
    if(Existing==Index)return true;
    SyncRuntime();auto P=Snapshot();
    if(Existing>=0)P.QuickBindings[Existing]=P.QuickBindings[Index];
    P.QuickBindings[Index]=FColdSteelQuickBinding();P.QuickBindings[Index].Skill=Id;
    return CommitState(P);
}
bool UColdSteelStatusModel::BindQuickItem(int32 Index,const FString& Id)
{
    if(!Current.QuickBindings.IsValidIndex(Index))return false;
    if(Index<ColdSteelQuickBar::ItemOffset&&!Id.IsEmpty())return false;
    if(Id.IsEmpty())return ClearQuickBinding(Index);
    const auto* Item=FindItem(Id);
    // Match the drag preview: equipped backpack compartments are carried inventory too.
    if(!Item||(Item->Place!=0&&Item->Place!=ColdSteelInventory::ColdSteelCompartment::Place)||ColdSteelInventory::Text(*Item,TEXT("category"))!=TEXT("consumable"))
    {
        Message=TEXT("仅可绑定背包或夹层中的消耗品");return false;
    }
    int32 Existing=INDEX_NONE;
    for(int32 I=0;I<ColdSteelQuickBar::Count;++I)
    {const auto* Bound=ResolveQuickItem(I);if(Current.QuickBindings[I].ItemId==Id||(Bound&&Bound->InstanceId==Id)){Existing=I;break;}}
    if(Existing==Index)return true;
    FColdSteelQuickBinding Binding;Binding.ItemId=Id;Binding.ItemDefinition=Item->Definition;
    SyncRuntime();auto P=Snapshot();if(Existing>=0)P.QuickBindings[Existing]=P.QuickBindings[Index];
    P.QuickBindings[Index]=Binding;return CommitState(P);
}
bool UColdSteelStatusModel::SwapQuickBindings(int32 From,int32 To)
{
    if(!Current.QuickBindings.IsValidIndex(From)||!Current.QuickBindings.IsValidIndex(To))return false;
    if(From<ColdSteelQuickBar::ItemOffset||To<ColdSteelQuickBar::ItemOffset)return false;
    if(From==To)return true;
    SyncRuntime();auto P=Snapshot();P.QuickBindings.Swap(From,To);return CommitState(P);
}
bool UColdSteelStatusModel::ClearQuickBinding(int32 Index)
{
    if(!Current.QuickBindings.IsValidIndex(Index))return false;
    if(Current.QuickBindings[Index].IsEmpty())return true;
    SyncRuntime();auto P=Snapshot();P.QuickBindings[Index]=FColdSteelQuickBinding();return CommitState(P);
}
bool UColdSteelStatusModel::UseQuickBinding(int32 Index)
{
    const auto B=QuickBinding(Index);
    if(B.Skill.IsNone()){const auto* I=ResolveQuickItem(Index);return I&&UseItem(I->InstanceId);}
    return UseQuickSkill(B.Skill);
}

bool UColdSteelStatusModel::UseQuickSkill(FName Skill)
{
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player||!CanBindQuickSkill(Skill))return false;
    if(Skill!=TEXT("dodge")&&UFPSPotionUseComponent::BlocksWeaponAttack(Player))return false;
    if(Skill!=TEXT("quickCombat")&&UBoundCongregateCaptureComponent::IsCaptured(Player))return false;
    if(Skill==TEXT("leapStrike"))
    {auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();return Tool&&Tool->BeginLeapStrike();}
    if(Skill==TEXT("chainSlash"))
    {
        auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();
        return Sword&&Sword->BeginChainSlash();
    }
    if(Skill==TEXT("shadowStepSlash"))
    {
        if(auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsEquipped())return Kukri->BeginShadowStep();
        if(auto* Offhand=Player->FindComponentByClass<UOffhandKukriComponent>();
            Offhand&&(Offhand->IsEquipped()||UStaffOffhandMeleeComponent::IsEquippedOn(Player)))return Offhand->BeginShadowStep();
        return false;
    }
    if(Skill==TEXT("swordUppercut"))
    {
        if(const auto* Tool=ActiveProductionTool();Tool&&PojunGrip::UsesHammerMotion(*Tool))
            if(auto* Ability=Player->FindComponentByClass<UProductionToolComponent>())return Ability->BeginUppercut();
        if(auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsEquipped())return Kukri->BeginUppercut();
        // 手枪＋副手弯刀：上挑由副手刀镜像出手（OffhandKukriUppercut.cpp），排在主手弯刀之后、双手剑之前。
        if(auto* Offhand=Player->FindComponentByClass<UOffhandKukriComponent>();
            Offhand&&(Offhand->IsEquipped()||UStaffOffhandMeleeComponent::IsEquippedOn(Player)))return Offhand->BeginUppercut();
        if(auto* Ability=Player->FindComponentByClass<URuneSwordComponent>())return Ability->BeginUppercut();
    }
    if(Skill==TEXT("heavyStrike"))
    {
        if(auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsEquipped())return Kukri->TriggerHeavySkill();
        if(auto* Ability=Player->FindComponentByClass<URuneSwordComponent>())return Ability->TriggerHeavySkill();
    }
    if(Skill==TEXT("whirlwind"))
    {
        if(const auto* Tool=ActiveProductionTool();Tool&&PojunGrip::UsesHammerMotion(*Tool))
            if(auto* Ability=Player->FindComponentByClass<UProductionToolComponent>())return Ability->BeginWhirlwind();
        // 尼泊尔弯刀 → 单手旋风（KukriWhirlwind.cpp）；剑组件总在，所以弯刀排在剑之前。
        if(auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();
            Kukri&&(Kukri->IsEquipped()||UStaffOffhandMeleeComponent::IsEquippedOn(Player)))return Kukri->BeginWhirlwind();
        if(auto* Ability=Player->FindComponentByClass<URuneSwordComponent>())return Ability->BeginWhirlwind();
    }
    if(Skill==TEXT("illuminationArrow"))if(auto* Ability=Player->FindComponentByClass<UFPSIlluminationArrowComponent>())return Ability->Trigger();
    if(Skill==TEXT("elementalArrow"))if(auto* Ability=Player->FindComponentByClass<UFPSElementalArrowComponent>())return Ability->Trigger();
    if(Skill==TEXT("magicArrowRain"))if(auto* Ability=Player->FindComponentByClass<UFPSMagicArrowRainComponent>())return Ability->Trigger();
    if(Skill==TEXT("dodge"))return Player->TryDodge();
    if(Skill==TEXT("quickCombat"))return TriggerQuickCombat();
    if(Skill==TEXT("fireball"))if(auto* Ability=Player->FindComponentByClass<UFPSFireballComponent>()){Ability->Trigger();return true;}
    if(Skill==TEXT("iceSpike"))if(auto* Ability=Player->FindComponentByClass<UFPSIceSpikeComponent>()){Ability->Trigger();return true;}
    if(Skill==TEXT("blizzard"))if(auto* Ability=Player->FindComponentByClass<UFPSBlizzardComponent>()){Ability->Trigger();return true;}
    if(Skill==TEXT("iceWall"))if(auto* Ability=Player->FindComponentByClass<UFPSIceWallComponent>()){Ability->Trigger();return true;}
    if(Skill==TEXT("iceArmor"))if(auto* Ability=Player->FindComponentByClass<UFPSIceArmorComponent>()){Ability->Trigger();return true;}
    if(Skill==TEXT("lightningHaste"))if(auto* Ability=Player->FindComponentByClass<UFPSLightningHasteComponent>()){Ability->Trigger();return true;}
    if(Skill==TEXT("holyLight"))if(auto* Ability=Player->FindComponentByClass<UFPSHolyLightComponent>())
    {const auto* PC=Cast<APlayerController>(Player->GetController());Ability->Trigger(PC&&(PC->IsInputKeyDown(EKeys::LeftAlt)||PC->IsInputKeyDown(EKeys::RightAlt)));return true;}
    if(ElectricMagic::IsSkill(Skill))if(auto* Ability=Player->FindComponentByClass<UFPSElectricMagicComponent>()){Ability->Trigger(Skill);return true;}
    if(Skill==TEXT("lightningStrike"))if(auto* Ability=Player->FindComponentByClass<UFPSLightningComponent>()){Ability->Trigger();return true;}
    if(FireMagic::IsSkill(Skill))if(auto* Ability=Player->FindComponentByClass<UFPSFireMagicComponent>()){Ability->Trigger(Skill);return true;}
    return false;
}

bool UColdSteelStatusModel::BeginSpellAimPreview(int32 Index)
{
    return BeginSpellAimPreviewForSkill(QuickBinding(Index).Skill,Index);
}

bool UColdSteelStatusModel::BeginSpellAimPreviewForSkill(FName Skill,int32 Index)
{
    if(UFPSPotionUseComponent::BlocksWeaponAttack(UGameplayStatics::GetPlayerPawn(this,0)))return false;
    if(UBoundCongregateCaptureComponent::IsCaptured(UGameplayStatics::GetPlayerPawn(this,0)))return false;
    if(!CanBindQuickSkill(Skill))return false;
    if(Skill!=TEXT("leapStrike"))if(auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0))
        if(auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>())Tool->SetLeapAimPreview(false);
    if(Skill!=TEXT("meteor"))if(auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0))
        if(auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>())Fire->SetMeteorAimPreview(false);
    if(Skill==TEXT("thunderLance")){auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);if(!CanBindQuickSkill(Skill)||!Pawn)return false;if(auto* Ability=Pawn->FindComponentByClass<UFPSElectricMagicComponent>()){Ability->Trigger(Skill);AimPreviewIndex=Index;AimPreviewPawn=Cast<AFPSGAMECharacter>(Pawn);AimPreviewSkill=Skill;return true;}return false;}
    if(Skill!=TEXT("fireball")&&Skill!=TEXT("iceSpike")&&Skill!=TEXT("blizzard")&&Skill!=TEXT("meteor")&&Skill!=TEXT("leapStrike"))return false;
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player)return false;
    if(Skill==TEXT("leapStrike"))
    {
        CancelSpellAimPreview();
        auto* Ability=Player->FindComponentByClass<UProductionToolComponent>();
        if(!Ability)return false;
        Ability->SetLeapAimPreview(true);
        // Rejected holds are consumed too; release must never fall back to a new cast.
    }
    else if(Skill==TEXT("meteor"))
    {
        auto* Ability=Player->FindComponentByClass<UFPSFireMagicComponent>();
        if(!Ability)return false;
        Ability->SetMeteorAimPreview(true);
        // Consume a rejected press as well; do not fall through to instant cast.
    }
    else if(Skill==TEXT("fireball"))
    {
        auto* Ability=Player->FindComponentByClass<UFPSFireballComponent>();
        if(!Ability)return false;
        Ability->SetAimPreview(true);
        if(!Ability->IsAimPreviewActive())return false;
    }
    else if(Skill==TEXT("iceSpike"))
    {
        auto* Ability=Player->FindComponentByClass<UFPSIceSpikeComponent>();
        if(!Ability)return false;
        Ability->SetAimPreview(true);
        if(!Ability->IsAimPreviewActive())return false;
    }
    else
    {
        auto* Ability=Player->FindComponentByClass<UFPSBlizzardComponent>();
        if(!Ability)return false;
        Ability->SetAimPreview(true);
        if(!Ability->IsAimPreviewActive())return false;
    }
    AimPreviewIndex=Index;AimPreviewPawn=Player;AimPreviewSkill=Skill;
    return true;
}

bool UColdSteelStatusModel::EndSpellAimPreview(int32 Index)
{
    if(AimPreviewIndex!=Index)return false;
    const auto ExpectedPawn=AimPreviewPawn;const FName Skill=AimPreviewSkill;
    AimPreviewIndex=INDEX_NONE;AimPreviewPawn.Reset();AimPreviewSkill=NAME_None;
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player||ExpectedPawn.Get()!=Player)return true;
    if(Skill==TEXT("thunderLance")){if(auto* Ability=Player->FindComponentByClass<UFPSElectricMagicComponent>())Ability->ReleaseLance();return true;}
    // The release fires only while this preview is still alive: a projectile that expired
    // (hover timeout, death, loadout change) must not start a fresh cast instead.
    if(Skill==TEXT("leapStrike"))
    {
        if(auto* Ability=Player->FindComponentByClass<UProductionToolComponent>())
            if(Ability->IsLeapAimPreviewActive())Ability->ReleaseLeapAimPreview();
    }
    else if(Skill==TEXT("meteor"))
    {
        if(auto* Ability=Player->FindComponentByClass<UFPSFireMagicComponent>())
        {if(Ability->IsMeteorAimPreviewActive())Ability->ReleaseMeteorAimPreview();}
    }
    else if(Skill==TEXT("fireball"))
    {
        if(auto* Ability=Player->FindComponentByClass<UFPSFireballComponent>())
        {if(Ability->IsAimPreviewActive())Ability->ReleaseAimPreview();}
    }
    else if(Skill==TEXT("iceSpike"))
    {
        if(auto* Ability=Player->FindComponentByClass<UFPSIceSpikeComponent>())
        {if(Ability->IsAimPreviewActive())Ability->ReleaseAimPreview();}
    }
    else if(Skill==TEXT("blizzard"))
    {
        if(auto* Ability=Player->FindComponentByClass<UFPSBlizzardComponent>())
        {if(Ability->IsAimPreviewActive())Ability->ReleaseAimPreview();}
    }
    return true;
}

void UColdSteelStatusModel::CancelSpellAimPreview()
{
    AimPreviewIndex=INDEX_NONE;AimPreviewPawn.Reset();AimPreviewSkill=NAME_None;
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player)return;
    if(auto* Tool=Player->FindComponentByClass<UProductionToolComponent>())Tool->SetLeapAimPreview(false);
    if(auto* Fireball=Player->FindComponentByClass<UFPSFireballComponent>())Fireball->SetAimPreview(false);
    if(auto* Ice=Player->FindComponentByClass<UFPSIceSpikeComponent>())Ice->SetAimPreview(false);
    if(auto* IceWall=Player->FindComponentByClass<UFPSIceWallComponent>())IceWall->SuspendPreview();
    if(auto* Blizzard=Player->FindComponentByClass<UFPSBlizzardComponent>())Blizzard->SuspendPreview();
    if(auto* Fire=Player->FindComponentByClass<UFPSFireMagicComponent>())Fire->SetMeteorAimPreview(false);
    if(auto* Electric=Player->FindComponentByClass<UFPSElectricMagicComponent>())Electric->CancelPending();
}
