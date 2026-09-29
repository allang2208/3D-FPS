#include "ProductionFallingTree.h"
#include "ProductionResource.h"
#include "ProductionHarvestAssets.h"
#include "ProductionHarvestSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/NaniteAssemblyData.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Materials/MaterialInterface.h"

// Falling-tree render path diagnostic: one line per felled tree, so the log shows whether the
// cut upper section really renders its Nanite leaf assembly or degrades to classic LODs /
// fallback geometry (the "tree turns into triangles" report of 2026-09-25).
static TAutoConsoleVariable<int32> CVarTreeFallDiag(
    TEXT("fps.Harvest.TreeFallDiag"),1,
    TEXT("1=log one render-path diagnostic line per felled tree, 0=off."),ECVF_Default);

// 2026-09-26 三角碎片排查：组合部件摆在哪里由 FNaniteAssemblyData::Nodes 决定（变换空间、局部变换、
// 骨骼绑定），python 只读得到 Parts。这里把关键统计打出来，和源树逐项对比——若 Nodes 为空、
// 没有骨骼绑定、或平移量比源树大一个数量级，就是"整块树冠塌成一堆大平板"的原因。
static void LogNaniteAssemblyDiag(const TCHAR* Label,const USkeletalMesh* Mesh)
{
    if(!Mesh)
    {
        UE_LOG(LogTemp,Display,TEXT("FALLDIAG_ASM %s <no mesh>"),Label);
        return;
    }
#if WITH_EDITORONLY_DATA
    const FNaniteAssemblyData& Data=Mesh->GetNaniteSettings().NaniteAssemblyData;
    float MaxTranslation=0.f;
    int32 BoneRelative=0,NoInfluence=0,NegativeBone=0,OutOfRangeBone=0;
    const int32 BoneCount=Mesh->GetRefSkeleton().GetNum();
    for(const FNaniteAssemblyNode& Node:Data.Nodes)
    {
        if(Node.TransformSpace==ENaniteAssemblyNodeTransformSpace::BoneRelative)++BoneRelative;
        if(Node.BoneInfluences.Num()==0)++NoInfluence;
        MaxTranslation=FMath::Max(MaxTranslation,Node.Transform.GetTranslation().Size());
        for(const FNaniteAssemblyBoneInfluence& Influence:Node.BoneInfluences)
        {
            if(Influence.BoneIndex<0)++NegativeBone;
            else if(Influence.BoneIndex>=BoneCount)++OutOfRangeBone;
        }
    }
    UE_LOG(LogTemp,Display,
        TEXT("FALLDIAG_ASM %s mesh=%s parts=%d nodes=%d valid=%d bones=%d bone_relative=%d no_influence=%d bad_bone=%d max_node_translation=%.1f"),
        Label,*GetNameSafe(Mesh),Data.Parts.Num(),Data.Nodes.Num(),Data.IsValid()?1:0,BoneCount,
        BoneRelative,NoInfluence,NegativeBone+OutOfRangeBone,MaxTranslation);
#else
    // Nanite assembly authoring settings are stripped from standalone builds.
    UE_LOG(LogTemp,Display,TEXT("FALLDIAG_ASM %s mesh=%s editor_assembly_data=unavailable"),Label,*GetNameSafe(Mesh));
#endif
}

AProductionFallingTree::AProductionFallingTree()
{
    PrimaryActorTick.bCanEverTick=true;
    Tree=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("CutUpperTree"));
    Tree->SetMobility(EComponentMobility::Movable);
    RootComponent=Tree;Tree->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Tree->SetCanEverAffectNavigation(false);Tree->SetComponentTickEnabled(false);
    // 断口封盖（2026-09-26 用户反馈"倒下的树断面中空"）：保底路径用原树网格 + 材质 step(H,P.z)
    // 把切口以下裁掉，而原树干是空心筒，断口能看到中空；这里贴一片真实切面封住。
    // 网格顶点就保存在树本地坐标（切面在 Z=42），组件不需要任何偏移；不碰撞、不导航、不投影（在筒内）。
    CutCap=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CutFaceCap"));
    CutCap->SetupAttachment(Tree);
    CutCap->SetMobility(EComponentMobility::Movable);
    CutCap->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CutCap->SetCanEverAffectNavigation(false);
    CutCap->SetComponentTickEnabled(false);
    CutCap->SetCastShadow(false);
    CutCap->SetVisibility(false);
}
static TAutoConsoleVariable<int32> CVarTreeFallUseSourceMesh(
    TEXT("fps.Harvest.TreeFallUseSourceMesh"),0,
    TEXT("0 (default)=fell the re-authored SK_CutUpper_* severed section: true geometric cut, baked ")
    TEXT("ring-grain cap (2026-09-29 用户要求从树干中截断，非整树遮罩). 1=source mesh + material mask.")
    ,ECVF_Default);
