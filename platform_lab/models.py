from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Document(Strict):
    id: str
    tenant: str
    readers: List[str]
    text: str = Field(max_length=20000)

class Case(Strict):
    id: str
    cluster: str
    split: Literal['dev', 'holdout']
    category: str
    tenant: str
    principal: str
    query: str = Field(min_length=1, max_length=4000)
    required: List[str]
    forbidden: List[str] = []
    expected_sources: List[str] = []
    expect_abstention: bool = False

class Dataset(Strict):
    version: str
    documents: List[Document]
    cases: List[Case]

class RunRequest(Strict):
    split: Literal['dev', 'holdout'] = 'dev'
    provider: Literal['offline', 'openai', 'anthropic'] = 'offline'
    model: str = Field(default='extractive-v1', min_length=1, max_length=100)
    prompt: str = Field(default='Answer accurately and completely using the supplied sources.', min_length=1, max_length=4000)
    repeats: int = Field(default=1, ge=1, le=5)
    judge_provider: Optional[Literal['openai', 'anthropic']] = None
    judge_model: Optional[str] = Field(default=None, max_length=100)

class Answer(Strict):
    answer: str = Field(max_length=16000)
    citations: List[str]
    abstain: bool

class Judgment(Strict):
    groundedness: int = Field(ge=0, le=4)
    completeness: int = Field(ge=0, le=4)
    evidence: str = Field(max_length=2000)

class Comparison(Strict):
    baseline: str
    candidate: str
    margin: float = Field(default=.05, ge=0, le=1)
