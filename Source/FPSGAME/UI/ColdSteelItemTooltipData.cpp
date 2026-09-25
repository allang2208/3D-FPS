#include "ColdSteelItemTooltipData.h"
#include "../Combat/CombatItemFormula.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../Weapons/RuneSwordGuardTuning.h"
#include "../FPSGAMECharacter.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UObject/UnrealType.h"

namespace
{
using J=TSharedPtr<FJsonObject>;
J Object(const J& O,const TCHAR* Key){const J* V=nullptr;return O&&O->TryGetObjectField(Key,V)?*V:nullptr;}
FString String(const J& O,const TCHAR* Key,const FString& Default=TEXT("")){FString V;return O&&O->TryGetStringField(Key,V)?V:Default;}
double Number(const J& O,const TCHAR* Key,double Default=0){double V;return O&&O->TryGetNumberField(Key,V)?V:Default;}
FString N(double V){FString S=FString::Printf(TEXT("%.2f"),V);while(S.EndsWith(TEXT("0")))S.LeftChopInline(1);if(S.EndsWith(TEXT(".")))S.LeftChopInline(1);return S==TEXT("-0")?TEXT("0"):S;}
float Field(const UObject* O,const TCHAR* Key){const auto* P=FindFProperty<FFloatProperty>(O->GetClass(),Key);return P?P->GetPropertyValue_InContainer(O):0;}
FString Signed(double V,const TCHAR* Unit=TEXT("")){return (V>0?TEXT("+"):TEXT(""))+N(V)+Unit;}
FString Value(const TSharedPtr<FJsonValue>& V){if(!V)return TEXT("");if(V->Type==EJson::String)return V->AsString();if(V->Type==EJson::Number)return N(V->AsNumber());if(V->Type==EJson::Boolean)return V->AsBool()?TEXT("是"):TEXT("否");return TEXT("");}
void Row(FColdSteelTooltipCard& C,const FString& Label,const FString& Val,int32 Tone=0){if(!Val.IsEmpty())C.Rows.Add({Label,Val,Tone,false});}
void Section(FColdSteelTooltipCard& C,const FString& Label){C.Rows.Add({Label,TEXT(""),0,true});}
FString Category(const FString& K){static const TMap<FString,FString> M={{TEXT("weapon_ranged"),TEXT("远程武器")},{TEXT("weapon_melee"),TEXT("近战武器")},{TEXT("armor"),TEXT("防具")},{TEXT("accessory"),TEXT("饰品")},{TEXT("consumable"),TEXT("消耗品")},{TEXT("material"),TEXT("材料")},{TEXT("enhancement"),TEXT("强化材料")},{TEXT("tribute"),TEXT("贡品")},{TEXT("gold"),TEXT("金币")}};const auto* V=M.Find(K);return V?*V:K;}
void Delta(FColdSteelTooltipCard& C,const FString& Label,double V,const TCHAR* Unit,bool Lower=false){if(FMath::Abs(V)>.00001)Row(C,Label,Signed(V,Unit),(V>0)!=Lower?1:-1);}
J Reference(){static J Root;static bool Loaded=false;if(!Loaded){Loaded=true;FString Text;if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/tooltip-reference.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root);}return Root;}
}

