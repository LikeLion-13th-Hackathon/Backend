from django.shortcuts import render

<<<<<<< Updated upstream
# Create your views here.
=======
class MenuList(generics.ListAPIView):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
 
>>>>>>> Stashed changes
