import bpy
from .. import utilities_color
from ..settings import tt_settings, prefs

GAMMA = 2.2
LAYER_NAME = 'TexTools_colorID'


class ScopedEditMode:
    def __init__(self, context):
        self.context = context
        self.active_obj = context.active_object
        self.selected_objects = context.selected_objects.copy()
        self.previous_mode = self.active_obj.mode if self.active_obj else 'OBJECT'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context.view_layer.objects.active:
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        for obj in self.selected_objects:
            try:
                obj.select_set(True)
            except RuntimeError:
                pass

        if self.active_obj and self.active_obj.name in self.context.scene.objects:
            self.context.view_layer.objects.active = self.active_obj
            if self.previous_mode in {'EDIT', 'OBJECT', 'POSE', 'SCULPT', 'VERTEX_PAINT', 'WEIGHT_PAINT'}:
                try:
                    bpy.ops.object.mode_set(mode=self.previous_mode)
                except RuntimeError:
                    pass


def assign_color(operator, context, index):
    target_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

    if not target_objects:
        return {'CANCELLED'}

    with ScopedEditMode(context):

        rgba_color = _get_target_rgba(index)

        for obj in target_objects:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj

            bpy.ops.object.mode_set(mode='EDIT')
            if operator.previous_mode_was_object:
                bpy.ops.mesh.select_all(action='SELECT')

            if tt_settings().color_assign_mode == 'MATERIALS':
                _assign_material(obj, index)
            else:
                _assign_vertex_color(obj, rgba_color)

    utilities_color.update_properties_tab()
    utilities_color.update_view_mode()

    return {'FINISHED'}


def _get_target_rgba(index):
    color = utilities_color.get_color(index).copy()
    if prefs().bool_color_id_vertex_color_gamma:
        color[0] = pow(color[0], 1 / GAMMA)
        color[1] = pow(color[1], 1 / GAMMA)
        color[2] = pow(color[2], 1 / GAMMA)
    return color[0], color[1], color[2], 1.0


def _assign_material(obj, index):
    while index >= len(obj.material_slots):
        bpy.ops.object.material_slot_add()

    utilities_color.assign_slot(obj, index)

    obj.active_material_index = index
    bpy.ops.object.material_slot_assign()


def _assign_vertex_color(obj, rgba_color):
    bpy.ops.object.mode_set(mode='OBJECT')
    layer = _get_or_create_color_layer(obj)

    if not layer:
        return

    target_polys = [p for p in obj.data.polygons if p.select and not p.hide]

    if target_polys:
        for poly in target_polys:
            for loop_index in poly.loop_indices:
                layer.data[loop_index].color = rgba_color

        obj.data.update()


def _get_or_create_color_layer(obj):
    mesh = obj.data

    if hasattr(mesh, "color_attributes"):
        layer = mesh.color_attributes.get(LAYER_NAME)
        if not layer:
            layer = mesh.color_attributes.new(
                name=LAYER_NAME,
                type='BYTE_COLOR',
                domain='CORNER',
            )
        try:
            layer_index = mesh.color_attributes.find(LAYER_NAME)
            mesh.color_attributes.active_color_index = layer_index
        except AttributeError:
            pass
        return layer

    elif hasattr(mesh, "vertex_colors"):
        layer = mesh.vertex_colors.get(LAYER_NAME)
        if not layer:
            layer = mesh.vertex_colors.new(name=LAYER_NAME)
        layer.active = True
        return layer

    return None
