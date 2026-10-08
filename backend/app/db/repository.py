from uuid import uuid4
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL, EMBEDDING_DIM
from app.db.models import Base, AgentRun, AgentEvent

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30}
    if DATABASE_URL.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)
Session = sessionmaker(engine, expire_on_commit=False)
if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")


def init_db():
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as c:
            c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            c.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS chunk_vectors (chunk_id text PRIMARY KEY REFERENCES chunks(id), embedding vector({EMBEDDING_DIM}))"
                )
            )


def new_id():
    return str(uuid4())


def row_dict(row):
    if row is None:
        return None
    return {
        col.name: (
            getattr(row, col.name).isoformat()
            if hasattr(getattr(row, col.name), "isoformat")
            else getattr(row, col.name)
        )
        for col in row.__table__.columns
    }


def add_event(
    run_id, node, input_summary, output_summary, duration=0, tool=None, event_type="completed"
):
    with Session.begin() as s:
        s.add(
            AgentEvent(
                run_id=run_id,
                node=node,
                tool=tool,
                input_summary=input_summary,
                output_summary=output_summary,
                duration=round(duration, 3),
                event_type=event_type,
            )
        )


def get_run(run_id):
    with Session() as s:
        run = row_dict(s.get(AgentRun, run_id))
        if run is None:
            return None
        run["events"] = [
            row_dict(e)
            for e in s.scalars(
                select(AgentEvent).where(AgentEvent.run_id == run_id).order_by(AgentEvent.id)
            )
        ]
        return run
