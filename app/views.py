
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, flash, json
from app.models import Product, Brand, Cart, Wishlist, User, Order, OrderItem, ProductSize
from app import db
import random, string

views = Blueprint('views', __name__)

@views.route('/')
def homepage():
    brands_list = Brand.query.all()
    products_list = Product.query.limit(20).all()  # Fetching 20 products (adjust as needed)
    return render_template('home.html', brands=brands_list, products=products_list)


@views.route('/brand/<int:brand_id>')
def brand_info(brand_id):
    brand_data = Brand.query.get_or_404(brand_id)
    brand_items = Product.query.filter_by(brand_id=brand_id).all()
    return render_template('brand_details.html', brand=brand_data, products=brand_items)

# @views.route('/product/<int:product_id>')
# def product_info(product_id):
#     product_data = Product.query.get_or_404(product_id)
#     return render_template('product_details.html', product=product_data)

@views.route('/category/<string:category_name>')
def products_by_category(category_name):
    products = Product.query.filter_by(category=category_name).all()
    return render_template('category.html', products=products, category_name=category_name)


### updated cart 
@views.route('/cart')
def show_cart():
    if 'user_id' not in session:
        flash("You must be logged in to view your cart!", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cart_items = db.session.query(Cart, Product).join(Product, Cart.product_id == Product.id).filter(Cart.user_id == user_id).all()
    
    total_mrp = sum(cart.quantity * product.previous_price for cart, product in cart_items)
    total_discount = sum(cart.quantity * product.discount for cart, product in cart_items if product.discount)
    total_amount = int(total_mrp - total_discount)  # Ensure final amount is an integer
    
    return render_template("cart.html", cart_items=cart_items, total_mrp=total_mrp, total_discount=total_discount, total_amount=total_amount)

@views.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash("You must be logged in to add items to the cart!", "danger")
        return redirect(url_for('auth.login'))

    product = Product.query.get_or_404(product_id)
    user_id = session['user_id']

    cart_item = Cart.query.filter_by(user_id=user_id, product_id=product.id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        new_cart_item = Cart(user_id=user_id, product_id=product.id, quantity=1)
        db.session.add(new_cart_item)

    db.session.commit()
    flash("Product added to cart!", "success")
    return redirect(url_for('views.show_cart'))

@views.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'user_id' not in session:
        flash("You must be logged in to remove items from the cart!", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash("Product removed from cart!", "success")
    else:
        flash("Product not found in cart!", "danger")

    return redirect(url_for('views.show_cart'))


@views.route('/move_to_cart/<int:product_id>', methods=['POST'])
def move_to_cart(product_id):
    if 'user_id' not in session:
        flash("You must be logged in to move items to the cart!", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    # Check if item exists in wishlist
    wishlist_item = Wishlist.query.filter_by(user_id=user_id, product_id=product_id).first()
    if wishlist_item:
        # Move item to cart
        cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += 1  # Increase quantity if already exists
        else:
            new_cart_item = Cart(user_id=user_id, product_id=product_id, quantity=1)
            db.session.add(new_cart_item)

        # Remove from wishlist
        db.session.delete(wishlist_item)
        db.session.commit()

        flash("Item moved to cart!", "success")
    else:
        flash("Item not found in wishlist!", "danger")

    return redirect(url_for('views.show_wishlist'))


@views.route('/update_cart_quantity/<int:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Login required"}), 403

    user_id = session['user_id']
    new_quantity = int(request.form.get('quantity', 1))

    cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity = new_quantity
        db.session.commit()

    total_mrp = sum(cart.quantity * product.previous_price for cart, product in db.session.query(Cart, Product).join(Product).filter(Cart.user_id == user_id).all())
    total_discount = sum(cart.quantity * product.discount for cart, product in db.session.query(Cart, Product).join(Product).filter(Cart.user_id == user_id).all() if product.discount)
    total_amount = int(total_mrp - total_discount)

    return jsonify({"success": True, "total_amount": total_amount})

### this button code that add cart to wishlist

@views.route('/move_to_wishlist/<int:product_id>', methods=['POST'])
def move_to_wishlist(product_id):
    if 'user_id' not in session:
        flash("You must be logged in to move items to the wishlist!", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    # Check if item exists in cart
    cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        # Check if item already exists in wishlist
        wishlist_item = Wishlist.query.filter_by(user_id=user_id, product_id=product_id).first()
        if not wishlist_item:
            new_wishlist_item = Wishlist(user_id=user_id, product_id=product_id)
            db.session.add(new_wishlist_item)

        # Remove from cart
        db.session.delete(cart_item)
        db.session.commit()

        flash("Item moved to wishlist!", "success")
    else:
        flash("Item not found in cart!", "danger")

    return redirect(url_for('views.show_cart'))









### Updated wishlist

@views.route('/wishlist')
def show_wishlist():
    if 'user_id' not in session:
        flash("You must be logged in to view your wishlist!", "danger")
        return redirect(url_for('auth.login'))

    wishlist = db.session.query(Wishlist, Product).join(Product, Wishlist.product_id == Product.id)\
        .filter(Wishlist.user_id == session['user_id']).all()
    
    wishlist_items = [{"wishlist": item[0], "product": item[1]} for item in wishlist]
    return render_template('wishlist.html', wishlist_items=wishlist_items)

@views.route('/add_to_wishlist/<int:product_id>', methods=['POST'])
def wishlist_add(product_id):
    if 'user_id' not in session:
        flash("You must be logged in to add items to your wishlist!", "danger")
        return redirect(url_for('auth.login'))

    existing_item = Wishlist.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    if not existing_item:
        new_wishlist_item = Wishlist(user_id=session['user_id'], product_id=product_id)
        db.session.add(new_wishlist_item)
        db.session.commit()
    
    return redirect(url_for('views.show_wishlist'))


@views.route('/remove_from_wishlist/<int:product_id>', methods=['POST'])
def remove_from_wishlist(product_id):
    if 'user_id' not in session:
        flash("You must be logged in to remove items from your wishlist!", "danger")
        return redirect(url_for('auth.login'))

    wishlist_item = Wishlist.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()
        flash("Product removed from wishlist!", "success")
    else:
        flash("Product not found in wishlist!", "danger")
    
    return redirect(url_for('views.show_wishlist'))


@views.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    category_name = request.args.get('category', '').strip()
    brand_name = request.args.get('brand', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    color = request.args.get('color', '').strip()

    # Start filtering products
    search_query = Product.query

    if query:
        search_query = search_query.filter(
            (Product.product_name.ilike(f"%{query}%")) | (Product.description.ilike(f"%{query}%"))
        )
    if category_name:
        search_query = search_query.filter(Product.category.ilike(f"%{category_name}%"))
    if brand_name:
        search_query = search_query.join(Brand).filter(Brand.name.ilike(f"%{brand_name}%"))
    if color:
        search_query = search_query.filter(Product.color.ilike(f"%{color}%"))
    if min_price is not None:
        search_query = search_query.filter(Product.current_price >= min_price)
    if max_price is not None:
        search_query = search_query.filter(Product.current_price <= max_price)

    search_results = search_query.all()

    categories = db.session.query(Product.category).distinct()
    brands = Brand.query.all()
    colors = db.session.query(Product.color).distinct()  # Fetch unique colors

    return render_template(
        'search_results.html',
        products=search_results,
        query=query,
        category=category_name,
        brand=brand_name,
        min_price=min_price,
        max_price=max_price,
        color=color,
        categories=[c[0] for c in categories],
        brands=brands,
        colors=[c[0] for c in colors]  # Pass colors correctly
    )





#suggested Product code
@views.route('/product/<int:product_id>')
def product_info(product_id):
    product = Product.query.get_or_404(product_id)

    # Fetch product sizes (if available)
    sizes = ProductSize.query.filter_by(product_id=product.id).all()

    # Fetch 4 completely random products (excluding the current product)
    suggested_products = Product.query.filter(Product.id != product.id).order_by(db.func.random()).limit(4).all()

    return render_template("product_details.html", product=product, sizes=sizes, suggested_products=suggested_products, stock=product.count)



@views.route('/checkout')
def checkout():
    cart_items = session.get('cart', [])
    if not cart_items:
        return render_template('checkout.html', cart_items=[], subtotal=0, shipping=0, tax=0, total=0)

    subtotal = sum(item['price'] for item in cart_items)
    shipping = 50 if subtotal > 0 else 0
    tax = round(subtotal * 0.05, 2)
    total = subtotal + shipping + tax

    return render_template('checkout.html', cart_items=cart_items, subtotal=subtotal, shipping=shipping, tax=tax, total=total)


@views.route('/place_order', methods=['POST'])
def place_order():
    # Retrieve customer details from form
    address_line_1 = request.form.get('address_line_1')
    state = request.form.get('state')
    city = request.form.get('city')
    pincode = request.form.get('pincode')
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    email = request.form.get('email')

    # Retrieve cart from session
    cart = session.get('cart', [])

    if not cart:
        flash('Your cart is empty!', 'danger')
        return redirect(url_for('views.checkout'))

    # Generate a guest order ID
    guest_order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # Create a new order (without user_id)
    new_order = Order(
        customer_id=None,  # No user ID for guest
        customer_name=f"{firstname} {lastname}",
        address_line_1=address_line_1,
        state=state,
        city=city,
        pincode=pincode,
        price=0,
        status="Pending",
        mail=email,
        guest_order_id=guest_order_id  # Save guest ID to track order
    )
    db.session.add(new_order)
    db.session.commit()

    # Iterate over cart items and add to order
    for cart_item in cart:
        product = Product.query.get(cart_item['product_id'])
        if not product:
            flash(f"Product with ID {cart_item['product_id']} not found.", 'danger')
            continue

        total_cost = product.price * cart_item['quantity']
        new_order.price += total_cost

        order_item = OrderItem(
            OrderID=new_order.id,
            ProductID=cart_item['product_id'],
            UserID=None,  # No user ID for guest
            Quantity=cart_item['quantity'],
            Price=total_cost
        )
        db.session.add(order_item)

        # Reduce product stock
        product.stock_quantity -= cart_item['quantity']

    db.session.commit()

    # Clear cart session after order placement
    session.pop('cart', None)

    return jsonify({"success": True, "order_id": guest_order_id})


@views.route('/my_orders')
def my_orders():
    orders = Order.query.all()
    orders_with_items = []
    for order in orders:
        order_items = OrderItem.query.filter_by(OrderID=order.id).all()
        items_data = [{'name': item.product.name, 'quantity': item.Quantity} for item in order_items]

        orders_with_items.append({
            'id': order.id,
            'status': order.status,
            'price': order.price,
            'order_items': items_data
        })

    return render_template('my_orders.html', orders=orders_with_items)

@views.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = 'Cancelled'
    
    order_items = OrderItem.query.filter_by(OrderID=order_id).all()
    for order_item in order_items:
        product = Product.query.get(order_item.ProductID)
        product.stock_quantity += order_item.Quantity

    db.session.commit()
    return redirect(url_for('views.my_orders'))

@views.route('/order/<int:order_id>')
def view_order_items(order_id):
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('views.my_orders'))
    
    order_items = OrderItem.query.filter_by(OrderID=order.id).all()
    return render_template('view_order_items.html', order=order, order_items=order_items)

@views.route('/order/<int:order_id>/remove_item/<int:item_id>', methods=['POST'])
def remove_order_item(order_id, item_id):
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('views.view_order_items', order_id=order_id))
    
    order_item = OrderItem.query.filter_by(OrderItemID=item_id, OrderID=order.id).first()
    if not order_item:
        flash("Item not found.", "danger")
        return redirect(url_for('views.view_order_items', order_id=order_id))
    
    product = Product.query.get(order_item.ProductID)
    if product:
        product.stock_quantity += order_item.Quantity
    
    db.session.delete(order_item)
    db.session.commit()

    if not OrderItem.query.filter_by(OrderID=order.id).all():
        db.session.delete(order)
        db.session.commit()
        return redirect(url_for('views.my_orders'))
    
    return redirect(url_for('views.view_order_items', order_id=order_id))









