from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # YGOPRODECK numeric ID
    name: Mapped[str] = mapped_column(String(255), index=True)
    type: Mapped[str] = mapped_column(String(100))
    archetype: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ygopro_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, index=True)
    tier: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    player_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    placements: Mapped[list["Placement"]] = relationship(back_populates="tournament")


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ygopro_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    archetype: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deck_url: Mapped[str] = mapped_column(Text)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    placements: Mapped[list["Placement"]] = relationship(back_populates="deck")
    cards: Mapped[list["DeckCard"]] = relationship(back_populates="deck", cascade="all, delete-orphan")


class Placement(Base):
    __tablename__ = "placements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    deck_id: Mapped[Optional[int]] = mapped_column(ForeignKey("decks.id"), nullable=True, index=True)
    placement: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    player_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    tournament: Mapped["Tournament"] = relationship(back_populates="placements")
    deck: Mapped[Optional["Deck"]] = relationship(back_populates="placements")


class DeckCard(Base):
    __tablename__ = "deck_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id"), index=True)
    card_id: Mapped[int] = mapped_column(Integer, index=True)
    card_name: Mapped[str] = mapped_column(String(255), index=True)
    card_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zone: Mapped[str] = mapped_column(String(10))  # main, extra, side
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    deck: Mapped["Deck"] = relationship(back_populates="cards")
