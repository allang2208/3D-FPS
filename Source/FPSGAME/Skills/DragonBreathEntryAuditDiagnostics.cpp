#include "DragonBreathEntryAuditDiagnostics.h"
#include "CoreMinimal.h"
#if WITH_EDITOR
#include "Dom/JsonObject.h"
#include "Engine/TextureRenderTargetVolume.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include "MaterialShared.h"
#include "Misc/FileHelper.h"
#include "NiagaraComponent.h"
#include "NiagaraComputeExecutionContext.h"
#include "NiagaraDataInterfaceRenderTargetVolume.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstance.h"
#include "NiagaraSystemInstanceController.h"
#include "RenderingThread.h"
#include "SceneInterface.h"
#include "RHIGPUReadback.h"
#include "TextureResource.h"
#include "Serialization/JsonSerializer.h"

namespace
{
TSharedRef<FJsonObject> ReadStore(const FNiagaraParameterStore& Store)
{
    auto Result=MakeShared<FJsonObject>();TArray<FNiagaraVariable> Vars;Store.GetParameters(Vars);
    for(const auto& Var:Vars)
    {
        const auto* Struct=Var.GetType().GetScriptStruct();const uint8* Data=Store.GetParameterData(Var);
        if(!Struct||!Data||Var.IsDataInterface()||Var.IsUObject())continue;
        FString Value;Struct->ExportText(Value,Data,nullptr,nullptr,PPF_None,nullptr);
        Result->SetStringField(Var.GetName().ToString(),Value);
    }
    return Result;
}
}

void CaptureDragonEntryVolume(UNiagaraComponent* FX,const FString& Output)
{
    if(!FX)return;
    auto Result=MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("scene_proxy"),FX->GetSceneProxy()!=nullptr);
    Result->SetBoolField(TEXT("recently_rendered"),FX->WasRecentlyRendered(.5f));
    Result->SetStringField(TEXT("transform"),FX->GetComponentTransform().ToString());
    Result->SetStringField(TEXT("bounds"),FX->Bounds.GetBox().ToString());
    Result->SetObjectField(TEXT("user_parameters"),ReadStore(FX->GetOverrideParameters()));
    TArray<UMaterialInterface*> Materials;FX->GetUsedMaterials(Materials);
    TArray<TSharedPtr<FJsonValue>> MaterialRows;
    for(auto* Material:Materials)if(Material)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("path"),Material->GetPathName());
        auto* Resource=Material->GetMaterialResource(FX->GetWorld()->Scene->GetShaderPlatform());
        Row->SetBoolField(TEXT("shader_map_complete"),Resource&&Resource->IsGameThreadShaderMapComplete());
        MaterialRows.Add(MakeShared<FJsonValueObject>(Row));
    }
    Result->SetArrayField(TEXT("materials"),MaterialRows);
    if(auto Controller=FX->GetSystemInstanceController())
    {
        // Diagnostic-only readback, after the recorded first release. Never used
        // by automatic preparation or by the ordinary regression captures.
        Controller->WaitForConcurrentTickAndFinalize();
        auto* Instance=Controller->GetSystemInstance_Unsafe();
        if(Instance)for(const auto& Emitter:Instance->GetEmitters())
        {
            auto Row=MakeShared<FJsonObject>();
            Row->SetNumberField(TEXT("state"),int32(Emitter->GetExecutionState()));
            Row->SetNumberField(TEXT("particles_estimate"),Emitter->GetNumParticles());
            Row->SetObjectField(TEXT("renderer_parameters"),ReadStore(Emitter->GetRendererBoundVariables()));
            if(auto* GPU=Emitter->GetGPUContext())
                for(auto* DI:GPU->GetDataInterfaces())if(auto* Volume=Cast<UNiagaraDataInterfaceRenderTargetVolume>(DI))
                {
                    auto* Data=static_cast<FRenderTargetVolumeRWInstanceData_GameThread*>(Instance->FindDataInterfaceInstanceData(Volume));
                    if(!Data||!Data->TargetTexture)continue;
                    auto* Resource=Data->TargetTexture->GameThread_GetRenderTargetResource();
                    FRHITexture* Texture=Resource?Resource->GetRenderTargetTexture():nullptr;if(!Texture)continue;
                    const FIntVector Size=Data->Size;
                    double MaxDensity=0,MaxHeat=0;int32 Hot=0;
                    ENQUEUE_RENDER_COMMAND(DragonFirstCastGridRead)([Texture,Size,&MaxDensity,&MaxHeat,&Hot](FRHICommandListImmediate& Cmd)
                    {
                        const auto Format=Texture->GetFormat();const int32 PixelBytes=GPixelFormats[Format].BlockBytes;
                        FRHIGPUTextureReadback Readback(TEXT("DragonFirstCastGridRead"));
                        Readback.EnqueueCopy(Cmd,Texture,FIntVector::ZeroValue,0,Size);Cmd.SubmitAndBlockUntilGPUIdle(true);
                        int32 Pitch=0,Height=0;const auto* Bytes=static_cast<const uint8*>(Readback.Lock(Pitch,&Height));
                        if(Bytes)for(int32 Z=0;Z<Size.Z;++Z)for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
                        {
                            const uint8* P=Bytes+((Z*Height+Y)*Pitch+X)*PixelBytes;FLinearColor V(0,0,0,0);
                            if(Format==PF_A32B32G32R32F)V=*reinterpret_cast<const FLinearColor*>(P);
                            else if(Format==PF_FloatRGBA)V=reinterpret_cast<const FFloat16Color*>(P)->GetFloats();
                            else if(Format==PF_G32R32F){V.R=reinterpret_cast<const float*>(P)[0];V.G=reinterpret_cast<const float*>(P)[1];}
                            else if(Format==PF_G16R16F){V.R=reinterpret_cast<const FFloat16*>(P)[0];V.G=reinterpret_cast<const FFloat16*>(P)[1];}
                            MaxDensity=FMath::Max(MaxDensity,double(V.R));MaxHeat=FMath::Max(MaxHeat,double(V.G));Hot+=V.G>.1f;
                        }
                        Readback.Unlock();
                    });
                    FlushRenderingCommands();
                    auto Grid=MakeShared<FJsonObject>();Grid->SetStringField(TEXT("size"),Size.ToString());
                    Grid->SetNumberField(TEXT("max_density"),MaxDensity);Grid->SetNumberField(TEXT("max_temperature"),MaxHeat);Grid->SetNumberField(TEXT("hot_voxels"),Hot);
                    Row->SetObjectField(Volume->GetName(),Grid);
                }
            Result->SetObjectField(Emitter->GetEmitterHandle().GetName().ToString(),Row);
        }
    }
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*Output);
}
#endif
