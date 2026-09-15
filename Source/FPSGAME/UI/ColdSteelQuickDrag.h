#pragma once
#include "CoreMinimal.h"
#include "Blueprint/DragDropOperation.h"
#include "ColdSteelQuickBarTypes.h"
#include "ColdSteelQuickDrag.generated.h"

UCLASS()
class UColdSteelQuickDrag : public UDragDropOperation
{
    GENERATED_BODY()
public:
    int32 SourceSlot=INDEX_NONE;
    FName Skill;
    TArray<FColdSteelQuickBinding> Bindings;
    TWeakObjectPtr<class UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelDragVisual> Visual;
    bool IsCurrent() const;
    void ReleaseVisual();
    virtual void Dragged_Implementation(const FPointerEvent& Event) override;
    virtual void Drop_Implementation(const FPointerEvent& Event) override;
    virtual void DragCancelled_Implementation(const FPointerEvent& Event) override;
};
