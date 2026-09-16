#pragma once
#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "VoxelBuildAudit.generated.h"

class AVoxelBuildWorld;
class APlayerController;
class UVoxelBuildPalette;

/**
 * 建筑系统的运行期验收（2026-09-16）。命令行 `-VoxelBuildAudit` 启动，跑到结束自动 `quit`。
 *
 * 负责验证的功能（每一项都对应玩家可见的契约）：
 *  1. 材质表：三种材质的密度/抗压/抗拉/抗剪/耐久与代码一致（防止数值被无声改回去）。
 *  2. 过载曲线：30 s 上限、最低 3 s、越超载越快（与解算器共用 VoxelJointStrength::OverloadSecondsToFailure）。
 *  3. 体素块物品：voxel_block_wood/stone/marble 存在于物品目录、可堆叠 999、图标文件在位（拆除/残骸回收依赖）。
 *  4. 放置-撤销-拆除闭环：在玩家脚下真实地面放置体素 → 撤销应"拆掉最近一批"并报出回收材料 → 直接拆除应
 *     报出同样的材料（对应"拆除进背包 / 撤销=拆除"的规则）。
 *  5. 存档往返：世界存档文件在编辑后被写盘（存在且字节数增长）。
 *
 * 不负责：视觉、手感、帧率、多人；这些仍由用户实测。
 */
UCLASS()
class FPSGAME_API UVoxelBuildAudit : public UObject
{
    GENERATED_BODY()
public:
    /** 命令行是否要求跑这次验收。 */
    static bool Requested();
    void Start(APlayerController* InController);
    /** 由控制器的定时器驱动；返回 true 表示已结束。 */
    bool Tick();
private:
    bool CheckTable();
    bool CheckOverloadCurve();
    bool CheckItemCatalog();
    bool CheckPlacementRoundTrip();
    void Report(const TCHAR* Name,bool bPass);
    UPROPERTY() TObjectPtr<APlayerController> Controller;
    UPROPERTY() TObjectPtr<AVoxelBuildWorld> World;
    UPROPERTY() TObjectPtr<UVoxelBuildPalette> Palette;
    int32 Checks=0,Failures=0,Stage=0;
    FIntVector TestCell=FIntVector(INT32_MAX);
    int32 BlocksAfterPlace=0;
    bool bUndoRecycled=false,bDismantleRecycled=false;
    FString SaveSlot;
};
