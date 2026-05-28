from sqlalchemy import Column, Integer
from sqlalchemy.orm import declared_attr, declarative_base


class Base:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


DeclarativeBase = declarative_base(cls=Base)
