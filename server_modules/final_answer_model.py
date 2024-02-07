import json
from sqlalchemy import JSON, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    __abstract__ = True
    id = Column(Integer, primary_key=True)

class FinalAnswerModel(Base):
    __tablename__ = "final_answer"
    id = Column(Integer, primary_key=True)
    session_id = Column(String)
    final_answer = Column(JSON)

    def __repr__(self) -> str:
        return f"FinalAnswer(session_id={self.session_id}, final_answer={json.dumps(self.final_answer)})"