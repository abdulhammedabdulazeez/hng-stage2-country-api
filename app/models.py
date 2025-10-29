from sqlmodel import Column, Field, Relationship, SQLModel, null
import uuid
from sqlalchemy import TIMESTAMP
from typing import Optional
from datetime import datetime


class Country(SQLModel, table=True):
    __tablename__ = "countries"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False, index=True)
    capital: Optional[str]
    region: Optional[str]
    population: int = Field(nullable=False)
    currency_code: Optional[str] = Field(default=None)
    exchange_rate: Optional[float] = Field(default=None)
    estimated_gdp: Optional[float] = Field(default=None)
    flag_url: Optional[str] = Field(default=None)
    last_refreshed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )


class AppMetadata(SQLModel, table=True):
    __tablename__ = "app_metadata"
    id: int = Field(primary_key=True, default=1)
    last_refreshed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
