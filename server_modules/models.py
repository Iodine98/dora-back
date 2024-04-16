import json
from sqlalchemy import JSON, Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __abstract__ = True


class SecondBase(DeclarativeBase):
    __abstract__ = True


class ChatHistoryModel(SecondBase):
    __tablename__ = "message_store"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36))
    message = Column(JSON)


class FinalAnswerModel(Base):
    __tablename__ = "final_answer"
    session_id = Column(String(36), primary_key=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    number_of_messages = Column(Integer, default=-1)
    original_answer = Column(JSON)
    edited_answer = Column(JSON)

    def __repr__(self) -> str:
        return f"FinalAnswer(session_id={self.session_id}, original_answer={json.dumps(self.original_answer)}, edited_answer={json.dumps(self.edited_answer)}, start_time={self.start_time}, end_time={self.end_time})"