#pragma once
#include "CoreMinimal.h"
#include "VoxelBuildTypes.h"
class UVoxelBuildSave;

/** Plain payload, safe to encode and write on a worker. */
struct FVoxelDiskSnapshot
{
    int32 Version=4,CellSizeCm=20;
    FString WorldKey;
    TArray<FVoxelSavedCell> Cells;
    TArray<FVoxelFreeVolume> FreeVolumes;
    TMap<FVoxelBuildKey,float> Damage;
    TSet<FVoxelBrokenBond> BrokenBonds;
    TArray<FVoxelFragmentSave> Fragments;
    TSet<FVoxelBuildKey> LegacyProtected;
    TArray<FVoxelBuildPrefabInstance> Prefabs;
};
namespace VoxelPersistence
{
    /**
     * 审计 C6：Load 原先只返回裸指针，任何失败都让调用方只能报"版本不兼容"，
     * 既误导玩家、也没有日志、也不会回退到 Write 自己维护的 `.pre-structure` 备份。
     * 现在区分失败原因，让调用方能给出正确提示并尝试备份。
     */
    enum class ELoadResult : uint8
    {
        /** 读到完整有效的存档（Out 非空）。 */
        Ok,
        /** 槽位不存在或文件为空 —— 首次进入该世界，属正常情况，不应报错。 */
        Missing,
        /** 读到字节但 CRC/长度校验不过 —— 文件损坏。 */
        Corrupt,
        /** CRC 通过但反序列化失败或有尾随字节 —— 解析错误。 */
        ParseFailed,
        /** 旧版 USaveGame 反射格式（非 VBX3），可能缺少构件等字段。 */
        LegacyFormat,
        /** 无法读取槽位（IO 失败）。 */
        ReadFailed,
    };
    /** 供日志与状态行显示的可读原因；永不返回空串。 */
    const TCHAR* Describe(ELoadResult Result);

    /**
     * @param OutResult     失败原因（成功时为 Ok）
     * @param bAllowLegacy  是否接受旧版 USaveGame 反射格式（保留原行为：接受）
     *
     * 注意：Slot 是**槽位名**，内部会拼成 `<Saved>/SaveGames/<Slot>.sav`。
     * 要直接读某个具体文件（例如 `.pre-structure` 备份）请用 LoadFromFile。
     */
    UVoxelBuildSave* Load(const FString& Slot,ELoadResult& OutResult,bool bAllowLegacy=true);
    /** 从**完整文件路径**读取（审计 C6：备份文件不在槽位命名规则内，不能走 Load）。 */
    UVoxelBuildSave* LoadFromFile(const FString& FullPath,ELoadResult& OutResult,bool bAllowLegacy=true);
    FVoxelDiskSnapshot Take(UVoxelBuildSave* Source);
    bool Write(FString Slot,FVoxelDiskSnapshot Snapshot);
    /** 审计 C6：`.pre-structure` 备份路径（Write 会在首次写入前保留一份）。 */
    FString PreStructurePath(const FString& Slot);
}
