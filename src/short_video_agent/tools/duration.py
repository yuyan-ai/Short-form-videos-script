from ..policy import fingerprint

def estimate(draft):
    scenes = []
    for scene in draft["scenes"]:
        voice_seconds = sum(c.isalnum() for c in scene["voiceover"]) / 4
        subtitle_seconds = sum(c.isalnum() for c in scene["subtitle"]) / 4
        content_seconds = max(voice_seconds, subtitle_seconds)
        padding = max(0, scene["min_visual_seconds"] - content_seconds)
        seconds = round(max(content_seconds, scene["min_visual_seconds"]) + 0.5, 2)
        scenes.append({"scene_id": scene["scene_id"], "seconds": seconds,
                       "voice_seconds": voice_seconds, "subtitle_seconds": subtitle_seconds,
                       "padding_seconds": round(padding, 2)})
    return {"draft_hash": fingerprint(draft), "scenes": scenes,
            "total_seconds": round(sum(s["seconds"] for s in scenes), 2),
            "voice_seconds": round(sum(s["voice_seconds"] for s in scenes), 2),
            "padding_seconds": round(sum(s["padding_seconds"] for s in scenes), 2),
            "method": "每秒4个字/字符，逐镜取最低画面时长与朗读时长较大值，加0.5秒停顿；仅为估算"}
