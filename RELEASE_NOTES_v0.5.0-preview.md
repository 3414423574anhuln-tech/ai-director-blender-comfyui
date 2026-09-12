# AI Director v0.5.0 Preview

这是 AI Director for Blender + ComfyUI 的第一个公开预览版本。

## 怎么用

1. 下载 `AI-Director-Blender-v0.5.0-preview.py`，在 Blender 的 `Edit → Preferences → Add-ons → Install from Disk` 中安装并启用。
2. 在 Blender 3D View 中按 `N`，打开 `3D导演台`。
3. 下载并解压 `ComfyUI-AI-Director-v0.5.0-preview.zip`，把 `ComfyUI-AI-Director` 放进 `ComfyUI/custom_nodes/`，然后重启 ComfyUI。
4. 在 ComfyUI 中添加 `AI Director Loader`。
5. 回 Blender，在 `3D导演台 → 导演输出` 中，把 `ComfyUI目录` 指向 `ComfyUI/custom_nodes/ComfyUI-AI-Director`。
6. 设置景别、运镜、焦距、时长、人物动作和情绪，然后点击 `导出到 ComfyUI`。
7. 回 ComfyUI 运行工作流。Loader 会读取新的 `director_scene.json`。把它的 `prompt` 输出与原始视频 Prompt 合并，再接入视频模型。

例如 Blender 中设置 `中景 + 缓慢推进 + 50mm`，ComfyUI 会收到类似：

`medium shot, slow dolly in, 50mm lens`

## 当前状态

这是 Preview 版本，不是正式生产版。当前已支持 3D 导演台、视角切换、相机视锥、多人物预设、导演参数导出和 ComfyUI Loader；多镜头 Timeline、完整姿势 Rig 和模型专用 Prompt Adapter 尚未实现。

MIT License
