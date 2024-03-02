from django.utils.cache import add_never_cache_headers

class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if the current page is not the product_detail page
        if not request.path.startswith('/product/'):
            # Cache other pages
            add_never_cache_headers(response)
        
        return response