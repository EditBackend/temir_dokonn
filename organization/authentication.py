# organization/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from .models import Employee


class EmployeeJWTAuthentication(JWTAuthentication):
    """ Simple JWT ni Employee modeliga moslashtirish (AllowAny ni buzmaydigan holatda) """

    def authenticate(self, request):
        # 1. Avval so'rovda umuman Token kelganmi yoki yo'qmi, shuni tekshiramiz
        header = self.get_header(request)
        if header is None:
            # Agar token kelmagan bo'lsa (masalan register_request da), xato otmaymiz!
            # Shunchaki None qaytaramiz, shunda DRF o'zi @permission_classes([AllowAny]) borligini ko'rib o'tkazib yuboradi.
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        # 2. Agar token kelgan bo'lsa, uni validatsiya qilamiz
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

    def get_user(self, validated_token):
        try:
            user_id = validated_token.get('user_id')
            if not user_id:
                raise AuthenticationFailed('Token ichida user_id topilmadi.', code='token_not_valid')

            user = Employee.objects.get(id=user_id)

            if not hasattr(user, 'is_authenticated'):
                user.is_authenticated = True

            return user
        except Employee.DoesNotExist:
            raise AuthenticationFailed('Xodim topilmadi (User not found).', code='user_not_found')