#include "MonsterToughnessTypes.h"
#include "../Skills/IceSpikeDamage.h"

thread_local EMonsterAttackForm MonsterToughness::ActiveForm = EMonsterAttackForm::Impact;

EMonsterAttackForm MonsterToughness::FormOf(const UDamageType* Type)
{
    if (!Type) return ActiveForm;
    if (Type->IsA<UBladeToughnessDamage>()) return EMonsterAttackForm::Blade;
    if (Type->IsA<UBluntToughnessDamage>()) return EMonsterAttackForm::Blunt;
    if (Type->IsA<UImpactToughnessDamage>()) return EMonsterAttackForm::Impact;
    // 冰锥是穿刺；火球与腐液等法术按冲击结算。
    if (Type->IsA<UIceSpikeDamage>()) return EMonsterAttackForm::Blade;
    // 怪物对玩家的攻击不进入韧性结算，形式只作记录。
    return ActiveForm;
}

EMonsterAttackForm MonsterToughness::FormOf(const TSubclassOf<UDamageType>& Type)
{
    return Type ? FormOf(Type->GetDefaultObject<UDamageType>()) : ActiveForm;
}

TSubclassOf<UDamageType> MonsterToughness::DamageTypeFor(EMonsterAttackForm Form)
{
    switch (Form)
    {
    case EMonsterAttackForm::Blade: return UBladeToughnessDamage::StaticClass();
    case EMonsterAttackForm::Blunt: return UBluntToughnessDamage::StaticClass();
    default: return UImpactToughnessDamage::StaticClass();
    }
}

const TCHAR* MonsterToughness::FormName(EMonsterAttackForm Form)
{
    switch (Form)
    {
    case EMonsterAttackForm::Blade: return TEXT("锐器");
    case EMonsterAttackForm::Blunt: return TEXT("钝器");
    default: return TEXT("冲击");
    }
}