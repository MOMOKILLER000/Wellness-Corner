from django.utils.cache import add_never_cache_headers
from django.contrib import messages
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
    


class ResetMessagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Clear messages before processing each view
        stored_messages = messages.get_messages(request)
        stored_messages.used = True

    def __call__(self, request):
        response = self.get_response(request)
        return response