from django.utils.cache import add_never_cache_headers

class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if the current page is the product_detail page
        if request.path.startswith('/product_detail/'):
            # Exclude product_detail page from caching
            add_never_cache_headers(response)
        else:
            # Cache other pages
            pass
        
        return response