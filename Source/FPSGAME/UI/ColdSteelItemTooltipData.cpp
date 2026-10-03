#include "ColdSteelItemTooltipData.h"
#include "ColdSteelWeaponText.h"
#include "../Combat/CombatItemFormula.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../Weapons/RuneSwordGuardTuning.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionToolEnhance.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionTreeHealth.h"
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
FString Signed(double V,const TCHAR* Unit=TEXT("")){return (V>0?TEXT("+"):TEXT(""))+N(V)+Unit;}
FString Value(const TSharedPtr<FJsonValue>& V){if(!V)return TEXT("");if(V->Type==EJson::String)return V->AsString();if(V->Type==EJson::Number)return N(V->AsNumber());if(V->Type==EJson::Boolean)return V->AsBool()?TEXT("是"):TEXT("否");return TEXT("");}
void Row(FColdSteelTooltipCard& C,const FString& Label,const FString& Val,int32 Tone=0){if(!Val.IsEmpty())C.Rows.Add({Label,Val,Tone,false});}
void DamageRows(FColdSteelTooltipCard& C,const FWeaponDamageParts& D)
{
    Row(C,ColdSteelWeaponText::TotalDamage,N(D.Total()));
    Row(C,ColdSteelWeaponText::BasePhysical,N(D.BasePhysical));
    if(D.AddedPhysical>0)Row(C,ColdSteelWeaponText::AddedPhysical,N(D.AddedPhysical));
    if(D.AddedMagic>0)Row(C,ColdSteelWeaponText::AddedMagic,N(D.AddedMagic));
}
void Section(FColdSteelTooltipCard& C,const FString& Label){C.Rows.Add({Label,TEXT(""),0,true});}
FString Category(const FString& K){static const TMap<FString,FString> M={{TEXT("weapon_ranged"),TEXT("远程武器")},{TEXT("weapon_bow"),TEXT("远程武器")},{TEXT("weapon_melee"),TEXT("近战武器")},{TEXT("weapon_magic"),TEXT("魔法武器")},{TEXT("weapon"),TEXT("武器")},{TEXT("tool"),TEXT("生产工具")},{TEXT("armor"),TEXT("防具")},{TEXT("accessory"),TEXT("饰品")},{TEXT("consumable"),TEXT("消耗品")},{TEXT("material"),TEXT("材料")},{TEXT("enhancement"),TEXT("强化材料")},{TEXT("tribute"),TEXT("贡品")},{TEXT("gold"),TEXT("金币")}};const auto* V=M.Find(K);return V?*V:K;}
FString EquipSlotLabel(const FString& K){static const TMap<FString,FString> M={{TEXT("weapon"),TEXT("武器槽")},{TEXT("armor"),TEXT("防具槽")},{TEXT("gloves"),TEXT("手套槽")}};const auto* V=M.Find(K);return V?*V:K;}
void Delta(FColdSteelTooltipCard& C,const FString& Label,double V,const TCHAR* Unit,bool Lower=false){if(FMath::Abs(V)>.00001)Row(C,Label,Signed(V,Unit),(V>0)!=Lower?1:-1);}
// 附魔只存攻击间隔倍率；玩家口径用射速倍率表达，1/3 与 2 倍都读得懂。
FString RateMultiplier(double IntervalMultiplier){return IntervalMultiplier>1.?FString::Printf(TEXT("1/%s"),*N(IntervalMultiplier)):N(1./IntervalMultiplier);}
J Reference(){static J Root;static bool Loaded=false;if(!Loaded){Loaded=true;FString Text;if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/tooltip-reference.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root);}return Root;}
}

