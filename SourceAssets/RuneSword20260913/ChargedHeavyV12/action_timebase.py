"""Preserve seconds when accepted actions share a scene with 480 Hz baking."""
def rescale_action(action,factor):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.co.x*=factor
                        key.handle_left.x*=factor
                        key.handle_right.x*=factor
                    curve.update()
