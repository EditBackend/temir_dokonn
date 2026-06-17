# organization/authentication.py (yoki views.py ning eng tepasiga qo'shing)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from .models import Employee


class EmployeeJWTAuthentication(JWTAuthentication):
    """ Simple JWT'ni standart User o'rniga Employee modelidan qidirishga majburlash """

    def get_user(self, validated_token):
        try:
            # Token ichidan haqiqiy xodim ID'sini olamiz
            user_id = validated_token.get('user_id')
            if not user_id:
                raise AuthenticationFailed('Token ichida user_id topilmadi', code='user_not_found')

            # Standart User'dan emas, o'zimizning Employee modelidan qidiramiz
            user = Employee.objects.get(id=user_id)

            # TenantViewSetMixin va DRF ishlashi uchun obyektdagi majburiy atributlarni simulyatsiya qilamiz
            if not hasattr(user, 'is_authenticated'):
                user.is_authenticated = True

            return user
        except Employee.DoesNotExist:
            raise AuthenticationFailed('Xodim bazadan topilmadi (User not found)', code='user_not_found')