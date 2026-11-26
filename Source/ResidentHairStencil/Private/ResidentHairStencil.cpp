#include "ResidentHairStencil.h"
#include "GlobalShader.h"
#include "HairStrandsInterface.h"
#include "HAL/IConsoleManager.h"
#include "Modules/ModuleManager.h"
#include "PixelShaderUtils.h"
#include "PrimitiveSceneProxy.h"
#include "RenderGraphBuilder.h"
#include "RHIStaticStates.h"
#include "SceneRendering.h"
#include "PostProcess/PostProcessInputs.h"
#include "SceneViewExtension.h"
#include "ShaderCompilerCore.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, ResidentHairStencil)

class FResidentHairStencilPS : public FGlobalShader
{
    DECLARE_GLOBAL_SHADER(FResidentHairStencilPS);
    SHADER_USE_PARAMETER_STRUCT(FResidentHairStencilPS, FGlobalShader);
    class FSeparateStencil : SHADER_PERMUTATION_BOOL("SEPARATE_STENCIL");
    using FPermutationDomain = TShaderPermutationDomain<FSeparateStencil>;
    BEGIN_SHADER_PARAMETER_STRUCT(FParameters, )
        SHADER_PARAMETER(uint32, HairMaterialId)
        SHADER_PARAMETER(uint32, ResidentStencil)
        SHADER_PARAMETER(float, CoverageThreshold)
        SHADER_PARAMETER_RDG_TEXTURE(Texture2D<uint>, VisNodeIndex)
        SHADER_PARAMETER_RDG_TEXTURE(Texture2D<float>, Coverage)
        SHADER_PARAMETER_RDG_BUFFER_SRV(StructuredBuffer<FPackedHairVis>, VisNodeData)
        RENDER_TARGET_BINDING_SLOTS()
    END_SHADER_PARAMETER_STRUCT()

    static bool ShouldCompilePermutation(const FGlobalShaderPermutationParameters& Parameters)
    {
        return IsHairStrandsSupported(EHairStrandsShaderType::Strands, Parameters.Platform);
    }

    static void ModifyCompilationEnvironment(const FGlobalShaderPermutationParameters& Parameters, FShaderCompilerEnvironment& Environment)
    {
        FGlobalShader::ModifyCompilationEnvironment(Parameters, Environment);
        if (FPermutationDomain(Parameters.PermutationId).Get<FSeparateStencil>())
            Environment.SetRenderTargetOutputFormat(0, PF_R16G16_UINT);
    }
};
IMPLEMENT_GLOBAL_SHADER(FResidentHairStencilPS, "/Project/ResidentHairStencil/ResidentHairStencil.usf", "MainPS", SF_Pixel);

namespace ResidentHairStencil
{
    class FViewExtension : public FWorldSceneViewExtension
    {
    public:
        using FWorldSceneViewExtension::FWorldSceneViewExtension;

        void PrePostProcessPass_RenderThread(FRDGBuilder& Graph, const FSceneView& SceneView,
            const FPostProcessingInputs& Inputs) override
        {
            if (SceneView.bIsSceneCapture || SceneView.bIsReflectionCapture || SceneView.bIsPlanarReflection
                || !Inputs.CustomDepthTexture || !Inputs.CustomDepthTexture->HasBeenProduced()) return;

            const auto& View = static_cast<const FViewInfo&>(SceneView);
            const auto& Hair = View.HairStrandsViewData;
            const auto& Visibility = Hair.VisibilityData;
            if (!Visibility.NodeIndex || !Visibility.NodeVisData || !Visibility.CoverageTexture || View.GetFeatureLevel() < ERHIFeatureLevel::SM5) return;

            // With Nanite's separate depth export, post-process materials sample a
            // two-channel integer render target instead of the hardware stencil plane.
            FRDGTextureRef SeparateStencil = nullptr;
            if (Inputs.bSeparateCustomStencil)
            {
                FRDGTextureSRVRef StencilSRV = Inputs.SceneTextures->GetContents()->CustomStencilTexture;
                if (!StencilSRV || StencilSRV->GetParent()->Desc.Format != PF_R16G16_UINT) return;
                SeparateStencil = StencilSRV->GetParent();
            }
            static const auto* CoverageCVar = IConsoleManager::Get().FindConsoleVariable(TEXT("r.HairStrands.Selection.CoverageThreshold"));

            // UE's strand custom-depth pass writes the visible strand depth but leaves
            // stencil unchanged. Supply the resident ID on the same animated pixels.
            for (const auto& Group : Hair.MacroGroupDatas)
            {
                FIntRect Rect = Group.ScreenRect;
                Rect.Clip(View.ViewRect);
                if (Rect.IsEmpty()) continue;
                for (const auto& Primitive : Group.PrimitivesInfos)
                {
                    const auto* Proxy = Primitive.PrimitiveSceneProxy;
                    if (!Primitive.Mesh || !Proxy || !Proxy->ShouldRenderCustomDepth()) continue;
                    const int32 Stencil = Proxy->GetCustomDepthStencilValue();
                    if (!(Stencil >= FocusBase && Stencil < FocusBase + SlotCount)
                        && !(Stencil >= ShopBase && Stencil < ShopBase + SlotCount)) continue;

                    auto* Parameters = Graph.AllocParameters<FResidentHairStencilPS::FParameters>();
                    Parameters->HairMaterialId = Primitive.MaterialId;
                    Parameters->ResidentStencil = Stencil;
                    Parameters->CoverageThreshold = CoverageCVar ? FMath::Clamp(CoverageCVar->GetFloat(), 0.f, 1.f) : 0.f;
                    Parameters->VisNodeIndex = Visibility.NodeIndex;
                    Parameters->Coverage = Visibility.CoverageTexture;
                    Parameters->VisNodeData = Graph.CreateSRV(Visibility.NodeVisData);
                    Parameters->RenderTargets.DepthStencil = FDepthStencilBinding(Inputs.CustomDepthTexture,
                        ERenderTargetLoadAction::ELoad, SeparateStencil ? ERenderTargetLoadAction::ENoAction : ERenderTargetLoadAction::ELoad,
                        SeparateStencil ? FExclusiveDepthStencil::DepthWrite_StencilNop : FExclusiveDepthStencil::DepthWrite_StencilWrite);
                    if (SeparateStencil)
                        Parameters->RenderTargets[0] = FRenderTargetBinding(SeparateStencil, ERenderTargetLoadAction::ELoad);
                    FResidentHairStencilPS::FPermutationDomain Permutation;
                    Permutation.Set<FResidentHairStencilPS::FSeparateStencil>(SeparateStencil != nullptr);
                    TShaderMapRef<FResidentHairStencilPS> Shader(View.ShaderMap, Permutation);
                    auto* DepthState = SeparateStencil ? TStaticDepthStencilState<true, CF_DepthNearOrEqual>::GetRHI()
                        : TStaticDepthStencilState<true, CF_DepthNearOrEqual, true, CF_Always, SO_Keep, SO_Keep, SO_Replace>::GetRHI();
                    FPixelShaderUtils::AddFullscreenPass(Graph, View.ShaderMap, RDG_EVENT_NAME("ResidentHairStencil"), Shader,
                        Parameters, Rect, nullptr, nullptr, DepthState, Stencil);
                }
            }
        }
    };

    TSharedRef<ISceneViewExtension, ESPMode::ThreadSafe> CreateViewExtension(UWorld* World)
    {
        return FSceneViewExtensions::NewExtension<FViewExtension>(World);
    }
}
