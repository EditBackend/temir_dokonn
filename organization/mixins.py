from rest_framework import serializers


class TenantViewSetMixin:
    """
    Ushbu Mixin qo'shilgan barcha API'lar avtomatik ravishda
    faqat login qilgan xodimning kompaniyasiga tegishli ma'lumotlarni qaytaradi
    va yangi ma'lumot ochilganda kompaniyani avtomat biriktiradi.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user  # Tizimga login qilgan xodim

        # Agar foydalanuvchi login qilgan bo'lsa va uning kompaniyasi bo'lsa
        if hasattr(user, 'company') and user.company:
            return queryset.filter(company=user.company)

        return queryset.none()  # Agar login qilmagan bo'lsa, hech narsa ko'rsatmaydi

    def perform_create(self, serializer):
        # Yangi ma'lumot saqlanayotganda (POST), kompaniya ID-sini avtomat bazaga yozadi
        user = self.request.user
        if hasattr(user, 'company') and user.company:
            serializer.save(company=user.company)
        else:
            raise serializers.ValidationError({"error": "Sizda kompaniya mavjud emas yoki tizimga kirmagansiz!"})