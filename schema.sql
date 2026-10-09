CREATE TABLE IF NOT EXISTS firms (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS advisor_users (
    id BIGSERIAL PRIMARY KEY,
    firm_id BIGINT NOT NULL REFERENCES firms(id),
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS advisor_users_email_lower ON advisor_users (lower(email));

CREATE TABLE IF NOT EXISTS clients (
    id BIGSERIAL PRIMARY KEY,
    firm_id BIGINT NOT NULL REFERENCES firms(id),
    business_name TEXT NOT NULL,
    industry TEXT NOT NULL,
    annual_revenue BIGINT NOT NULL CHECK (annual_revenue >= 0),
    annual_ebitda BIGINT,
    employee_count INTEGER CHECK (employee_count IS NULL OR employee_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS clients_firm_idx ON clients (firm_id);

CREATE TABLE IF NOT EXISTS business_users (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL REFERENCES clients(id),
    display_name TEXT NOT NULL,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS business_users_email_lower ON business_users (lower(email));

CREATE TABLE IF NOT EXISTS questions (
    id BIGSERIAL PRIMARY KEY,
    field_key TEXT NOT NULL UNIQUE,
    prompt TEXT NOT NULL,
    display_order INTEGER NOT NULL UNIQUE CHECK (display_order BETWEEN 1 AND 10)
);

CREATE TABLE IF NOT EXISTS answer_options (
    id BIGSERIAL PRIMARY KEY,
    question_id BIGINT NOT NULL REFERENCES questions(id),
    rating TEXT NOT NULL CHECK (rating IN ('high', 'medium', 'low')),
    label TEXT NOT NULL,
    points INTEGER NOT NULL CHECK (points IN (0, 5, 10)),
    UNIQUE (question_id, rating)
);

CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL REFERENCES clients(id),
    question_id BIGINT NOT NULL REFERENCES questions(id),
    option_id BIGINT NOT NULL REFERENCES answer_options(id),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (client_id, question_id)
);
CREATE INDEX IF NOT EXISTS responses_client_idx ON questionnaire_responses (client_id);

CREATE TABLE IF NOT EXISTS advisor_decisions (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL REFERENCES clients(id),
    advisor_id BIGINT NOT NULL REFERENCES advisor_users(id),
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected', 'clarification')),
    private_note TEXT NOT NULL DEFAULT '',
    owner_message TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS decisions_client_idx ON advisor_decisions (client_id, created_at DESC);

CREATE TABLE IF NOT EXISTS clarification_replies (
    id BIGSERIAL PRIMARY KEY,
    decision_id BIGINT NOT NULL UNIQUE REFERENCES advisor_decisions(id),
    business_user_id BIGINT NOT NULL REFERENCES business_users(id),
    message TEXT NOT NULL CHECK (char_length(message) BETWEEN 1 AND 2000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
