"""First persistence model: raw assertion contexts, immutable snapshots and derived events."""
from datetime import date
from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Release(Base):
    __tablename__='source_releases'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    release_date: Mapped[date] = mapped_column(Date)
    retrieved_date: Mapped[date] = mapped_column(Date)
    filename: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    byte_size: Mapped[int] = mapped_column(BigInteger)
    headers: Mapped[list] = mapped_column(JSONB)
    __table_args__=(CheckConstraint("kind IN ('variant', 'submission')",name='ck_release_kind'),)


class Variant(Base):
    __tablename__='variants'
    variation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    genes: Mapped[list] = mapped_column(JSONB)
    __table_args__=(CheckConstraint('variation_id > 0',name='ck_variant_positive'),)


class AggregateSnapshot(Base):
    __tablename__='aggregate_snapshots'
    release_id: Mapped[int] = mapped_column(ForeignKey('source_releases.id'), primary_key=True)
    variation_id: Mapped[int] = mapped_column(ForeignKey('variants.variation_id'), primary_key=True)
    classifications: Mapped[list] = mapped_column(JSONB)
    review_statuses: Mapped[list] = mapped_column(JSONB)
    genes: Mapped[list] = mapped_column(JSONB)
    source_lines: Mapped[list] = mapped_column(JSONB)
    vcv_accession_version: Mapped[str | None] = mapped_column(Text)


class ConditionContext(Base):
    __tablename__='condition_contexts'
    context_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    submitted: Mapped[str] = mapped_column(Text)
    reported: Mapped[str] = mapped_column(Text)
    medgen_ids: Mapped[list] = mapped_column(JSONB)


class SubmissionSnapshot(Base):
    __tablename__='submission_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey('source_releases.id'))
    variation_id: Mapped[int] = mapped_column(ForeignKey('variants.variation_id'), index=True)
    scv_base: Mapped[str] = mapped_column(String(32))
    scv_version: Mapped[int] = mapped_column(Integer)
    condition_hash: Mapped[str] = mapped_column(ForeignKey('condition_contexts.context_hash'))
    submitter_name: Mapped[str] = mapped_column(Text)
    submitter_id: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(Text)
    classification_type: Mapped[str] = mapped_column(String(24))
    last_evaluated_raw: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(Text)
    rcv_accessions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    vcv_accession_version: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
    __table_args__=(UniqueConstraint('release_id','scv_base',name='uq_submission_release_scv'),
                    CheckConstraint('scv_version > 0',name='ck_scv_version'))


class Comparison(Base):
    __tablename__='comparisons'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    previous_variant_release_id: Mapped[int] = mapped_column(ForeignKey('source_releases.id'))
    current_variant_release_id: Mapped[int] = mapped_column(ForeignKey('source_releases.id'))
    previous_submission_release_id: Mapped[int] = mapped_column(ForeignKey('source_releases.id'))
    current_submission_release_id: Mapped[int] = mapped_column(ForeignKey('source_releases.id'))
    aggregate_sha256: Mapped[str] = mapped_column(String(64))
    submission_sha256: Mapped[str] = mapped_column(String(64))
    scope: Mapped[dict] = mapped_column(JSONB)


class AggregateChange(Base):
    __tablename__='aggregate_changes'
    comparison_id: Mapped[str] = mapped_column(ForeignKey('comparisons.id'), primary_key=True)
    variation_id: Mapped[int] = mapped_column(ForeignKey('variants.variation_id'), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)


class SubmissionChange(Base):
    __tablename__='submission_changes'
    comparison_id: Mapped[str] = mapped_column(ForeignKey('comparisons.id'), primary_key=True)
    scv_base: Mapped[str] = mapped_column(String(32), primary_key=True)
    previous_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey('submission_snapshots.id'))
    current_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey('submission_snapshots.id'))
    status: Mapped[str] = mapped_column(String(32))
    flags: Mapped[list] = mapped_column(JSONB)
    payload: Mapped[dict] = mapped_column(JSONB)
