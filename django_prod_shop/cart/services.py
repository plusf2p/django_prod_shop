from .models import Cart


def get_or_create_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_cart(request):
    user = request.user
    
    if user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    session_key = get_or_create_session_key(request)
    cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart
