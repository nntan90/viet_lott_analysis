-- ================================================================
-- VIETLOTT AI PREDICTION PIPELINE v4.0
-- Database Schema — Supabase PostgreSQL
-- Changes from v3.0: lotto_535 replaces lottery_635
--   - lottery_results: +draw_time, +draw_session
--   - predictions: +special_number
--   - match_results: +draw_session, +predicted_special, +actual_special,
--                    +special_matched, +prize_level
-- ================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ================================================================
-- TABLE: lottery_results
-- ================================================================
CREATE TABLE IF NOT EXISTS lottery_results (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    draw_id         VARCHAR(10) NOT NULL,
    lottery_type    VARCHAR(20) NOT NULL,   -- power_655 | mega_645 | lotto_535
    draw_date       DATE        NOT NULL,
    draw_time       TIME,                   -- 13:00 | 21:00 (lotto_535 only)
    draw_session    VARCHAR(2),             -- 'AM' | 'PM' (lotto_535 only)
    numbers         INTEGER[]   NOT NULL,   -- 6 sorted nums (655/645) | 5 sorted nums (535)
    jackpot2        INTEGER,                -- power_655: bonus num | lotto_535: special num [1-12]
    jackpot_amount  BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    -- draw_session is NULL for 655 and 645; include in constraint for 535 dedup
    CONSTRAINT uq_lottery_draw UNIQUE (lottery_type, draw_id, draw_session)
);

CREATE INDEX IF NOT EXISTS idx_lottery_results_type_date
    ON lottery_results (lottery_type, draw_date DESC);

-- ================================================================
-- TABLE: prediction_cycles
-- ================================================================
CREATE TABLE IF NOT EXISTS prediction_cycles (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    lottery_type    VARCHAR(20) NOT NULL,
    cycle_number    INTEGER     NOT NULL,
    status          VARCHAR(20) DEFAULT 'active',   -- active | completed
    draws_tracked   INTEGER     DEFAULT 0,           -- 0 → 5
    model_version   VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    CONSTRAINT uq_cycle UNIQUE (lottery_type, cycle_number)
);

CREATE INDEX IF NOT EXISTS idx_prediction_cycles_type_status
    ON prediction_cycles (lottery_type, status);

-- ================================================================
-- TABLE: predictions
-- 1 row = 1 cycle = 1 bộ số (1 vé)
-- ================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id        UUID        REFERENCES prediction_cycles(id) ON DELETE CASCADE,
    lottery_type    VARCHAR(20) NOT NULL,
    numbers         INTEGER[]   NOT NULL,   -- main numbers: 6 (655/645) | 5 (535)
    special_number  INTEGER,               -- lotto_535 only: [1–12], different from numbers
    model_version   VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_cycle
    ON predictions (cycle_id);

-- ================================================================
-- TABLE: match_results
-- 1 row = 1 lần dò | 5 rows/cycle/lottery_type
-- ================================================================
CREATE TABLE IF NOT EXISTS match_results (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id         UUID        REFERENCES prediction_cycles(id) ON DELETE CASCADE,
    lottery_type     VARCHAR(20) NOT NULL,
    draw_id          VARCHAR(10) NOT NULL,
    draw_date        DATE        NOT NULL,
    draw_session     VARCHAR(2),             -- AM | PM for lotto_535
    draw_number      INTEGER     NOT NULL,   -- 1 → 5
    predicted_nums   INTEGER[]   NOT NULL,   -- from predictions.numbers
    predicted_special INTEGER,              -- from predictions.special_number
    actual_numbers   INTEGER[]   NOT NULL,   -- official draw
    actual_special   INTEGER,               -- official jackpot2 / special
    matched_numbers  INTEGER[]   NOT NULL,   -- intersection of main sets
    matched_count    INTEGER     NOT NULL,   -- 0 → 5/6
    special_matched  BOOLEAN     DEFAULT FALSE,
    prize_level      VARCHAR(20),           -- JACKPOT_1|JACKPOT_2|PRIZE_1..5|PRIZE_KK|NO_PRIZE
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_match UNIQUE (cycle_id, draw_id, draw_session)
);

CREATE INDEX IF NOT EXISTS idx_match_results_cycle
    ON match_results (cycle_id);

-- ================================================================
-- TABLE: model_configs
-- ================================================================
CREATE TABLE IF NOT EXISTS model_configs (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    lottery_type     VARCHAR(20)  NOT NULL,
    model_name       VARCHAR(50)  NOT NULL,
    parameters       JSONB        NOT NULL,
    ensemble_weight  DECIMAL(5,3) NOT NULL,
    version          VARCHAR(20),
    is_active        BOOLEAN      DEFAULT TRUE,
    created_at       TIMESTAMPTZ  DEFAULT NOW(),
    CONSTRAINT uq_model_config UNIQUE (lottery_type, model_name, version)
);

CREATE INDEX IF NOT EXISTS idx_model_configs_type_active
    ON model_configs (lottery_type, is_active);

-- ================================================================
-- TABLE: model_training_logs
-- ================================================================
CREATE TABLE IF NOT EXISTS model_training_logs (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    lottery_type        VARCHAR(20),
    trigger_reason      TEXT,
    old_params          JSONB,
    new_params          JSONB,
    performance_before  JSONB,
    training_status     VARCHAR(20),   -- triggered|success|failed|skipped
    trained_at          TIMESTAMPTZ    DEFAULT NOW()
);

-- ================================================================
-- SEED: Default model configs v4.0
-- ================================================================
INSERT INTO model_configs (lottery_type, model_name, parameters, ensemble_weight, version)
VALUES
-- Power 6/55
('power_655', 'lstm',        '{"sequence_length":50,"hidden_units":128,"dropout_rate":0.3,"epochs":100,"batch_size":32,"learning_rate":0.001}', 0.400, '4.0'),
('power_655', 'xgboost',     '{"n_estimators":200,"max_depth":6,"learning_rate":0.05,"feature_window":20,"subsample":0.8}',                     0.350, '4.0'),
('power_655', 'statistical', '{"frequency_window":100,"gap_window":50,"weight_recency":0.6}',                                                   0.250, '4.0'),
-- Mega 6/45
('mega_645',  'lstm',        '{"sequence_length":50,"hidden_units":128,"dropout_rate":0.3,"epochs":100,"batch_size":32,"learning_rate":0.001}', 0.400, '4.0'),
('mega_645',  'xgboost',     '{"n_estimators":200,"max_depth":6,"learning_rate":0.05,"feature_window":20,"subsample":0.8}',                     0.350, '4.0'),
('mega_645',  'statistical', '{"frequency_window":100,"gap_window":50,"weight_recency":0.6}',                                                   0.250, '4.0'),
-- Lotto 5/35
('lotto_535', 'lstm',        '{"sequence_length":50,"hidden_units":128,"dropout_rate":0.3,"epochs":100,"batch_size":32,"learning_rate":0.001}', 0.400, '4.0'),
('lotto_535', 'xgboost',     '{"n_estimators":200,"max_depth":6,"learning_rate":0.05,"feature_window":20,"subsample":0.8}',                     0.350, '4.0'),
('lotto_535', 'statistical', '{"frequency_window":100,"gap_window":50,"weight_recency":0.6}',                                                   0.250, '4.0')
ON CONFLICT DO NOTHING;
