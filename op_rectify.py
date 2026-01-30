import bmesh
import bpy
from .services.rectify_service import align_uv_rectify


class op(bpy.types.Operator):
    bl_idname = "uv.textools_rectify"
    bl_label = "Rectify"
    bl_description = "Align selected UV faces to rectangular distribution (Quads only)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.active_object.mode != 'EDIT':
            return False
        if not context.object.data.uv_layers:
            return False
        return True

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()

        success = align_uv_rectify(obj, bm, uv_layer.name)

        if not success:
            self.report({'WARNING'}, "No quads selected or operation failed.")
            return {'CANCELLED'}

        return {'FINISHED'}