// 2026-09-28 用户第四轮反馈（"整棵模型倒伏非常不自然，应该截断"）推翻 09-26 的第三次取舍：
// 默认恢复"42 cm 截断 + 断口封盖"。当时弃用截断的原因——切口以上外张的板根树皮（A/B 超出
// 封盖 ~6cm、C ~3.5cm、D ~1cm，实测剖面见 Tools/Production/probe_tree_flare_profile.py）
// 悬空支棱——已由 M_FallingPoplar 遮罩的径向裁剪（HarvestCutRadius/HarvestFlareTop，
// Tools/Production/patch_falling_poplar_flare_clamp.py 落盘）解决：板根带内裁到封盖半径，
// 封盖重新盖满断口。设 0 可回 09-26 的整树倒伏表现对照，不需重新构建。
static TAutoConsoleVariable<int32> CVarTreeFallCutAtStump(
    TEXT("fps.Harvest.TreeFallCutAtStump"),1,
    TEXT("1 (default)=cut the falling tree at the stump height (42cm material mask + cut-face cap ")
    TEXT("+ radial flare clamp), 0=fell the whole original tree with no cut."),ECVF_Default);

// 径向裁剪表（树本地 cm，2026-09-28 实测）：ClampRadius=SM_CutCap_* 包围盒最大半宽+0.2
// （A:39.74 B:39.60 C:26.05 D:13.74），保证可见断口圆盘不超过封盖；FlareBandTop=板根
// 剖面回落到干身半径的高度（A/B/D ~85cm，C 只到 62——C 是丛生形，z≥70cm 起半径增大是
// 真实分干，裁到 90 会砍掉树干）。带内 [CutHeight,FlareBandTop) 超半径的板根树皮被遮罩裁掉。
static constexpr float CutClampRadiusCm[4]={40.f,39.8f,26.3f,13.9f};
static constexpr float FlareBandTopCm[4]={90.f,90.f,62.f,90.f};

// 内壁舌头方位角掩码表（2026-09-29 用户第六轮反馈"倒木还有一根突出物"，probe_stub_sectors 实测）：
// SK_CutUpper_* 树干内壁层（r 15-30）在个别扇区下垂到 z≈80（其余扇区 ~200 才开始），且该扇区
// 外皮稀疏——倒伏后内壁从缺口露出=切口端上方"光滑发黑细杆"。M_CutUpperMotion 的 Custom 节点按
// (yaw 窗 Y±W)∧(60<z<ZMax)∧(r<31) 掩掉内壁舌头（60 以下不碰=年轮断面封盖；r<31=保留外皮）。
// Y/W 单位度（环形回绕），ZMax 树本地 cm；W=0 或 ZMax=0 ⇒ 掩码全关（材质默认 0，安全）。
// C 丛生形内壁即真实干身，禁用（Y 任意、W=0）。
static constexpr float StubYawDeg[4]={337.5f,347.5f,0.f,30.f};
static constexpr float StubYawTolDeg[4]={25.f,22.f,0.f,18.f};
static constexpr float StubZMaxCm[4]={210.f,210.f,0.f,210.f};

