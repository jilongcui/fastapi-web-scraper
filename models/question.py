from pydantic import BaseModel

class Question(BaseModel):
    careerId: str | None = None
    careerName: str | None = None
    typeId: str | None = None
    typeName: str | None = None
    title: str
    origin: str
    province: str | None = None
    year: str | None = None
    text: str
    options: list[str]
    allowMultipleSelections: bool = False
    correctAnswer: str 
    knowledgers: str
    explanation: str | None = None
    material: str | None = None
    mindmapUrl: str | None = None
    comment: str | None = None