FColdSteelTooltipContent BuildColdSteelItemTooltip(const FColdSteelItem& I,UColdSteelStatusModel* Model,UGunsmithSystem* G)
{
    FColdSteelTooltipContent Out;J O;
    O=CombatItemFormula::Read(I);if(!O)return Out;
    Out.Name=String(O,TEXT("name"),I.Definition);Out.Type=String(O,TEXT("type"),Category(String(O,TEXT("category"))));
    Out.Rarity=String(O,TEXT("rarity"),TEXT("common"));Out.Level=Number(O,TEXT("level"));Out.Icon=String(O,TEXT("ue_icon"));Out.Description=String(O,TEXT("desc"));
    const int32 Enhance=Number(O,TEXT("enhanceLevel"));if(Enhance>0)Out.Enhancement=FString::Printf(TEXT("已强化 +%d"),Enhance);
    auto Damage=[&](double Base){return ColdSteelWeaponStats::Damage(I,Model,Base);};

    const double InnateInt=Number(O,TEXT("innate_erosion_intelligence")),InnateWis=Number(O,TEXT("innate_erosion_wisdom"));
    if(InnateInt>0||InnateWis>0)
    {
        const double Multiplier=G?G->Calculate(I.Definition,G->Installed(I)).Melee.InnateErosionMultiplier:1.;
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("武器自带效果 · 侵蚀");C.MinimumWidth=460;
        Row(C,TEXT("常驻附加魔法伤害"),TEXT("智力×")+N(InnateInt*100)+TEXT("% + 精神×")+N(InnateWis*100)+TEXT("%"),1);
        if(Multiplier!=1)Row(C,TEXT("精神迸发后"),TEXT("智力×")+N(InnateInt*Multiplier*100)+TEXT("% + 精神×")+N(InnateWis*Multiplier*100)+TEXT("%"),1);
        Row(C,TEXT("结算"),TEXT("随连击、重击等攻击倍率放大，按魔法防御减免；更换其他符文仍保留自带侵蚀。"));
    }

    const J Enchant=Object(O,TEXT("_enchantData"));const J EE=Object(O,TEXT("_enchantEffects"));
    if(Enchant&&(Object(Enchant,TEXT("prefix"))||Object(Enchant,TEXT("suffix")))){
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("附魔效果");C.MinimumWidth=300;
        FString Name=String(Object(Enchant,TEXT("prefix")),TEXT("name"));
        const FString Suffix=String(Object(Enchant,TEXT("suffix")),TEXT("name"));if(!Suffix.IsEmpty()){if(!Name.IsEmpty())Name+=TEXT(" · ");Name+=Suffix;}
        Row(C,TEXT("当前词缀"),Name);
        if(EE){Delta(C,TEXT("攻击力"),Number(EE,TEXT("damagePercent"))*100,TEXT("%"));
            if(EE->HasField(TEXT("attackIntervalMul")))Row(C,TEXT("攻击间隔"),TEXT("×")+N(Number(EE,TEXT("attackIntervalMul"))),Number(EE,TEXT("attackIntervalMul"))<1?1:-1);
            Delta(C,TEXT("暴击率"),Number(EE,TEXT("critRate"))*100,TEXT("%"));Delta(C,TEXT("穿透目标"),Number(EE,TEXT("piercingBonus")),TEXT("个"));
            bool Poison=false;if(EE->TryGetBoolField(TEXT("poisonOnHit"),Poison)&&Poison)Row(C,TEXT("特殊效果"),TEXT("攻击叠加中毒"),1);}
    }
    const auto* Weapon=G?G->Weapon(I.Definition):nullptr;const FGunsmithParts Parts=G&&G->ModifiableWeapon(I.Definition)?G->Installed(I):FGunsmithParts();
    bool Installed=false;for(const auto& P:Parts)if(G->Option(I.Definition,P.Key,P.Value))Installed=true;
    const J Craft=Object(O,TEXT("_craftData")),CE=Object(O,TEXT("_craftEffects"));
    if(Installed||(Craft&&!Craft->Values.IsEmpty())){
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("改造项目");C.MinimumWidth=600;
        if(Installed){for(const auto& Slot:G->Slots(I.Definition))if(const auto* Id=Parts.Find(Slot))if(const auto* P=G->Option(I.Definition,Slot,*Id)){
                Section(C,P->Name);
                if(P->Effects.IsEmpty())Row(C,TEXT(""),P->Description);
                else for(const auto& E:P->Effects)Row(C,TEXT(""),E.Key,E.Value);
                C.Rows.Last().bDashedAfter=true;}
            const auto S=G->Calculate(I.Definition,Parts),B=G->Calculate(I.Definition,{});Section(C,TEXT("合计改造数值"));
            if(G->IsMelee(I.Definition))
            {
                Delta(C,TEXT("基础伤害"),(S.Melee.Damage-1)*100,TEXT("%"));
                Delta(C,TEXT("三连击第二段伤害"),(S.Melee.ComboSecond-1)*100,TEXT("%"));
                Delta(C,TEXT("三连击第三段伤害"),(S.Melee.ComboThird-1)*100,TEXT("%"));
                Delta(C,TEXT("魔法技能冷却时间"),(S.Melee.MagicCooldown-1)*100,TEXT("%"),true);
                Delta(C,TEXT("魔法伤害"),(S.Melee.MagicDamage-1)*100,TEXT("%"));
                Delta(C,TEXT("魔法值消耗"),(S.Melee.MagicCost-1)*100,TEXT("%"),true);
                Delta(C,TEXT("重击伤害倍率"),(S.Melee.HeavyDamage-1)*100,TEXT("%"));
                Delta(C,TEXT("重击伤害倍率加值"),S.Melee.HeavyDamageAdd,TEXT(""));
                Delta(C,TEXT("攻击造成击退"),(S.Melee.Knockback-1)*100,TEXT("%"));
                Delta(C,TEXT("快速近战伤害倍率加值"),S.Melee.QuickCombatDamageAdd,TEXT(""));
                Delta(C,TEXT("快速近战击退距离"),(S.Melee.QuickCombatKnockback-1)*100,TEXT("%"));
                Delta(C,TEXT("附加魔法伤害·智力系数"),S.Melee.RuneIntelligence*100,TEXT("%"));
                Delta(C,TEXT("附加魔法伤害·精神系数"),S.Melee.RuneWisdom*100,TEXT("%"));
                Delta(C,TEXT("自带侵蚀附加伤害"),(S.Melee.InnateErosionMultiplier-1)*100,TEXT("%"));
                Delta(C,TEXT("剑刃攻击魔法易伤"),S.Melee.RuneVulnerability*100,TEXT("%"));
                Delta(C,TEXT("命中减魔法CD(秒)"),S.Melee.CooldownReduceSecondsPerHit,TEXT("s"));
                Delta(C,TEXT("攻击速度"),(S.Melee.AttackSpeed-1)*100,TEXT("%"));
                Delta(C,TEXT("攻击范围"),(S.Melee.Range-1)*100,TEXT("%"));
                Delta(C,TEXT("耐力消耗"),(S.Melee.Stamina-1)*100,TEXT("%"),true);
                Delta(C,TEXT("造成硬直时间"),(S.Melee.HitReaction-1)*100,TEXT("%"));
                Delta(C,TEXT("韧性伤害"),(S.Melee.ToughnessDamage-1)*100,TEXT("%"));
                Delta(C,TEXT("物理防御穿透"),S.Melee.PhysicalArmorPenetration*100,TEXT("%"));
                Delta(C,TEXT("格挡减伤"),(S.Melee.BlockReduction-1)*100,TEXT("%"));
                Delta(C,TEXT("弹反判定时间"),(S.Melee.ParryWindow-1)*100,TEXT("%"));
                if(S.Melee.ClovenSeconds>0)
                {
                    Row(C,TEXT("成功弹反"),TEXT("承锋·瞬重斩 · ")+N(S.Melee.ClovenSeconds)+TEXT(" s"),1);
                    Delta(C,TEXT("承锋重击物理伤害"),(S.Melee.ClovenPhysical-1)*100,TEXT("%"));
                    Delta(C,TEXT("承锋重击韧性伤害"),(S.Melee.ClovenToughness-1)*100,TEXT("%"));
                }
            }
            else {
            Delta(C,TEXT("伤害"),S.Damage-B.Damage,TEXT(""));Delta(C,TEXT("弹匣容量"),S.Capacity-B.Capacity,TEXT("发"));
            Delta(C,TEXT("瞄准耗时"),(S.ADS-B.ADS)*1000,TEXT("ms"),true);Delta(C,TEXT("射击间隔"),(S.Interval-B.Interval)*1000,TEXT("ms"),true);
            Delta(C,TEXT("普通换弹"),(S.Reload-B.Reload)*1000,TEXT("ms"),true);Delta(C,TEXT("空仓换弹"),(S.EmptyReload-B.EmptyReload)*1000,TEXT("ms"),true);
            Delta(C,TEXT("后坐力指数"),S.Recoil-B.Recoil,TEXT(""),true);Delta(C,TEXT("枪械稳定性"),S.Handling.Stability-B.Handling.Stability,TEXT("分"));
            Delta(C,TEXT("枪械稳定性·回稳90%"),S.Handling.ADSRecoveryMilliseconds()-B.Handling.ADSRecoveryMilliseconds(),TEXT("ms"),true);
            if(B.Spread>0)Delta(C,TEXT("腰射散布"),(S.Spread/B.Spread-1)*100,TEXT("%"),true);
            Delta(C,TEXT("射程"),S.Range-B.Range,TEXT("m"));Delta(C,TEXT("弹速"),S.Speed-B.Speed,TEXT("m/s"));}}
        if(Craft){const auto Config=Object(Object(Reference(),TEXT("craft")),*I.Definition);const auto Options=Object(Config,TEXT("options"));
            for(const auto& P:Craft->Values){const TArray<TSharedPtr<FJsonValue>>* List=nullptr;if(!Options||!Options->TryGetArrayField(FString(*P.Key),List))continue;
                for(const auto& V:*List){const auto Option=V->AsObject();if(String(Option,TEXT("id"))==Value(P.Value)){Section(C,String(Option,TEXT("name")));Row(C,TEXT(""),String(Option,TEXT("desc")));C.Rows.Last().bDashedAfter=true;break;}}}}
        if(CE&&!CE->Values.IsEmpty()){
            Section(C,TEXT("合计改造数值"));
            struct FEffect{const TCHAR* Key;const TCHAR* Label;const TCHAR* Unit;double Scale;bool Lower;};
            const FEffect Effects[]={{TEXT("damagePercent"),TEXT("伤害"),TEXT("%"),100,false},{TEXT("piercingBonus"),TEXT("穿透目标"),TEXT("个"),1,false},{TEXT("critChancePercent"),TEXT("暴击率"),TEXT("%"),100,false},{TEXT("rangeDelta"),TEXT("攻击距离"),TEXT("px"),1,false},{TEXT("projectileSpeedPercent"),TEXT("弹速"),TEXT("%"),100,false},{TEXT("moveSpeedPercent"),TEXT("移速"),TEXT("%"),100,false},{TEXT("attackIntervalDelta"),TEXT("攻击间隔"),TEXT("ms"),1,true},{TEXT("magazineDelta"),TEXT("弹容量"),TEXT("发"),1,false},{TEXT("magazinePercent"),TEXT("弹容量"),TEXT("%"),100,false},{TEXT("reloadTimeDelta"),TEXT("换弹耗时"),TEXT("ms"),1,true},{TEXT("maxSpreadAngleDelta"),TEXT("最大散布"),TEXT("°"),1,true},{TEXT("defensePercent"),TEXT("防御"),TEXT("%"),100,false},{TEXT("staminaCostDelta"),TEXT("体力消耗"),TEXT(""),1,true},{TEXT("knockbackDelta"),TEXT("击退距离"),TEXT("px"),1,false}};
            for(const auto& E:Effects)Delta(C,E.Label,Number(CE,E.Key)*E.Scale,E.Unit,E.Lower);
        }
    }
    auto& Main=Out.Cards.AddDefaulted_GetRef();Main.MinimumWidth=460;
    const TArray<TSharedPtr<FJsonValue>>* Stats=nullptr;
    FGunsmithStats S;if(Weapon)S=G->Calculate(I.Definition,Parts);
    if(O->TryGetArrayField(TEXT("stats"),Stats))for(const auto& V:*Stats){const auto St=V->AsObject();const FString Label=String(St,TEXT("name"),String(St,TEXT("label")));FString Val=St->HasField(TEXT("value"))?Value(St->Values[TEXT("value")]):TEXT("");
        if((Weapon||ColdSteelInventory::IsTwoHandedSword(I))&&Label==TEXT("物理攻击"))continue;
        if(Weapon&&Label==TEXT("弹匣容量"))continue;
        if(!Weapon&&I.Definition==TEXT("ue_m4a1")&&Label==TEXT("物理攻击"))Val=N(Damage(Field(GetDefault<AFPSGAMECharacter>(),TEXT("DamagePerShot"))));
        bool Positive=false;St->TryGetBoolField(TEXT("pos"),Positive);if(!Label.IsEmpty())Row(Main,Label,Val,Positive?1:0);}
    Section(Main,TEXT("物品信息"));Row(Main,TEXT("分类"),Category(String(O,TEXT("category"))));
    Row(Main,TEXT("武器类型"),String(O,TEXT("weaponTypeTag"),String(O,TEXT("weaponType"))));Row(Main,TEXT("装备槽位"),String(O,TEXT("equipSlot")));
    const FString Cat=String(O,TEXT("category"));const J Attack=Object(O,TEXT("attack")),Defense=Object(O,TEXT("defense"));
    if(ColdSteelInventory::IsTwoHandedSword(I)){
        Section(Main,TEXT("近战参数"));AppendColdSteelTooltipAttackFormula(I,Model,Number(O,TEXT("melee_damage"),55),Main);
        const auto Melee=ColdSteelMelee::Evaluate(I,Model);
        Row(Main,TEXT("普通攻击总伤害"),N(Melee.Damage));
        Row(Main,TEXT("快速近战伤害倍率"),N(Melee.QuickCombat.DamageMultiplier)+TEXT("×"));
        Row(Main,TEXT("快速近战伤害"),N(Melee.QuickCombat.Damage));
        Row(Main,TEXT("快速近战击退距离"),N(Melee.QuickCombat.KnockbackCM)+TEXT(" cm"));
        Row(Main,TEXT("基础物理伤害"),N(Melee.DamageParts.BasePhysical));
        if(Melee.DamageParts.AddedPhysical>0)Row(Main,TEXT("附加物理伤害"),N(Melee.DamageParts.AddedPhysical));
        if(Melee.DamageParts.AddedMagic>0)Row(Main,TEXT("附加魔法伤害"),N(Melee.DamageParts.AddedMagic));
        Row(Main,TEXT("结算方式"),TEXT("基础与附加共同乘攻击方式倍率，再按物理/魔法防御分别减免"));
        Row(Main,TEXT("三连击第二段伤害"),N(Melee.ComboSecondDamage));
        Row(Main,TEXT("三连击第三段伤害"),N(Melee.ComboThirdDamage));
        if(Melee.Modifiers.MagicCooldown!=1)Row(Main,TEXT("魔法技能冷却倍率"),N(Melee.Modifiers.MagicCooldown)+TEXT("×"));
        if(Melee.Modifiers.MagicDamage!=1)Row(Main,TEXT("魔法伤害倍率"),N(Melee.Modifiers.MagicDamage)+TEXT("×"));
        if(Melee.Modifiers.CooldownReduceSecondsPerHit>0)Row(Main,TEXT("近战命中额外减少魔法冷却"),N(.5f+Melee.Modifiers.CooldownReduceSecondsPerHit)+TEXT(" s / 挥"));
        if(Melee.Modifiers.RuneVulnerability>0)Row(Main,TEXT("剑刃攻击命中魔法易伤"),N(Melee.Modifiers.RuneVulnerability*100)+TEXT("% · ")+N(Melee.Modifiers.RuneVulnerabilitySeconds)+TEXT(" s"));
        Row(Main,TEXT("攻击间隔"),N(Melee.AttackSeconds)+TEXT(" s"));
        Row(Main,TEXT("突刺时间"),N(Melee.ThrustSeconds)+TEXT(" s"));
        Row(Main,TEXT("最大攻击距离"),N(Melee.ThrustReach/100)+TEXT(" m"));
        Row(Main,TEXT("普通挥砍距离"),N(Melee.SlashReach/100)+TEXT(" m"));
        Row(Main,TEXT("攻击耐力消耗（含重击）"),N(Melee.AttackStamina));
        Row(Main,TEXT("命中硬直时间倍率"),N(Melee.Modifiers.HitReaction)+TEXT("×"));
        if(!FMath::IsNearlyEqual(Melee.Modifiers.ToughnessDamage,1.))Row(Main,TEXT("韧性伤害倍率"),N(Melee.Modifiers.ToughnessDamage)+TEXT("×"));
        if(Melee.Modifiers.PhysicalArmorPenetration>0)Row(Main,TEXT("改造物理防御穿透"),N(Melee.Modifiers.PhysicalArmorPenetration*100)+TEXT("%"));
        Row(Main,TEXT("格挡伤害减免"),N(Melee.BlockReduction*100)+TEXT("%"));
        Row(Main,TEXT("弹反判定时间"),N(Melee.ParrySeconds)+TEXT(" s"));
        if(Melee.Modifiers.RiposteSeconds>0)Row(Main,TEXT("成功弹反"),TEXT("反击激励 · ")+N(Melee.Modifiers.RiposteSeconds)+TEXT(" s"));
        if(Melee.Modifiers.ClovenSeconds>0)
        {
            Row(Main,TEXT("成功弹反"),TEXT("下次普攻瞬发重击 · ")+N(Melee.Modifiers.ClovenSeconds)+TEXT(" s"));
            Row(Main,TEXT("承锋重击物理伤害"),TEXT("+")+N((Melee.Modifiers.ClovenPhysical-1)*100)+TEXT("%"));
            Row(Main,TEXT("承锋重击韧性伤害"),TEXT("+")+N((Melee.Modifiers.ClovenToughness-1)*100)+TEXT("%"));
        }
        Row(Main,TEXT("防御受击耐力消耗"),N(Melee.BlockStamina));
        Row(Main,TEXT("握持"),TEXT("双手 · 占用副手槽"));
    }else if(ColdSteelInventory::IsEquippedProductionTool(I)){
        const bool bPickaxe=I.Definition==TEXT("tool_pickaxe");
        // Same 近战参数 layout as the swords: formula, then total/base/added damage, then
        // interval, stamina, reach and grip; tool-only harvest numbers move to their own section.
        Section(Main,TEXT("近战参数"));
        const double Base=Number(O,TEXT("melee_damage"),bPickaxe?10:12);
        const auto DamageParts=ColdSteelWeaponStats::DamageParts(I,Model,Base);
        AppendColdSteelTooltipAttackFormula(I,Model,Base,Main);
        Row(Main,TEXT("普通攻击总伤害"),N(DamageParts.Total()));
        Row(Main,TEXT("基础物理伤害"),N(DamageParts.BasePhysical));
        if(DamageParts.AddedPhysical>0)Row(Main,TEXT("附加物理伤害"),N(DamageParts.AddedPhysical));
        if(DamageParts.AddedMagic>0)Row(Main,TEXT("附加魔法伤害"),N(DamageParts.AddedMagic));
        Row(Main,TEXT("攻击间隔"),N(Number(O,TEXT("swing_seconds"),1.1))+TEXT(" s"));
        Row(Main,TEXT("最大攻击距离"),N(Number(O,TEXT("combat_reach_cm"),180)/100)+TEXT(" m"));
        Row(Main,TEXT("攻击耐力消耗"),N(Model?double(Model->StaminaSettings().HarvestCost):10.));
        Row(Main,TEXT("握持"),TEXT("双手 · 占用同组主手与副手槽"));
        Section(Main,TEXT("采集参数"));
        Row(Main,TEXT("装备方式"),TEXT("背包右键 / 拖入主手武器槽；G / 滚轮切换"));
        Row(Main,bPickaxe?TEXT("采矿距离"):TEXT("伐木距离"),N(Number(O,TEXT("harvest_reach_cm"),320)/100)+TEXT(" m"));
        if(!bPickaxe)Row(Main,TEXT("伐木命中宽容半径"),N(Number(O,TEXT("harvest_sweep_radius_cm"),32))+TEXT(" cm"));
        Row(Main,TEXT("采集规则"),bPickaxe?TEXT("三次有效命中开采；伤害属性不改变采矿所需次数"):TEXT("三次有效命中砍倒；伤害属性不改变伐木所需次数"));
    }else if(ColdSteelInventory::IsBow(I)){
        Section(Main,TEXT("弓箭参数"));
        const auto BowDamage=ColdSteelWeaponStats::DamageParts(I,Model,Number(O,TEXT("full_damage"),46));
        Row(Main,TEXT("满拉武器伤害"),N(BowDamage.Total()));
        Row(Main,TEXT("基础物理伤害"),N(BowDamage.BasePhysical));
        if(BowDamage.AddedPhysical>0)Row(Main,TEXT("附加物理伤害"),N(BowDamage.AddedPhysical));
        if(BowDamage.AddedMagic>0)Row(Main,TEXT("附加魔法伤害"),N(BowDamage.AddedMagic));
        Row(Main,TEXT("拉满耗时"),N(FMath::Max(.3,ColdSteelWeaponStats::Interval(&I,Model,Number(O,TEXT("draw_seconds"),1.4))))+TEXT(" s"));
        Row(Main,TEXT("搭箭耗时"),N(Number(O,TEXT("nock_seconds"),.68))+TEXT(" s"));
        Row(Main,TEXT("满拉箭速"),N(Number(O,TEXT("full_speed_cm"),9800)/100)+TEXT(" m/s"));
        Row(Main,TEXT("最大飞行距离"),N(Number(O,TEXT("range_cm"),3200)/100)+TEXT(" m"));
        Row(Main,TEXT("满拉体力消耗"),N(Number(O,TEXT("stamina_cost"),3)));
        if(Model){Row(Main,TEXT("箭种"),Model->AmmoLabel(Model->AmmoDefinitionFor(I)));Row(Main,TEXT("箭种效果"),Model->AmmoEffectSummary(Model->AmmoDefinitionFor(I)));}
        Row(Main,TEXT("操作"),TEXT("左键按住搭箭、拉开，松开出箭；右键稳持；R 搭箭"));
        Row(Main,TEXT("握持"),TEXT("双手 · 占用副手槽"));
    }else if(Weapon){Section(Main,TEXT("枪械参数"));AppendColdSteelTooltipAttackFormula(I,Model,S.Damage,Main);
        const auto DamageParts=ColdSteelWeaponStats::DamageParts(I,Model,S.Damage);
        Row(Main,TEXT("武器总伤害"),N(DamageParts.Total()));
        if(DamageParts.Additional()>0)Row(Main,TEXT("基础物理伤害"),N(DamageParts.BasePhysical));
        if(DamageParts.AddedPhysical>0)Row(Main,TEXT("附加物理伤害"),N(DamageParts.AddedPhysical));
        if(DamageParts.AddedMagic>0)Row(Main,TEXT("附加魔法伤害"),N(DamageParts.AddedMagic));
        Row(Main,TEXT("子弹数"),FString::Printf(TEXT("%d / %d 发"),I.Magazine,S.Capacity));Row(Main,TEXT("弹药"),Model?Model->AmmoLabel(Model->AmmoDefinitionFor(I)):ColdSteelWeaponStats::AmmoName(Weapon->Ammo));
        if(Model)
        {
            Row(Main,TEXT("弹种效果"),Model->AmmoEffectSummary(Model->AmmoDefinitionFor(I)));
            Row(Main,TEXT("装填后射击伤害"),N(DamageParts.Total()*Model->AmmoDamageMultiplier(I)));
        }
        Row(Main,S.BurstCount>1?TEXT("组内射击间隔"):TEXT("攻击间隔"),N(FMath::RoundToInt(ColdSteelWeaponStats::Interval(&I,Model,S.Interval)*1000))+TEXT(" ms"));
        const double FireInterval=ColdSteelWeaponStats::Interval(&I,Model,S.Interval);
        Row(Main,S.BurstCount>1?TEXT("组内理论射速"):TEXT("理论射速"),FireInterval>0?N(60./FireInterval)+TEXT(" 发/分"):TEXT("—"));
        if(S.BurstCount>1)
        {
            const double BurstDelay=ColdSteelWeaponStats::Interval(&I,Model,S.BurstDelay);
            const double Cycle=(S.BurstCount-1)*FireInterval+FMath::Max(FireInterval,BurstDelay);
            Row(Main,TEXT("开火模式"),FString::Printf(TEXT("%d 连发 · 每组重新扣动扳机"),S.BurstCount));
            Row(Main,TEXT("连发组末发后间隔"),N(FMath::RoundToInt(BurstDelay*1000))+TEXT(" ms"));
            Row(Main,TEXT("含组间隔理论射速"),N(60.*S.BurstCount/Cycle)+TEXT(" 发/分"));
        }
        Row(Main,TEXT("正常换弹"),N(ColdSteelWeaponStats::Reload(&I,Model,S.Reload))+TEXT(" s"));Row(Main,TEXT("空仓换弹"),N(ColdSteelWeaponStats::Reload(&I,Model,S.EmptyReload))+TEXT(" s"));
        Row(Main,TEXT("瞄准耗时"),N(FMath::RoundToInt(S.ADS*1000))+TEXT("ms"));Row(Main,TEXT("后坐力（越低越好）"),N(S.Recoil));Row(Main,TEXT("枪械稳定性（越高越好）"),N(S.Handling.Stability)+TEXT(" /100"));
        Row(Main,TEXT("首发上跳"),FString::Printf(TEXT("%.3f°"),S.Handling.FirstShotDegrees()));
        Row(Main,TEXT("连射上跳/发"),FString::Printf(TEXT("%.3f°"),S.Handling.MaxVerticalDegrees()));
        Row(Main,TEXT("ADS首发水平/发"),FString::Printf(TEXT("%.3f°"),S.Handling.FirstHorizontalDegrees()));
        Row(Main,TEXT("ADS水平上限/发"),FString::Printf(TEXT("%.3f°"),S.Handling.MaxHorizontalDegrees()));
        Row(Main,TEXT("枪械稳定性·回稳90%"),N(FMath::RoundToInt(S.Handling.ADSRecoveryMilliseconds()))+TEXT("ms"));
        Row(Main,TEXT("有效射程"),N(S.Range)+TEXT(" m"));
        Row(Main,TEXT("子弹速度"),S.Speed<=0?TEXT("即时命中"):N(S.Speed)+TEXT("m/s"));
        Row(Main,TEXT("腰射散布倍率"),N(S.Spread)+TEXT("×"));
    }else if(I.Definition==TEXT("ue_m4a1")){
        Section(Main,TEXT("枪械参数"));const auto* D=GetDefault<AFPSGAMECharacter>();
        Row(Main,TEXT("当前伤害"),N(Damage(S.Damage)));Row(Main,TEXT("子弹数"),FString::Printf(TEXT("%d / %d 发"),I.Magazine,D->GetMagazineCapacity()));
        Row(Main,TEXT("攻击间隔"),N(FMath::RoundToInt(ColdSteelWeaponStats::Interval(&I,Model,S.Interval)*1000))+TEXT(" ms"));
        Row(Main,TEXT("普通换弹"),N(ColdSteelWeaponStats::Reload(&I,Model,Field(D,TEXT("ReloadDuration"))))+TEXT(" s"));Row(Main,TEXT("空仓换弹"),N(ColdSteelWeaponStats::Reload(&I,Model,Field(D,TEXT("EmptyReloadDuration"))))+TEXT(" s"));Row(Main,TEXT("瞄准耗时"),N(FMath::RoundToInt(Field(D,TEXT("ADSInDuration"))*1000))+TEXT("ms"));
    }else if(Attack){Section(Main,TEXT("攻击参数"));
        const struct{const TCHAR* Key;const TCHAR* Label;const TCHAR* Unit;} Fields[]={{TEXT("range"),TEXT("攻击距离"),TEXT("px")},{TEXT("bulletSpeed"),TEXT("子弹速度"),TEXT("px/s")},{TEXT("projectileSpeed"),TEXT("投射速度"),TEXT("px/s")},{TEXT("attackInterval"),TEXT("攻击间隔"),TEXT("ms")},{TEXT("knockback"),TEXT("击退距离"),TEXT("px")}};
        for(const auto& F:Fields)if(Attack->HasField(F.Key))Row(Main,F.Label,N(Number(Attack,F.Key))+F.Unit);Row(Main,TEXT("伤害类型"),String(Attack,TEXT("damageType")));Row(Main,TEXT("命中类型"),String(Attack,TEXT("hitType")));
        const auto Ammo=Object(O,TEXT("ammoConfig"));if(Ammo){Section(Main,TEXT("枪械参数"));if(Ammo->HasField(TEXT("max")))Row(Main,TEXT("子弹数"),Value(Ammo->Values[TEXT("max")])+TEXT("发"));if(Ammo->HasField(TEXT("reloadTime")))Row(Main,TEXT("换弹时间"),N(Number(Ammo,TEXT("reloadTime")))+TEXT("ms"));}}
    if(Defense){Section(Main,TEXT("防御参数"));const double Base=Number(Defense,TEXT("base")),Per=Number(Defense,TEXT("perEnhance"));const auto* E=Model?Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;Row(Main,TEXT("防御力"),N(E?E->Defense(I):Base+Enhance*Per));Row(Main,TEXT("防御基础"),N(Base));Row(Main,TEXT("每级强化防御"),N(Per));
        if(Defense->HasField(TEXT("damageReduction")))Row(Main,TEXT("防御减伤"),N(Number(Defense,TEXT("damageReduction"))*100)+TEXT("%"));if(Defense->HasField(TEXT("staminaCost")))Row(Main,TEXT("防御受击体力"),N(Number(Defense,TEXT("staminaCost"))));}
    const J Bonuses=Object(O,TEXT("bonusStats"));if(Bonuses&&!Bonuses->Values.IsEmpty()){
        Section(Main,TEXT("属性加成"));const TMap<FString,FString> Names={{TEXT("str"),TEXT("力量")},{TEXT("dex"),TEXT("敏捷")},{TEXT("int"),TEXT("智力")},{TEXT("con"),TEXT("体质")},{TEXT("wis"),TEXT("精神")},{TEXT("luck"),TEXT("幸运")},{TEXT("atk"),TEXT("物理攻击")},{TEXT("matk"),TEXT("魔法攻击")},{TEXT("crit"),TEXT("暴击率")},{TEXT("maxHp"),TEXT("最大生命")},{TEXT("maxMp"),TEXT("最大魔法")}};
        for(const auto& P:Bonuses->Values){FString Key(*P.Key);if(const auto* Label=Names.Find(Key))Delta(Main,*Label,P.Value->AsNumber(),Key==TEXT("crit")?TEXT("%"):TEXT(""));}}
    if(O->HasField(TEXT("armorSet"))){Section(Main,TEXT("套装效果"));FString Bonus=String(O,TEXT("setBonusDesc"));if(Bonus.IsEmpty())Bonus=String(Object(O,TEXT("setBonuses")),*String(O,TEXT("armorSet")));Row(Main,TEXT("效果"),Bonus);}
    if(auto Special=Object(O,TEXT("specialAttack"))){Section(Main,TEXT("特殊攻击"));Row(Main,TEXT("伤害类型"),String(Special,TEXT("damageType")));Row(Main,TEXT("伤害公式"),String(Special,TEXT("damageFormula")));for(const auto& F:TArray<TPair<FString,FString>>{{TEXT("duration"),TEXT("持续时间")},{TEXT("cooldown"),TEXT("冷却时间")}})if(Special->HasField(F.Key))Row(Main,F.Value,N(Number(Special,*F.Key))+TEXT("秒"));}
    if(Cat==TEXT("consumable")){const auto Effect=Object(O,TEXT("useEffect"));if(Effect&&!Effect->Values.IsEmpty()){
        Section(Main,TEXT("使用效果"));if(Effect->HasField(TEXT("hp")))Row(Main,TEXT("恢复生命"),Signed(Number(Effect,TEXT("hp"))),1);if(Effect->HasField(TEXT("mp")))Row(Main,TEXT("恢复魔法"),Signed(Number(Effect,TEXT("mp"))),1);
        if(Effect->HasField(TEXT("maxHpPercent")))Row(Main,TEXT("恢复最大生命"),Signed(Number(Effect,TEXT("maxHpPercent")),TEXT("%")),1);if(Effect->HasField(TEXT("maxMpPercent")))Row(Main,TEXT("恢复最大魔法"),Signed(Number(Effect,TEXT("maxMpPercent")),TEXT("%")),1);}
        if(Number(O,TEXT("useCooldown"))>0)Row(Main,TEXT("冷却时间"),N(Number(O,TEXT("useCooldown")))+TEXT("秒"));Row(Main,TEXT("使用方式"),TEXT("双击 / Enter / 拖入快捷栏"));}
    if(I.Count>1)Row(Main,TEXT("堆叠数量"),FString::Printf(TEXT("%lld / %lld"),I.Count,I.StackMax));
    if(I.Place==4)Row(Main,TEXT("取出方式"),TEXT("右键 / 双击 / Enter / 拖入背包"));
    // 武器特殊性质取自枪匠目录，而不是物品实例快照：目录每次读盘解析，
    // 所以新增或修改 traits 不必走存档迁移就能生效（文案 desc 则需要迁移）。
    // 用 ModifiableWeapon 而不是 Weapon：后者只覆盖枪械，近战在 MeleeWeapons 里。
    if(const auto* Definition=G?G->ModifiableWeapon(I.Definition):nullptr)
    {
        if(Definition->Source.IsValid())
        {
            const TArray<TSharedPtr<FJsonValue>>* List=nullptr;
            if(Definition->Source->TryGetArrayField(TEXT("traits"),List)&&List)
            {
                for(const auto& Entry:*List)
                {
                    const J Trait=Entry->AsObject();
                    if(!Trait)continue;
                    FColdSteelTooltipTrait TraitRow;
                    TraitRow.Icon=String(Trait,TEXT("icon"),TEXT("neutral"));
                    TraitRow.Text=String(Trait,TEXT("text"));
                    if(!TraitRow.Text.IsEmpty())Out.Traits.Add(MoveTemp(TraitRow));
                }
            }
        }
    }
    CompleteColdSteelTooltipSummary(I,Model,G,Out);
    return Out;
}
