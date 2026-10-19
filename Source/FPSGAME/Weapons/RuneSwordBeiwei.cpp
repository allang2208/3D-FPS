#include "RuneSwordComponent.h"
#include "BeiweiSwordTrailComponent.h"
#include "MeleeRuneVisual.h"
#include "FrostSwordRunes.h"
#include "RuneSwordChixiaoRhythm.h"
#include "ModularSwordVisual.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Characters/FPSPlayerBodyComponent.h"

void URuneSwordComponent::RefreshBeiwei(const FColdSteelItem* Item)
{
    const bool Enabled=Item&&Item->Definition==ColdSteelFrostRunes::Zhanmadao&&
        ColdSteelMeleeRune::Selected(*Item)==ColdSteelFrostRunes::Beiwei;
    const bool Zhufeng=Item&&ColdSteelModularSword::UsesZhufengWhirlwind(*Item);
    const bool HasTrail=Enabled||Zhufeng||(Item&&ColdSteelModularSword::UsesChixiaoDoubleHeavy(*Item));
    if(!HasTrail||Item->InstanceId!=InstanceId)if(BeiweiTrail)BeiweiTrail->Clear();
    BeiweiInstance=Enabled?Item->InstanceId:FString();
    ZhufengTrailInstance=Zhufeng?Item->InstanceId:FString();
    if(HasTrail&&!BeiweiTrail&&GetNetMode()!=NM_DedicatedServer&&Character.IsValid()&&Character->IsLocallyControlled())
    {
        BeiweiTrail=NewObject<UBeiweiSwordTrailComponent>(GetOwner());GetOwner()->AddInstanceComponent(BeiweiTrail);
        BeiweiTrail->SetView(true,false);BeiweiTrail->RegisterComponent();
    }
}
bool URuneSwordComponent::IsBeiweiMartialReleasing() const
{
    if(BeiweiInstance.IsEmpty()||BeiweiInstance!=InstanceId||!CanPresent()||!CanUse())return false;
    if(bChixiaoHeavy&&bAttacking)return RuneSwordChixiaoRhythm::IsContact(Elapsed);
    if(bWhirlwind)return Elapsed>=WhirlwindTuning.ReadySeconds&&Elapsed<=WhirlwindTuning.ReadySeconds+WhirlwindTuning.SpinSeconds;
    const bool Martial=bUppercut||(bAttacking&&(bHeavyAttack||bDashAttack||bQuickCombatStrike));
    return Martial&&Elapsed>=ContactStart-.06f&&Elapsed<=ContactEnd+.10f;
}
bool URuneSwordComponent::IsChixiaoHeavyReleasing() const
{
    return bChixiaoHeavy&&bAttacking&&CanPresent()&&CanUse()&&RuneSwordChixiaoRhythm::IsContact(Elapsed);
}
bool URuneSwordComponent::IsZhufengWhirlwindReleasing() const
{
    // Both the dash replacement and a manually cast whirlwind use this blade's palette.
    return !ZhufengTrailInstance.IsEmpty()&&ZhufengTrailInstance==InstanceId&&bWhirlwind&&CanPresent()&&CanUse()&&
        Elapsed>=WhirlwindTuning.ReadySeconds&&Elapsed<=WhirlwindTuning.ReadySeconds+WhirlwindTuning.SpinSeconds;
}
void URuneSwordComponent::TickBeiweiTrail()
{
    if(!BeiweiTrail)return;
    FVector Base,Tip;
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool Crimson=IsChixiaoHeavyReleasing();
    const bool Cyan=IsZhufengWhirlwindReleasing();
    const bool Active=!(Body&&Body->IsThirdPersonViewEnabled())&&(Cyan||Crimson||IsBeiweiMartialReleasing())&&GetFireMagicBladePoints(Base,Tip);
    BeiweiTrail->Feed(Base,Tip,Active,Cyan?ESwordTrailPalette::Cyan:Crimson?ESwordTrailPalette::Crimson:ESwordTrailPalette::Gold);
}
