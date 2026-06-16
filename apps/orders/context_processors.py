from .services import CartService

def cart_processor(request):
    """
    Supplies the user's or session's cart and item count to the layout context.
    """
    cart_count = 0
    cart_subtotal = 0.0
    
    # We do a safe try-except to prevent migration errors or early page crashes
    try:
        service = CartService()
        if request.user.is_authenticated:
            cart = service.get_cart(user=request.user)
            cart_count = cart.total_items
            cart_subtotal = float(cart.subtotal)
        else:
            session_key = request.session.session_key
            if session_key:
                cart = service.get_cart(session_key=session_key)
                cart_count = cart.total_items
                cart_subtotal = float(cart.subtotal)
    except Exception:
        pass

    return {
        'cart_count': cart_count,
        'cart_subtotal': cart_subtotal
    }
