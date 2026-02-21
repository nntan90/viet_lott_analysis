-- ================================================================
-- VIETLOTT AI PREDICTION PIPELINE v3.0
-- Database Schema — Supabase PostgreSQL
-- Run this script once in the Supabase SQL Editor
-- ================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ================================================================
-- TABLE: lottery_results
-- Stores every official draw result
-- ================================================================
CREATE TABLE IF NOT EXISTS lottery_results (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    draw_id         VARCHAR(10) NOT NULL,
    lottery_type    VARCHAR(20) NOT NULL,  -- 'power_655' | 'mega_645' | 'lottery_635'
    draw_date       DATE        NOT NULL,
    numbers         INTEGER[]   NOT NULL,  -- exactly 6 numbers, sorted ascending
    jackpot2        INTEGER,               -- bonus number, only for power_655
    jackpot_amount  BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_lottery_draw UNIQUE (lottery_type, draw_id)
);

CREATE INDEX IF NOT EXISTS idx_lottery_results_type_date
    ON lottery_results (lottery_type, draw_date DESC);

-- ================================================================
-- TABLE: prediction_cycles
-- 1 row = 1 cycle (5 draws per cycle)
-- ================================================================
CREATE TABLE IF NOT EXISTS prediction_cycles (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    lottery_type    VARCHAR(20) NOT NULL,
    cycle_number    INTEGER     NOT NULL,
    status          VARCHAR(20) DEFAULT 'active',   -- 'active' | 'completed'
    draws_tracked   INTEGER     DEFAULT 0,           -- increments 0 → 5
    model_version   VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    CONSTRAINT uq_cycle UNIQUE (lottery_type, cycle_number)
);

CREATE INDEX IF NOT EXISTS idx_prediction_cycles_type_status
    ON prediction_cycles (lottery_type, status);

-- ================================================================
-- TABLE: predictions
-- 1 row = 1 cycle = 6 numbers (fixed for the whole cycle)
-- ================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id        UUID        REFERENCES prediction_cycles(id) ON DELETE CASCADE,
    lottery_type    VARCHAR(20) NOT NULL,
    numbers         INTEGER[]   NOT NULL,  -- exactly 6 numbers chosen by AI
    model_version   VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_cycle
    ON predictions (cycle_id);

-- ================================================================
-- TABLE: match_results
-- 1 row = 1 draw check within a cycle
-- 5 rows per cycle per lottery_type
-- ================================================================
CREATE TABLE IF NOT EXISTS match_results (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id         UUID        REFERENCES prediction_cycles(id) ON DELETE CASCADE,
    lottery_type     VARCHAR(20) NOT NULL,
    draw_id          VARCHAR(10) NOT NULL,
    draw_date        DATE        NOT NULL,
    draw_number      INTEGER     NOT NULL,   -- 1 → 5 within cycle
    predicted_nums   INTEGER[]   NOT NULL,   -- copy of AI's 6 numbers
    actual_numbers   INTEGER[]   NOT NULL,   -- official draw result
    jackpot2         INTEGER,                -- only for power_655
    matched_numbers  INTEGER[]   NOT NULL,   -- intersection
    matched_count    INTEGER     NOT NULL,   -- 0 → 6
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_match UNIQUE (cycle_id, draw_id)
);

CREATE INDEX IF NOT EXISTS idx_match_results_cycle
    ON match_results (cycle_id);

-- ================================================================
-- TABLE: model_configs
-- Stores tunable model parameters — edit without touching code
-- ================================================================
CREATE TABLE IF NOT EXISTS model_configs (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    lottery_type     VARCHAR(20)  NOT NULL,
    model_name       VARCHAR(50)  NOT NULL,  -- 'lstm' | 'xgboost' | 'statistical' | 'markov'
    parameters       JSONB        NOT NULL,
    ensemble_weight  DECIMAL(5,3) NOT NULL,  -- 0.000 – 1.000
    version          VARCHAR(20),
    is_active        BOOLEAN      DEFAULT TRUE,
    created_at       TIMESTAMPTZ  DEFAULT NOW(),
    CONSTRAINT uq_model_config UNIQUE (lottery_type, model_name, version)
);

CREATE INDEX IF NOT EXISTS idx_model_configs_type_active
    ON model_configs (lottery_type, is_active);

-- ================================================================
-- TABLE: model_training_logs
-- Audit log for every retrain event
-- ================================================================
CREATE TABLE IF NOT EXISTS model_training_logs (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    lottery_type        VARCHAR(20),
    trigger_reason      TEXT,
    old_params          JSONB,
    new_params          JSONB,
    performance_before  JSONB,
    training_status     VARCHAR(20), -- 'triggered'|'success'|'failed'|'skipped'
    trained_at          TIMESTAMPTZ  DEFAULT NOW()
);

-- ================================================================
-- SEED: Default model configs (v3.0 weights from Master Plan)
-- ================================================================
INSERT INTO model_configs (lottery_type, model_name, parameters, ensemble_weight, version)
VALUES
-- Power 6/55
('power_655', 'lstm',        '{"sequence_length":50,"hidden_units":128,"dropout_rate":0.3,"epochs":100,"batch_size":32,"learning_rate":0.001}', 0.400, '3.0'),
('power_655', 'xgboost',     '{"n_estimators":200,"max_depth":6,"learning_rate":0.05,"feature_window":20,"subsample":0.8}',                     0.350, '3.0'),
('power_655', 'statistical', '{"frequency_window":100,"gap_window":50,"weight_recency":0.6}',                                                   0.250, '3.0'),
-- Mega 6/45
('mega_645',  'lstm',        '{"sequence_length":50,"hidden_units":128,"dropout_rate":0.3,"epochs":100,"batch_size":32,"learning_rate":0.001}', 0.400, '3.0'),
('mega_645',  'xgboost',     '{"n_estimators":200,"max_depth":6,"learning_rate":0.05,"feature_window":20,"subsample":0.8}',                     0.350, '3.0'),
('mega_645',  'statistical', '{"frequency_window":100,"gap_window":50,"weight_recency":0.6}',                                                   0.250, '3.0'),
-- Lottery 6/35
('lottery_635','lstm',       '{"sequence_length":50,"hidden_units":128,"dropout_rate":0.3,"epochs":100,"batch_size":32,"learning_rate":0.001}', 0.400, '3.0'),
('lottery_635','xgboost',    '{"n_estimators":200,"max_depth":6,"learning_rate":0.05,"feature_window":20,"subsample":0.8}',                     0.350, '3.0'),
('lottery_635','statistical','{"frequency_window":100,"gap_window":50,"weight_recency":0.6}',                                                   0.250, '3.0')
ON CONFLICT DO NOTHING;
