#include "ColdSteelDoubleDoor.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    // SourceAssets/DoubleDoor20260918 生成；换外观只改这两个默认值。
    // 名字按类区分（unity 合并块里匿名命名空间是共享的，同名常量会撞 C2374）。
    const TCHAR* DoubleDoorFrameMesh=TEXT("/Game/Props/DoubleDoor20260918/SM_DoubleDoorFrame_200.SM_DoubleDoorFrame_200");
    const TCHAR* DoubleDoorLeafMesh=TEXT("/Game/Props/DoubleDoor20260918/SM_DoubleDoorLeaf_200.SM_DoubleDoorLeaf_200");
}

AColdSteelDoubleDoor::AColdSteelDoubleDoor()
{
    // 与 build_double_door_meshes_20260918.py 的尺寸常量对齐：框边梃 8、门扇板厚 5（半厚 2.5）。
    FrameMemberCm=8.f;
    LeafHalfThicknessCm=2.5f;
    // 门沿用单扇门那套：开完 6 秒自动关上（窗是保持打开）。
    AutoCloseSeconds=6.f;

    static ConstructorHelpers::FObjectFinder<UStaticMesh> FrameAsset(DoubleDoorFrameMesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> LeafAsset(DoubleDoorLeafMesh);
    if(FrameAsset.Succeeded())Frame->SetStaticMesh(FrameAsset.Object);
    if(LeafAsset.Succeeded())
    {
        LeafLeft->SetStaticMesh(LeafAsset.Object);
        LeafRight->SetStaticMesh(LeafAsset.Object);
    }
}
