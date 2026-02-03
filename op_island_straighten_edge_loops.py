import bpy
import bmesh
from .services.rectify_service import align_uv_rectify
from .services.straight_service import align_uv_straight_edge


class op(bpy.types.Operator):
    bl_idname = "uv.textools_island_straighten_edge_loops"
    bl_label = "Straight edges chain"
    bl_description = "Straighten selected UV edges (or Rectify if faces selected)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and
                context.active_object.type == 'MESH' and
                context.active_object.mode == 'EDIT' and
                context.active_object.data.uv_layers)

    def execute(self, context):
        obj = context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        uv_layer_name = me.uv_layers.active.name if me.uv_layers.active else None
        if not uv_layer_name:
            self.report({"ERROR"}, "No UV Map found")
            return {"CANCELLED"}

        # Check for face selection
        selected_faces = [f for f in bm.faces if f.select]

        if selected_faces:
            # Use Rectify logic
            success = align_uv_rectify(obj, bm, uv_layer_name, keep_bounds=True)
            if not success:
                self.report({"WARNING"}, "Rectify failed. Select connected Quad faces.")
                return {"CANCELLED"}
        else:
            # Use Straight logic
            success = align_uv_straight_edge(bm, uv_layer_name)
            if not success:
                self.report({"WARNING"}, "Straighten failed. Select UV edges.")
                return {"CANCELLED"}

        bmesh.update_edit_mesh(me)
        return {'FINISHED'}
