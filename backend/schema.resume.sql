-- schema.resume.sql
-- Table used for storing resume analysis history.

CREATE TABLE IF NOT EXISTS resume_analyzer (
    Analysis_id INT AUTO_INCREMENT PRIMARY KEY,
    resume_text LONGTEXT NOT NULL,
    jd_text LONGTEXT NOT NULL,
    matched_skills JSON NULL,
    missing_skills JSON NULL,
    matched_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    suggestions JSON NULL,
    created_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
