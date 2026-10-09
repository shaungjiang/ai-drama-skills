from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from ai_drama.core.storage import uid, now, safe_id


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class WorkflowStatus(StrEnum):
    CREATED = "CREATED"
    STATIC_VALIDATED = "STATIC_VALIDATED"
    ENV_VALIDATED = "ENV_VALIDATED"
    RUNTIME_VERIFIED = "RUNTIME_VERIFIED"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    DISABLED = "DISABLED"
    OUTDATED = "OUTDATED"


class CharacterState(Model):
    state_id: str = Field(default_factory=lambda: uid("state"))
    version: int = Field(default=1, ge=1)
    clothing: str = "待设计"
    accessories: list[str] = Field(default_factory=list)
    weapons: list[str] = Field(default_factory=list)
    health: str = "正常"
    reference_images: list[str] = Field(default_factory=list)
    approved: bool = False
    approval_note: str | None = None


class Character(Model):
    character_id: str = Field(default_factory=lambda: uid("char"))
    name: str
    gender: str = "未设定"
    age: str = "未设定"
    identity: str = "未设定"
    appearance: str = "待设计"
    face_shape: str = "待设计"
    facial_features: str = "待设计"
    hairstyle: str = "待设计"
    hair_color: str = "待设计"
    skin_color: str = "待设计"
    physique: str = "待设计"
    personality: str = "未设定"
    visual_anchors: list[str] = Field(default_factory=list)
    states: list[CharacterState] = Field(default_factory=lambda: [CharacterState()])
    active_state: int = 1

    @model_validator(mode="after")
    def valid_state(self):
        versions = [s.version for s in self.states]
        if len(set(versions)) != len(versions) or self.active_state not in versions:
            raise ValueError("Character state versions must be unique and active_state must exist")
        return self

    def state(self):
        return next(s for s in self.states if s.version == self.active_state)


class Location(Model):
    location_id: str = Field(default_factory=lambda: uid("loc"))
    name: str
    layout: str
    architecture: str
    visual_anchors: list[str] = Field(default_factory=list)
    reference_images: list[str] = Field(default_factory=list)
    approved: bool = False


class Prop(Model):
    prop_id: str = Field(default_factory=lambda: uid("prop"))
    name: str
    appearance: str
    owner_id: str | None = None
    rule: str = "不可凭空消失"


class Scene(Model):
    scene_id: str
    location_id: str
    time: str = "夜晚"
    weather: str = "无雨"
    lighting: str = "左侧暖主光、右侧冷辅光"
    characters: list[str] = Field(default_factory=list)
    objective: str = ""


class VisualStyle(Model):
    style_id: Literal["cinematic_3d_donghua", "cinematic_live_action"]
    mode: Literal["AUTO", "MANUAL", "LOCKED"] = "AUTO"
    confirmed: bool = False
    rules: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class ImagePrompt(Model):
    prompt_id: str = Field(default_factory=lambda: uid("prompt"))
    shot_id: str
    frame: Literal["first", "last"] = "first"
    language: Literal["zh", "en"] = "zh"
    positive: str
    negative: str
    model_family: str
    source_hash: str


class Shot(Model):
    shot_id: str
    scene_id: str
    characters: list[str] = Field(default_factory=list)
    duration: float = Field(gt=0, le=15)
    size: str = "中景"
    angle: str = "平视"
    composition: str = "人物位于左侧三分线，右侧保留行动空间"
    eye_line: str = "画面右侧"
    axis_side: str = "A"
    camera_movement: str = "固定机位"
    action: str
    expression: str = "克制"
    dialogue: str = ""
    environment: str = "稳定"
    first_frame: str
    last_frame: str
    frame_mode: Literal["single", "dual"] = "single"
    transition: str = "直接切换"
    previous_link: str = ""
    next_link: str = ""
    continuity_in: dict[str, str] = Field(default_factory=dict)
    continuity_out: dict[str, str] = Field(default_factory=dict)
    state_versions: dict[str, int] = Field(default_factory=dict)
    prop_ids: list[str] = Field(default_factory=list)
    source_excerpt: str = ""

    @field_validator("shot_id", "scene_id")
    @classmethod
    def ids(cls, value):
        return safe_id(value)


