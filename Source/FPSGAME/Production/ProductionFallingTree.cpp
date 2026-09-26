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
    TEXT("fps.Harvest.TreeFallUseSourceMesh"),1,
    TEXT("1 (default)=fell the source tree mesh with the material-space cut: proven crown rendering, ")
    TEXT("no re-authored Nanite assembly. 0=use the re-authored SK_CutUpper_* mesh for comparison."),
    ECVF_Default);
// 2026-09-26 用户第三次反馈：倒树**不该做截断**（原设计就是整棵原树模型倒下）。默认 0＝不截断，
// 材质遮罩的 HarvestCutHeight 压到模型最低点以下（step 恒为 1），封盖也不挂。设 1 可切回
// "42 cm 截断 + 断口封盖"的旧表现做对照，不需要重新构建。
static TAutoConsoleVariable<int32> CVarTreeFallCutAtStump(
    TEXT("fps.Harvest.TreeFallCutAtStump"),0,
    TEXT("1=cut the falling tree at the stump height (42cm material mask + cut-face cap), ")
    TEXT("0 (default)=fell the whole original tree with no cut."),ECVF_Default);

void AProductionFallingTree::InitializeFall(const FProductionResource& Resource,const FVector& Direction)
{
    FProductionResource Target=Resource;Target.Direction=Direction;
    Plan=FProductionTreeFallPlan::Make(Target);
    const int32 Variant=ProductionHarvestAssets::TreeVariant(Resource.Mesh);
    // 2026-09-26 三角碎片修复：重制的 SK_CutUpper_* 只有 LOD0 树干几何，树冠完全靠 Nanite 组合的
    // Nodes（变换空间/局部变换/骨骼绑定）摆位；那份数据在重制流程里没能保住，整个树冠塌成一堆
    // 几米大的平板。这里默认改用**站立树正在用的同一份原树网格**（画面里已加载，零额外加载，
    // 骨架/蒙皮/组合都是已验证可渲染的）。想把重制版调回来对照时把 CVar 设 0 即可，不需要重新构建。
    //
    // 2026-09-26 用户第三次反馈（"原来设计应该是树木原模型倒下，没有做截断处理"）：整棵树直接倒，
    // 不在 42 cm 处截断——否则切口以上还会留着向外张开的根部树皮（板根）悬在空中。所以默认把
    // 材质遮罩的 HarvestCutHeight 压到模型最低点以下（遮罩恒为 1＝等于不裁），断口封盖也只在
    // 需要截断时才挂。旧表现可用控制台 fps.Harvest.TreeFallCutAtStump 1 对照。
    const bool bUseSourceMesh=CVarTreeFallUseSourceMesh.GetValueOnGameThread()!=0;
    const bool bCutAtStump=CVarTreeFallCutAtStump.GetValueOnGameThread()!=0;
    const float MaskHeight=bCutAtStump?Plan.CutHeight:-1000.f;
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
            Tree->SetMaterial(Index,MID);Materials.Add(MID);
        }
    }
    // 断口封盖：只在"材质遮罩在 42 cm 处截断"时才需要（fps.Harvest.TreeFallCutAtStump 1）；
    // 默认整棵树倒下、不截断，所以不挂封盖。重制网格 `SK_CutUpper_*` 自带真实封盖，也不需要。
    // 挂上时：封盖顶点就在树本地坐标里，直接挂在 Tree 下、不加偏移；材质 M_FallingCutEnd 带切面 UV
    // 与 HarvestFade，加入 Materials 后与树干一起抖动淡出（Tree 隐藏时随 bPropagateToChildren 一起隐藏）。
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
        UE_LOG(LogTemp,Display,TEXT("FALLDIAG mesh=%s nanite_data=%d force_disable_nanite=%d disallow_nanite=%d skinned_nanite_allowed=%d lods=%d predicted_lod=%d cut_at_stump=%d cap=%s slots=[%s]"),
            *GetNameSafe(Tree->GetSkeletalMeshAsset()),Tree->HasValidNaniteData()?1:0,Tree->IsForceDisableNanite()?1:0,
            Tree->IsDisallowNanite()?1:0,USkinnedMeshComponent::ShouldRenderNaniteSkinnedMeshes()?1:0,
            Tree->GetNumLODs(),Tree->GetPredictedLODLevel(),bCutAtStump?1:0,*GetNameSafe(CutCap->GetStaticMesh()),*SlotInfo);
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
