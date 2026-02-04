# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

MOD_NAME = "NT_UV_Morph"


def ensure_uv_morph_node_group() -> bpy.types.NodeTree:
    """
    Creates and returns the Geometry Nodes group for UV Morph if it doesn't exist.
    """
    if MOD_NAME in bpy.data.node_groups:
        return bpy.data.node_groups[MOD_NAME]

    ng = bpy.data.node_groups.new(name=MOD_NAME, type="GeometryNodeTree")

    # IO =========================================================================================
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")

    input_factor = ng.interface.new_socket(
        name="Factor", in_out="INPUT", socket_type="NodeSocketFloat"
    )
    input_factor.default_value = 1.0
    input_factor.min_value = 0.0
    input_factor.max_value = 1.0

    input_scale = ng.interface.new_socket(
        name="Scale", in_out="INPUT", socket_type="NodeSocketFloat"
    )
    input_scale.default_value = 5.0
    input_scale.min_value = 0.001

    input_uv_name = ng.interface.new_socket(
        name="UV Map", in_out="INPUT", socket_type="NodeSocketString"
    )
    input_uv_name.default_value = "UVMap"

    # Node Creation =================================================================================
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes = ng.nodes
    links = ng.links

    node_in = nodes.new("NodeGroupInput")
    node_in.location = (-800, 0)
    node_out = nodes.new("NodeGroupOutput")
    node_out.location = (800, 0)

    node_split = nodes.new("GeometryNodeSplitEdges")
    node_split.location = (-600, 0)

    node_uv_attr = nodes.new("GeometryNodeInputNamedAttribute")
    node_uv_attr.data_type = "FLOAT_VECTOR"
    node_uv_attr.location = (-600, 200)

    node_scale_math = nodes.new("ShaderNodeVectorMath")
    node_scale_math.operation = "SCALE"
    node_scale_math.location = (-350, 200)
    node_scale_math.label = "UV Scale"

    node_pos = nodes.new("GeometryNodeInputPosition")
    node_pos.location = (-400, 0)

    node_mix = nodes.new("ShaderNodeMix")
    node_mix.data_type = "VECTOR"
    node_mix.clamp_factor = True
    node_mix.location = (-100, 100)
    node_mix.label = "Morph Mix"

    node_set_pos = nodes.new("GeometryNodeSetPosition")
    node_set_pos.location = (200, 0)

    # linking =========================================================================
    links.new(node_in.outputs["Geometry"], node_split.inputs["Mesh"])
    links.new(node_split.outputs["Mesh"], node_set_pos.inputs["Geometry"])
    links.new(node_set_pos.outputs["Geometry"], node_out.inputs["Geometry"])

    links.new(node_in.outputs["UV Map"], node_uv_attr.inputs["Name"])

    links.new(node_uv_attr.outputs["Attribute"], node_scale_math.inputs[0])
    links.new(node_in.outputs["Scale"], node_scale_math.inputs[3])
    links.new(node_scale_math.outputs["Vector"], node_mix.inputs["B"])

    links.new(node_in.outputs["Factor"], node_mix.inputs["Factor"])
    links.new(node_pos.outputs["Position"], node_mix.inputs["A"])

    links.new(node_mix.outputs["Result"], node_set_pos.inputs["Position"])

    return ng


def set_modifier_factor(mod: bpy.types.NodesModifier, value: float) -> None:
    """
    Sets the 'Factor' input value of a Geometry Nodes modifier.
    """
    ng = mod.node_group
    if not ng or not hasattr(ng, "interface"):
        return

    for item in ng.interface.items_tree:
        if item.name == "Factor" and item.item_type == "SOCKET":
            if item.identifier in mod.keys():
                mod[item.identifier] = value
                return

    if "Factor" in mod.keys():
        mod["Factor"] = value


def toggle_uv_morph_modifier(obj: bpy.types.Object) -> bool:
    """
    Returns:
        True if Added, False if Removed
    """
    if MOD_NAME in obj.modifiers:
        obj.modifiers.remove(obj.modifiers[MOD_NAME])
        return False

    ng = ensure_uv_morph_node_group()
    mod = obj.modifiers.new(name=MOD_NAME, type="NODES")
    mod.node_group = ng
    mod.show_on_cage = True
    mod.show_in_editmode = True

    active_uv = obj.data.uv_layers.active
    if active_uv:
        if "UV Map" in mod.keys():
            mod["UV Map"] = active_uv.name

    return True


def _create_snapshot_mesh(
    context: bpy.types.Context, original_obj: bpy.types.Object, is_start: bool
) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    original_obj.select_set(True)
    context.view_layer.objects.active = original_obj

    bpy.ops.object.duplicate()
    new_obj = context.active_object
    if is_start:
        new_obj.name = f"{original_obj.name}_UV_Mesh"

    mod = new_obj.modifiers[MOD_NAME]
    set_modifier_factor(mod, 0.0 if is_start else 1.0)
    bpy.ops.object.modifier_apply(modifier=MOD_NAME)

    return new_obj


def execute_bake_process(
    context: bpy.types.Context, original_obj: bpy.types.Object
) -> bpy.types.Object:
    """
    Assume the context is overridden.
    """
    basis_obj = _create_snapshot_mesh(context, original_obj, True)
    target_obj = _create_snapshot_mesh(context, original_obj, False)

    bpy.ops.object.select_all(action="DESELECT")
    target_obj.select_set(True)
    basis_obj.select_set(True)
    context.view_layer.objects.active = basis_obj

    bpy.ops.object.join_shapes()

    if basis_obj.data.shape_keys:
        keys = basis_obj.data.shape_keys.key_blocks
        keys[-1].name = "UV_Morph"
        keys[-1].value = 0.0

    bpy.ops.object.select_all(action="DESELECT")
    target_obj.select_set(True)
    bpy.ops.object.delete()

    bpy.ops.object.select_all(action="DESELECT")
    basis_obj.select_set(True)
    context.view_layer.objects.active = basis_obj

    return basis_obj
