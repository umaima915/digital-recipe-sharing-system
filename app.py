# app.py
# Digital Recipe Sharing System - Flask Backend
# ===============================================

from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
import time
from config import DB_CONFIG, SECRET_KEY
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ============================================
# IMAGE UPLOAD CONFIGURATION
# ============================================
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Create uploads folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
def allowed_file(filename):
    """Check if uploaded file has valid image extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================
# DATABASE CONNECTION
# ============================================
def get_db():
    """Returns a MySQL database connection"""
    return mysql.connector.connect(**DB_CONFIG)

# ============================================
# LOGIN REQUIRED DECORATOR
# ============================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ADMIN REQUIRED DECORATOR
# ============================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access only!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# CONTEXT PROCESSOR - Makes categories available everywhere
# ============================================
@app.context_processor
def inject_categories():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories ORDER BY name")
        categories = cursor.fetchall()
        cursor.close()
        db.close()
        return {'all_categories': categories}
    except:
        return {'all_categories': []}

# ============================================
# HOMEPAGE
# ============================================
@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM top_recipes")
    top_recipes = cursor.fetchall()
    
    cursor.close()
    db.close()
    return render_template('index.html', recipes=top_recipes)

# ============================================
# REGISTER
# ============================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, 'user')",
                (username, email, password)
            )
            db.commit()
            flash('Registration successful! Please login.', 'success')
            cursor.close()
            db.close()
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'error')
            cursor.close()
            db.close()
    
    return render_template('register.html')

# ============================================
# LOGIN
# ============================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        db.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

# ============================================
# LOGOUT
# ============================================
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# ============================================
# DASHBOARD ROUTER
# ============================================
@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))

# ============================================
# USER DASHBOARD
# ============================================
@app.route('/dashboard/user')
@login_required
def user_dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT r.*, 
               COALESCE(rv.avg_rating, 0) as avg_rating,
               COALESCE(rv.total_reviews, 0) as total_reviews
        FROM recipes r
        LEFT JOIN recipe_ratings_view rv ON r.id = rv.recipe_id
        WHERE r.user_id = %s
        ORDER BY r.created_at DESC
    """, (session['user_id'],))
    my_recipes = cursor.fetchall()
    
    cursor.execute("SELECT rv.* FROM recipe_ratings_view rv ORDER BY rv.created_at DESC")
    all_recipes = cursor.fetchall()
    
    cursor.close()
    db.close()
    return render_template('dashboard_user.html', 
                           my_recipes=my_recipes, 
                           all_recipes=all_recipes)

