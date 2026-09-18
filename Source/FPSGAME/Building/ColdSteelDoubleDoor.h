#pragma once

#include "CoreMinimal.h"
#include "ColdSteelWindow.h"
#include "ColdSteelDoubleDoor.generated.h"

/**
 * 2×2 m 双开门（两扇对开）。开合逻辑、铰链贴面、被挡反向、玩家不参与阻塞判定、整体换材质等
 * 全部沿用 `AColdSteelWindow`——那套逻辑本来就是"双扇平开"，门只是另一组尺寸与网格：
 *   框架 20 × 200 × 200 cm（占格 (1,10,10)，正好 10×10 格），边梃 8 → 洞口 184×184；
 *   两扇各 91.5 × 183 × 5（门扇比窗扇厚一档），每扇靠中缝一侧一个 Ø8 圆形把手（距地约 1.08 m）。
 *
 * 网格在 `SourceAssets/DoubleDoor20260918/`，默认开角 85°（与窗同一理由：贯通把手的摆向侧会扫框，
 * 这里把手距铰链 85.5 cm、凸出 2.5 cm，85° 时余量约 5 cm）。
 */
UCLASS()
class FPSGAME_API AColdSteelDoubleDoor : public AColdSteelWindow
{
    GENERATED_BODY()
public:
    AColdSteelDoubleDoor();
};
