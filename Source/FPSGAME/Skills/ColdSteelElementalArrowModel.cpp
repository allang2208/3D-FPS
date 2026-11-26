#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillTree.h"
#include "ElementalArrowTypes.h"
#include "ColdSteelSkillRules.h"
#include "ColdSteelSpellRewards.h"

FElementalArrowCast UColdSteelStatusModel::ElementalArrowStats(EArrowElement Element,int32 AtLevel) const
{
    const auto& D=MasteryDefinition(TEXT("elementalArrow"));const auto& T=D.ElementalArrow;
    const int32 L=FMath::Clamp(AtLevel<0?MasteryProgress(D.Id).Level:AtLevel,1,D.MaxLevel);
    // Own specializations (2026-11-15): 爆燃箭 fire multiplier, 霜凝 chill, 导电 stun; 节能 in ElementalArrowManaCost.
    const float Multiplier=ElementalArrow::DamageMultiplier(T,Element,L)+(Element==EArrowElement::Fire?SpecStat(TEXT("elementalArrow"),TEXT("fireMultiplier")):0.f);
    // Fireball specs are NOT applied in full here; fire arrows take the inherited 50% share below,
    // and the shared burst radius of ice/lightning arrows stays unaffected by fireball specs.
    FElementalArrowCast C;C.Element=Element;C.Fire=FireballStats(-1,false);
    C.Fire.Radius*=T.RadiusMultiplier;
    if(Element==EArrowElement::Fire)
    {
        C.Fire.Radius*=1.f+InheritedFireSpecStat(TEXT("radiusPercent"))/100.f;
        if(const auto* Arrow=ColdSteelSkillTree::FindSpec(TEXT("elementalArrow"));Arrow&&Arrow->InheritNodes.Contains(FName(TEXT("ignite"))))
            if(const int32 Stacks=FMath::RoundToInt(SpecStat(TEXT("fireball"),TEXT("burnStacks")));Stacks>0)
            {
                const auto* Ignite=ColdSteelSkillTree::FindSpec(TEXT("fireball"))->Find(TEXT("ignite"));
                C.Fire.SpecBurnStacks=Stacks;C.Fire.SpecBurnMagicAttack=Derived(TEXT("matk"));
                C.Fire.SpecBurnSeconds=Ignite?Ignite->Param(TEXT("burnSeconds"),3.5f):3.5f;
                C.Fire.SpecBurnMultiplier=(Ignite?Ignite->Param(TEXT("burnMultiplier"),.5f):.5f)*Arrow->InheritScale;
            }
    }
    C.Radius=C.Fire.Radius;
    if(Element==EArrowElement::Fire){C.Fire.Damage=FMath::FloorToFloat(C.Fire.Damage*Multiplier);C.ManaCost=C.Fire.ManaCost;C.Cooldown=C.Fire.Cooldown;}
    else if(Element==EArrowElement::Ice)
    {
        C.Ice=IceSpikeStats();C.Ice.Damage=FMath::FloorToFloat(C.Ice.Damage*Multiplier);
        C.Ice.ChillDuration=T.ChillSeconds+SpecStat(TEXT("elementalArrow"),TEXT("chillSeconds"));C.Ice.ChillSlow=T.ChillSlow;C.Ice.bRefreshChillDuration=true;
        C.ManaCost=C.Ice.ManaCost;C.Cooldown=C.Ice.Cooldown;
    }
    else if(Element==EArrowElement::Lightning)
    {
        C.Lightning=LightningStats();C.Lightning.Damage=FMath::FloorToFloat(C.Lightning.Damage*Multiplier);
        C.Lightning.StunSeconds=T.StunSeconds+SpecStat(TEXT("elementalArrow"),TEXT("stunSeconds"));C.Lightning.StunExtensionSeconds=0;
        C.ManaCost=C.Lightning.ManaCost;C.Cooldown=C.Lightning.Cooldown;
    }
    C.ManaCost=ElementalArrowManaCost(C.ManaCost);
    return C;
}
float UColdSteelStatusModel::ElementalArrowManaCost(float SpellCost) const
{
    auto T=MasteryDefinition(TEXT("elementalArrow")).ElementalArrow;
    T.ManaCostMultiplier=FMath::Max(.1f,T.ManaCostMultiplier+SpecStat(TEXT("elementalArrow"),TEXT("manaMultiplier")));
    return ElementalArrow::ManaCost(T,SpellCost);
}
void UColdSteelStatusModel::StageElementalArrowTraining(FColdSteelProfile& P,int32 Hits,int32 Kills) const
{
    const auto& D=MasteryDefinition(TEXT("elementalArrow"));
    ColdSteelSkills::AddExperience(P,D,ColdSteelSpellRewards::HitTrainingExperience(D,Hits,Kills,Hits>=2));
}
float UColdSteelStatusModel::ElementalArrowCooldown(EArrowElement Element) const
{return Element==EArrowElement::Fire?FireballCooldown():Element==EArrowElement::Ice?IceSpikeCooldown():Element==EArrowElement::Lightning?LightningCooldown():0.f;}
float UColdSteelStatusModel::ElementalArrowCooldownDuration(EArrowElement Element) const
{return Element==EArrowElement::Fire?Current.FireballCooldownDuration:Element==EArrowElement::Ice?Current.IceSpikeCooldownDuration:Current.LightningCooldownDuration;}
bool UColdSteelStatusModel::CanPrepareElementalArrow(EArrowElement Element,FString& Reason) const
{
    if(!ActiveBow()){Reason=TEXT("需要装备弓");return false;}
    if(Current.bMagicArrowRainReserved){Reason=TEXT("请先取消魔法箭雨");return false;}
    if(MasteryProgress(TEXT("elementalArrow")).Level<1){Reason=TEXT("未学习元素箭");return false;}
    if(!ElementalArrow::IsElement(Element)||MasteryProgress(ElementalArrow::Spell(Element)).Level<1){Reason=TEXT("对应魔法未学习");return false;}
    if((Element==EArrowElement::Fire&&Current.bFireballReserved)||(Element==EArrowElement::Ice&&Current.bIceSpikeReserved))
    {Reason=TEXT("对应魔法正在使用");return false;}
    if(ElementalArrowCooldown(Element)>0.f){Reason=TEXT("对应魔法冷却中");return false;}
    if(!CanSpendMana(ElementalArrowManaCost(SpellManaCost(ElementalArrow::Spell(Element)))))
    {Reason=TEXT("魔法不足");return false;}
    return true;
}
void UColdSteelStatusModel::StageElementalArrowCost(FColdSteelProfile& P,const FElementalArrowCast& C,float BowStaminaCost) const
{
    if(BowStaminaCost>0){P.Stamina=FMath::Max(0.f,P.Stamina-BowStaminaCost);P.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;}
    if(!HasInfiniteMana())P.Mana-=C.ManaCost;
    const float Cooldown=HasNoAbilityCooldown()?0.f:C.Cooldown;
    if(C.Element==EArrowElement::Fire)P.FireballCooldown=P.FireballCooldownDuration=Cooldown;
    else if(C.Element==EArrowElement::Ice)P.IceSpikeCooldown=P.IceSpikeCooldownDuration=Cooldown;
    else if(C.Element==EArrowElement::Lightning)P.LightningCooldown=P.LightningCooldownDuration=Cooldown;
}
