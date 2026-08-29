CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0),
    email VARCHAR(320) NOT NULL UNIQUE,
    is_male BOOLEAN NOT NULL
);

INSERT INTO users (id, name, age, email, is_male)
VALUES
    (1, 'Alex Johnson', 29, 'alex.johnson@example.com', TRUE),
    (2, 'Maria Garcia', 34, 'maria.garcia@example.com', FALSE),
    (3, 'Sam Lee', 41, 'sam.lee@example.com', TRUE),
    (4, 'Nina Patel', 26, 'nina.patel@example.com', FALSE),
    (5, 'Owen Smith', 38, 'owen.smith@example.com', TRUE)
ON CONFLICT (id) DO NOTHING;
