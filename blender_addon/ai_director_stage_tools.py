bl_info = {
    "name": "AI Director Stage Tools",
    "author": "OpenAI",
    "version": (0, 5, 0),
    "blender": (5, 2, 0),
    "location": "3D View > Sidebar > 3D导演台",
    "description": "LibTV-like 3D director tools with direct ComfyUI export",
    "category": "3D View",
}

import bpy
import os
import json
import math
from bpy.app.handlers import persistent
from mathutils import Vector

PANEL_CATEGORY = "3D导演台"
CAMERA_NAME = "机位1"
FRUSTUM_NAME = "AI_Director_Camera_Frustum"
FRUSTUM_COLOR = (0.05, 0.85, 1.00, 1.0)
COMFYUI_EXPORT_FILENAME = "director_scene.json"

CHARACTER_COLORS = [
    (0.305, 0.557, 0.969, 1.0),
    (0.969, 0.325, 0.325, 1.0),
    (0.320, 0.820, 0.500, 1.0),
    (1.000, 0.610, 0.230, 1.0),
    (0.700, 0.430, 0.950, 1.0),
    (0.160, 0.780, 0.820, 1.0),
    (0.950, 0.520, 0.720, 1.0),
    (0.850, 0.800, 0.280, 1.0),
]

SHOT_MAP = {
    "ECU": "extreme close-up",
    "CU": "close-up",
    "MCU": "medium close-up",
    "MS": "medium shot",
    "FS": "full shot",
    "WS": "wide shot",
    "EWS": "extreme wide shot",
}

MOVEMENT_MAP = {
    "STATIC": "static camera",
    "DOLLY_IN": "slow dolly in",
    "DOLLY_OUT": "slow dolly out",
    "TRACK_LEFT": "tracking left",
    "TRACK_RIGHT": "tracking right",
    "PAN_LEFT": "pan left",
    "PAN_RIGHT": "pan right",
    "ORBIT_LEFT": "slow orbit left",
    "ORBIT_RIGHT": "slow orbit right",
}

PRESETS = {
    "STANDARD_MALE": {"scale": (0.84, 0.77, 1.00)},
    "STANDARD_FEMALE": {"scale": (0.78, 0.71, 0.96), "female": True},
    "ATHLETIC": {"scale": (0.94, 0.86, 1.02), "thickness": 1.08},
    "SLIM": {"scale": (0.70, 0.64, 1.00), "thickness": 0.92},
    "TEEN": {"scale": (0.72, 0.66, 0.88), "head": 1.08},
    "CHILD": {"scale": (0.68, 0.62, 0.72), "head": 1.18},
    "BROAD": {"scale": (1.02, 0.92, 1.00), "thickness": 1.12},
    "CHIBI": {"scale": (0.82, 0.76, 0.58), "head": 1.72},
}


def is_character_root(obj):
    return bool(obj and (
        obj.get("ai_director_character_root", False)
        or (obj.type == "EMPTY" and obj.name.startswith("角色"))
    ))


def character_root_from_object(obj):
    current = obj
    while current:
        if is_character_root(current):
            return current
        current = current.parent
    return None


def character_roots():
    roots = [obj for obj in bpy.data.objects if is_character_root(obj)]
    return sorted(roots, key=lambda o: o.name)


def descendants(root):
    result = []

    def walk(obj):
        for child in obj.children:
            result.append(child)
            walk(child)

    walk(root)
    return result


def get_camera():
    return bpy.data.objects.get(CAMERA_NAME)


def get_template_character():
    obj = bpy.data.objects.get("角色A")
    if is_character_root(obj):
        return obj
    roots = character_roots()
    return roots[0] if roots else None


def tag_existing_characters():
    for obj in bpy.data.objects:
        if obj.type == "EMPTY" and obj.name.startswith("角色"):
            obj["ai_director_character_root"] = True


def excel_letters(index):
    n = index + 1
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def next_character_name():
    used = {obj.name for obj in character_roots()}
    i = 0
    while True:
        name = f"角色{excel_letters(i)}"
        if name not in used:
            return name
        i += 1


def next_spawn_location():
    count = len(character_roots())
    if count == 0:
        x = 0.0
    else:
        ring = (count + 1) // 2
        x = -1.40 * ring if count % 2 == 1 else 1.40 * ring
    return Vector((x, 0.0, 0.0))


def iter_view3d_spaces():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    yield space


