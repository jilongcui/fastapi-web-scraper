from pydantic import BaseModel

class Interview(BaseModel):
    careerId: str | None = None
    careerName: str | None = None
    departmentId: str
    department: str | None = None
    title: str
    origin: str
    province: str | None = None
    year: str | None = None
    text: str
    analysis: str 
    sampleAnswer: str
    introduction: str | None = None
    material: str | None = None
    mindmapUrl: str | None = None
    comment: str | None = None