class Episode(Model):
    episode_id: str = "EP01"
    title: str
    duration: float = Field(default=60, gt=0)
    scenes: list[Scene] = Field(default_factory=list)
    shots: list[Shot] = Field(default_factory=list)
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    props: list[Prop] = Field(default_factory=list)
    relationships: list[dict[str, str]] = Field(default_factory=list)
    synopsis: str = ""
    hook: str = ""
    cliffhanger: str = ""
    authoring: Literal["extractive_draft", "codex_reviewed", "authored_demo"] = "extractive_draft"

    @field_validator("episode_id")
    @classmethod
    def ids(cls, value):
        return safe_id(value)

    @model_validator(mode="after")
    def references(self):
        groups = [self.shots, self.scenes, self.characters, self.locations, self.props]
        fields = ["shot_id", "scene_id", "character_id", "location_id", "prop_id"]
        for items, field in zip(groups, fields):
            ids = [getattr(item, field) for item in items]
            if len(set(ids)) != len(ids):
                raise ValueError(f"Duplicate {field}")
        chars = {c.character_id for c in self.characters}
        locations = {l.location_id for l in self.locations}
        scenes = {s.scene_id for s in self.scenes}
        props = {p.prop_id for p in self.props}
        for scene in self.scenes:
            if scene.location_id not in locations or not set(scene.characters) <= chars:
                raise ValueError("Scene has unknown location or character")
        for shot in self.shots:
            if shot.scene_id not in scenes or not set(shot.characters) <= chars or not set(shot.prop_ids) <= props:
                raise ValueError("Shot has unknown scene, character or prop")
            for cid, version in shot.state_versions.items():
                character = next((c for c in self.characters if c.character_id == cid), None)
                if character is None or version not in {s.version for s in character.states}:
                    raise ValueError("Shot references unknown character state")
        if self.shots and abs(sum(s.duration for s in self.shots) - self.duration) > 0.1:
            raise ValueError("Shot durations must add up to episode duration")
        return self


class Project(Model):
    project_id: str = Field(default_factory=lambda: uid("project"))
    name: str
    source_path: str
    source_hash: str
    duration: float = Field(default=60, gt=0)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    style: VisualStyle
    episodes: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now)


class FrameAsset(Model):
    asset_id: str = Field(default_factory=lambda: uid("asset"))
    shot_id: str
    frame: Literal["first", "last", "character", "location"]
    path: str
    sha256: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    job_id: str
    reference_paths: list[str] = Field(default_factory=list)
    visual_review: Literal["PENDING", "PASS", "WARNING", "ERROR"] = "PENDING"
    review_note: str = ""
    review_method: Literal["pending", "human", "visual-model"] = "pending"


class GenerationJob(Model):
    job_id: str = Field(default_factory=lambda: uid("job"))
    shot_id: str
    workflow_id: str
    model: str
    seed: int = Field(ge=0)
    prompt: str
    parameters: dict[str, Any]
    output_path: str
    status: Literal["PENDING", "SUBMITTED", "RUNNING", "SUCCEEDED", "FAILED", "UNKNOWN"] = "PENDING"
    error: str | None = None
    prompt_id: str | None = None
    attempts: int = 0
    created_at: str = Field(default_factory=now)
    completed_at: str | None = None
    assets: list[FrameAsset] = Field(default_factory=list)


class WorkflowDefinition(Model):
    api: dict[str, Any]
    visual: dict[str, Any]
    bindings: dict[str, list[list[str]]] = Field(default_factory=dict)


class WorkflowRegistryEntry(Model):
    workflow_id: str
    workflow_name: str
    model_family: str
    model_version: str
    task_type: str
    supported_styles: list[str]
    supported_inputs: list[str]
    required_nodes: list[str]
    workflow_path: str
    api_workflow_path: str
    metadata_path: str
    validation_status: WorkflowStatus = WorkflowStatus.CREATED
    runtime_verified: bool = False
    version: int = Field(default=1, ge=1)
    parent_id: str | None = None
    last_tested_at: str | None = None
    environment_fingerprint: str
    graph_hash: str
    runtime_graph_hash: str | None = None
    evidence_job: str | None = None
    validation_errors: list[str] = Field(default_factory=list)


class QCIssue(Model):
    severity: Literal["PASS", "WARNING", "ERROR"]
    category: str
    message: str
    shot_id: str | None = None
    method: Literal["metadata", "file", "human", "visual-model", "runtime"] = "metadata"


class QCReport(Model):
    report_id: str = Field(default_factory=lambda: uid("qc"))
    episode_id: str
    created_at: str = Field(default_factory=now)
    status: Literal["PASS", "WARNING", "ERROR"]
    issues: list[QCIssue]
    visual_scoring: str = "No automatic visual quality score; human review required."
