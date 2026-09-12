# AI Director for Blender + ComfyUI

A prototype 3D director workflow that connects Blender camera and character direction data to ComfyUI.

## Features

- Blender 3D director panel
- Director View / Camera View switching
- Visible camera frustum
- Lightweight mannequin characters
- Character presets and complete-character duplication
- Shot size, camera movement, duration, action, and mood controls
- One-click export of `director_scene.json`
- ComfyUI `AI Director Loader` custom node
- Automatic ComfyUI refresh when the exported JSON changes

## Requirements

- Blender 5.2 or compatible Blender version
- ComfyUI
- Windows is currently the primary tested target

## Repository layout

```text
blender_addon/
  ai_director_stage_tools.py

comfyui_custom_node/
  ComfyUI-AI-Director/
    __init__.py
    nodes.py

examples/
  director_scene.example.json
```

## Blender installation

1. Open Blender.
2. Go to `Edit > Preferences > Add-ons`.
3. Choose `Install from Disk`.
4. Select `blender_addon/ai_director_stage_tools.py`.
5. Enable **AI Director Stage Tools**.
6. In the 3D View, press `N`.
7. Open the **3D导演台** tab.

## ComfyUI installation

Copy:

```text
comfyui_custom_node/ComfyUI-AI-Director
```

to:

```text
ComfyUI/custom_nodes/ComfyUI-AI-Director
```

Restart ComfyUI and search for `AI Director Loader`.

## Connecting Blender to ComfyUI

In Blender:

1. Open `N > 3D导演台`.
2. Find **导演输出**.
3. Set **ComfyUI目录** to your actual `ComfyUI/custom_nodes/ComfyUI-AI-Director` folder.
4. Set shot size, camera movement, duration, action, and mood.
5. Click **导出到 ComfyUI**.

Blender writes `director_scene.json` into the ComfyUI custom node folder.

The ComfyUI loader outputs:

- `prompt`
- `shot`
- `movement`
- `lens_mm`
- `duration_s`
- `camera_data`

## Current limitations

This is an early prototype.

- The mannequin system is lightweight and not a full production rig.
- The current workflow exports one global director instruction block.
- Camera frustum refresh may need to be triggered after some camera parameter changes.
- The Blender scene currently expects a camera named `机位1` and uses `角色A` as the base character template.
- Multi-shot timeline editing and pose-rig authoring are not implemented yet.
