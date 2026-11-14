"""Create release snapshots condition contexts and comparison events"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '2443fd918acb'
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    op.create_table('condition_contexts',
    sa.Column('context_hash', sa.String(length=64), nullable=False),
    sa.Column('submitted', sa.Text(), nullable=False),
    sa.Column('reported', sa.Text(), nullable=False),
    sa.Column('medgen_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.PrimaryKeyConstraint('context_hash')
    )
    op.create_table('source_releases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('release_date', sa.Date(), nullable=False),
    sa.Column('retrieved_date', sa.Date(), nullable=False),
    sa.Column('filename', sa.Text(), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('byte_size', sa.BigInteger(), nullable=False),
    sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint("kind IN ('variant', 'submission')", name='ck_release_kind'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sha256')
    )
    op.create_table('variants',
    sa.Column('variation_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('genes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint('variation_id > 0', name='ck_variant_positive'),
    sa.PrimaryKeyConstraint('variation_id')
    )
    op.create_table('aggregate_snapshots',
    sa.Column('release_id', sa.Integer(), nullable=False),
    sa.Column('variation_id', sa.BigInteger(), nullable=False),
    sa.Column('classifications', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('review_statuses', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('genes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('source_lines', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('vcv_accession_version', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['release_id'], ['source_releases.id'], ),
    sa.ForeignKeyConstraint(['variation_id'], ['variants.variation_id'], ),
    sa.PrimaryKeyConstraint('release_id', 'variation_id')
    )
    op.create_table('comparisons',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('previous_variant_release_id', sa.Integer(), nullable=False),
    sa.Column('current_variant_release_id', sa.Integer(), nullable=False),
    sa.Column('previous_submission_release_id', sa.Integer(), nullable=False),
    sa.Column('current_submission_release_id', sa.Integer(), nullable=False),
    sa.Column('aggregate_sha256', sa.String(length=64), nullable=False),
    sa.Column('submission_sha256', sa.String(length=64), nullable=False),
    sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['current_submission_release_id'], ['source_releases.id'], ),
    sa.ForeignKeyConstraint(['current_variant_release_id'], ['source_releases.id'], ),
    sa.ForeignKeyConstraint(['previous_submission_release_id'], ['source_releases.id'], ),
    sa.ForeignKeyConstraint(['previous_variant_release_id'], ['source_releases.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('submission_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('release_id', sa.Integer(), nullable=False),
    sa.Column('variation_id', sa.BigInteger(), nullable=False),
    sa.Column('scv_base', sa.String(length=32), nullable=False),
    sa.Column('scv_version', sa.Integer(), nullable=False),
    sa.Column('condition_hash', sa.String(length=64), nullable=False),
    sa.Column('submitter_name', sa.Text(), nullable=False),
    sa.Column('submitter_id', sa.Text(), nullable=True),
    sa.Column('classification', sa.Text(), nullable=False),
    sa.Column('classification_type', sa.String(length=24), nullable=False),
    sa.Column('last_evaluated_raw', sa.Text(), nullable=False),
    sa.Column('review_status', sa.Text(), nullable=False),
    sa.Column('rcv_accessions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('vcv_accession_version', sa.Text(), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint('scv_version > 0', name='ck_scv_version'),
    sa.ForeignKeyConstraint(['condition_hash'], ['condition_contexts.context_hash'], ),
    sa.ForeignKeyConstraint(['release_id'], ['source_releases.id'], ),
    sa.ForeignKeyConstraint(['variation_id'], ['variants.variation_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('release_id', 'scv_base', name='uq_submission_release_scv')
    )
    op.create_index(op.f('ix_submission_snapshots_variation_id'), 'submission_snapshots', ['variation_id'], unique=False)
    op.create_table('aggregate_changes',
    sa.Column('comparison_id', sa.String(length=80), nullable=False),
    sa.Column('variation_id', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['comparison_id'], ['comparisons.id'], ),
    sa.ForeignKeyConstraint(['variation_id'], ['variants.variation_id'], ),
    sa.PrimaryKeyConstraint('comparison_id', 'variation_id')
    )
    op.create_index(op.f('ix_aggregate_changes_status'), 'aggregate_changes', ['status'], unique=False)
    op.create_table('submission_changes',
    sa.Column('comparison_id', sa.String(length=80), nullable=False),
    sa.Column('scv_base', sa.String(length=32), nullable=False),
    sa.Column('previous_snapshot_id', sa.Integer(), nullable=True),
    sa.Column('current_snapshot_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['comparison_id'], ['comparisons.id'], ),
    sa.ForeignKeyConstraint(['current_snapshot_id'], ['submission_snapshots.id'], ),
    sa.ForeignKeyConstraint(['previous_snapshot_id'], ['submission_snapshots.id'], ),
    sa.PrimaryKeyConstraint('comparison_id', 'scv_base')
    )
def downgrade():
    op.drop_table('submission_changes')
    op.drop_index(op.f('ix_aggregate_changes_status'), table_name='aggregate_changes')
    op.drop_table('aggregate_changes')
    op.drop_index(op.f('ix_submission_snapshots_variation_id'), table_name='submission_snapshots')
    op.drop_table('submission_snapshots')
    op.drop_table('comparisons')
    op.drop_table('aggregate_snapshots')
    op.drop_table('variants')
    op.drop_table('source_releases')
    op.drop_table('condition_contexts')
