"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-27 02:55:20.944850
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table('provider_search_areas',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, dimension=2, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), sa.Computed('ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography', persisted=True), nullable=False),
    sa.Column('radius_m', sa.Integer(), nullable=False),
    sa.Column('result_count', sa.Integer(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_search_areas'))
    )
    op.create_index('ix_provider_search_areas_location', 'provider_search_areas', ['location'], unique=False, postgresql_using='gist')
    op.create_table('providers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('provider_type', sa.String(length=40), nullable=False),
    sa.Column('specialties', postgresql.ARRAY(sa.String(length=80)), server_default='{}', nullable=False),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('phone', sa.String(length=100), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('website', sa.String(length=500), nullable=True),
    sa.Column('opening_hours', sa.String(length=500), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, dimension=2, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), sa.Computed('ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography', persisted=True), nullable=False),
    sa.Column('timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('source_id', sa.String(length=100), nullable=False),
    sa.Column('source_url', sa.String(length=500), nullable=True),
    sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("provider_type IN ('hospital', 'clinic', 'doctor', 'physiotherapist', 'chiropractor', 'rehabilitation')", name=op.f('ck_providers_provider_type_valid')),
    sa.CheckConstraint("source IN ('openstreetmap', 'manual')", name=op.f('ck_providers_provider_source')),
    sa.CheckConstraint('latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180', name=op.f('ck_providers_coordinates_valid')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_providers')),
    sa.UniqueConstraint('source', 'source_id', name=op.f('uq_providers_source_source_id'))
    )
    op.create_index('ix_providers_location', 'providers', ['location'], unique=False, postgresql_using='gist')
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=200), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('email = lower(email)', name=op.f('ck_users_email_lowercase')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('audit_logs',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('resource_type', sa.String(length=40), nullable=True),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_logs_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index('ix_audit_logs_user_created', 'audit_logs', ['user_id', 'created_at'], unique=False)
    op.create_table('doctors',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('provider_id', sa.Uuid(), nullable=False),
    sa.Column('full_name', sa.String(length=200), nullable=False),
    sa.Column('qualifications', sa.String(length=255), nullable=True),
    sa.Column('specialization', sa.String(length=120), nullable=False),
    sa.Column('experience_years', sa.SmallInteger(), nullable=True),
    sa.Column('consultation_fee', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), server_default='INR', nullable=False),
    sa.Column('phone', sa.String(length=100), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('is_bookable', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("source IN ('openstreetmap', 'manual')", name=op.f('ck_doctors_doctor_source')),
    sa.CheckConstraint('consultation_fee >= 0', name=op.f('ck_doctors_fee_non_negative')),
    sa.CheckConstraint('experience_years BETWEEN 0 AND 70', name=op.f('ck_doctors_experience_range')),
    sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name=op.f('fk_doctors_provider_id_providers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_doctors'))
    )
    op.create_index(op.f('ix_doctors_provider_id'), 'doctors', ['provider_id'], unique=False)
    op.create_table('patient_profiles',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('sex', sa.String(length=20), nullable=True),
    sa.Column('height_cm', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('weight_kg', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("sex IN ('female', 'male', 'other', 'prefer_not_to_say')", name=op.f('ck_patient_profiles_sex_valid')),
    sa.CheckConstraint('height_cm BETWEEN 50 AND 250', name=op.f('ck_patient_profiles_height_range')),
    sa.CheckConstraint('weight_kg BETWEEN 10 AND 400', name=op.f('ck_patient_profiles_weight_range')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_patient_profiles_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_patient_profiles'))
    )
    op.create_table('posture_analyses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('stage', sa.String(length=40), nullable=True),
    sa.Column('failure_code', sa.String(length=50), nullable=True),
    sa.Column('failure_message', sa.Text(), nullable=True),
    sa.Column('view', sa.String(length=20), nullable=True),
    sa.Column('original_image_key', sa.String(length=255), nullable=False),
    sa.Column('annotated_image_key', sa.String(length=255), nullable=True),
    sa.Column('image_width', sa.Integer(), nullable=False),
    sa.Column('image_height', sa.Integer(), nullable=False),
    sa.Column('image_sha256', sa.String(length=64), nullable=False),
    sa.Column('quality_checks', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('unavailable_metrics', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('alignment_score', sa.Float(), nullable=True),
    sa.Column('pose_model', sa.String(length=100), nullable=True),
    sa.Column('pipeline_version', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed')", name=op.f('ck_posture_analyses_analysis_status')),
    sa.CheckConstraint("view IN ('front', 'back', 'left_side', 'right_side')", name=op.f('ck_posture_analyses_posture_view')),
    sa.CheckConstraint('alignment_score BETWEEN 0 AND 100', name=op.f('ck_posture_analyses_score_range')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_posture_analyses_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_posture_analyses'))
    )
    op.create_index('ix_posture_analyses_user_created', 'posture_analyses', ['user_id', sa.literal_column('created_at DESC')], unique=False)
    op.create_table('ai_recommendations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('analysis_id', sa.Uuid(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('explanation', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('corrective_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("source IN ('ollama', 'rule_based')", name=op.f('ck_ai_recommendations_explanation_source')),
    sa.ForeignKeyConstraint(['analysis_id'], ['posture_analyses.id'], name=op.f('fk_ai_recommendations_analysis_id_posture_analyses'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_recommendations')),
    sa.UniqueConstraint('analysis_id', name=op.f('uq_ai_recommendations_analysis_id'))
    )
    op.create_table('appointments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('doctor_id', sa.Uuid(), nullable=False),
    sa.Column('analysis_id', sa.Uuid(), nullable=True),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    postgresql.ExcludeConstraint((sa.column('doctor_id'), '='), (sa.text('tstzrange(starts_at, ends_at)'), '&&'), where=sa.text("status IN ('pending', 'confirmed')"), using='gist', name='ex_appointments_doctor_overlap'),
    postgresql.ExcludeConstraint((sa.column('patient_id'), '='), (sa.text('tstzrange(starts_at, ends_at)'), '&&'), where=sa.text("status IN ('pending', 'confirmed')"), using='gist', name='ex_appointments_patient_overlap'),
    sa.CheckConstraint("status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')", name=op.f('ck_appointments_appointment_status')),
    sa.CheckConstraint('ends_at > starts_at', name=op.f('ck_appointments_time_order')),
    sa.ForeignKeyConstraint(['analysis_id'], ['posture_analyses.id'], name=op.f('fk_appointments_analysis_id_posture_analyses'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], name=op.f('fk_appointments_doctor_id_doctors')),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], name=op.f('fk_appointments_patient_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_appointments'))
    )
    op.create_index(op.f('ix_appointments_doctor_id'), 'appointments', ['doctor_id'], unique=False)
    op.create_index('ix_appointments_patient_starts', 'appointments', ['patient_id', 'starts_at'], unique=False)
    op.create_table('doctor_availability',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('doctor_id', sa.Uuid(), nullable=False),
    sa.Column('weekday', sa.SmallInteger(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('end_time', sa.Time(), nullable=False),
    sa.Column('slot_minutes', sa.SmallInteger(), server_default='30', nullable=False),
    sa.CheckConstraint('end_time > start_time', name=op.f('ck_doctor_availability_time_order')),
    sa.CheckConstraint('slot_minutes BETWEEN 10 AND 120', name=op.f('ck_doctor_availability_slot_length')),
    sa.CheckConstraint('weekday BETWEEN 0 AND 6', name=op.f('ck_doctor_availability_weekday_range')),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], name=op.f('fk_doctor_availability_doctor_id_doctors'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_doctor_availability'))
    )
    op.create_index(op.f('ix_doctor_availability_doctor_id'), 'doctor_availability', ['doctor_id'], unique=False)
    op.create_table('patient_snapshots',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('analysis_id', sa.Uuid(), nullable=False),
    sa.Column('full_name', sa.String(length=200), nullable=False),
    sa.Column('age', sa.SmallInteger(), nullable=True),
    sa.Column('sex', sa.String(length=20), nullable=True),
    sa.Column('height_cm', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('weight_kg', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('symptoms', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("sex IN ('female', 'male', 'other', 'prefer_not_to_say')", name=op.f('ck_patient_snapshots_sex_valid')),
    sa.CheckConstraint('age BETWEEN 0 AND 120', name=op.f('ck_patient_snapshots_age_range')),
    sa.CheckConstraint('height_cm BETWEEN 50 AND 250', name=op.f('ck_patient_snapshots_height_range')),
    sa.CheckConstraint('weight_kg BETWEEN 10 AND 400', name=op.f('ck_patient_snapshots_weight_range')),
    sa.ForeignKeyConstraint(['analysis_id'], ['posture_analyses.id'], name=op.f('fk_patient_snapshots_analysis_id_posture_analyses'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_snapshots')),
    sa.UniqueConstraint('analysis_id', name=op.f('uq_patient_snapshots_analysis_id'))
    )
    op.create_table('posture_findings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('analysis_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('metric', sa.String(length=50), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('observation', sa.Text(), nullable=False),
    sa.CheckConstraint("severity IN ('mild', 'moderate', 'pronounced')", name=op.f('ck_posture_findings_finding_severity')),
    sa.CheckConstraint('confidence BETWEEN 0 AND 1', name=op.f('ck_posture_findings_confidence_range')),
    sa.ForeignKeyConstraint(['analysis_id'], ['posture_analyses.id'], name=op.f('fk_posture_findings_analysis_id_posture_analyses'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_posture_findings')),
    sa.UniqueConstraint('analysis_id', 'code', name=op.f('uq_posture_findings_analysis_id_code'))
    )
    op.create_table('posture_measurements',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('analysis_id', sa.Uuid(), nullable=False),
    sa.Column('metric', sa.String(length=50), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.CheckConstraint('confidence BETWEEN 0 AND 1', name=op.f('ck_posture_measurements_confidence_range')),
    sa.ForeignKeyConstraint(['analysis_id'], ['posture_analyses.id'], name=op.f('fk_posture_measurements_analysis_id_posture_analyses'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_posture_measurements')),
    sa.UniqueConstraint('analysis_id', 'metric', name=op.f('uq_posture_measurements_analysis_id_metric'))
    )
    op.create_table('posture_reports',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('analysis_id', sa.Uuid(), nullable=False),
    sa.Column('storage_key', sa.String(length=255), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['analysis_id'], ['posture_analyses.id'], name=op.f('fk_posture_reports_analysis_id_posture_analyses'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_posture_reports')),
    sa.UniqueConstraint('analysis_id', name=op.f('uq_posture_reports_analysis_id'))
    )


def downgrade() -> None:
    op.drop_table('posture_reports')
    op.drop_table('posture_measurements')
    op.drop_table('posture_findings')
    op.drop_table('patient_snapshots')
    op.drop_index(op.f('ix_doctor_availability_doctor_id'), table_name='doctor_availability')
    op.drop_table('doctor_availability')
    op.drop_index('ix_appointments_patient_starts', table_name='appointments')
    op.drop_index(op.f('ix_appointments_doctor_id'), table_name='appointments')
    op.drop_table('appointments')
    op.drop_table('ai_recommendations')
    op.drop_index('ix_posture_analyses_user_created', table_name='posture_analyses')
    op.drop_table('posture_analyses')
    op.drop_table('patient_profiles')
    op.drop_index(op.f('ix_doctors_provider_id'), table_name='doctors')
    op.drop_table('doctors')
    op.drop_index('ix_audit_logs_user_created', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_index('ix_providers_location', table_name='providers', postgresql_using='gist')
    op.drop_table('providers')
    op.drop_index('ix_provider_search_areas_location', table_name='provider_search_areas', postgresql_using='gist')
    op.drop_table('provider_search_areas')
