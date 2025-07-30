from django.shortcuts import redirect,render
from django.contrib.auth import logout

class BlockedUserLogoutMiddleware:
    """ IF THE ADMIN IS BLOCKING AN ACTIVE USER EVEN IF HE IS AUTHENTICATED,
    HE WILL REDIRECTED TO THE LOGIN PAGE.
    """
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
            return redirect('login')
        
        return self.get_response(request)