// Integration reference only: preserve shared host declarations and prerequisites.

// Source line 118
FQuickCombatCast UColdSteelStatusModel::QuickCombatStats(int32 AtLevel,const FMeleeModifiers* PreviewModifiers,const FColdSteelItem* PreviewWeapon) const
{
    // The conical seat substitutes current weapon physical damage for strength
    // in the same skill formula; level growth and action bonuses remain shared.
    const auto& T=QuickCombatSkill.QuickCombat;
    const int32 L=FMath::Clamp(AtLevel<0?QuickCombatProgress().Level:AtLevel,1,QuickCombatSkill.MaxLevel);
    const float Strength=float(Attribute(TEXT("str")));
    const auto Mods=PreviewModifiers?*PreviewModifiers:ColdSteelMelee::QuickCombatModifiers(this);
    FQuickCombatCast C;
    C.DamageMultiplier=float((1.+Mods.QuickCombatDamageAdd)*Mods.AllAttackDamage*Mods.MartialDamage);
    const auto* QuickItem=PreviewWeapon?PreviewWeapon:ActiveProductionTool()?ActiveProductionTool():Equipped();
    float DamageInput=Strength;
    if(Mods.bQuickCombatUsesWeaponDamage&&QuickItem&&ColdSteelInventory::IsTwoHandedBlunt(*QuickItem))
    {
        auto WeaponMods=Mods;
        // All-attack damage is applied once, outside the complete quick formula.
        WeaponMods.AllAttackDamage=1.;
        const auto Weapon=ColdSteelTool::Evaluate(*QuickItem,this,nullptr,&WeaponMods);
        DamageInput=float(Weapon.Damage.BasePhysical+Weapon.Damage.AddedPhysical);
    }
    C.Damage=(T.DamageBase+T.DamagePerLevel*L+DamageInput*(T.StrengthFactorBase+T.StrengthFactorPerLevel*L))*C.DamageMultiplier;
    if(QuickItem&&(ColdSteelInventory::IsDualPistol(*QuickItem)||ColdSteelStaff::IsStaff(*QuickItem)))QuickItem=ColdSteelMelee::PairedOneHandedWeapon(QuickItem,this);
    C.Damage*=UKukriBerserkerComponent::DamageMultiplier(QuickItem,this);
    C.KnockbackCM=T.KnockbackCM*float(Mods.QuickCombatKnockback*Mods.AllAttackKnockback);
    C.ToughnessMultiplier=float(Mods.QuickCombatToughnessMultiplier());
    C.BleedChance=FMath::Clamp(float(Mods.QuickCombatBleedChance),0.f,1.f);
    C.bAreaHit=Mods.bQuickCombatAOE;
    C.RangeCM=T.RangeCM*Mods.MartialRange*Mods.QuickCombatRange;
    C.StaminaCost=QuickCombatStaminaCost(L,&Mods);
    return C;
}
