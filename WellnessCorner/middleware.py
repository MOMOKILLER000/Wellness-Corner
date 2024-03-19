from django.utils.cache import add_never_cache_headers
from django.contrib import messages
class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if '/product/' in request.path:
            
            add_never_cache_headers(response)
        
        return response
    

class ResetMessagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        
        stored_messages = messages.get_messages(request)
        stored_messages.used = True

    def __call__(self, request):
        response = self.get_response(request)
        return response