void AProductionFallingTree::InitializeFall(const FProductionResource& Resource,const FVector& Direction)
{
    FProductionResource Target=Resource;Target.Direction=Direction;
    Plan=FProductionTreeFallPlan::Make(Target);
    const int32 Variant=ProductionHarvestAssets::TreeVariant(Resource.Mesh);
    // 2026-09-29 用户第五轮反馈（"要从树干中截断倒下，不是整树倒下再放树桩"）：默认改回重制的
    // SK_CutUpper_* 真切断网格——它就是 42 cm 以上的上半段（自带年轮断面封盖），树桩留在原地，
    // 倒下的是被锯下来的那一段，不是"整树＋材质遮罩"。2026-09-29 实测其 Nanite 组合数据与源树
    // 逐项一致（FALLDIAG_ASM parts=12 nodes=1250 bones=1687），使用标志齐全；当年 09-25 的
    // "树冠塌三角"成因未明但资产无恙，若复现可 fps.Harvest.TreeFallUseSourceMesh 1 一键退回
    // "原树网格 + 材质遮罩"路径（那套材质已从备份恢复原状，不含径向裁剪）。
    // 板根裙边：几何路径由 M_CutUpperMotion 的径向裁剪（同式 saturate(step(T,P.z)+step(len,R))）
    // 裁掉；原树路径的 M_FallingPoplar 保持出厂原样（无裁剪参数，设参为无害空操作）。
    const bool bUseSourceMesh=CVarTreeFallUseSourceMesh.GetValueOnGameThread()!=0;
    const bool bCutAtStump=CVarTreeFallCutAtStump.GetValueOnGameThread()!=0;
    const float MaskHeight=bCutAtStump?Plan.CutHeight:-1000.f;
    // 截断时启用板根径向裁剪；不截断时半径放到 1e5、带顶 0（遮罩 saturate(1+..) 恒 1，等于不裁）。
    const int32 ClampVariant=FMath::Clamp(Variant,0,3);
    const float ClampRadius=bCutAtStump?CutClampRadiusCm[ClampVariant]:100000.f;
    const float FlareBandTop=bCutAtStump?FlareBandTopCm[ClampVariant]:0.f;
    USkeletalMesh* SourceTreeMesh=bUseSourceMesh?Cast<USkeletalMesh>(Resource.Mesh.ResolveObject()):nullptr;
    if(!SourceTreeMesh)
        SourceTreeMesh=Cast<USkeletalMesh>(ProductionHarvestAssets::FallingMesh(Variant).ResolveObject());
    Tree->SetSkeletalMesh(SourceTreeMesh);
    Tree->SetBoundsScale(1.15f);
    SetActorTransform(Resource.Transform);InitialRotation=Resource.Transform.GetRotation();
    Scale=Resource.Transform.GetScale3D();EffectSeed=Resource.Seed;
    LocalFallDirection=InitialRotation.UnrotateVector(Plan.Direction);
    for(int32 Index=0;Index<Tree->GetNumMaterials();++Index)
    {
        UMaterialInterface* Source=Tree->GetMaterial(Index);
        if(bUseSourceMesh)
        {
            // 原树网格的槽是站立树的 MI_BlackPoplarPCG_*（没有切口遮罩）。换成上一代倒树材质
            // M_FallingPoplar 的实例：它带 step(H,P.z) 遮罩，且 Harvest* 参数名与下面设置的完全一致。
            const FString Slot=Tree->GetMaterialSlotNames().IsValidIndex(Index)
                ?Tree->GetMaterialSlotNames()[Index].ToString():FString();
            const bool bFoliage=Slot.Contains(TEXT("Foliage"));
            if(UMaterialInterface* Cut=Cast<UMaterialInterface>(
                ProductionHarvestAssets::FallingMaterial(bFoliage?1:0).TryLoad()))
                Source=Cut;
        }
        if(auto* MID=Source?UMaterialInstanceDynamic::Create(Source,this):nullptr)
        {
            MID->SetScalarParameterValue(TEXT("HarvestCutHeight"),MaskHeight);
            MID->SetScalarParameterValue(TEXT("HarvestTreeHeight"),Plan.LocalHeight);
            MID->SetScalarParameterValue(TEXT("HarvestCutRadius"),ClampRadius);
            MID->SetScalarParameterValue(TEXT("HarvestFlareTop"),FlareBandTop);
            // 内壁舌头方位角掩码（材质无这些参数时为无害空操作；C 变体 W=0 关闭）
            MID->SetScalarParameterValue(TEXT("HarvestStubYaw"),StubYawDeg[ClampVariant]);
            MID->SetScalarParameterValue(TEXT("HarvestStubYawTol"),StubYawTolDeg[ClampVariant]);
            MID->SetScalarParameterValue(TEXT("HarvestStubZMax"),StubZMaxCm[ClampVariant]);
            Tree->SetMaterial(Index,MID);Materials.Add(MID);
        }
    }
    // 断口封盖：默认路径（原树网格 + 42 cm 材质遮罩 + 径向裁剪）挂上 SM_CutCap_*，断面就是
    // M_FallingCutEnd 的年轮切面（T_PoplarEndReference），倒树底部不再露出空心筒口。
    // 封盖顶点就在树本地坐标里（切面 Z=42），直接挂在 Tree 下、不加偏移；加入 Materials 后
    // 与树干一起抖动淡出（Tree 隐藏时随 bPropagateToChildren 一起隐藏）。
    // 整树倒伏（TreeFallCutAtStump 0）与重制网格（UseSourceMesh 0，自带封盖）时不挂。
    CutCap->SetStaticMesh(nullptr);CutCap->SetVisibility(false);
    if(bUseSourceMesh&&bCutAtStump)
        if(UStaticMesh* CapMesh=Cast<UStaticMesh>(ProductionHarvestAssets::CutCap(Variant).ResolveObject()))
        {
            CutCap->SetStaticMesh(CapMesh);
            CutCap->SetRelativeLocation(FVector::ZeroVector);
            CutCap->SetRelativeScale3D(FVector::OneVector);
            if(UMaterialInterface* CapSource=CapMesh->GetMaterial(0))
                if(auto* CapMID=UMaterialInstanceDynamic::Create(CapSource,this))
                {
                    CapMID->SetScalarParameterValue(TEXT("HarvestCutHeight"),Plan.CutHeight);
                    CapMID->SetScalarParameterValue(TEXT("HarvestTreeHeight"),Plan.LocalHeight);
                    CapMID->SetScalarParameterValue(TEXT("HarvestFade"),1.f);
                    CutCap->SetMaterial(0,CapMID);Materials.Add(CapMID);
                }
            CutCap->SetVisibility(true);
        }
    if(CVarTreeFallDiag.GetValueOnGameThread()!=0)
    {
        FString SlotInfo;
        const TArray<FName>& SlotNames=Tree->GetMaterialSlotNames();
        for(int32 Index=0;Index<Tree->GetNumMaterials();++Index)
        {
            const FString Slot=SlotNames.IsValidIndex(Index)?SlotNames[Index].ToString():FString::Printf(TEXT("#%d"),Index);
            SlotInfo+=FString::Printf(TEXT("%s=%s "),*Slot,*GetNameSafe(Tree->GetMaterial(Index)));
        }
        UE_LOG(LogTemp,Display,TEXT("FALLDIAG mesh=%s nanite_data=%d force_disable_nanite=%d disallow_nanite=%d skinned_nanite_allowed=%d lods=%d predicted_lod=%d cut_at_stump=%d clamp_r=%.1f flare_top=%.0f stub_yaw=%.1f+-%.0f stub_zmax=%.0f cap=%s slots=[%s]"),
            *GetNameSafe(Tree->GetSkeletalMeshAsset()),Tree->HasValidNaniteData()?1:0,Tree->IsForceDisableNanite()?1:0,
            Tree->IsDisallowNanite()?1:0,USkinnedMeshComponent::ShouldRenderNaniteSkinnedMeshes()?1:0,
            Tree->GetNumLODs(),Tree->GetPredictedLODLevel(),bCutAtStump?1:0,ClampRadius,FlareBandTop,
            StubYawDeg[ClampVariant],StubYawTolDeg[ClampVariant],StubZMaxCm[ClampVariant],
            *GetNameSafe(CutCap->GetStaticMesh()),*SlotInfo);
        // 与源树对比：源树此刻已在场景里加载，用 FindObject 取，不触发同步加载。
        // 走原树网格时 falling 与 source 会相同，此时另行报告重制版网格（仅当它已被加载）。
        const TCHAR Letter=static_cast<TCHAR>(TEXT('A')+FMath::Clamp(Variant,0,3));
        LogNaniteAssemblyDiag(TEXT("falling"),Tree->GetSkeletalMeshAsset());
        const FString SourcePath=FString::Printf(
            TEXT("/Game/WorldGeneration/TemperateHills/SK_BlackPoplarPCG_%c.SK_BlackPoplarPCG_%c"),Letter,Letter);
        LogNaniteAssemblyDiag(TEXT("source"),FindObject<USkeletalMesh>(nullptr,*SourcePath));
        const FString AuthoredPath=FString::Printf(
            TEXT("/Game/Items/HarvestTimber/SK_CutUpper_%c.SK_CutUpper_%c"),Letter,Letter);
        if(const USkeletalMesh* Authored=FindObject<USkeletalMesh>(nullptr,*AuthoredPath))
            LogNaniteAssemblyDiag(TEXT("authored"),Authored);
    }
    if(auto* Sound=Cast<USoundBase>(ProductionHarvestAssets::TreeSound(false).ResolveObject()))
        UGameplayStatics::PlaySoundAtLocation(this,Sound,Plan.Pivot,.7f,.94f+(EffectSeed%13)*.01f);
    SetLifeSpan(Plan.ReleaseSeconds()+Plan.FadeSeconds+.1f);
}
void AProductionFallingTree::Tick(float Delta)
{
    Super::Tick(Delta);Elapsed+=Delta;
    const float FallTime=Elapsed-Plan.AnticipationSeconds;
    float Angle=0;
    if(FallTime<0)
    {
        const float T=Elapsed/Plan.AnticipationSeconds;
        Angle=1.2f*T*T*(3-2*T)+.22f*FMath::Sin(T*2*PI)*(1-T);
    }
    else
    {
        const float T=FMath::Clamp(FallTime/Plan.FallSeconds,0.f,1.f);
        Angle=FMath::Lerp(1.2f,Plan.LandingAngle,FMath::Pow(T,1.9f));
        if(T>=1)
        {
            const float ContactAge=FallTime-Plan.FallSeconds;
            Angle-=2.2f*FMath::Exp(-5.f*ContactAge)*FMath::Abs(FMath::Sin(10.f*ContactAge));
        }
    }
    const FQuat Rotation=FQuat(Plan.Axis,FMath::DegreesToRadians(Angle))*InitialRotation;
    SetActorLocationAndRotation(Plan.Pivot-Rotation.RotateVector(Plan.LocalHinge*Scale),Rotation);
    const float Speed=(Angle-PreviousAngle)/FMath::Max(Delta,.001f);PreviousAngle=Angle;
    const float ContactAge=FallTime-Plan.FallSeconds;
    const float TargetBend=ContactAge>=0?45.f*FMath::Exp(-4.f*ContactAge)*FMath::Sin(11.f*ContactAge):-FMath::Min(55.f,Speed*.5f);
    CrownBend=FMath::FInterpTo(CrownBend,TargetBend,Delta,7.f);
    const float Fade=1-FMath::Clamp((Elapsed-Plan.ReleaseSeconds())/Plan.FadeSeconds,0.f,1.f);
    const FVector Bend=LocalFallDirection*CrownBend;
    for(auto& MID:Materials)
    {
        MID->SetVectorParameterValue(TEXT("HarvestCrownBend"),FLinearColor(Bend.X,Bend.Y,Bend.Z,0));
        MID->SetScalarParameterValue(TEXT("HarvestFade"),Fade);
    }
    auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();
    if(!CrownTouched&&Angle>=Plan.CrownAngle)
    {CrownTouched=true;if(Harvest)Harvest->Burst(true,Plan.CrownContact,EffectSeed,true);}
    if(!Landed&&ContactAge>=0)
    {
        Landed=true;
        if(Harvest)Harvest->Burst(true,Plan.TrunkContact,EffectSeed+1,true);
        if(auto* Sound=Cast<USoundBase>(ProductionHarvestAssets::TreeSound(true).ResolveObject()))
            UGameplayStatics::PlaySoundAtLocation(this,Sound,Plan.TrunkContact,.9f,.92f+(EffectSeed%15)*.01f);
    }
    if(Fade<=0){Tree->SetVisibility(false,true);SetActorTickEnabled(false);}
}