FColdSteelTooltipContent BuildColdSteelItemTooltip(const FColdSteelItem& I,UColdSteelStatusModel* Model,UGunsmithSystem* G)
{
    FColdSteelTooltipContent Out;TArray<FColdSteelTooltipRow> ForgeSummary;J O;
    O=CombatItemFormula::Read(I);if(!O)return Out;
    Out.Name=String(O,TEXT("name"),I.Definition);Out.Type=String(O,TEXT("type"),Category(String(O,TEXT("category"))));
    if(ColdSteelInventory::IsBow(I))Out.Type=String(O,TEXT("weaponTypeTag"),TEXT("弓"));
    Out.Rarity=String(O,TEXT("rarity"),TEXT("common"));Out.Level=Number(O,TEXT("level"));Out.Icon=String(O,TEXT("ue_icon"));Out.Description=String(O,TEXT("desc"));
    const int32 Enhance=Number(O,TEXT("enhanceLevel"));if(Enhance>0)Out.Enhancement=FString::Printf(TEXT("已强化 +%d"),Enhance);
    // 采集工具的「强化」是外观档位（独立字段 tool_enhance_level），与武器「已强化 +N」
    // 同一位置口径但不同措辞：这里写档位与材质名，不进武器的数值语义。铁铲无目录等级。
    // 只有斧／镐认这个字段（IsEquippedProductionTool），其余物品不显示这一行。
    if(ColdSteelInventory::IsEquippedProductionTool(I))
    {
        const int32 ToolLevel=ColdSteelToolEnhance::Level(I);
        const FString MaterialName=ColdSteelToolEnhance::LevelName(ToolLevel);
        Out.Enhancement=FString::Printf(TEXT("强化 Lv.%d"),ToolLevel)+(MaterialName.IsEmpty()?FString():TEXT(" · ")+MaterialName);
    }

    const double InnateInt=Number(O,TEXT("innate_erosion_intelligence")),InnateWis=Number(O,TEXT("innate_erosion_wisdom"));
    if(InnateInt>0||InnateWis>0)
    {
        const double Multiplier=G?G->Calculate(I.Definition,G->Installed(I)).Melee.InnateErosionMultiplier:1.;
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("武器自带效果 · 侵蚀");C.MinimumWidth=460;
        Row(C,TEXT("常驻附加魔法伤害"),TEXT("智力×")+N(InnateInt*100)+TEXT("% + 精神×")+N(InnateWis*100)+TEXT("%"),1);
        if(Multiplier!=1)Row(C,TEXT("精神迸发后"),TEXT("智力×")+N(InnateInt*Multiplier*100)+TEXT("% + 精神×")+N(InnateWis*Multiplier*100)+TEXT("%"),1);
        Row(C,TEXT("结算"),TEXT("随连击、重击等攻击倍率放大，按魔法防御减免；更换其他符文仍保留自带侵蚀。"));
    }

    if(const J Forge=Object(O,TEXT("_forgeQuality")))
    {
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("锻造工艺");C.MinimumWidth=300;
        Row(C,ColdSteelWeaponText::ForgeQuality,String(Forge,TEXT("label"),TEXT("—")));
        const double Multiplier=FMath::Clamp(Number(Forge,TEXT("multiplier"),1),.75,1.25);
        const double Percent=(Multiplier-1)*100;
        Row(C,ColdSteelWeaponText::ForgeDamageModifier,Signed(Percent,TEXT("%")),Percent>0?1:Percent<0?-1:0);
        ForgeSummary=C.Rows;
        Row(C,TEXT("有效命中"),N(Number(Forge,TEXT("hits")))+TEXT(" / ")+N(Number(Forge,TEXT("total"),20)));
        Row(C,TEXT("工艺倍率"),FString::Printf(TEXT("×%.3f"),Multiplier));
        Row(C,TEXT("作用范围"),TEXT("作用于基础伤害计算，已计入武器总伤害；附加伤害按各自公式结算，不统一乘此倍率。"));
        Row(C,TEXT("品质说明"),TEXT("锻造品质由本次锻打表现决定，与物品稀有度、强化等级分别记录。"));
    }
    if(const J Assembly=Object(O,TEXT("_assemblyQuality")))
    {
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("枪械装配工艺");C.MinimumWidth=300;
        Row(C,TEXT("装配品质"),String(Assembly,TEXT("label"),TEXT("—")));
        Row(C,TEXT("工艺评分"),N(Number(Assembly,TEXT("score")))+TEXT(" / 100"));
        Row(C,TEXT("后坐力降低"),N((1-FMath::Clamp(Number(Assembly,TEXT("recoil"),1),.88,1.))*100)+TEXT("%"),1);
        Row(C,TEXT("腰射散布降低"),N((1-FMath::Clamp(Number(Assembly,TEXT("spread"),1),.85,1.))*100)+TEXT("%"),1);
        Row(C,TEXT("作用范围"),TEXT("已计入实战和合计参数，随本枪保存；更换配件保留装配工艺。"));
    }
    const J Enchant=Object(O,TEXT("_enchantData"));const J EE=Object(O,TEXT("_enchantEffects"));
    if(Enchant&&(Object(Enchant,TEXT("prefix"))||Object(Enchant,TEXT("suffix")))){
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("附魔效果");C.MinimumWidth=300;
        FString Name=String(Object(Enchant,TEXT("prefix")),TEXT("name"));
        const FString Suffix=String(Object(Enchant,TEXT("suffix")),TEXT("name"));if(!Suffix.IsEmpty()){if(!Name.IsEmpty())Name+=TEXT(" · ");Name+=Suffix;}
        Row(C,TEXT("当前词缀"),Name);
        if(EE){Delta(C,TEXT("伤害"),Number(EE,TEXT("damagePercent"))*100,TEXT("%"));
            if(EE->HasField(TEXT("attackIntervalMul")))Row(C,ColdSteelWeaponText::AttackInterval,TEXT("×")+N(Number(EE,TEXT("attackIntervalMul"))),Number(EE,TEXT("attackIntervalMul"))<1?1:-1);
            Delta(C,TEXT("暴击率"),Number(EE,TEXT("critRate"))*100,TEXT("%"));Delta(C,TEXT("穿透目标"),Number(EE,TEXT("piercingBonus")),TEXT("个"));
            bool Poison=false;if(EE->TryGetBoolField(TEXT("poisonOnHit"),Poison)&&Poison)Row(C,TEXT("特殊效果"),TEXT("攻击叠加中毒"),1);
            const double TurboStart=Number(EE,TEXT("turboRampStartMul")),TurboPeak=Number(EE,TEXT("turboRampPeakMul")),TurboSeconds=Number(EE,TEXT("turboRampSeconds"));
            if(TurboStart>0.&&TurboPeak>0.&&TurboSeconds>0.)
            {Row(C,TEXT("射速倍率"),RateMultiplier(TurboStart)+TEXT(" → ")+RateMultiplier(TurboPeak)+TEXT(" 倍"),1);
                Row(C,TEXT("加速时间"),N(TurboSeconds)+TEXT(" 秒，停火立即复位"),1);}
            bool ConvergenceShot=false;EE->TryGetBoolField(TEXT("convergenceShot"),ConvergenceShot);
            bool Cowboy=false;EE->TryGetBoolField(TEXT("cowboyReload"),Cowboy);
            if(Cowboy)
            {
                Row(C,TEXT("牛仔补弹"),TEXT("进入滑铲状态 0.25 秒后，瞬间补满本枪弹匣"),1);
                Row(C,TEXT("弹药消耗"),TEXT("扣除弹药袋中当前对应弹药；不足时补入剩余数量"));
                Row(C,TEXT("触发限制"),TEXT("每次滑铲仅一次；无对应弹药或满弹匣不触发；双持仅附魔枪生效"));
                Row(C,TEXT("换弹表现"),TEXT("无换弹动画，仅播放一次开弹巢声或插弹匣声"));
            }
            bool RiftSlash=false;EE->TryGetBoolField(TEXT("riftSlash"),RiftSlash);
            if(RiftSlash)
            {
                Row(C,TEXT("裂空剑气"),TEXT("蓄满重击挥出时，向前发射一道蓝白弧形剑气"),1);
                Row(C,TEXT("剑气射程"),N(Number(EE,TEXT("riftSlashRangeM")))+TEXT(" 米"),1);
                Row(C,TEXT("剑气伤害"),N(Number(EE,TEXT("riftSlashDamageScale"))*100.)+TEXT("% 本次重击伤害，继承伤害类型与穿透属性"),1);
                Row(C,TEXT("穿透规则"),TEXT("穿透敌人，每个敌人仅命中一次；遇墙消散"));
                Row(C,TEXT("触发规则"),TEXT("未蓄满不触发；不额外消耗法力；剑气不再触发附魔连锁"));
            }
            bool Shatter=false;EE->TryGetBoolField(TEXT("shatterBullet"),Shatter);
            bool Electrified=false;EE->TryGetBoolField(TEXT("electrifiedMelee"),Electrified);
            const double ElectricRadius=Number(EE,TEXT("electrifiedRadiusM"));
            const int32 ElectricFloor=int32(Number(EE,TEXT("electrifiedMinLevel")));
            if(Electrified&&ElectricRadius>0.&&ElectricFloor>0)
            {
                const int32 Level=FMath::Max(ElectricFloor,Model?Model->LightningProgress().Level:0);
                Row(C,TEXT("命中放电"),TEXT("25% 概率，")+N(ElectricRadius)+TEXT(" 米内随机一名其他敌人"),1);
                Row(C,TEXT("近战击杀"),TEXT("100% 放电，")+N(ElectricRadius)+TEXT(" 米内随机一名其他敌人"),1);
                Row(C,TEXT("闪电击杀"),N(ElectricRadius)+TEXT(" 米内所有其他敌人，可继续击杀连锁"),1);
                Row(C,TEXT("闪电等级"),FString::Printf(TEXT("Lv.%d（至少 %d 级，随自身闪电等级提高）"),Level,ElectricFloor),1);
                if(Model){const auto Spell=Model->LightningStats(Level);
                    Row(C,TEXT("首跳基础伤害"),N(Spell.Damage)+TEXT(" · 闪电魔法，暴击与目标防御另计"),1);
                    Row(C,TEXT("逐跳衰减"),N(Spell.ChainDecay*100.)+TEXT("%，同层每个目标独立结算"));}
                Row(C,TEXT("连锁规则"),TEXT("同一轮不重复命中；受墙体遮挡；不消耗法力、不占用技能冷却"));
                Row(C,TEXT("武器特效"),TEXT("刃部环绕紫色闪电"),1);
            }
            const double ShatterRadius=Number(EE,TEXT("shatterRadiusM")),ShatterScale=Number(EE,TEXT("shatterDamageScale"));
            if(Shatter&&ShatterRadius>0.&&ShatterScale>0.)
            {
                Row(C,TEXT("命中弹射"),N(ShatterRadius)+TEXT(" 米内随机一名其他敌人"),1);
                Row(C,TEXT("击杀弹射"),N(ShatterRadius)+TEXT(" 米内所有其他敌人，各一颗子弹"),1);
                Row(C,TEXT("弹射伤害"),N(ShatterScale*100.)+TEXT("% 原命中伤害，继承类型与暴击，由新目标防御结算"),1);
                Row(C,TEXT("弹射限制"),TEXT("仅一次，不连锁；受墙体遮挡"));
            }
            const double ConvergenceScale=Number(EE,TEXT("convergenceDamageScale"));
            if(ConvergenceShot&&ConvergenceScale>0.)
            {Row(C,TEXT("射击模式"),TEXT("一次射击打空弹匣"),1);
                Row(C,TEXT("聚合伤害"),TEXT("消耗发数合计的 ")+N(ConvergenceScale*100.)+TEXT("%，类型沿用原枪械"),1);}}
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
            const auto S=G->CalculateItem(I,Parts),B=G->CalculateItem(I,{});Section(C,TEXT("合计改造数值"));
            if(G->IsStaff(I.Definition)){Row(C,TEXT("杖冠"),TEXT("仅匹配杖头专精时生效"));Row(C,TEXT("费用"),TEXT("免费改造，应用后保存"));}
            else if(G->IsTool(I.Definition))
            {
                // 行名与 tool-gunsmith.json 的 effects 措辞一致；采集与自卫分两段列出。
                Delta(C,ColdSteelWeaponText::HarvestYieldMultiplier,(S.Tool.HarvestYield-1)*100,TEXT("%"));
                Delta(C,TEXT("所需有效命中"),double(S.Tool.HarvestHitsAdd),TEXT(" 次"),true);
                Delta(C,TEXT("采集距离"),(S.Tool.HarvestReach-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::HarvestRadius,S.Tool.HarvestRadiusAddCM,TEXT(" cm"));
                Delta(C,TEXT("额外产出几率"),S.Tool.BonusHarvestChance*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::BaseDamageModifier,(S.Tool.Damage-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::AttackSpeed,(S.Tool.AttackSpeed-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::StaminaCost,(S.Tool.Stamina-1)*100,TEXT("%"),true);
                Delta(C,ColdSteelWeaponText::AttackDistance,(S.Tool.CombatReach-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::ToughnessMultiplier,(S.Tool.ToughnessDamage-1)*100,TEXT("%"));
                Delta(C,TEXT("暴击率"),S.Tool.CriticalChanceAdd,TEXT("%"));
            }
            else if(G->IsBow(I.Definition))
            {
                Delta(C,ColdSteelWeaponText::BaseDamageModifier,(S.Bow.Damage-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::DrawTime,(S.Bow.Draw-1)*100,TEXT("%"),true);
                Delta(C,ColdSteelWeaponText::NockTime,(S.Bow.Nock-1)*100,TEXT("%"),true);
                Delta(C,ColdSteelWeaponText::ProjectileSpeed,(S.Bow.Speed-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::StaminaCost,(S.Bow.Stamina-1)*100,TEXT("%"),true);
                Delta(C,ColdSteelWeaponText::HoldTime,(S.Bow.Hold-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::Sway,(S.Bow.Sway-1)*100,TEXT("%"),true);
                Delta(C,ColdSteelWeaponText::HipSpreadMultiplier,(S.Bow.Spread-1)*100,TEXT("%"),true);
                Delta(C,ColdSteelWeaponText::ADS,(S.Bow.ADS-1)*100,TEXT("%"),true);
            }
            else if(G->IsMelee(I.Definition))
            {
                Delta(C,ColdSteelWeaponText::BaseDamageModifier,(S.Melee.Damage-1)*100,TEXT("%"));
                Delta(C,TEXT("三连击第二段伤害"),(S.Melee.ComboSecond-1)*100,TEXT("%"));
                Delta(C,TEXT("三连击第三段伤害"),(S.Melee.ComboThird-1)*100,TEXT("%"));
                Delta(C,TEXT("第三段突刺韧性伤害"),(S.Melee.ComboThirdToughness-1)*100,TEXT("%"));
                Delta(C,TEXT("魔法技能冷却时间"),(S.Melee.MagicCooldown-1)*100,TEXT("%"),true);
                Delta(C,TEXT("魔法伤害"),(S.Melee.MagicDamage-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::MagicCostMultiplier,(S.Melee.MagicCost-1)*100,TEXT("%"),true);
                Delta(C,TEXT("重击伤害倍率"),(S.Melee.HeavyDamage-1)*100,TEXT("%"));
                Delta(C,TEXT("重击韧性伤害"),(S.Melee.HeavyToughness-1)*100,TEXT("%"));
                Delta(C,TEXT("重击伤害倍率加值"),S.Melee.HeavyDamageAdd,TEXT(""));
                Delta(C,TEXT("攻击造成击退"),(S.Melee.Knockback-1)*100,TEXT("%"));
                Delta(C,TEXT("快速近战伤害倍率加值"),S.Melee.QuickCombatDamageAdd,TEXT(""));
                Delta(C,TEXT("快速近战击退距离"),(S.Melee.QuickCombatKnockback-1)*100,TEXT("%"));
                Delta(C,TEXT("快速近战韧性伤害"),(S.Melee.QuickCombatToughness-1)*100,TEXT("%"));
                if(S.Melee.QuickCombatBleedChance>0)Row(C,ColdSteelWeaponText::QuickCombatBleed,N(S.Melee.QuickCombatBleedChance*100)+TEXT("% 概率施加1层"),1);
                if(S.Melee.bQuickCombatAOE)Row(C,ColdSteelWeaponText::QuickCombatHitMode,TEXT("范围多目标 · 判定范围不变"),1);
                Delta(C,TEXT("附加魔法伤害·智力系数"),S.Melee.RuneIntelligence*100,TEXT("%"));
                Delta(C,TEXT("附加魔法伤害·精神系数"),S.Melee.RuneWisdom*100,TEXT("%"));
                Delta(C,TEXT("自带侵蚀附加伤害"),(S.Melee.InnateErosionMultiplier-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::RuneVulnerability,S.Melee.RuneVulnerability*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::CooldownReducePerHit,S.Melee.CooldownReduceSecondsPerHit,TEXT(" s"));
                Delta(C,ColdSteelWeaponText::AttackSpeed,(S.Melee.AttackSpeed-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::AttackDistance,(S.Melee.Range-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::StaminaCost,(S.Melee.Stamina-1)*100,TEXT("%"),true);
                Delta(C,TEXT("造成硬直时间"),(S.Melee.HitReaction-1)*100,TEXT("%"));
                Delta(C,ColdSteelWeaponText::ToughnessMultiplier,(S.Melee.ToughnessDamage-1)*100,TEXT("%"));
                Delta(C,TEXT("物理防御穿透"),S.Melee.PhysicalArmorPenetration*100,TEXT("%"));
                Delta(C,TEXT("格挡减伤"),(S.Melee.BlockReduction-1)*100,TEXT("%"));
                Delta(C,TEXT("弹反判定时间"),(S.Melee.ParryWindow-1)*100,TEXT("%"));
                if(S.Melee.ClovenSeconds>0)
                {
                    Row(C,TEXT("成功弹反"),TEXT("承锋·瞬重斩 · ")+N(S.Melee.ClovenSeconds)+TEXT(" s"),1);
                    Delta(C,ColdSteelWeaponText::ClovenPhysicalDamage,(S.Melee.ClovenPhysical-1)*100,TEXT("%"));
                    Delta(C,ColdSteelWeaponText::ClovenToughnessDamage,(S.Melee.ClovenToughness-1)*100,TEXT("%"));
                }
            }
            else {
            Delta(C,ColdSteelWeaponText::BaseDamageModifier,S.Damage-B.Damage,TEXT(""));Delta(C,ColdSteelWeaponText::Capacity,S.Capacity-B.Capacity,TEXT("发"));
            Delta(C,ColdSteelWeaponText::ADS,(S.ADS-B.ADS)*1000,TEXT("ms"),true);Delta(C,TEXT("射击间隔"),(S.Interval-B.Interval)*1000,TEXT("ms"),true);
            Delta(C,ColdSteelWeaponText::Reload,(S.Reload-B.Reload)*1000,TEXT("ms"),true);Delta(C,ColdSteelWeaponText::EmptyReload,(S.EmptyReload-B.EmptyReload)*1000,TEXT("ms"),true);
            Delta(C,ColdSteelWeaponText::RecoilIndex,S.Recoil-B.Recoil,TEXT(""),true);Delta(C,ColdSteelWeaponText::Stability,S.Handling.Stability-B.Handling.Stability,TEXT(""));
            Delta(C,TEXT("枪械稳定性·回稳90%"),S.Handling.ADSRecoveryMilliseconds()-B.Handling.ADSRecoveryMilliseconds(),TEXT("ms"),true);
            if(B.Spread>0)Delta(C,TEXT("腰射散布"),(S.Spread/B.Spread-1)*100,TEXT("%"),true);
            Delta(C,TEXT("射程"),S.Range-B.Range,TEXT("m"));Delta(C,ColdSteelWeaponText::ProjectileSpeed,S.Speed-B.Speed,TEXT("m/s"));}}
        if(Craft){const auto Config=Object(Object(Reference(),TEXT("craft")),*I.Definition);const auto Options=Object(Config,TEXT("options"));
            for(const auto& P:Craft->Values){const TArray<TSharedPtr<FJsonValue>>* List=nullptr;if(!Options||!Options->TryGetArrayField(FString(*P.Key),List))continue;
                for(const auto& V:*List){const auto Option=V->AsObject();if(String(Option,TEXT("id"))==Value(P.Value)){Section(C,String(Option,TEXT("name")));Row(C,TEXT(""),String(Option,TEXT("desc")));C.Rows.Last().bDashedAfter=true;break;}}}}
        if(CE&&!CE->Values.IsEmpty()){
            Section(C,TEXT("合计改造数值"));
            struct FEffect{const TCHAR* Key;const TCHAR* Label;const TCHAR* Unit;double Scale;bool Lower;};
            const FEffect Effects[]={{TEXT("damagePercent"),TEXT("伤害"),TEXT("%"),100,false},{TEXT("piercingBonus"),TEXT("穿透目标"),TEXT("个"),1,false},{TEXT("critChancePercent"),TEXT("暴击率"),TEXT("%"),100,false},{TEXT("rangeDelta"),TEXT("攻击距离"),TEXT("px"),1,false},{TEXT("projectileSpeedPercent"),ColdSteelWeaponText::ProjectileSpeed,TEXT("%"),100,false},{TEXT("moveSpeedPercent"),TEXT("移速"),TEXT("%"),100,false},{TEXT("attackIntervalDelta"),ColdSteelWeaponText::AttackInterval,TEXT("ms"),1,true},{TEXT("magazineDelta"),ColdSteelWeaponText::Capacity,TEXT("发"),1,false},{TEXT("magazinePercent"),ColdSteelWeaponText::Capacity,TEXT("%"),100,false},{TEXT("reloadTimeDelta"),TEXT("换弹耗时"),TEXT("ms"),1,true},{TEXT("maxSpreadAngleDelta"),TEXT("最大散布"),TEXT("°"),1,true},{TEXT("defensePercent"),TEXT("防御"),TEXT("%"),100,false},{TEXT("staminaCostDelta"),ColdSteelWeaponText::StaminaCost,TEXT(""),1,true},{TEXT("knockbackDelta"),TEXT("击退距离"),TEXT("px"),1,false}};
            for(const auto& E:Effects)Delta(C,E.Label,Number(CE,E.Key)*E.Scale,E.Unit,E.Lower);
        }
    }
    auto& Main=Out.Cards.AddDefaulted_GetRef();Main.MinimumWidth=460;
    const TArray<TSharedPtr<FJsonValue>>* Stats=nullptr;
    FGunsmithStats S;if(Weapon)S=G->CalculateItem(I,Parts);
    if(O->TryGetArrayField(TEXT("stats"),Stats))for(const auto& V:*Stats){const auto St=V->AsObject();const FString Label=String(St,TEXT("name"),String(St,TEXT("label")));FString Val=St->HasField(TEXT("value"))?Value(St->Values[TEXT("value")]):TEXT("");
        // 枪/剑/杖的攻防展示走下面的计算行，目录 stats 里的静态行（含转轮的
        // 弹巢容量）是创建时快照，会与实算的武器总伤害、装备魔攻重复或冲突。
        const bool bStaff=ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("staff");
        if((Weapon||ColdSteelInventory::IsTwoHandedSword(I)||bStaff)&&Label==TEXT("物理攻击"))continue;
        if(bStaff&&Label==TEXT("魔法攻击"))continue;
        if(Weapon&&(Label==ColdSteelWeaponText::Capacity||Label==TEXT("弹巢容量")))continue;
        bool Positive=false;St->TryGetBoolField(TEXT("pos"),Positive);if(!Label.IsEmpty())Row(Main,Label,Val,Positive?1:0);}
    Section(Main,TEXT("物品信息"));Row(Main,TEXT("分类"),Category(String(O,TEXT("category"))));
    Row(Main,TEXT("武器类型"),String(O,TEXT("weaponTypeTag"),String(O,TEXT("weaponType"))));Row(Main,TEXT("装备槽位"),EquipSlotLabel(String(O,TEXT("equipSlot"))));
    const FString Cat=String(O,TEXT("category"));const J Defense=Object(O,TEXT("defense"));
    if(ColdSteelInventory::IsTwoHandedSword(I)){
        Section(Main,ColdSteelWeaponText::CombatParameters);AppendColdSteelTooltipAttackFormula(I,Model,Number(O,TEXT("melee_damage"),55),Main);
        const auto Melee=ColdSteelMelee::Evaluate(I,Model);
        const bool OverheadFinisher=ColdSteelModularSword::UsesOverheadFinisher(I);
        DamageRows(Main,Melee.DamageParts);
        Row(Main,TEXT("快速近战伤害倍率"),N(Melee.QuickCombat.DamageMultiplier)+TEXT("×"));
        Row(Main,TEXT("快速近战伤害"),N(Melee.QuickCombat.Damage));
        Row(Main,TEXT("快速近战击退距离"),N(Melee.QuickCombat.KnockbackCM)+TEXT(" cm"));
        Row(Main,TEXT("快速近战韧性伤害倍率"),N(Melee.QuickCombat.ToughnessMultiplier)+TEXT("×"));
        if(Melee.QuickCombat.BleedChance>0)Row(Main,TEXT("快速近战流血"),N(Melee.QuickCombat.BleedChance*100)+TEXT("% 概率施加1层"));
        Row(Main,TEXT("快速近战命中方式"),Melee.QuickCombat.bAreaHit?TEXT("范围多目标 · 判定范围不变"):TEXT("单目标"));
        Row(Main,TEXT("三连击第二段伤害"),N(Melee.ComboSecondDamage));
        Row(Main,TEXT("三连击第三段伤害"),N(Melee.ComboThirdDamage));
        if(!FMath::IsNearlyEqual(Melee.Modifiers.ComboThirdToughness,1.))Row(Main,OverheadFinisher?TEXT("第三段竖劈韧性伤害倍率"):TEXT("第三段突刺韧性伤害倍率"),N(Melee.Modifiers.ThirdThrustToughnessMultiplier())+TEXT("×"));
        if(Melee.Modifiers.MagicCooldown!=1)Row(Main,TEXT("魔法技能冷却倍率"),N(Melee.Modifiers.MagicCooldown)+TEXT("×"));
        if(Melee.Modifiers.MagicDamage!=1)Row(Main,TEXT("魔法伤害倍率"),N(Melee.Modifiers.MagicDamage)+TEXT("×"));
        if(Melee.Modifiers.CooldownReduceSecondsPerHit>0)Row(Main,ColdSteelWeaponText::CooldownReducePerHit,N(.5f+Melee.Modifiers.CooldownReduceSecondsPerHit)+TEXT(" s / 挥"));
        if(Melee.Modifiers.RuneVulnerability>0)Row(Main,ColdSteelWeaponText::RuneVulnerability,N(Melee.Modifiers.RuneVulnerability*100)+TEXT("% · ")+N(Melee.Modifiers.RuneVulnerabilitySeconds)+TEXT(" s"));
        Row(Main,ColdSteelWeaponText::AttackInterval,N(FMath::RoundToInt(Melee.AttackSeconds*1000))+TEXT(" ms"));
        Row(Main,OverheadFinisher?TEXT("竖劈时间"):TEXT("突刺时间"),N(Melee.ThrustSeconds)+TEXT(" s"));
        if(OverheadFinisher)Row(Main,TEXT("第三段命中区域"),TEXT("前方矩形"));
        Row(Main,ColdSteelWeaponText::AttackDistance,N(Melee.ThrustReach/100)+TEXT(" m"));
        Row(Main,TEXT("普通挥砍距离"),N(Melee.SlashReach/100)+TEXT(" m"));
        Row(Main,ColdSteelWeaponText::StaminaCost,N(Melee.AttackStamina));
        Row(Main,TEXT("命中硬直时间倍率"),N(Melee.Modifiers.HitReaction)+TEXT("×"));
        if(!FMath::IsNearlyEqual(Melee.Modifiers.ToughnessDamage,1.))Row(Main,ColdSteelWeaponText::ToughnessMultiplier,N(Melee.Modifiers.ToughnessDamage)+TEXT("×"));
        if(Melee.Modifiers.PhysicalArmorPenetration>0)Row(Main,TEXT("改造物理防御穿透"),N(Melee.Modifiers.PhysicalArmorPenetration*100)+TEXT("%"));
        Row(Main,TEXT("格挡伤害减免"),N(Melee.BlockReduction*100)+TEXT("%"));
        Row(Main,TEXT("弹反判定时间"),N(Melee.ParrySeconds)+TEXT(" s"));
        if(Melee.Modifiers.RiposteSeconds>0)Row(Main,TEXT("成功弹反"),TEXT("反击激励 · ")+N(Melee.Modifiers.RiposteSeconds)+TEXT(" s"));
        if(Melee.Modifiers.ClovenSeconds>0)
        {
            Row(Main,TEXT("成功弹反"),TEXT("承锋·瞬重斩 · ")+N(Melee.Modifiers.ClovenSeconds)+TEXT(" s"));
            Row(Main,ColdSteelWeaponText::ClovenPhysicalDamage,TEXT("+")+N((Melee.Modifiers.ClovenPhysical-1)*100)+TEXT("%"));
            Row(Main,ColdSteelWeaponText::ClovenToughnessDamage,TEXT("+")+N((Melee.Modifiers.ClovenToughness-1)*100)+TEXT("%"));
        }
        Row(Main,ColdSteelWeaponText::BlockStaminaCost,N(Melee.BlockStamina));
        Row(Main,TEXT("握持"),TEXT("双手 · 占用副手槽"));
    }else if(ColdSteelInventory::IsEquippedProductionTool(I)){
        const bool bPickaxe=I.Definition==TEXT("tool_pickaxe");
        // Same 近战参数 layout as the swords: formula, then total/base/added damage, then
        // interval, stamina, reach and grip; tool-only harvest numbers move to their own section.
        // 改造后的实值走工具评估入口：提示栏、工作台与实战读同一份结果，不各自换算。
        const auto Tool=ColdSteelTool::Evaluate(I,Model);
        Section(Main,ColdSteelWeaponText::CombatParameters);
        const double Base=Number(O,TEXT("melee_damage"),bPickaxe?10:12);
        AppendColdSteelTooltipAttackFormula(I,Model,Base,Main);
        DamageRows(Main,Tool.Damage);
        if(Tool.CriticalChanceAdd>0)Row(Main,TEXT("暴击率"),TEXT("+")+N(Tool.CriticalChanceAdd)+TEXT("%"));
        if(!FMath::IsNearlyEqual(Tool.ToughnessDamage,1.))Row(Main,ColdSteelWeaponText::ToughnessMultiplier,N(Tool.ToughnessDamage)+TEXT("×"));
        Row(Main,ColdSteelWeaponText::AttackInterval,N(FMath::RoundToInt(Tool.SwingSeconds*1000))+TEXT(" ms"));
        Row(Main,ColdSteelWeaponText::AttackDistance,N(Tool.CombatReachCM/100)+TEXT(" m"));
        Row(Main,ColdSteelWeaponText::StaminaCost,N(Tool.StaminaCost));
        Row(Main,TEXT("握持"),TEXT("双手 · 占用同组主手与副手槽"));
        Section(Main,TEXT("采集参数"));
        Row(Main,TEXT("装备方式"),TEXT("背包右键 / 拖入主手武器槽；G / 滚轮切换"));
        Row(Main,ColdSteelWeaponText::HarvestDistance,N(Tool.HarvestReachCM/100)+TEXT(" m"));
        if(Tool.HarvestRadiusCM>0)Row(Main,ColdSteelWeaponText::HarvestRadius,N(Tool.HarvestRadiusCM)+TEXT(" cm"));
        if(!FMath::IsNearlyEqual(Tool.HarvestYield,1.))Row(Main,TEXT("采集产出倍率"),N(Tool.HarvestYield)+TEXT("×"));
        if(Tool.BonusHarvestChance>0)Row(Main,TEXT("额外产出几率"),N(Tool.BonusHarvestChance*100)+TEXT("%"));
        if(bPickaxe)
        {
            Row(Main,TEXT("采矿伤害"),N(ProductionTreeHealth::StrikeDamage(Tool))+TEXT(" / 挥"));
            Row(Main,TEXT("采集规则"),TEXT("岩石有生命值，按采矿伤害扣血，归零才碎；伤害随属性与改造提升"));
        }
        else
        {
            // 树木像怪物一样有生命值：一次挥砍按伐木伤害扣血，归零才倒。
            Row(Main,TEXT("伐木伤害"),N(ProductionTreeHealth::StrikeDamage(Tool))+TEXT(" / 挥"));
            // Actual swings depend on the target tree's species, size and remaining health.
            // The hit-modifier baseline is not an actual "standard tree" swing count.
            Row(Main,TEXT("采集规则"),TEXT("树木有生命值，按伐木伤害扣血，归零才倒；挥砍数随伤害与命中改造变化"));
        }
    }else if(I.Definition==TEXT("tool_shovel")){
        // 铁铲不进武器槽、没有战斗参数：地形挖/填规则单独成段。数值取目录 dig
        // 块（展示口径），与 TemperateHills 挖填实现的 20 cm 层、2 泥土同源。
        Section(Main,TEXT("采集参数"));
        Row(Main,TEXT("装备方式"),TEXT("按 8 取用 · F7 收起"));
        const auto Dig=Object(O,TEXT("dig"));
        const auto D=[&](const TCHAR* Key,double Def){return Dig?Number(Dig,Key,Def):Def;};
        const double Layer=D(TEXT("layer_cm"),20),Soil=D(TEXT("soil_per_layer"),2),Footprint=D(TEXT("footprint_cm"),240);
        Row(Main,TEXT("单层范围"),N(Footprint)+TEXT(" × ")+N(Footprint)+TEXT(" cm（对齐 ")+N(Layer)+TEXT(" cm 网格）"));
        Row(Main,TEXT("左键挖掘"),TEXT("每击挖低 ")+N(Layer)+TEXT(" cm · 获得 ")+N(Soil)+TEXT(" 个泥土"));
        Row(Main,TEXT("右键回填"),TEXT("每层抬高 ")+N(Layer)+TEXT(" cm · 消耗 ")+N(Soil)+TEXT(" 个泥土"));
        Row(Main,TEXT("回填上限"),TEXT("生成地面以上 ")+N(D(TEXT("rise_limit_cm"),100)/100)+TEXT(" m"));
        Row(Main,TEXT("挖掘下限"),TEXT("生成地面以下 ")+N(D(TEXT("drop_limit_cm"),400)/100)+TEXT(" m"));
    }else if(ColdSteelInventory::IsBow(I)){
        Section(Main,ColdSteelWeaponText::CombatParameters);
        const auto Bow=ColdSteelBow::Evaluate(I,Model);const auto& BowDamage=Bow.Damage;
        const double Base=Number(O,TEXT("full_damage"),69)*(G?G->Calculate(I.Definition,Parts).Bow.Damage:1.);
        AppendColdSteelTooltipAttackFormula(I,Model,Base,Main);
        DamageRows(Main,BowDamage);
        if(const double CritBonus=ColdSteelInventory::Number(I,TEXT("critDamageBonus"));CritBonus>0)
            Row(Main,ColdSteelWeaponText::CriticalBonus,TEXT("+")+N(CritBonus*100)+TEXT("%"));
        Row(Main,ColdSteelWeaponText::DrawTime,N(Bow.Draw)+TEXT(" s"));
        Row(Main,ColdSteelWeaponText::NockTime,N(Bow.Nock)+TEXT(" s"));
        Row(Main,ColdSteelWeaponText::ProjectileSpeed,N(Bow.Speed)+TEXT(" m/s"));
        Row(Main,ColdSteelWeaponText::FlightLimit,N(Number(O,TEXT("range_cm"),3200)/100)+TEXT(" m"));
        Row(Main,ColdSteelWeaponText::StaminaCost,N(Bow.Stamina));
        Row(Main,ColdSteelWeaponText::HoldTime,N(Bow.Hold)+TEXT(" s"));
        Row(Main,ColdSteelWeaponText::Sway,N(Bow.Sway));
        Row(Main,ColdSteelWeaponText::HipSpreadAngle,N(FMath::RadiansToDegrees(FMath::Atan(Bow.Spread)))+TEXT("°"));
        Row(Main,ColdSteelWeaponText::ADS,N(FMath::RoundToInt(Bow.ADS*1000))+TEXT(" ms"));
        if(Model)
        {
            Row(Main,ColdSteelWeaponText::Ammo,Model->AmmoLabel(Model->AmmoDefinitionFor(I)));
            Row(Main,ColdSteelWeaponText::AmmoEffect,Model->AmmoEffectSummary(Model->AmmoDefinitionFor(I)));
            Row(Main,ColdSteelWeaponText::AmmoAdjustedDamage,N(BowDamage.Total()*Model->AmmoDamageMultiplier(I)));
        }
        Row(Main,TEXT("握持"),TEXT("双手 · 占用副手槽"));
    }else if(ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("staff")){
        Section(Main,ColdSteelWeaponText::CombatParameters);AppendColdSteelTooltipAttackFormula(I,Model,3,Main);
        DamageRows(Main,ColdSteelWeaponStats::DamageParts(I,Model,3));
        Row(Main,ColdSteelWeaponText::AttackInterval,N(FMath::RoundToInt(ColdSteelWeaponStats::Interval(&I,Model,.5)*1000))+TEXT(" ms"));
        // 装备魔攻 = 实值行（与角色端 EquipmentMagicAttack 同源取值），公式表达式以堆叠行随后——
        // 结构对齐枪械的「攻击力计算公式 → 数值行」；挥杖的基伤走钝击物理，故分项保留物理口径。
        if(const auto MF=Object(O,TEXT("matkFormula")))
        {
            const auto Coef=[&](double M,double E)->FString{FString R=N(M);if(!FMath::IsNearlyEqual(E,0.))R+=TEXT("+")+N(E)+TEXT("×强化");return R;};
            const double EnhanceBase=Number(MF,TEXT("enhanceBase"));
            if(Model)Row(Main,TEXT("装备魔攻"),N(Model->EquipmentMagicAttack()));
            Main.Rows.Add({TEXT("装备魔攻公式"),N(Number(MF,TEXT("base")))+(EnhanceBase>0?TEXT(" + ")+N(EnhanceBase)+TEXT("×强化等级"):FString())
                +TEXT(" + 智力×(")+Coef(Number(MF,TEXT("intMul")),Number(MF,TEXT("enhanceIntMul")))+TEXT(")")
                +TEXT(" + 精神×(")+Coef(Number(MF,TEXT("wisMul")),Number(MF,TEXT("enhanceWisMul")))+TEXT(")"),0,true});
        }
        Row(Main,TEXT("握持"),TEXT("单手主手；左键挥杖，技能快捷键施法"));
    }else if(Weapon){Section(Main,ColdSteelWeaponText::CombatParameters);AppendColdSteelTooltipAttackFormula(I,Model,S.Damage,Main);
        const auto DamageParts=ColdSteelWeaponStats::DamageParts(I,Model,S.Damage);
        DamageRows(Main,DamageParts);
        Row(Main,TEXT("子弹数"),FString::Printf(TEXT("%d / %d 发"),I.Magazine,S.Capacity));Row(Main,ColdSteelWeaponText::Ammo,Model?Model->AmmoLabel(Model->AmmoDefinitionFor(I)):ColdSteelWeaponStats::AmmoName(Weapon->Ammo));
        if(Model)
        {
            Row(Main,ColdSteelWeaponText::AmmoEffect,Model->AmmoEffectSummary(Model->AmmoDefinitionFor(I)));
            Row(Main,ColdSteelWeaponText::AmmoAdjustedDamage,N(DamageParts.Total()*Model->AmmoDamageMultiplier(I)));
        }
        Row(Main,S.BurstCount>1?TEXT("组内射击间隔"):ColdSteelWeaponText::AttackInterval,N(FMath::RoundToInt(ColdSteelWeaponStats::Interval(&I,Model,S.Interval)*1000))+TEXT(" ms"));
        const double FireInterval=ColdSteelWeaponStats::Interval(&I,Model,S.Interval);
        Row(Main,S.BurstCount>1?TEXT("组内理论射速"):TEXT("理论射速"),FireInterval>0?N(60./FireInterval)+TEXT(" 发/分"):TEXT("—"));
        // 涡轮增压：理论射速是不开火的静态值，实战读数是起步与峰值两档。
        const double TurboStart=Number(EE,TEXT("turboRampStartMul")),TurboPeak=Number(EE,TEXT("turboRampPeakMul")),TurboSeconds=Number(EE,TEXT("turboRampSeconds"));
        if(FireInterval>0.&&TurboStart>0.&&TurboPeak>0.&&TurboSeconds>0.)
        {
            Row(Main,TEXT("起步射速"),N(60./(FireInterval*TurboStart))+TEXT(" 发/分"));
            Row(Main,TEXT("峰值射速"),N(60./(FireInterval*TurboPeak))+TEXT(" 发/分"));
        }
        // 汇聚：单发按满匣口径聚合，面板给出可直接对照的整匣数字。
        // 无附魔物品（如改造台的产品预览）没有 _enchantEffects，EE 为空，必须先判空再读布尔键。
        bool ConvergenceShot=false;if(EE)EE->TryGetBoolField(TEXT("convergenceShot"),ConvergenceShot);
        const double ConvergenceScale=Number(EE,TEXT("convergenceDamageScale"));
        if(ConvergenceShot&&ConvergenceScale>0.&&S.Capacity>0&&DamageParts.Total()>0.)
        {
            const double MagazineTotal=DamageParts.Total()*S.Capacity;
            Row(Main,TEXT("满匣聚合伤害"),N(MagazineTotal*ConvergenceScale)+TEXT("（")+FString::FromInt(S.Capacity)+TEXT(" 发合计 ")+N(MagazineTotal)+TEXT("）"));
            Row(Main,TEXT("射击模式"),TEXT("一次射击打空弹匣，伤害类型沿用原枪械"));
        }
        if(S.BurstCount>1)
        {
            const double BurstDelay=ColdSteelWeaponStats::Interval(&I,Model,S.BurstDelay);
            const double Cycle=(S.BurstCount-1)*FireInterval+FMath::Max(FireInterval,BurstDelay);
            Row(Main,TEXT("开火模式"),FString::Printf(TEXT("%d 连发 · 每组重新扣动扳机"),S.BurstCount));
            Row(Main,TEXT("连发组末发后间隔"),N(FMath::RoundToInt(BurstDelay*1000))+TEXT(" ms"));
            Row(Main,TEXT("含组间隔理论射速"),N(60.*S.BurstCount/Cycle)+TEXT(" 发/分"));
        }
        Row(Main,ColdSteelWeaponText::Reload,N(ColdSteelWeaponStats::Reload(&I,Model,S.Reload))+TEXT(" s"));Row(Main,ColdSteelWeaponText::EmptyReload,N(ColdSteelWeaponStats::Reload(&I,Model,S.EmptyReload))+TEXT(" s"));
        Row(Main,ColdSteelWeaponText::ADS,N(FMath::RoundToInt(S.ADS*1000))+TEXT(" ms"));Row(Main,ColdSteelWeaponText::RecoilIndex,N(S.Recoil));Row(Main,ColdSteelWeaponText::Stability,N(S.Handling.Stability)+TEXT(" /100"));
        Row(Main,TEXT("首发上跳"),FString::Printf(TEXT("%.3f°"),S.Handling.FirstShotDegrees()));
        Row(Main,TEXT("连射上跳/发"),FString::Printf(TEXT("%.3f°"),S.Handling.MaxVerticalDegrees()));
        Row(Main,TEXT("ADS首发水平/发"),FString::Printf(TEXT("%.3f°"),S.Handling.FirstHorizontalDegrees()));
        Row(Main,TEXT("ADS水平上限/发"),FString::Printf(TEXT("%.3f°"),S.Handling.MaxHorizontalDegrees()));
        Row(Main,TEXT("枪械稳定性·回稳90%"),N(FMath::RoundToInt(S.Handling.ADSRecoveryMilliseconds()))+TEXT(" ms"));
        Row(Main,ColdSteelWeaponText::EffectiveRange,N(S.Range)+TEXT(" m"));
        Row(Main,ColdSteelWeaponText::ProjectileSpeed,S.Speed<=0?TEXT("即时命中"):N(S.Speed)+TEXT(" m/s"));
        Row(Main,ColdSteelWeaponText::HipSpreadMultiplier,N(S.Spread)+TEXT("×"));
        if(const double CritBonus=ColdSteelInventory::Number(I,TEXT("critDamageBonus"));CritBonus>0)
            Row(Main,ColdSteelWeaponText::CriticalBonus,TEXT("+")+N(CritBonus*100)+TEXT("%"));
    }
    if(Defense){Section(Main,TEXT("防御参数"));const double Base=Number(Defense,TEXT("base")),Per=Number(Defense,TEXT("perEnhance"));const auto* E=Model?Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;Row(Main,TEXT("防御力"),N(E?E->Defense(I):Base+Enhance*Per));Row(Main,TEXT("防御基础"),N(Base));Row(Main,TEXT("每级强化防御"),N(Per));
        if(Defense->HasField(TEXT("damageReduction")))Row(Main,TEXT("防御减伤"),N(Number(Defense,TEXT("damageReduction"))*100)+TEXT("%"));if(Defense->HasField(TEXT("staminaCost")))Row(Main,TEXT("防御受击体力"),N(Number(Defense,TEXT("staminaCost"))));}
    const J Bonuses=Object(O,TEXT("bonusStats"));if(Bonuses&&!Bonuses->Values.IsEmpty()){
        Section(Main,TEXT("属性加成"));const TMap<FString,FString> Names={{TEXT("str"),TEXT("力量")},{TEXT("dex"),TEXT("敏捷")},{TEXT("int"),TEXT("智力")},{TEXT("con"),TEXT("体质")},{TEXT("wis"),TEXT("精神")},{TEXT("luck"),TEXT("幸运")},{TEXT("atk"),TEXT("物理攻击")},{TEXT("matk"),TEXT("魔法攻击")},{TEXT("crit"),TEXT("暴击率")},{TEXT("maxHp"),TEXT("最大生命")},{TEXT("maxMp"),TEXT("最大魔法")},{TEXT("meleeAttackSpeed"),TEXT("近战攻击速度")},{TEXT("meleeStaminaCost"),TEXT("近战体力消耗")},{TEXT("moveSpeedPercent"),TEXT("移动速度")},{TEXT("reloadSpeed"),TEXT("换弹速度")},{TEXT("bowDrawSpeed"),TEXT("拉弓速度")}};
        for(const auto& P:Bonuses->Values){FString Key(*P.Key);if(const auto* Label=Names.Find(Key)){const bool Percent=Key==TEXT("crit")||Key==TEXT("meleeAttackSpeed")||Key==TEXT("meleeStaminaCost")||Key==TEXT("moveSpeedPercent")||Key==TEXT("reloadSpeed")||Key==TEXT("bowDrawSpeed");Delta(Main,*Label,P.Value->AsNumber()*(Percent&&Key!=TEXT("crit")?100.:1.),Percent?TEXT("%"):TEXT(""),Key==TEXT("meleeStaminaCost"));}}}
    if(O->HasField(TEXT("armorSet"))){Section(Main,TEXT("套装效果"));FString Bonus=String(O,TEXT("setBonusDesc"));if(Bonus.IsEmpty())Bonus=String(Object(O,TEXT("setBonuses")),*String(O,TEXT("armorSet")));Row(Main,TEXT("效果"),Bonus);}
    if(auto Special=Object(O,TEXT("specialAttack"))){Section(Main,TEXT("特殊攻击"));Row(Main,TEXT("伤害类型"),String(Special,TEXT("damageType")));Row(Main,TEXT("伤害公式"),String(Special,TEXT("damageFormula")));for(const auto& F:TArray<TPair<FString,FString>>{{TEXT("duration"),TEXT("持续时间")},{TEXT("cooldown"),TEXT("冷却时间")}})if(Special->HasField(F.Key))Row(Main,F.Value,N(Number(Special,*F.Key))+TEXT("秒"));}
    if(Cat==TEXT("consumable")){const auto Effect=Object(O,TEXT("useEffect"));if(Effect&&!Effect->Values.IsEmpty()){
        Section(Main,TEXT("使用效果"));if(Effect->HasField(TEXT("hp")))Row(Main,TEXT("恢复生命"),Signed(Number(Effect,TEXT("hp"))),1);if(Effect->HasField(TEXT("mp")))Row(Main,TEXT("恢复魔法"),Signed(Number(Effect,TEXT("mp"))),1);
        if(Effect->HasField(TEXT("hydration")))
        {
            const double Water=Number(Effect,TEXT("hydration"));
            Row(Main,Water<0?TEXT("消耗水分"):TEXT("恢复水分"),Signed(Water),Water<0?-1:1);
        }
        if(Effect->HasField(TEXT("hunger")))Row(Main,TEXT("恢复饥饿度"),Signed(Number(Effect,TEXT("hunger"))),1);
        if(Effect->HasField(TEXT("sanity")))Row(Main,TEXT("恢复 SAN"),Signed(Number(Effect,TEXT("sanity"))),1);
        if(Effect->HasField(TEXT("maxHpPercent")))Row(Main,TEXT("恢复最大生命"),Signed(Number(Effect,TEXT("maxHpPercent")),TEXT("%")),1);if(Effect->HasField(TEXT("maxMpPercent")))Row(Main,TEXT("恢复最大魔法"),Signed(Number(Effect,TEXT("maxMpPercent")),TEXT("%")),1);}
        if(I.Definition==TEXT("mineral_water"))
        {
            const int32 Uses=FMath::Clamp(int32(Number(O,TEXT("remainingUses"),2)),1,2);
            Row(Main,TEXT("剩余次数"),FString::Printf(TEXT("%d / 2"),Uses));
            Row(Main,TEXT("瓶内水量"),Uses==2?TEXT("满瓶"):TEXT("半瓶"));
        }
        if(I.Definition==TEXT("baguette_bread")||I.Definition==TEXT("bread"))Row(Main,TEXT("食用次数"),TEXT("单次使用"));
        if(Number(O,TEXT("useDuration"))>0)Row(Main,TEXT("使用时长"),N(Number(O,TEXT("useDuration")))+TEXT("秒"));
        if(Number(O,TEXT("useCooldown"))>0)Row(Main,TEXT("冷却时间"),N(Number(O,TEXT("useCooldown")))+TEXT("秒"));Row(Main,TEXT("使用方式"),TEXT("右键 / 双击 / Enter / 快捷栏"));}
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
    if(!ForgeSummary.IsEmpty())
    {
        Out.Summary.Append(MoveTemp(ForgeSummary));
        Out.ValueScope+=TEXT(" 锻造伤害修正已计入当前伤害，无需再次相乘。");
    }
    return Out;
}
