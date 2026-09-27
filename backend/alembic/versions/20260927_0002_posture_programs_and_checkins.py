"""posture programs, exercise library, daily checkins, occupation, language

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27 06:15:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update patient_profiles
    op.add_column('patient_profiles', sa.Column('occupation', sa.String(length=50), nullable=True))
    op.add_column('patient_profiles', sa.Column('preferred_language', sa.String(length=10), server_default='en', nullable=False))

    # 2. Update patient_snapshots
    op.add_column('patient_snapshots', sa.Column('occupation', sa.String(length=50), nullable=True))
    op.add_column('patient_snapshots', sa.Column('preferred_language', sa.String(length=10), server_default='en', nullable=True))

    # 3. Create exercise_library
    op.create_table(
        'exercise_library',
        sa.Column('id', sa.String(length=60), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=False),
        sa.Column('target_area', sa.String(length=100), nullable=False),
        sa.Column('difficulty', sa.String(length=30), nullable=False),
        sa.Column('duration', sa.String(length=50), nullable=False),
        sa.Column('repetitions', sa.String(length=80), nullable=False),
        sa.Column('frequency', sa.String(length=80), nullable=False),
        sa.Column('safety_notes', sa.Text(), nullable=False),
        sa.Column('target_findings', postgresql.ARRAY(sa.String(length=50)), server_default='{}', nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_exercise_library'))
    )

    # 4. Create daily_checkins
    op.create_table(
        'daily_checkins',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('checkin_date', sa.Date(), nullable=False),
        sa.Column('neck_discomfort', sa.SmallInteger(), nullable=False),
        sa.Column('shoulder_discomfort', sa.SmallInteger(), nullable=False),
        sa.Column('back_discomfort', sa.SmallInteger(), nullable=False),
        sa.Column('exercises_completed', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('neck_discomfort BETWEEN 1 AND 10', name=op.f('ck_daily_checkins_neck_discomfort_range')),
        sa.CheckConstraint('shoulder_discomfort BETWEEN 1 AND 10', name=op.f('ck_daily_checkins_shoulder_discomfort_range')),
        sa.CheckConstraint('back_discomfort BETWEEN 1 AND 10', name=op.f('ck_daily_checkins_back_discomfort_range')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_daily_checkins_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_daily_checkins'))
    )
    op.create_index('ix_daily_checkins_user_date', 'daily_checkins', ['user_id', 'checkin_date'], unique=True)

    # 5. Create posture_programs
    op.create_table(
        'posture_programs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('analysis_id', sa.Uuid(), nullable=True),
        sa.Column('occupation', sa.String(length=50), nullable=True),
        sa.Column('preferred_language', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('weeks_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('completed_days', postgresql.ARRAY(sa.String(length=20)), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['posture_analyses.id'], name=op.f('fk_posture_programs_analysis_id_posture_analyses'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_posture_programs_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_posture_programs'))
    )
    op.create_index('ix_posture_programs_user_id', 'posture_programs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_posture_programs_user_id', table_name='posture_programs')
    op.drop_table('posture_programs')
    op.drop_index('ix_daily_checkins_user_date', table_name='daily_checkins')
    op.drop_table('daily_checkins')
    op.drop_table('exercise_library')
    op.drop_column('patient_snapshots', 'preferred_language')
    op.drop_column('patient_snapshots', 'occupation')
    op.drop_column('patient_profiles', 'preferred_language')
    op.drop_column('patient_profiles', 'occupation')
