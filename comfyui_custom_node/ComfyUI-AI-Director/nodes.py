import os
import json
import hashlib


class AIDirectorLoader:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_file": (
                    "STRING",
                    {
                        "default": "director_scene.json",
                        "multiline": False,
                    },
                ),
            }
        }

    RETURN_TYPES = (
        "STRING",
        "STRING",
        "STRING",
        "FLOAT",
        "FLOAT",
        "STRING",
    )

    RETURN_NAMES = (
        "prompt",
        "shot",
        "movement",
        "lens_mm",
        "duration_s",
        "camera_data",
    )

    FUNCTION = "load_director_data"
    CATEGORY = "AI Director"

    def _resolve_path(self, json_file):
        if os.path.isabs(json_file):
            return json_file

        node_folder = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(node_folder, json_file)

    def load_director_data(self, json_file):
        path = self._resolve_path(json_file)

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"AI Director JSON not found: {path}"
            )

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        director_prompt = data.get("generated_prompt", "")
        prompt = (
            "\n\n"
            "DIRECTOR INSTRUCTIONS:\n\n"
            + director_prompt
        )

        shot_data = data.get("shot", {})
        shot = shot_data.get(
            "size_prompt",
            shot_data.get("size", "")
        )
        duration = float(
            shot_data.get("duration_seconds", 0.0)
        )

        camera = data.get("camera", {})
        movement = camera.get(
            "movement_prompt",
            camera.get("movement", "")
        )
        lens = float(camera.get("lens_mm", 0.0))

        camera_data = json.dumps(
            camera,
            ensure_ascii=False,
            indent=2
        )

        return (
            prompt,
            shot,
            movement,
            lens,
            duration,
            camera_data,
        )

    @classmethod
    def IS_CHANGED(cls, json_file):
        if os.path.isabs(json_file):
            path = json_file
        else:
            node_folder = os.path.dirname(
                os.path.abspath(__file__)
            )
            path = os.path.join(node_folder, json_file)

        if not os.path.exists(path):
            return "FILE_NOT_FOUND"

        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()


NODE_CLASS_MAPPINGS = {
    "AIDirectorLoader": AIDirectorLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AIDirectorLoader": "🎬 AI Director Loader",
}
