#include "ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSLightningComponent.h"
#include "../Skills/FPSHolyLightComponent.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "GameFramework/PlayerController.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

namespace ColdSteelQuickBar
{
const TCHAR* KeyLabel(int32 Index)
{
    static const TCHAR* Labels[]={TEXT("Q"),TEXT("E"),TEXT("X"),TEXT("1"),TEXT("2"),TEXT("3"),TEXT("4")};
    return Index>=0&&Index<Count?Labels[Index]:TEXT("");
}
int32 KeyIndex(const FKey& Key)
{
    const FKey Keys[]={EKeys::Q,EKeys::E,EKeys::X,EKeys::One,EKeys::Two,EKeys::Three,EKeys::Four};
    for(int32 I=0;I<Count;++I)if(Key==Keys[I])return I;
    return INDEX_NONE;
}
void MirrorLegacy(FColdSteelProfile& P)
{
    if(P.QuickBarVersion!=1||P.QuickBindings.Num()!=Count)return;
    P.Hotbar.SetNum(4);P.HotbarDefinitions.SetNum(4);
    for(int32 I=0;I<4;++I){P.Hotbar[I]=P.QuickBindings[I+ItemOffset].ItemId;P.HotbarDefinitions[I]=P.QuickBindings[I+ItemOffset].ItemDefinition;}
}
bool Migrate(FColdSteelProfile& P)
{
    if(P.QuickBarVersion!=0)return false;
    P.QuickBindings.SetNum(Count);P.QuickBindings[0].Skill=TEXT("fireball");
    TSet<FString> Seen;
    for(int32 I=0;I<4;++I)
    {
        if(!P.Hotbar.IsValidIndex(I)||!P.HotbarDefinitions.IsValidIndex(I)||P.HotbarDefinitions[I].IsEmpty())continue;
        if(!P.Hotbar[I].IsEmpty()&&Seen.Contains(P.Hotbar[I]))continue;
        auto& B=P.QuickBindings[I+ItemOffset];B.ItemId=P.Hotbar[I];B.ItemDefinition=P.HotbarDefinitions[I];Seen.Add(B.ItemId);
    }
    P.QuickBarVersion=1;MirrorLegacy(P);return true;
}
bool Validate(const FColdSteelProfile& P,FString& Reason)
{
    if(P.QuickBarVersion==0)return true;
    Reason=TEXT("快捷栏绑定无效，保留原存档");
    if(P.QuickBarVersion!=1||P.QuickBindings.Num()!=Count)return false;
    TSet<FName> Skills;TSet<FString> Items;
    for(const auto& B:P.QuickBindings)
    {
        if(!B.Skill.IsNone())
        {
            if((!FireMagic::IsSkill(B.Skill)&&B.Skill!=TEXT("fireball")&&B.Skill!=TEXT("iceSpike")&&B.Skill!=TEXT("lightningStrike")&&B.Skill!=TEXT("holyLight")&&B.Skill!=TEXT("dodge")&&B.Skill!=TEXT("heavyStrike")&&B.Skill!=TEXT("quickCombat")&&B.Skill!=TEXT("whirlwind"))||!B.ItemId.IsEmpty()||!B.ItemDefinition.IsEmpty()||Skills.Contains(B.Skill))return false;
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
{ if(FireMagic::IsSkill(Id))return &FireMagicDefinition(Id);if(Id==TEXT("holyLight"))return &HolyLightSkill;if(Id==TEXT("lightningStrike"))return &LightningSkill;if(Id==TEXT("iceSpike"))return &IceSpikeSkill;if(Id==TEXT("heavyStrike")||Id==TEXT("whirlwind"))return &MasteryDefinition(Id);if(Id==TEXT("quickCombat"))return &QuickCombatSkill;if(Id==TEXT("runeBlades"))return &RuneBladesSkill;return Id==TEXT("fireball")?&FireballSkill:Id==TEXT("dodge")?&DodgeSkill:nullptr; }
bool UColdSteelStatusModel::CanBindQuickSkill(FName Id) const
{ const auto* P=Current.Skills.Find(Id);return QuickSkillDefinition(Id)&&P&&P->Level>0; }
const FColdSteelItem* UColdSteelStatusModel::ResolveQuickItem(int32 Index) const
{
    const auto B=QuickBinding(Index);if(!B.Skill.IsNone()||B.ItemDefinition.IsEmpty())return nullptr;
    const auto* I=FindItem(B.ItemId);
    if(I&&I->Place==0&&I->Definition==B.ItemDefinition&&ColdSteelInventory::Text(*I,TEXT("category"))==TEXT("consumable"))return I;
    return Current.Items.FindByPredicate([&](const auto& V){return V.Place==0&&V.Definition==B.ItemDefinition&&ColdSteelInventory::Text(V,TEXT("category"))==TEXT("consumable");});
}
bool UColdSteelStatusModel::BindQuickSkill(int32 Index,FName Id)
{
    if(!Current.QuickBindings.IsValidIndex(Index)||!CanBindQuickSkill(Id))return false;
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
    if(Id.IsEmpty())return ClearQuickBinding(Index);
    const auto* Item=FindItem(Id);
    if(!Item||Item->Place!=0||ColdSteelInventory::Text(*Item,TEXT("category"))!=TEXT("consumable"))return false;
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
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player||!CanBindQuickSkill(B.Skill))return false;
    if(B.Skill==TEXT("heavyStrike"))if(auto* Ability=Player->FindComponentByClass<URuneSwordComponent>())return Ability->TriggerHeavySkill();
    if(B.Skill==TEXT("whirlwind"))if(auto* Ability=Player->FindComponentByClass<URuneSwordComponent>())return Ability->BeginWhirlwind();
    if(B.Skill==TEXT("dodge"))return Player->TryDodge();
    if(B.Skill==TEXT("quickCombat"))return TriggerQuickCombat();
    if(B.Skill==TEXT("fireball"))if(auto* Ability=Player->FindComponentByClass<UFPSFireballComponent>()){Ability->Trigger();return true;}
    if(B.Skill==TEXT("iceSpike"))if(auto* Ability=Player->FindComponentByClass<UFPSIceSpikeComponent>()){Ability->Trigger();return true;}
    if(B.Skill==TEXT("holyLight"))if(auto* Ability=Player->FindComponentByClass<UFPSHolyLightComponent>())
    {const auto* PC=Cast<APlayerController>(Player->GetController());Ability->Trigger(PC&&(PC->IsInputKeyDown(EKeys::LeftAlt)||PC->IsInputKeyDown(EKeys::RightAlt)));return true;}
    if(B.Skill==TEXT("lightningStrike"))if(auto* Ability=Player->FindComponentByClass<UFPSLightningComponent>()){Ability->Trigger();return true;}
    if(FireMagic::IsSkill(B.Skill))if(auto* Ability=Player->FindComponentByClass<UFPSFireMagicComponent>()){Ability->Trigger(B.Skill);return true;}
    return false;
}

bool UColdSteelStatusModel::BeginSpellAimPreview(int32 Index)
{
    const FName Skill=QuickBinding(Index).Skill;
    if(Skill!=TEXT("fireball")&&Skill!=TEXT("iceSpike"))return false;
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player)return false;
    if(Skill==TEXT("fireball"))
    {
        auto* Ability=Player->FindComponentByClass<UFPSFireballComponent>();
        if(!Ability)return false;
        Ability->SetAimPreview(true);
        if(!Ability->IsAimPreviewActive())return false;
    }
    else
    {
        auto* Ability=Player->FindComponentByClass<UFPSIceSpikeComponent>();
        if(!Ability)return false;
        Ability->SetAimPreview(true);
        if(!Ability->IsAimPreviewActive())return false;
    }
    AimPreviewIndex=Index;
    return true;
}

bool UColdSteelStatusModel::EndSpellAimPreview(int32 Index)
{
    if(AimPreviewIndex!=Index)return false;
    AimPreviewIndex=INDEX_NONE;
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player)return true;
    const FName Skill=QuickBinding(Index).Skill;
    // The release fires only while this preview is still alive: a projectile that expired
    // (hover timeout, death, loadout change) must not start a fresh cast instead.
    if(Skill==TEXT("fireball"))
    {
        if(auto* Ability=Player->FindComponentByClass<UFPSFireballComponent>())
        {const bool bFire=Ability->IsAimPreviewActive();Ability->SetAimPreview(false);if(bFire)Ability->Trigger();}
    }
    else if(Skill==TEXT("iceSpike"))
    {
        if(auto* Ability=Player->FindComponentByClass<UFPSIceSpikeComponent>())
        {const bool bFire=Ability->IsAimPreviewActive();Ability->SetAimPreview(false);if(bFire)Ability->Trigger();}
    }
    return true;
}

void UColdSteelStatusModel::CancelSpellAimPreview()
{
    AimPreviewIndex=INDEX_NONE;
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player)return;
    if(auto* Fireball=Player->FindComponentByClass<UFPSFireballComponent>())Fireball->SetAimPreview(false);
    if(auto* Ice=Player->FindComponentByClass<UFPSIceSpikeComponent>())Ice->SetAimPreview(false);
}
