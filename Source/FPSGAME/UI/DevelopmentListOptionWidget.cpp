#include "DevelopmentListOptionWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/TextBlock.h"

void UDevelopmentListOptionWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);
    Label = WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetAutoWrapText(false);
    WidgetTree->RootWidget = Label;
}
