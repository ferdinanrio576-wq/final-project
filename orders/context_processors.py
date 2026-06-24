import uuid
from .services import CartService

def _get_session_key(request):
    """Dapatkan session key yang kompatibel dengan cookie-based sessions."""
    key = getattr(request.session, 'session_key', None)
    if key:
        return key
    # Fallback: baca UUID dari session data (untuk cookie-based sessions)
    return request.session.get('_cart_session_id')

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
            session_key = _get_session_key(request)
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
