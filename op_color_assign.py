import bpy
from .services import color_assign_service


class op(bpy.types.Operator):
    bl_idname = "uv.textools_color_assign"
    bl_label = "Assign Color"
    bl_description = "Assign color to selected Objects or faces in Edit Mode"
    bl_options = {"UNDO"}

    index: bpy.props.IntProperty(description="Color Index", default=0)
    previous_mode_was_object: bpy.props.BoolProperty(default=False, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        if context.area.ui_type != "UV":
            return False
        if not context.active_object:
            return False
        if not any(o.type == "MESH" for o in context.selected_objects):
            return False
        return True

    def execute(self, context):
        active_obj = context.active_object
        current_mode = active_obj.mode if active_obj else "OBJECT"
        self.previous_mode_was_object = current_mode == "OBJECT"
        return color_assign_service.assign_color(self, context, self.index)
