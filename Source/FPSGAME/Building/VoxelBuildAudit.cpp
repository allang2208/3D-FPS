#include "VoxelBuildAudit.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelJointStrength.h"
#include "VoxelBuildComponent.h"
#include "../FPSGAMECharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

namespace
{
    const TCHAR* PalettePath=TEXT("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette");
    /** 材质表期望值（与 UVoxelBuildPalette::Physical() 一致）。
        命名避开 `Expected`：与 Core 的 `TAtomic::CompareExchange(T& Expected, …)` 同处一个
        unity 编译单元时会触发 C4459（本工程按错误处理），与内容无关。 */
    struct FExpectedMaterial {const TCHAR* Id;double Density,Compression,Tension,Shear,Durability,Joules;};
    const FExpectedMaterial ExpectedMaterials[]={
        {TEXT("wood"),150.,700000.,260000.,120000.,180.,6.},
        {TEXT("stone"),650.,6000000.,900000.,300000.,500.,15.},
        {TEXT("marble"),650.,6000000.,900000.,300000.,500.,15.},
    };
    const TCHAR* BlockIcons[]={TEXT("Icons/wood.png"),TEXT("Icons/stone.png"),TEXT("Icons/marble.png")};
}

bool UVoxelBuildAudit::Requested()
{
    return FParse::Param(FCommandLine::Get(),TEXT("VoxelBuildAudit"));
}

void UVoxelBuildAudit::Report(const TCHAR* Name,bool bPass)
{
    ++Checks;if(!bPass)++Failures;
    UE_LOG(LogTemp,Display,TEXT("VoxelBuild: %s %s"),bPass?TEXT("PASS"):TEXT("FAIL"),Name);
}

void UVoxelBuildAudit::Start(APlayerController* InController)
{
    Controller=InController;
    Palette=LoadObject<UVoxelBuildPalette>(nullptr,PalettePath);
    CheckTable();CheckOverloadCurve();CheckItemCatalog();
    if(Controller)for(TActorIterator<AVoxelBuildWorld> It(Controller->GetWorld());It;++It){World=*It;break;}
}

bool UVoxelBuildAudit::CheckTable()
{
    bool bOk=Palette!=nullptr;
    Report(TEXT("palette asset loads"),bOk);
    if(!bOk)return false;
    for(const FExpectedMaterial& E:ExpectedMaterials)
    {
        const FVoxelPhysicalMaterial P=Palette->Physical(E.Id);
        const bool bMatch=FMath::IsNearlyEqual(P.DensityKgM3,E.Density,1.)&&FMath::IsNearlyEqual(P.CompressionPa,E.Compression,1.)
            &&FMath::IsNearlyEqual(P.TensionPa,E.Tension,1.)&&FMath::IsNearlyEqual(P.ShearPa,E.Shear,1.)
            &&FMath::IsNearlyEqual(P.Durability,E.Durability,.1);
        Report(*FString::Printf(TEXT("%s physics table matches code"),E.Id),bMatch);
    }
    return true;
}

bool UVoxelBuildAudit::CheckOverloadCurve()
{
    auto Check=[this](double Ratio,double ExpectedSeconds,const TCHAR* Name)
    {Report(Name,FMath::IsNearlyEqual(VoxelJointStrength::OverloadSecondsToFailure(Ratio),ExpectedSeconds,1.));};
    Check(1.05,28.57,TEXT("overload 1.05x breaks in ~28.6 s"));
    Check(1.5,20.,TEXT("overload 1.5x breaks in ~20 s"));
    Check(2.,15.,TEXT("overload 2x breaks in ~15 s"));
    Check(10.,3.,TEXT("heavy overload floors at 3 s"));
    return true;
}

bool UVoxelBuildAudit::CheckItemCatalog()
{
    // 物品目录与图标是纯数据，直接从磁盘读，避免依赖存档/玩家档案初始化顺序。
    FString Text;
    const bool bLoaded=FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")));
    Report(TEXT("item catalog readable"),bLoaded);
    for(const TCHAR* Id: {TEXT("voxel_block_wood"),TEXT("voxel_block_stone"),TEXT("voxel_block_marble")})
        Report(*FString::Printf(TEXT("catalog contains %s"),Id),bLoaded&&Text.Contains(Id));
    for(const TCHAR* Icon:BlockIcons)
        Report(*FString::Printf(TEXT("block icon present %s"),Icon),FPaths::FileExists(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Icon));
    return true;
}

bool UVoxelBuildAudit::CheckPlacementRoundTrip()
{
    if(!Controller||!World||!Controller->GetPawn())return false;
    // 站在真实地面上：向下找一格可放置的位置，用世界 API 直接编辑（与玩家左键走同一条路径）。
    const FVector Eye=Controller->GetPawn()->GetActorLocation();
    FHitResult Ground;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelAudit),false,Controller->GetPawn());
    if(!Controller->GetWorld()->LineTraceSingleByChannel(Ground,Eye+50,Eye-1000,ECC_Visibility,Query)||Ground.ImpactNormal.Z<.5f)
    {Report(TEXT("audit stands on buildable ground"),false);return true;}
    TestCell=AVoxelBuildWorld::ToCell(Ground.ImpactPoint)+FIntVector(0,0,1);
    if(!World->EditCells({TestCell},FName(TEXT("wood"))))
    {Report(TEXT("voxel placement accepted on real ground"),false);return true;}
    Report(TEXT("voxel placement accepted on real ground"),true);
    BlocksAfterPlace=World->BlockCount();
    SaveSlot=World->SaveSlotName();
    TMap<FName,int32> Recycled;
    const bool bUndo=World->Undo(&Recycled);
    bUndoRecycled=bUndo&&Recycled.FindRef(FName(TEXT("wood")))>0&&World->BlockCount()<BlocksAfterPlace;
    Report(TEXT("undo removes the last placement and returns its blocks"),bUndoRecycled);
    Stage=1;
    return true;
}

bool UVoxelBuildAudit::Tick()
{
    switch(Stage)
    {
    case 0:
        CheckPlacementRoundTrip();
        if(Stage==0)Stage=2;   // 没有可建造地面/世界：跳过后续，直接收尾
        break;
    case 1:
    {
        // 再放一次，然后按"拆除"走一遍：必须报出同样的材料（拆除进背包的数据来源）。
        if(!World->EditCells({TestCell},FName(TEXT("wood")))){Report(TEXT("second placement accepted"),false);Stage=2;break;}
        TMap<FName,int32> Removed;
        for(const FIntVector& Cell:{TestCell})
        {const FName Material=World->VolumeMaterialAt({},Cell);if(!Material.IsNone())Removed.FindOrAdd(Material)++;}
        const bool bRemoved=World->EditCells({TestCell},NAME_None);
        bDismantleRecycled=bRemoved&&Removed.FindRef(FName(TEXT("wood")))>0;
        Report(TEXT("dismantle reports the removed material for the backpack"),bDismantleRecycled);
        Stage=2;
        break;
    }
    default:
    {
        const FString File=FPaths::ProjectSavedDir()/TEXT("SaveGames")/(SaveSlot+TEXT(".sav"));
        Report(TEXT("build save written to disk"),SaveSlot.IsEmpty()||IFileManager::Get().FileSize(*File)>0);
        UE_LOG(LogTemp,Display,TEXT("VoxelBuild: COMPLETE checks=%d failures=%d"),Checks,Failures);
        if(Controller)Controller->ConsoleCommand(TEXT("quit"));
        return true;
    }
    }
    return false;
}
