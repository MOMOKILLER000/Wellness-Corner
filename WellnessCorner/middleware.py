from django.utils.cache import add_never_cache_headers

class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if the current page is the product_detail page
        if '/product/' in request.path:
            # Do not cache product_detail pages
            add_never_cache_headers(response)
        
        return response