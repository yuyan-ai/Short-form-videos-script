"""模型动作与脚本校验。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")
class Claim(Strict):
    text: str
    material_id: str
    fact_id: str
class Scene(Strict):
    scene_id: str = Field(min_length=1)
    visual: str
    voiceover: str
    subtitle: str
    min_visual_seconds: float = Field(ge=0, le=300, allow_inf_nan=False)
    claims: list[Claim]
class Draft(Strict):
    title: str = Field(min_length=1)
    scenes: list[Scene] = Field(min_length=1, max_length=30)
    @model_validator(mode="after")
    def unique_ids(self):
        if len({s.scene_id for s in self.scenes}) != len(self.scenes):
            raise ValueError("scene_id必须唯一")
        return self
class Action(Strict):
    name: Literal["search_materials", "save_draft", "estimate_duration", "check_rules", "request_info", "finish", "fail"]
    reason: str = Field(min_length=1, max_length=500)
    query: str | None = None
    draft: Draft | None = None
    @model_validator(mode="after")
    def arguments(self):
        if self.name == "search_materials" and not (self.query and self.query.strip()):
            raise ValueError("检索必须提供query")
        if self.name == "save_draft" and self.draft is None:
            raise ValueError("保存必须提供draft")
        if self.name != "save_draft" and self.draft is not None:
            raise ValueError("此动作不接受draft")
        return self