def style_viewports():
    for space in iter_view3d_spaces():
        try:
            space.shading.type = "SOLID"
            space.shading.color_type = "OBJECT"
            space.shading.background_type = "VIEWPORT"
            space.shading.background_color = (0.004, 0.005, 0.008)

            overlay = space.overlay
            overlay.show_overlays = True
            overlay.show_floor = True
            overlay.show_axis_x = False
            overlay.show_axis_y = False
            overlay.show_axis_z = False
            overlay.show_relationship_lines = False
            overlay.show_object_origins = False
            overlay.show_object_origins_all = False

            space.show_gizmo = True
        except Exception:
            pass


def _remove_frustum():
    obj = bpy.data.objects.get(FRUSTUM_NAME)
    if obj:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data and data.users == 0:
            bpy.data.curves.remove(data)


def _add_poly_segment(curve_data, p1, p2):
    spline = curve_data.splines.new(type="POLY")
    spline.points.add(1)
    spline.points[0].co = (*p1, 1.0)
    spline.points[1].co = (*p2, 1.0)


def rebuild_camera_frustum():
    cam = get_camera()
    if not cam or cam.type != "CAMERA":
        return False

    _remove_frustum()

    scene = bpy.context.scene
    frame = [Vector(v) for v in cam.data.view_frame(scene=scene)]

    target_depth = 3.0
    far = []
    for corner in frame:
        z = abs(corner.z) if abs(corner.z) > 1e-6 else 1.0
        far.append(corner * (target_depth / z))

    curve_data = bpy.data.curves.new(FRUSTUM_NAME, type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.bevel_depth = 0.009
    curve_data.bevel_resolution = 2

    origin = Vector((0.0, 0.0, 0.0))
    for corner in far:
        _add_poly_segment(curve_data, origin, corner)
    for i in range(4):
        _add_poly_segment(curve_data, far[i], far[(i + 1) % 4])

    frustum = bpy.data.objects.new(FRUSTUM_NAME, curve_data)

    collection = bpy.data.collections.get("场景") or scene.collection
    collection.objects.link(frustum)

    frustum.parent = cam
    frustum.location = (0.0, 0.0, 0.0)
    frustum.rotation_euler = (0.0, 0.0, 0.0)
    frustum.scale = (1.0, 1.0, 1.0)
    frustum.color = FRUSTUM_COLOR
    frustum.show_in_front = True
    frustum.hide_render = True
    frustum.hide_select = True
    frustum.display_type = "SOLID"

    cam.show_name = True
    cam.show_in_front = True
    cam.data.display_size = 0.75

    return True


def duplicate_object_data(obj):
    new_obj = obj.copy()
    if getattr(obj, "data", None) is not None:
        try:
            new_obj.data = obj.data.copy()
        except Exception:
            pass
    return new_obj


def duplicate_character_hierarchy(template, new_name, location):
    if not template:
        raise RuntimeError("没有找到角色模板")

    collection = bpy.data.collections.get("场景") or bpy.context.scene.collection
    source_objects = [template] + descendants(template)
    mapping = {}

    for old in source_objects:
        new = duplicate_object_data(old)
        mapping[old] = new
        collection.objects.link(new)

    for old, new in mapping.items():
        if old.parent in mapping:
            new.parent = mapping[old.parent]
            try:
                new.matrix_parent_inverse = old.matrix_parent_inverse.copy()
            except Exception:
                pass
        try:
            new.matrix_local = old.matrix_local.copy()
        except Exception:
            new.location = old.location.copy()
            new.rotation_euler = old.rotation_euler.copy()
            new.scale = old.scale.copy()

    root = mapping[template]
    root.name = new_name
    root["ai_director_character_root"] = True
    root.show_name = True
    root.location = location

    old_prefix = template.name
    for old, new in mapping.items():
        if old == template:
            continue
        if old.name.startswith(old_prefix + "_"):
            new.name = new_name + old.name[len(old_prefix):]
        else:
            new.name = new_name + "_" + old.name

    return root


def set_character_color(root, color):
    root.color = color
    for obj in [root] + descendants(root):
        try:
            obj.color = color
        except Exception:
            pass


def selected_character_root(context):
    return character_root_from_object(context.view_layer.objects.active)


def apply_preset(root, preset_id):
    preset = PRESETS[preset_id]
    root.scale = preset["scale"]

    thickness = preset.get("thickness", 1.0)
    head_factor = preset.get("head", 1.0)

    for obj in descendants(root):
        if obj.type != "MESH":
            continue

        if any(key in obj.name for key in (
            "胸腔", "骨盆", "腰", "上臂", "前臂", "大腿", "小腿"
        )):
            obj.scale.x *= thickness
            obj.scale.y *= thickness

        if "头" in obj.name:
            obj.scale *= head_factor

    if preset.get("female"):
        for obj in descendants(root):
            if "胸腔" in obj.name:
                obj.scale.x *= 0.92
            elif "骨盆" in obj.name:
                obj.scale.x *= 1.06


def create_character_from_preset(preset_id, forced_location=None):
    template = get_template_character()
    if not template:
        raise RuntimeError("找不到角色A模板，请保留角色A")

    root = duplicate_character_hierarchy(
        template,
        next_character_name(),
        Vector(forced_location) if forced_location else next_spawn_location(),
    )

    apply_preset(root, preset_id)

    roots = character_roots()
    try:
        index = roots.index(root)
    except ValueError:
        index = len(roots) - 1

    set_character_color(root, CHARACTER_COLORS[index % len(CHARACTER_COLORS)])

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    return root


def character_export_data(root):
    return {
        "name": root.name,
        "location": {
            "x": float(root.location.x),
            "y": float(root.location.y),
            "z": float(root.location.z),
        },
        "rotation_degrees": {
            "x": math.degrees(float(root.rotation_euler.x)),
            "y": math.degrees(float(root.rotation_euler.y)),
            "z": math.degrees(float(root.rotation_euler.z)),
        },
        "scale": {
            "x": float(root.scale.x),
            "y": float(root.scale.y),
            "z": float(root.scale.z),
        },
        "color_rgba": [float(v) for v in root.color],
    }


def build_director_export(scene):
    cam = get_camera()
    if not cam or cam.type != "CAMERA":
        raise RuntimeError("找不到机位1，无法导出")

    shot_id = scene.ai_director_shot
    movement_id = scene.ai_director_movement
    shot_text = SHOT_MAP.get(shot_id, "")
    movement_text = MOVEMENT_MAP.get(movement_id, "")
    action = scene.ai_director_action.strip()
    mood = scene.ai_director_mood.strip()

    prompt_parts = [
        shot_text,
        movement_text,
        f"{cam.data.lens:.0f}mm lens",
    ]
    if action:
        prompt_parts.append(action)
    if mood:
        prompt_parts.append(mood)

    return {
        "version": "0.5",
        "shot": {
            "size": shot_id,
            "size_prompt": shot_text,
            "duration_seconds": float(scene.ai_director_duration),
        },
        "camera": {
            "name": cam.name,
            "movement": movement_id,
            "movement_prompt": movement_text,
            "lens_mm": float(cam.data.lens),
            "location": {
                "x": float(cam.location.x),
                "y": float(cam.location.y),
                "z": float(cam.location.z),
            },
            "rotation_degrees": {
                "x": math.degrees(float(cam.rotation_euler.x)),
                "y": math.degrees(float(cam.rotation_euler.y)),
                "z": math.degrees(float(cam.rotation_euler.z)),
            },
        },
        "character": {"action": action},
        "characters": [character_export_data(root) for root in character_roots()],
        "mood": mood,
        "render": {
            "resolution_x": int(scene.render.resolution_x),
            "resolution_y": int(scene.render.resolution_y),
            "fps": int(scene.render.fps),
        },
        "generated_prompt": ", ".join(part for part in prompt_parts if part),
    }


def export_to_comfyui(scene):
    raw_folder = scene.ai_director_comfyui_folder.strip()
    if not raw_folder:
        raise RuntimeError(
            "请先在 3D导演台 > 导演输出 中选择 ComfyUI-AI-Director 文件夹"
        )

    folder = bpy.path.abspath(raw_folder)
    if not os.path.isdir(folder):
        raise RuntimeError(f"找不到 ComfyUI 导出目录：{folder}")

    output_path = os.path.join(folder, COMFYUI_EXPORT_FILENAME)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            build_director_export(scene),
            f,
            ensure_ascii=False,
            indent=4,
        )

    scene.ai_director_last_export = output_path
    return output_path


