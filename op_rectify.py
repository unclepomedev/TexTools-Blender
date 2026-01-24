import bmesh
import bpy
from mathutils import Vector


class op(bpy.types.Operator):
    bl_idname = "uv.textools_rectify"
    bl_label = "Rectify"
    bl_description = "Align selected UV faces or vertices to rectangular distribution"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.active_object.mode != "EDIT":
            return False
        if not context.object.data.uv_layers:
            return False
        return True

    def execute(self, context):
        obj = context.active_object
        try:
            area = next((a for a in context.screen.areas if a.type == "IMAGE_EDITOR"), None)
            if area:
                with context.temp_override(area=area):
                    bpy.ops.uv.select_split()
            else:
                bpy.ops.uv.select_split()
        except Exception:
            pass

        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({"WARNING"}, "No faces selected.")
            return {"CANCELLED"}

        islands = self.get_connected_components(selected_faces)

        if len(selected_faces) == len(bm.faces) and len(bm.faces) > 100:
            pass

        for island_faces in islands:
            self.rectify_island(bm, uv_layer, island_faces)

        bmesh.update_edit_mesh(obj.data)

        try:
            if area:
                with context.temp_override(area=area):
                    bpy.ops.uv.unwrap(method="CONFORMAL", margin=0)
            else:
                bpy.ops.uv.unwrap(method="CONFORMAL", margin=0)
        except Exception:
            pass

        return {"FINISHED"}

    def get_connected_components(self, faces):
        faces_set = set(faces)
        islands = []
        while faces_set:
            seed = faces_set.pop()
            island = {seed}
            stack = [seed]
            while stack:
                f = stack.pop()
                for edge in f.edges:
                    for link_face in edge.link_faces:
                        if link_face in faces_set:
                            island.add(link_face)
                            faces_set.remove(link_face)
                            stack.append(link_face)
            islands.append(list(island))
        return islands

    def rectify_island(self, bm, uv_layer, faces):
        face_set = set(faces)
        boundary_loops = []
        internal_loops = []

        for f in faces:
            for loop in f.loops:
                edge = loop.edge
                shared_selected_count = sum(1 for lf in edge.link_faces if lf in face_set)

                if shared_selected_count == 1:
                    boundary_loops.append(loop)
                else:
                    internal_loops.append(loop)

        if not boundary_loops:
            return

        for l in internal_loops:
            l[uv_layer].pin_uv = False

        coords = [l[uv_layer].uv for l in boundary_loops]
        min_x = min(c.x for c in coords)
        max_x = max(c.x for c in coords)
        min_y = min(c.y for c in coords)
        max_y = max(c.y for c in coords)

        width = max_x - min_x
        height = max_y - min_y

        if width < 1e-5:
            width = 1.0
        if height < 1e-5:
            height = 1.0

        for loop in boundary_loops:
            uv = loop[uv_layer].uv

            rel_x = (uv.x - min_x) / width
            rel_y = (uv.y - min_y) / height

            new_x, new_y = uv.x, uv.y
            threshold = 0.49

            if rel_x < threshold:
                new_x = min_x
            elif rel_x > (1.0 - threshold):
                new_x = max_x

            if rel_y < threshold:
                new_y = min_y
            elif rel_y > (1.0 - threshold):
                new_y = max_y

            loop[uv_layer].uv = Vector((new_x, new_y))
            loop[uv_layer].pin_uv = True