# ============================================
# ADMIN DASHBOARD
# ============================================
@app.route('/dashboard/admin')
@login_required
@admin_required
def admin_dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='user'")
    total_users = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM recipes")
    total_recipes = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM ratings_reviews")
    total_reviews = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT rv.*, u.email as author_email 
        FROM recipe_ratings_view rv 
        JOIN users u ON rv.author = u.username
        ORDER BY rv.created_at DESC
    """)
    all_recipes = cursor.fetchall()
    
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    all_users = cursor.fetchall()
    
    cursor.execute("""
        SELECT f.id, f.message, f.created_at, u.username, u.email
        FROM feedback f 
        INNER JOIN users u ON f.user_id = u.id 
        ORDER BY f.created_at DESC
    """)
    feedbacks = cursor.fetchall()
    
    # ========== YEH LINE HONI CHAHIYE ==========
    cursor.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 20")
    activities = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    # ========== activities KO TEMPLATE MEIN BHEJNA ZAROORI HAI ==========
    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_recipes=total_recipes,
                           total_reviews=total_reviews,
                           recipes=all_recipes,
                           users=all_users,
                           feedbacks=feedbacks,
                           activities=activities) 

# ============================================
# UPLOAD RECIPE 
# ============================================
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_recipe():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categories ORDER BY name")
    categories = cursor.fetchall()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        servings = request.form['servings']
        category_id = request.form.get('category_id', None)
        video_url = request.form.get('video_url', '')
        
        # ========== IMAGE IS REQUIRED ==========
        if 'recipe_image' not in request.files or request.files['recipe_image'].filename == '':
            flash('❌ Recipe image is required! Please upload a photo.', 'error')
            cursor.close()
            db.close()
            return render_template('upload_recipe.html', categories=categories)
        
        file = request.files['recipe_image']
        
        if not allowed_file(file.filename):
            flash('❌ Invalid file type! Only JPG, PNG, GIF, WEBP allowed.', 'error')
            cursor.close()
            db.close()
            return render_template('upload_recipe.html', categories=categories)
        
        # Save image with unique name
        original_name = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        image_filename = timestamp + '_' + original_name
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
        # Get ingredients
        ingredient_names = request.form.getlist('ingredient_name[]')
        ingredient_qty = request.form.getlist('ingredient_qty[]')
        ingredient_units = request.form.getlist('ingredient_unit[]')
        
        # Insert recipe (image is always present)
        cursor.execute(
            "INSERT INTO recipes (user_id, category_id, title, description, servings, video_url, image) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (session['user_id'], category_id if category_id else None, title, description, servings, video_url or None, image_filename)
        )
        recipe_id = cursor.lastrowid
        
        # Insert ingredients
        for i in range(len(ingredient_names)):
            if ingredient_names[i].strip():
                cursor.execute(
                    "INSERT INTO ingredients (recipe_id, name, quantity, unit) VALUES (%s, %s, %s, %s)",
                    (recipe_id, ingredient_names[i], ingredient_qty[i], ingredient_units[i])
                )
        
        db.commit()
        cursor.close()
        db.close()
        
        flash('✅ Recipe uploaded successfully!', 'success')
        return redirect(url_for('user_dashboard'))
    
    cursor.close()
    db.close()
    return render_template('upload_recipe.html', categories=categories)

# ============================================
# EDIT RECIPE
# ============================================
@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Check ownership
    cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    recipe = cursor.fetchone()
    
    if not recipe or recipe['user_id'] != session['user_id']:
        flash('You can only edit your own recipes!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get categories for dropdown
    cursor.execute("SELECT * FROM categories ORDER BY name")
    categories = cursor.fetchall()
    
    # Get existing ingredients
    cursor.execute("SELECT * FROM ingredients WHERE recipe_id = %s", (recipe_id,))
    existing_ingredients = cursor.fetchall()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        servings = request.form['servings']
        category_id = request.form.get('category_id', None)
        video_url = request.form.get('video_url', '')
        
        # Image handling (optional on edit)
        if 'recipe_image' in request.files and request.files['recipe_image'].filename != '':
            file = request.files['recipe_image']
            if allowed_file(file.filename):
                # Delete old image
                if recipe['image']:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], recipe['image'])
                    if os.path.exists(old_path):
                        os.remove(old_path)
                # Save new image
                original_name = secure_filename(file.filename)
                timestamp = str(int(time.time()))
                image_filename = timestamp + '_' + original_name
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            else:
                flash('Invalid image type!', 'error')
                return render_template('edit_recipe.html', recipe=recipe, categories=categories, ingredients=existing_ingredients)
        else:
            image_filename = recipe['image']  # Keep old image
        
        # Update recipe
        cursor.execute("""
            UPDATE recipes 
            SET title=%s, description=%s, servings=%s, category_id=%s, video_url=%s, image=%s 
            WHERE id=%s
        """, (title, description, servings, category_id if category_id else None, video_url or None, image_filename, recipe_id))
        
        # Delete old ingredients and re-insert
        cursor.execute("DELETE FROM ingredients WHERE recipe_id = %s", (recipe_id,))
        
        ingredient_names = request.form.getlist('ingredient_name[]')
        ingredient_qty = request.form.getlist('ingredient_qty[]')
        ingredient_units = request.form.getlist('ingredient_unit[]')
        
        for i in range(len(ingredient_names)):
            if ingredient_names[i].strip():
                cursor.execute(
                    "INSERT INTO ingredients (recipe_id, name, quantity, unit) VALUES (%s, %s, %s, %s)",
                    (recipe_id, ingredient_names[i], ingredient_qty[i], ingredient_units[i])
                )
        
        db.commit()
        cursor.close()
        db.close()
        flash('Recipe updated successfully! ✅', 'success')
        return redirect(url_for('view_recipe', recipe_id=recipe_id))
    
    cursor.close()
    db.close()
    return render_template('edit_recipe.html', recipe=recipe, categories=categories, ingredients=existing_ingredients)

# ============================================
# VIEW RECIPE DETAILS
# ============================================
@app.route('/recipe/<int:recipe_id>', methods=['GET', 'POST'])
def view_recipe(recipe_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM recipe_ratings_view WHERE recipe_id = %s", (recipe_id,))
    recipe = cursor.fetchone()
    
    if not recipe:
        flash('Recipe not found!', 'error')
        return redirect(url_for('index'))
    
    cursor.execute("SELECT * FROM ingredients WHERE recipe_id = %s", (recipe_id,))
    ingredients = cursor.fetchall()
    
    cursor.execute("""
        SELECT rr.*, u.username 
        FROM ratings_reviews rr 
        JOIN users u ON rr.user_id = u.id 
        WHERE rr.recipe_id = %s 
        ORDER BY rr.created_at DESC
    """, (recipe_id,))
    reviews = cursor.fetchall()
    
    scaled_ingredients = None
    new_servings = int(recipe['servings'])
    
    if request.method == 'POST' and 'new_servings' in request.form:
        try:
            new_servings = int(request.form['new_servings'])
        except:
            new_servings = int(recipe['servings'])
        
        original_servings = int(recipe['servings'])
        if original_servings > 0:
            multiplier = float(new_servings) / float(original_servings)
        else:
            multiplier = 1.0
        
        scaled_ingredients = []
        for ing in ingredients:
            original_qty = float(ing['quantity'])
            new_qty = round(original_qty * multiplier, 2)
            scaled_ingredients.append({
                'name': ing['name'],
                'quantity': new_qty,
                'unit': ing['unit']
            })
    
    cursor.close()
    db.close()
    return render_template('recipe_detail.html', 
                           recipe=recipe, 
                           ingredients=ingredients,
                           reviews=reviews,
                           scaled_ingredients=scaled_ingredients,
                           new_servings=new_servings)

# ============================================
# ADD REVIEW
# ============================================
@app.route('/review/<int:recipe_id>', methods=['POST'])
@login_required
def add_review(recipe_id):
    rating = request.form['rating']
    review_text = request.form['review_text']
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        "SELECT id FROM ratings_reviews WHERE recipe_id = %s AND user_id = %s",
        (recipe_id, session['user_id'])
    )
    existing = cursor.fetchone()
    
    if existing:
        flash('You have already reviewed this recipe!', 'error')
    else:
        cursor.execute(
            "INSERT INTO ratings_reviews (recipe_id, user_id, rating, review_text) VALUES (%s, %s, %s, %s)",
            (recipe_id, session['user_id'], rating, review_text)
        )
        db.commit()
        flash('Review added successfully!', 'success')
    
    cursor.close()
    db.close()
    return redirect(url_for('view_recipe', recipe_id=recipe_id))

# ============================================
# DELETE RECIPE
# ============================================
@app.route('/delete_recipe/<int:recipe_id>')
@login_required
def delete_recipe(recipe_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    recipe = cursor.fetchone()
    
    if recipe and (recipe['user_id'] == session['user_id'] or session.get('role') == 'admin'):
        # Delete image file from server
        if recipe['image']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], recipe['image'])
            if os.path.exists(image_path):
                os.remove(image_path)
        
        cursor.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
        db.commit()
        flash('Recipe deleted successfully!', 'success')
    else:
        flash('You do not have permission to delete this recipe!', 'error')
    
    cursor.close()
    db.close()
    return redirect(url_for('dashboard'))

# ============================================
# SUBMIT FEEDBACK
# ============================================
@app.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    message = request.form['message']
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO feedback (user_id, message) VALUES (%s, %s)",
        (session['user_id'], message)
    )
    db.commit()
    cursor.close()
    db.close()
    
    flash('Feedback submitted! Thank you.', 'success')
    return redirect(url_for('dashboard'))

# ============================================
# BROWSE ALL RECIPES
# ============================================
@app.route('/recipes')
def browse_recipes():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipe_ratings_view ORDER BY created_at DESC")
    recipes = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('all_recipes.html', recipes=recipes)

# ============================================
# BROWSE BY CATEGORY
# ============================================
@app.route('/category/<int:category_id>')
def browse_by_category(category_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
    category = cursor.fetchone()
    
    if not category:
        flash('Category not found!', 'error')
        return redirect(url_for('browse_recipes'))
    
    cursor.execute(
        "SELECT * FROM recipe_ratings_view WHERE category_id = %s ORDER BY created_at DESC",
        (category_id,)
    )
    recipes = cursor.fetchall()
    
    cursor.close()
    db.close()
    return render_template('browse_category.html', 
                           category=category, 
                           recipes=recipes)

# ============================================
# RUN
# ============================================
if __name__ == '__main__':
    app.run(debug=True)