class AIDIRECTOR_OT_add_character(bpy.types.Operator):
    bl_idname = "aidirector.add_character"
    bl_label = "添加角色"

    preset: bpy.props.EnumProperty(
        items=[
            ("STANDARD_MALE", "标准男性", ""),
            ("STANDARD_FEMALE", "标准女性", ""),
            ("ATHLETIC", "健硕", ""),
            ("SLIM", "纤细", ""),
            ("TEEN", "少年", ""),
            ("CHILD", "儿童", ""),
            ("BROAD", "宽厚", ""),
            ("CHIBI", "二头身", ""),
        ],
        default="STANDARD_MALE",
    )

    def execute(self, context):
        try:
            root = create_character_from_preset(self.preset)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        self.report({"INFO"}, f"已创建 {root.name}")
        return {"FINISHED"}


class AIDIRECTOR_OT_duplicate_character(bpy.types.Operator):
    bl_idname = "aidirector.duplicate_character"
    bl_label = "复制完整角色"

    def execute(self, context):
        source = selected_character_root(context)
        if not source:
            self.report({"ERROR"}, "请先选择一个角色")
            return {"CANCELLED"}

        location = source.location.copy()
        location.x -= 1.40

        root = duplicate_character_hierarchy(
            source,
            next_character_name(),
            location,
        )

        set_character_color(
            root,
            CHARACTER_COLORS[
                len(character_roots()) % len(CHARACTER_COLORS)
            ],
        )

        bpy.ops.object.select_all(action="DESELECT")
        root.select_set(True)
        context.view_layer.objects.active = root

        return {"FINISHED"}


