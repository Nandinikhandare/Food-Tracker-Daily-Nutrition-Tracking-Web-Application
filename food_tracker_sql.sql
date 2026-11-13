create database food_tracker;

Use food_tracker;

-- Create Food Entries Table
CREATE TABLE food_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    food_name VARCHAR(100) NOT NULL,
    meal_type VARCHAR(50) NOT NULL,
    calories INT NOT NULL,
    food_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- View Table Structure
DESCRIBE food_entries;

USE food_tracker;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

SHOW TABLES;

DESCRIBE users;

ALTER TABLE food_entries
ADD COLUMN user_id INT NULL AFTER id;

ALTER TABLE food_entries
ADD CONSTRAINT fk_food_entries_user
FOREIGN KEY (user_id)
REFERENCES users(id)
ON DELETE CASCADE;

DESCRIBE food_entries;

select * from users;
DESCRIBE users;

USE food_tracker;

SELECT DATABASE();

DESCRIBE users;

SELECT id, name, email, password FROM users;

SHOW DATABASES;
USE food_tracker;
SHOW TABLES;

USE food_tracker;

ALTER TABLE food_entries
ADD COLUMN protein DECIMAL(8,2) NOT NULL DEFAULT 0,
ADD COLUMN carbs DECIMAL(8,2) NOT NULL DEFAULT 0,
ADD COLUMN fats DECIMAL(8,2) NOT NULL DEFAULT 0;

DESCRIBE food_entries;


USE food_tracker;

CREATE TABLE IF NOT EXISTS water_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount_ml INT NOT NULL,
    water_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


