import json
from sqlalchemy import JSON, Column, Integer, String, DateTime
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase

from chatdoc.utils import Utils

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
    final_answer = Column(JSON)

    def __repr__(self) -> str:
        return f"FinalAnswer(session_id={self.session_id}, final_answer={json.dumps(self.final_answer)}, start_time={self.start_time}, end_time={self.end_time})"
    
def add_new_record(new_session_id: str) -> None:
    db_engine = sqlalchemy.create_engine(Utils.get_env_variable("FINAL_ANSWER_CONNECTION_STRING"))
    FinalAnswerModel.metadata.create_all(db_engine) # CREATE TABLE IF NOT EXISTS final_answer
    answer_model_record_query = sqlalchemy.select(FinalAnswerModel).where(FinalAnswerModel.session_id == new_session_id) # SELECT * FROM final_answer WHERE session_id = session_id
    insertion_stmt = sqlalchemy.insert(FinalAnswerModel).values(session_id=new_session_id, start_time=sqlalchemy.func.now())
    update_stmt = sqlalchemy.update(FinalAnswerModel).where(FinalAnswerModel.session_id == new_session_id).values(start_time=sqlalchemy.func.now(), final_answer={}, end_time=None, number_of_messages=-1) # INSERT INTO final_answer (session_id, final_answer) VALUES (session_id, final_answer
    with db_engine.connect() as connection:
        answer_model_record = connection.execute(answer_model_record_query)
        if not answer_model_record.fetchone():
            connection.execute(insertion_stmt)
        else:
            connection.execute(update_stmt)
        connection.commit()

def update_record_with_final_answer(session_id: str, final_answer: dict) -> None:
    db_final_answer_engine = sqlalchemy.create_engine(Utils.get_env_variable("FINAL_ANSWER_CONNECTION_STRING"))
    answer_model_record_query = sqlalchemy.select(FinalAnswerModel).where(FinalAnswerModel.session_id == session_id) # SELECT * FROM final_answer WHERE session_id = session_id
    update_stmt = sqlalchemy.update(FinalAnswerModel).where(FinalAnswerModel.session_id == session_id).values(final_answer=final_answer, end_time=sqlalchemy.func.now()) # INSERT INTO final_answer (session_id, final_answer) VALUES (session_id, final_answer)
    with db_final_answer_engine.connect() as connection:
        answer_model_record = connection.execute(answer_model_record_query)
        if not answer_model_record.fetchone():
            raise ValueError(f"No record found for session_id: {session_id}")
        connection.execute(update_stmt)
        connection.commit()
    db_chat_history_engine = sqlalchemy.create_engine(Utils.get_env_variable("CHAT_HISTORY_CONNECTION_STRING"))
    count_stmt = sqlalchemy.select(sqlalchemy.func.count(ChatHistoryModel.id)).where(ChatHistoryModel.session_id == session_id)
    with db_chat_history_engine.connect() as connection:
        number_of_messages = connection.execute(count_stmt).scalar()
        if number_of_messages is None:
            raise ValueError(f"No chat history found for session_id: {session_id}")
    update_message_count = sqlalchemy.update(FinalAnswerModel).where(FinalAnswerModel.session_id == session_id).values(number_of_messages=number_of_messages)
    with db_final_answer_engine.connect() as connection:
        connection.execute(update_message_count)
        connection.commit()