class AIDIRECTOR_OT_director_view(bpy.types.Operator):
    bl_idname = "aidirector.director_view"
    bl_label = "导演视角"

    def execute(self, context):
        root = selected_character_root(context) or get_template_character()
        if not root:
            self.report({"ERROR"}, "找不到角色")
            return {"CANCELLED"}

        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"ERROR"}, "请在3D视图中使用")
            return {"CANCELLED"}

        r3d = context.space_data.region_3d
        bpy.ops.view3d.view_axis(type="FRONT", align_active=False)

        if r3d.view_perspective == "ORTHO":
            bpy.ops.view3d.view_persportho()

        old_selected = list(context.selected_objects)
        old_active = context.view_layer.objects.active

        bpy.ops.object.select_all(action="DESELECT")
        root.select_set(True)
        context.view_layer.objects.active = root
        bpy.ops.view3d.view_selected(use_all_regions=False)

        root.select_set(False)
        for obj in old_selected:
            if obj and obj.name in bpy.data.objects:
                obj.select_set(True)
        if old_active and old_active.name in bpy.data.objects:
            context.view_layer.objects.active = old_active

        r3d.view_distance *= 2.35
        return {"FINISHED"}


class AIDIRECTOR_OT_camera_view(bpy.types.Operator):
    bl_idname = "aidirector.camera_view"
    bl_label = "机位视角"

    def execute(self, context):
        cam = get_camera()
        if not cam or cam.type != "CAMERA":
            self.report({"ERROR"}, "找不到机位1")
            return {"CANCELLED"}

        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"ERROR"}, "请在3D视图中使用")
            return {"CANCELLED"}

        context.scene.camera = cam
        context.space_data.region_3d.view_perspective = "CAMERA"
        return {"FINISHED"}


class AIDIRECTOR_OT_refresh_frustum(bpy.types.Operator):
    bl_idname = "aidirector.refresh_frustum"
    bl_label = "刷新相机轮廓"

    def execute(self, context):
        if not rebuild_camera_frustum():
            self.report({"ERROR"}, "找不到机位1")
            return {"CANCELLED"}
        return {"FINISHED"}


class AIDIRECTOR_OT_export_comfyui(bpy.types.Operator):
    bl_idname = "aidirector.export_comfyui"
    bl_label = "导出到 ComfyUI"

    def execute(self, context):
        try:
            path = export_to_comfyui(context.scene)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        self.report({"INFO"}, f"已导出：{path}")
        return {"FINISHED"}


