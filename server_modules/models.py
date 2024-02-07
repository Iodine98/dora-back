import json
from sqlalchemy import JSON, Column, Integer, String, DateTime
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase

from chatdoc.utils import Utils

class Base(DeclarativeBase):
    __abstract__ = True

class FinalAnswerModel(Base):
    __tablename__ = "final_answer"
    session_id = Column(String, primary_key=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    final_answer = Column(JSON)

    def __repr__(self) -> str:
        return f"FinalAnswer(session_id={self.session_id}, final_answer={json.dumps(self.final_answer)}, start_time={self.start_time}, end_time={self.end_time})"
    
def add_new_record(new_session_id: str) -> None:
    db_engine = sqlalchemy.create_engine(Utils.get_env_variable("FINAL_ANSWER_CONNECTION_STRING"))
    FinalAnswerModel.metadata.create_all(db_engine) # CREATE TABLE IF NOT EXISTS final_answer
    answer_model_record_query = sqlalchemy.select(FinalAnswerModel).where(FinalAnswerModel.session_id == new_session_id) # SELECT * FROM final_answer WHERE session_id = session_id
    insertion_stmt = sqlalchemy.insert(FinalAnswerModel).values(session_id=new_session_id, start_time=sqlalchemy.func.now())
    update_stmt = sqlalchemy.update(FinalAnswerModel).where(FinalAnswerModel.session_id == new_session_id).values(start_time=sqlalchemy.func.now(), final_answer={}, end_time=None) # INSERT INTO final_answer (session_id, final_answer) VALUES (session_id, final_answer
    with db_engine.connect() as connection:
        answer_model_record = connection.execute(answer_model_record_query)
        if not answer_model_record.fetchone():
            connection.execute(insertion_stmt)
        else:
            connection.execute(update_stmt)
        connection.commit()

def update_record_with_final_answer(session_id: str, final_answer: dict) -> None:
    db_engine = sqlalchemy.create_engine(Utils.get_env_variable("FINAL_ANSWER_CONNECTION_STRING"))
    answer_model_record_query = sqlalchemy.select(FinalAnswerModel).where(FinalAnswerModel.session_id == session_id) # SELECT * FROM final_answer WHERE session_id = session_id
    update_stmt = sqlalchemy.update(FinalAnswerModel).where(FinalAnswerModel.session_id == session_id).values(final_answer=final_answer, end_time=sqlalchemy.func.now()) # INSERT INTO final_answer (session_id, final_answer) VALUES (session_id, final_answer)
    with db_engine.connect() as connection:
        answer_model_record = connection.execute(answer_model_record_query)
        if not answer_model_record.fetchone():
            raise ValueError(f"No record found for session_id: {session_id}")
        connection.execute(update_stmt)
        connection.commit()