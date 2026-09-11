-- Схема БД для HSE Sport Centre Mini App (Postgres / Neon)
-- Выполнить один раз против базы, указанной в DATABASE_URL.

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'trainer', 'admin')),
    full_name TEXT NOT NULL,
    username TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sections (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    trainer_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Еженедельный шаблон расписания секции
CREATE TABLE IF NOT EXISTS schedule_slots (
    id BIGSERIAL PRIMARY KEY,
    section_id BIGINT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    weekday SMALLINT NOT NULL CHECK (weekday BETWEEN 0 AND 6), -- 0=понедельник ... 6=воскресенье
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    location TEXT NOT NULL DEFAULT ''
);

-- Конкретные занятия на определённую дату (генерируются из schedule_slots или создаются вручную)
CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    section_id BIGINT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    slot_id BIGINT REFERENCES schedule_slots(id) ON DELETE SET NULL,
    session_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (section_id, session_date, start_time)
);

CREATE TABLE IF NOT EXISTS enrollments (
    id BIGSERIAL PRIMARY KEY,
    section_id BIGINT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (section_id, student_id)
);

CREATE TABLE IF NOT EXISTS attendance (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'unmarked' CHECK (status IN ('unmarked', 'present', 'absent')),
    marked_at TIMESTAMPTZ,
    UNIQUE (session_id, student_id)
);

CREATE TABLE IF NOT EXISTS news (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sections_trainer ON sections(trainer_id);
CREATE INDEX IF NOT EXISTS idx_slots_section ON schedule_slots(section_id);
CREATE INDEX IF NOT EXISTS idx_sessions_section ON sessions(section_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_section ON enrollments(section_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id);