class AIDIRECTOR_PT_stage_tools(bpy.types.Panel):
    bl_label = "3D导演台"
    bl_idname = "AIDIRECTOR_PT_stage_tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = PANEL_CATEGORY

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.scale_y = 1.35
        row.operator("aidirector.director_view", icon="VIEW_PERSPECTIVE")
        row.operator("aidirector.camera_view", icon="VIEW_CAMERA")

        box = layout.box()
        box.label(text="添加角色")

        grid = box.grid_flow(
            row_major=True,
            columns=2,
            even_columns=True,
            align=True,
        )

        for preset_id, label in [
            ("STANDARD_MALE", "标准男性"),
            ("STANDARD_FEMALE", "标准女性"),
            ("ATHLETIC", "健硕"),
            ("SLIM", "纤细"),
            ("TEEN", "少年"),
            ("CHILD", "儿童"),
            ("BROAD", "宽厚"),
            ("CHIBI", "二头身"),
        ]:
            op = grid.operator(
                "aidirector.add_character",
                text=label,
                icon="OUTLINER_OB_ARMATURE",
            )
            op.preset = preset_id

        root = selected_character_root(context)
        box = layout.box()
        box.label(text="当前角色")

        if root:
            box.prop(root, "name", text="名称")
            box.prop(root, "location", text="位置")
            box.prop(root, "rotation_euler", text="旋转")
            box.prop(root, "scale", text="缩放")
            box.operator(
                "aidirector.duplicate_character",
                text="复制完整角色",
            )
        else:
            box.label(text="点击人物任意部位选择角色")

        box = layout.box()
        box.label(text="导演输出", icon="EXPORT")
        box.prop(context.scene, "ai_director_shot", text="景别")
        box.prop(context.scene, "ai_director_movement", text="运镜")
        box.prop(context.scene, "ai_director_duration", text="时长")
        box.prop(context.scene, "ai_director_action", text="人物动作")
        box.prop(context.scene, "ai_director_mood", text="画面情绪")
        box.prop(
            context.scene,
            "ai_director_comfyui_folder",
            text="ComfyUI目录",
        )
        box.operator(
            "aidirector.export_comfyui",
            text="导出到 ComfyUI",
            icon="EXPORT",
        )

        box = layout.box()
        box.label(text="机位", icon="CAMERA_DATA")
        cam = get_camera()
        if cam and cam.type == "CAMERA":
            box.prop(cam.data, "lens", text="焦距")
            box.prop(cam.data, "display_size", text="相机图标大小")
        box.operator(
            "aidirector.refresh_frustum",
            icon="CAMERA_DATA",
        )


classes = (
    AIDIRECTOR_OT_add_character,
    AIDIRECTOR_OT_duplicate_character,
    AIDIRECTOR_OT_director_view,
    AIDIRECTOR_OT_camera_view,
    AIDIRECTOR_OT_refresh_frustum,
    AIDIRECTOR_OT_export_comfyui,
    AIDIRECTOR_PT_stage_tools,
)


@persistent
def aidirector_load_post(_dummy):
    try:
        tag_existing_characters()
        style_viewports()
        rebuild_camera_frustum()
    except Exception:
        pass


def register():
    tag_existing_characters()

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.ai_director_shot = bpy.props.EnumProperty(
        name="景别",
        items=[
            ("ECU", "大特写", ""),
            ("CU", "特写", ""),
            ("MCU", "近景", ""),
            ("MS", "中景", ""),
            ("FS", "全身", ""),
            ("WS", "远景", ""),
            ("EWS", "大远景", ""),
        ],
        default="MS",
    )

    bpy.types.Scene.ai_director_movement = bpy.props.EnumProperty(
        name="运镜",
        items=[
            ("STATIC", "固定镜头", ""),
            ("DOLLY_IN", "缓慢推进", ""),
            ("DOLLY_OUT", "缓慢拉远", ""),
            ("TRACK_LEFT", "向左跟拍", ""),
            ("TRACK_RIGHT", "向右跟拍", ""),
            ("PAN_LEFT", "向左摇镜", ""),
            ("PAN_RIGHT", "向右摇镜", ""),
            ("ORBIT_LEFT", "向左环绕", ""),
            ("ORBIT_RIGHT", "向右环绕", ""),
        ],
        default="STATIC",
    )

    bpy.types.Scene.ai_director_duration = bpy.props.FloatProperty(
        name="镜头时长",
        default=5.0,
        min=0.1,
        max=60.0,
        unit="TIME",
    )

    bpy.types.Scene.ai_director_action = bpy.props.StringProperty(
        name="人物动作",
        default="remains still facing the camera",
    )

    bpy.types.Scene.ai_director_mood = bpy.props.StringProperty(
        name="画面情绪",
        default="restrained, distant, sense of fate",
    )

    bpy.types.Scene.ai_director_comfyui_folder = bpy.props.StringProperty(
        name="ComfyUI目录",
        subtype="DIR_PATH",
        default="",
    )

    bpy.types.Scene.ai_director_last_export = bpy.props.StringProperty(
        name="最后导出路径",
        default="",
        options={"HIDDEN"},
    )

    if aidirector_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(aidirector_load_post)

    style_viewports()
    rebuild_camera_frustum()


def unregister():
    if aidirector_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(aidirector_load_post)

    for prop_name in (
        "ai_director_shot",
        "ai_director_movement",
        "ai_director_duration",
        "ai_director_action",
        "ai_director_mood",
        "ai_director_comfyui_folder",
        "ai_director_last_export",
    ):
        if hasattr(bpy.types.Scene, prop_name):
            delattr(bpy.types.Scene, prop_name)

    _remove_frustum()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
