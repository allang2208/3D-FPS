#pragma once

#include "CoreMinimal.h"
#include "GameFramework/DamageType.h"
#include "MonsterToughnessTypes.generated.h"

/** 命中形式：决定这一次命中按哪条抗性折算削韧。 */
UENUM(BlueprintType)
enum class EMonsterAttackForm : uint8
{
    /** 锐器：刃口切割与突刺（剑、斧刃、冰锥）。 */
    Blade UMETA(DisplayName="锐器"),
    /** 钝器：锤击、配重、枪托与握把砸击。 */
    Blunt UMETA(DisplayName="钝器"),
    /** 冲击：爆炸、坍塌、撞击，以及未标注来源的伤害。 */
    Impact UMETA(DisplayName="冲击")
};

/** 三种形式各带一个伤害类型，作为攻击端到怪物受击端的唯一凭证。 */
UCLASS()
class FPSGAME_API UBladeToughnessDamage : public UDamageType { GENERATED_BODY() };
UCLASS()
class FPSGAME_API UBluntToughnessDamage : public UDamageType { GENERATED_BODY() };
UCLASS()
class FPSGAME_API UImpactToughnessDamage : public UDamageType { GENERATED_BODY() };

namespace MonsterToughness
{
    /**
     * 形式削韧系数：同一次伤害按形式折算成不同程度的韧性伤害。
     * 钝器最擅长破韧，冲击次之，锐器最低；未标注来源按冲击。
     */
    inline constexpr float BladePower = 1.f;
    inline constexpr float BluntPower = 1.6f;
    inline constexpr float ImpactPower = 1.25f;

    inline float FormPower(EMonsterAttackForm Form)
    {
        switch (Form)
        {
        case EMonsterAttackForm::Blade: return BladePower;
        case EMonsterAttackForm::Blunt: return BluntPower;
        default: return ImpactPower;
        }
    }

    /** 韧性伤害 = 实际伤害 × 形式系数 × (1 − 该形式抗性)。 */
    inline float ToughnessDamage(float Damage, EMonsterAttackForm Form, float Resistance)
    {
        return FMath::Max(0.f, Damage) * FormPower(Form) * (1.f - FMath::Clamp(Resistance, 0.f, .9f));
    }

    /**
     * 当前结算的命中形式。多数近战/技能路径不带伤害类型，攻击端在调用伤害前
     * 用 FScopedForm 标注；受击端同步读取。伤害类型能自证形式时优先用类型。
     * 线程局部变量不能带 DLL 导出宏（与 CombatFormulaRuntime 的既有口径一致）。
     */
    extern thread_local EMonsterAttackForm ActiveForm;

    /** 作用域内标注命中形式，退出时还原。 */
    struct FScopedForm
    {
        EMonsterAttackForm Previous;
        explicit FScopedForm(EMonsterAttackForm Form) : Previous(ActiveForm) { ActiveForm = Form; }
        ~FScopedForm() { ActiveForm = Previous; }
    };

    /**
     * 解析命中形式。伤害类型能自证形式时以类型为准（冰锥=锐器、刃/钝/冲击专用类型），
     * 其余情况回退到当前作用域标注，最终缺省为冲击。
     */
    FPSGAME_API EMonsterAttackForm FormOf(const UDamageType* Type);
    /** 同上，接受 TakeDamage 事件里的伤害类型类。 */
    FPSGAME_API EMonsterAttackForm FormOf(const TSubclassOf<UDamageType>& Type);
    /** 该形式对应的伤害类型类，供攻击端在 ApplyDamage/ApplyPointDamage 时携带。 */
    FPSGAME_API TSubclassOf<UDamageType> DamageTypeFor(EMonsterAttackForm Form);
    /** 形式名（锐器/钝器/冲击），用于日志与调参文档。 */
    FPSGAME_API const TCHAR* FormName(EMonsterAttackForm Form);
}