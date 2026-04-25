-- MySQL 8+ schema equivalent. Use this if the report requires MySQL.
-- In the submitted demo, the backend uses SQLite for easy run/no server setup.

CREATE TABLE images (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    original_path TEXT,
    stored_path TEXT NOT NULL,
    original_width INT,
    original_height INT,
    original_aspect DOUBLE,
    channels INT,
    status VARCHAR(50) DEFAULT 'success',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_images_filename(filename),
    INDEX idx_images_status(status)
);

CREATE TABLE feature_vectors (
    image_id BIGINT PRIMARY KEY,
    vector_dim INT NOT NULL,
    -- Store numpy float32 bytes. In MySQL, MEDIUMBLOB is enough for this project.
    raw_vector MEDIUMBLOB NOT NULL,
    norm_vector MEDIUMBLOB NOT NULL,
    -- Full feature record from part 1, including histograms and descriptors.
    raw_json JSON NOT NULL,
    CONSTRAINT fk_feature_vectors_images
        FOREIGN KEY (image_id) REFERENCES images(id)
        ON DELETE CASCADE
);

CREATE TABLE vector_metadata (
    `key` VARCHAR(100) PRIMARY KEY,
    `value` JSON NOT NULL
);
