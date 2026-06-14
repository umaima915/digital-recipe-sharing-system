-- ============================================
-- DATABASE: recipe_db
-- DIGITAL RECIPE SHARING SYSTEM
-- ============================================

CREATE DATABASE recipe_db;
USE recipe_db;

-- ============================================
-- TABLE 1: users
-- Stores both regular users and admins
-- ============================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert a default admin
INSERT INTO users (username, email, password, role) 
VALUES ('admin', 'admin@recipe.com', 'admin123', 'admin');

-- ============================================
-- TABLE 2: recipes
-- Main recipe storage
-- ============================================
CREATE TABLE recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    servings INT DEFAULT 2,
    category_id int,
    video_url VARCHAR(500) DEFAULT NULL,  -- Optional video
    image VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;
);

-- ============================================
-- TABLE 3: ingredients
-- Linked to recipes, used for ingredient calculator
-- ============================================
CREATE TABLE ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(30) NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ============================================
-- TABLE 4: ratings_reviews
-- Users can rate (1-5) and leave text review
-- ============================================
CREATE TABLE ratings_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT NOT NULL,
    user_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================
-- TABLE 5: activity_log
-- Stores trigger messages (add, review, delete)
-- ============================================
CREATE TABLE activity_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message VARCHAR(500) NOT NULL,
    log_type ENUM('recipe_added', 'review_added', 'recipe_deleted', 'duplicate_warning') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE 6: feedback
-- Users can submit feedback to admin
-- ============================================
CREATE TABLE feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
-- ============================================
-- TABLE 7: categories
-- Pre-defined recipe categories
-- ============================================
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    icon VARCHAR(10) DEFAULT '🍽️',
    description VARCHAR(200) DEFAULT NULL
);

-- Insert default categories
INSERT INTO categories (name, icon, description) VALUES
('Vegetarian', '🥬', 'Plant-based recipes without meat'),
('Non-Vegetarian', '🍗', 'Recipes with meat, chicken, or fish'),
('Desserts', '🍰', 'Sweet treats, cakes, and pastries'),
('Beverages', '🍹', 'Drinks, smoothies, and cocktails'),
('Snacks', '🍿', 'Quick bites and appetizers'),
('Breakfast', '🥞', 'Morning meals and brunch items'),
('Salads', '🥗', 'Fresh and healthy salad recipes'),
('Soups', '🍲', 'Warm and comforting soups'),
('Pizza/Pasta', '🍝', 'Italian pasta and noodle dishes'),
('Bakery', '🍞', 'Bread, cookies, and baked goods');

-- ============================================
-- VIEW: recipe_ratings_view
-- Shows average rating and review count per recipe
-- ============================================
CREATE VIEW recipe_ratings_view AS
SELECT 
    r.id AS recipe_id,
    r.title,
    r.description,
    r.servings,
    r.video_url,
    r.image,
    r.category_id,
    c.name AS category_name,
    c.icon AS category_icon,
    r.created_at,
    u.username AS author,
    COUNT(rr.id) AS total_reviews,
    COALESCE(AVG(rr.rating), 0) AS avg_rating
FROM recipes r
JOIN users u ON r.user_id = u.id
LEFT JOIN categories c ON r.category_id = c.id
LEFT JOIN ratings_reviews rr ON r.id = rr.recipe_id
GROUP BY r.id, r.title, r.description, r.servings, r.video_url, 
         r.image, r.category_id, c.name, c.icon, r.created_at, u.username;

-- ============================================
-- VIEW: top_recipes
-- Shows top 5 recipes by average rating
-- ============================================
CREATE VIEW top_recipes AS
SELECT * FROM recipe_ratings_view
WHERE total_reviews > 0
ORDER BY avg_rating DESC
LIMIT 5;

-- ============================================
-- TRIGGER 1: After recipe INSERT
-- Logs when a new recipe is added
-- ============================================
DELIMITER //
CREATE TRIGGER after_recipe_insert
AFTER INSERT ON recipes
FOR EACH ROW
BEGIN
    INSERT INTO activity_log (message, log_type)
    VALUES (CONCAT('✅ New recipe added: "', NEW.title, '" (Recipe ID: ', NEW.id, ')'), 'recipe_added');
END//
DELIMITER ;

-- ============================================
-- TRIGGER 2: Before recipe INSERT (DUPLICATE CHECK)
-- Warns if a recipe with same title already exists
-- ============================================
DELIMITER //
CREATE TRIGGER before_recipe_insert
BEFORE INSERT ON recipes
FOR EACH ROW
BEGIN
    DECLARE duplicate_count INT;
    SELECT COUNT(*) INTO duplicate_count FROM recipes WHERE title = NEW.title;
    IF duplicate_count > 0 THEN
        INSERT INTO activity_log (message, log_type)
        VALUES (CONCAT('⚠️ Duplicate Recipe Warning: "', NEW.title, '" already exists!'), 'duplicate_warning');
    END IF;
END//
DELIMITER ;

-- ============================================
-- TRIGGER 3: After review INSERT
-- Logs when someone reviews a recipe
-- ============================================
DELIMITER //
CREATE TRIGGER after_review_insert
AFTER INSERT ON ratings_reviews
FOR EACH ROW
BEGIN
    DECLARE recipe_title VARCHAR(150);
    DECLARE reviewer_name VARCHAR(50);
    SELECT title INTO recipe_title FROM recipes WHERE id = NEW.recipe_id;
    SELECT username INTO reviewer_name FROM users WHERE id = NEW.user_id;
    INSERT INTO activity_log (message, log_type)
    VALUES (CONCAT('⭐ New review on "', recipe_title, '" by ', reviewer_name, ' - Rating: ', NEW.rating, '/5'), 'review_added');
END//
DELIMITER ;

-- ============================================
-- TRIGGER 4: After recipe DELETE
-- Logs when a recipe is deleted
-- ============================================
DELIMITER //
CREATE TRIGGER after_recipe_delete
AFTER DELETE ON recipes
FOR EACH ROW
BEGIN
    INSERT INTO activity_log (message, log_type)
    VALUES (CONCAT('❌ Recipe deleted: "', OLD.title, '" (ID: ', OLD.id, ')'), 'recipe_deleted');
END//
DELIMITER ;