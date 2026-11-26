#include "ColdSteelMagicQuickCast.h"
#include "ColdSteelStatusModel.h"

namespace ColdSteelMagicQuickCast
{
bool IsMagic(FName Skill)
{
    return ElectricMagic::IsSkill(Skill)||FireMagic::IsSkill(Skill)||Skill==TEXT("fireball")||
        Skill==TEXT("iceSpike")||Skill==TEXT("iceWall")||Skill==TEXT("blizzard")||
        Skill==TEXT("holyLight")||Skill==TEXT("lightningHaste")||Skill==TEXT("iceArmor")||Skill==TEXT("lightningStrike");
}
bool Migrate(FColdSteelProfile& Profile)
{
    if(Profile.MagicWheelVersion!=0)return false;
    // Existing hotkeys stay independent. New and older saves start with an empty wheel.
    Profile.MagicWheelSkills.Init(NAME_None,Count);
    Profile.SelectedMagicSlot=INDEX_NONE;Profile.MagicWheelVersion=Version;return true;
}
bool Validate(const FColdSteelProfile& Profile,FString& Reason)
{
    if(Profile.MagicWheelVersion==0)return true;
    Reason=TEXT("快捷魔法配置无效，保留原存档");
    if(Profile.MagicWheelVersion!=Version||Profile.MagicWheelSkills.Num()!=Count)return false;
    TSet<FName> Seen;
    for(FName Skill:Profile.MagicWheelSkills)
    {
        if(Skill.IsNone())continue;
        if(!IsMagic(Skill)||Seen.Contains(Skill))return false;
        Seen.Add(Skill);
    }
    if(Profile.SelectedMagicSlot!=INDEX_NONE&&(!Profile.MagicWheelSkills.IsValidIndex(Profile.SelectedMagicSlot)||
        Profile.MagicWheelSkills[Profile.SelectedMagicSlot].IsNone()))return false;
    Reason.Reset();return true;
}
}

FName UColdSteelStatusModel::SelectedMagicSkill() const
{return Current.MagicWheelSkills.IsValidIndex(Current.SelectedMagicSlot)?Current.MagicWheelSkills[Current.SelectedMagicSlot]:NAME_None;}
float UColdSteelStatusModel::MagicCooldownRemaining(FName Skill) const
{
    if(ElectricMagic::IsSkill(Skill))return ElectricMagicCooldown(Skill);
    if(FireMagic::IsSkill(Skill))return FireMagicCooldown(Skill);
    if(Skill==TEXT("fireball"))return FireballCooldown();
    if(Skill==TEXT("iceSpike"))return IceSpikeCooldown();
    if(Skill==TEXT("iceWall"))return IceWallCooldown();
    if(Skill==TEXT("blizzard"))return BlizzardCooldown();
    if(Skill==TEXT("holyLight"))return HolyLightCooldown();
    if(Skill==TEXT("iceArmor"))return IceArmorCooldown();
    if(Skill==TEXT("lightningHaste"))return LightningHasteCooldown();
    if(Skill==TEXT("lightningStrike"))return LightningCooldown();
    return 0.f;
}
bool UColdSteelStatusModel::CanBindMagic(FName Skill) const
{return ColdSteelMagicQuickCast::IsMagic(Skill)&&CanBindQuickSkill(Skill);}
bool UColdSteelStatusModel::BindMagic(int32 Index,FName Skill)
{
    if(!Current.MagicWheelSkills.IsValidIndex(Index)||!CanBindMagic(Skill))return false;
    const int32 Existing=Current.MagicWheelSkills.Find(Skill);
    if(Existing==Index)return true;
    const FName Selected=SelectedMagicSkill();
    SyncRuntime();auto Profile=Snapshot();
    if(Existing>=0)Profile.MagicWheelSkills[Existing]=Profile.MagicWheelSkills[Index];
    Profile.MagicWheelSkills[Index]=Skill;
    Profile.SelectedMagicSlot=Selected.IsNone()?INDEX_NONE:Profile.MagicWheelSkills.Find(Selected);
    return CommitState(Profile);
}
bool UColdSteelStatusModel::ClearMagic(int32 Index)
{
    if(!Current.MagicWheelSkills.IsValidIndex(Index))return false;
    if(Current.MagicWheelSkills[Index].IsNone())return true;
    SyncRuntime();auto Profile=Snapshot();Profile.MagicWheelSkills[Index]=NAME_None;
    if(Profile.SelectedMagicSlot==Index)Profile.SelectedMagicSlot=INDEX_NONE;
    return CommitState(Profile);
}
bool UColdSteelStatusModel::SelectMagic(int32 Index)
{
    if(Index!=INDEX_NONE&&(!Current.MagicWheelSkills.IsValidIndex(Index)||!CanBindMagic(Current.MagicWheelSkills[Index])))return false;
    if(Current.SelectedMagicSlot==Index)return true;
    SyncRuntime();auto Profile=Snapshot();Profile.SelectedMagicSlot=Index;
    return CommitState(Profile);
}
bool UColdSteelStatusModel::PressStaffMagic()
{
    const FName Skill=SelectedMagicSkill();
    if(!HasEquippedStaff()||!CanBindMagic(Skill))return false;
    return BeginSpellAimPreviewForSkill(Skill,ColdSteelMagicQuickCast::StaffInput)||UseQuickSkill(Skill);
}
void UColdSteelStatusModel::ReleaseStaffMagic()
{EndSpellAimPreview(ColdSteelMagicQuickCast::StaffInput);}
void UColdSteelStatusModel::CancelStaffMagic()
{if(AimPreviewIndex==ColdSteelMagicQuickCast::StaffInput)CancelSpellAimPreview();}
