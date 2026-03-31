"""SQLAlchemy database models for the Zettelkasten MCP server."""

import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, Session, declarative_base, relationship, sessionmaker

from parazettel_mcp.config import config
from parazettel_mcp.models.schema import LinkType, NoteType

# Create base class for SQLAlchemy models
Base = declarative_base()

# Association table for tags and notes
note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", String(255), ForeignKey("notes.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class DBNote(Base):
    """Database model for a note."""

    __tablename__ = "notes"
    id = Column(String(255), primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    note_type = Column(
        String(50), default=NoteType.PERMANENT.value, nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON-serialized note.metadata dict
    # Action-item columns
    status = Column(String(50), nullable=True, index=True)
    source = Column(String(50), nullable=True, index=True)
    due_date = Column(Date, nullable=True, index=True)
    priority = Column(Integer, nullable=True)
    recurrence_rule = Column(String(255), nullable=True)
    estimated_minutes = Column(Integer, nullable=True)
    remind_at = Column(Date, nullable=True, index=True)
    project_id = Column(String(255), nullable=True, index=True)
    area_id = Column(String(255), nullable=True, index=True)

    # Relationships
    tags = relationship("DBTag", secondary=note_tags, back_populates="notes")
    outgoing_links = relationship(
        "DBLink",
        foreign_keys="DBLink.source_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    incoming_links = relationship(
        "DBLink",
        foreign_keys="DBLink.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation of note."""
        return f"<Note(id='{self.id}', title='{self.title}')>"


class DBTag(Base):
    """Database model for a tag."""

    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)

    # Relationships
    notes = relationship("DBNote", secondary=note_tags, back_populates="tags")

    def __repr__(self) -> str:
        """Return string representation of tag."""
        return f"<Tag(id={self.id}, name='{self.name}')>"


class DBLink(Base):
    """Database model for a link between notes."""

    __tablename__ = "links"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(255), ForeignKey("notes.id"), nullable=False)
    target_id = Column(String(255), ForeignKey("notes.id"), nullable=False)
    link_type = Column(String(50), default=LinkType.REFERENCE.value, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    # Relationships
    source = relationship(
        "DBNote", foreign_keys=[source_id], back_populates="outgoing_links"
    )
    target = relationship(
        "DBNote", foreign_keys=[target_id], back_populates="incoming_links"
    )

    # Add a unique constraint to prevent duplicate links of the same type
    __table_args__ = (
        UniqueConstraint(
            "source_id", "target_id", "link_type", name="unique_link_type"
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of link."""
        return (
            f"<Link(id={self.id}, source='{self.source_id}', "
            f"target='{self.target_id}', type='{self.link_type}')>"
        )


def init_db() -> Engine:
    """Initialize the database."""
    from sqlalchemy import event, text

    # Create engine based on configuration
    engine = create_engine(config.get_db_url())
    Base.metadata.create_all(engine)

    # Connection-scoped pragmas — applied on every new connection
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-8000")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    # One-time: WAL mode (persistent) and schema migration
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        # Add new columns to existing databases if absent
        existing = {
            row[1] for row in conn.execute(text("PRAGMA table_info(notes)")).fetchall()
        }
        new_cols = [
            ("metadata_json", "TEXT"),
            ("status", "VARCHAR(50)"),
            ("source", "VARCHAR(50)"),
            ("due_date", "DATE"),
            ("priority", "INTEGER"),
            ("recurrence_rule", "VARCHAR(255)"),
            ("estimated_minutes", "INTEGER"),
            ("remind_at", "DATE"),
            ("project_id", "VARCHAR(255)"),
            ("area_id", "VARCHAR(255)"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing:
                conn.execute(
                    text(f"ALTER TABLE notes ADD COLUMN {col_name} {col_type}")
                )
        conn.commit()
    return engine


def get_session_factory(engine=None):
    """Get a session factory for the database."""
    if engine is None:
        engine = create_engine(config.get_db_url())
    return sessionmaker(bind=engine)
