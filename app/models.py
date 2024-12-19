from sqlalchemy import Column, Integer, String, UniqueConstraint
from .database_sql import Base

class Word(Base):
    __tablename__ = 'words'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    word = Column(String(255), unique=True, index=True)
    frequency = Column(Integer)
    initials = Column(String(16), index=True)  # 添加初始字母字段
    # 新增列：key1, key2 和 key3，默认值为0
    key1 = Column(Integer, default=0)
    key2 = Column(Integer, default=0)
    key3 = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('word', name='uq_word'),
    )

