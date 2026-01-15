import bmesh
import bpy
from mathutils import Vector

from . import utilities_uv


class op(bpy.types.Operator):
    bl_idname = "uv.textools_island_straighten_edge_loops"
    bl_label = "Straight edges chain"
    bl_description = "Straighten selected edge-chain and relax the rest of the UV Island"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not bpy.context.active_object:
            return False
        if bpy.context.active_object.mode != 'EDIT':
            return False
        if not bpy.context.object.data.uv_layers:
            return False
        return True

    def execute(self, context):
        obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()

        selected_faces_loops = utilities_uv.selection_store(
            bm, uv_layer,
            return_selected_faces_edges=True
        )

        selected_loops = []
        if selected_faces_loops:
            for loops in selected_faces_loops.values():
                selected_loops.extend(loops)

        if not selected_loops:
            self.report({'WARNING'}, "No UV edges selected.")
            return {'CANCELLED'}

        coords = [l[uv_layer].uv for l in selected_loops]

        if len(coords) < 2:
            self.report({'WARNING'}, "Select at least 2 vertices.")
            return {'CANCELLED'}

        min_x = min(c.x for c in coords)
        max_x = max(c.x for c in coords)
        min_y = min(c.y for c in coords)
        max_y = max(c.y for c in coords)

        width = max_x - min_x
        height = max_y - min_y

        is_horizontal = width > height

        target_loops = list(set(selected_loops))
        original_pins = []

        if is_horizontal:
            avg_y = sum(c.y for c in coords) / len(coords)
            for loop in target_loops:
                loop[uv_layer].uv.y = avg_y
        else:
            avg_x = sum(c.x for c in coords) / len(coords)
            for loop in target_loops:
                loop[uv_layer].uv.x = avg_x

        for loop in target_loops:
            original_pins.append(loop[uv_layer].pin_uv)
            loop[uv_layer].pin_uv = True

        islands = utilities_uv.getSelectionIslands(bm, uv_layer, selected_faces=set(selected_faces_loops.keys()))

        if islands:
            for island in islands:
                for face in island:
                    face.select = True

            try:
                bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0)
            except Exception as e:
                print(f"Unwrap Warning: {e}")
        else:
            pass

        for i, loop in enumerate(target_loops):
            loop[uv_layer].pin_uv = original_pins[i]

        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}
