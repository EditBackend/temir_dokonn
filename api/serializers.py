from rest_framework import serializers
from django.contrib.auth import get_user_model
from datetime import datetime
from .models import Product, Sale, Category, Supplier, WarehouseIncome, Customer, Role, Employee, Batch, Expense, \
    ExpenseCategory,Unit,Sale



User = get_user_model()


# class EmployeeSerializer(serializers.ModelSerializer):
#     # create/edit paytida password yoziladi, lekin response’da ko‘rsatilmaydi
#     password = serializers.CharField(write_only=True, required=False)
#     class Meta:
#         model = User
#         fields = [
#             "id",
#             "login",      # login
#             "password",
#             "first_name",
#             "last_name",
#             "phone",
#             "role",
#             "is_active",
#         ]

    # def create(self, validated_data):
    #     password = validated_data.pop("password", None)
    #     user = User(**validated_data)
    #     if password:
    #         user.set_password(password)
    #     else:
    #         user.set_password("12345678")
    #     user.save()
    #     return user
    #
    # def update(self, instance, validated_data):
    #     password = validated_data.pop("password", None)
    #     for k, v in validated_data.items():
    #         setattr(instance, k, v)
    #     if password:
    #         instance.set_password(password)
    #     instance.save()
    #     return instance

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class EmployeeCreateSerializer(serializers.ModelSerializer):
    role_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Employee  # Xodimlar modeli nomi
        fields = ['id', 'first_name', 'last_name', 'phone', 'password', 'is_active', 'role', 'role_id']
        extra_kwargs = {'role': {'required': False}}

    def validate(self, attrs):
        role_id = attrs.get('role_id') or self.initial_data.get('role')

        # Agar frontendchi ob'ekt yoki matn yuborgan bo'lsa, ichidan ID ni qidiramiz
        if isinstance(role_id, dict):
            role_id = role_id.get('id')

        if role_id:
            try:
                from api.models import Role
                attrs['role'] = Role.objects.get(id=int(role_id))
            except (Role.DoesNotExist, ValueError, TypeError):
                raise serializers.ValidationError({"role": "Bunday Rol ID topilmadi."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('role_id', None)
        return super().create(validated_data)



class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id", "first_name", "last_name", "phone",
            "address", "debt", "total_debt", "created_at",
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    supplierName = serializers.CharField(source='supplier.name', read_only=True, default="-")
    categoryName = serializers.CharField(source='category.name', read_only=True, default="-")
    class Meta:
        model = Product
        fields = '__all__'

class SaleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ('total_price', 'created_at', 'check_number', 'product_name', 'customer_name')

    def get_customer_name(self, obj):
        if obj.customer:
            name = f"{obj.customer.first_name} {obj.customer.last_name}".strip()
            return name if name else obj.customer.phone
        return "-"



class WarehouseIncomeSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    supplier_name = serializers.ReadOnlyField(source='supplier.name')
    class Meta:
        model = WarehouseIncome
        fields = "__all__"
        read_only_fields = ('created_at', 'check_number')


class BatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Batch
        fields = '__all__'


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name']



class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default="-")
    category = ExpenseCategorySerializer(read_only=True)

    class Meta:
        model = Expense
        fields = '__all__'


class ExpenseCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Expense
        fields = ['date', 'category', 'category_id', 'amount', 'payment_type', 'note', 'branch']
        extra_kwargs = {
            'category': {'required': False}
        }

    def validate(self, attrs):
        category_id = attrs.get('category_id')
        if not category_id and 'category' in self.initial_data:
            try:
                category_id = int(self.initial_data.get('category'))
            except (ValueError, TypeError):
                pass

        if not category_id:
            raise serializers.ValidationError({"category": "Kategoriya ID si yuborilmadi."})

        try:
            attrs['category'] = ExpenseCategory.objects.get(id=category_id)
        except ExpenseCategory.DoesNotExist:
            raise serializers.ValidationError({"category": "Kategoriya topilmadi."})

        date_val = self.initial_data.get('date')
        if date_val:
            for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
                try:
                    attrs['date'] = datetime.strptime(str(date_val), fmt).date()
                    break
                except ValueError:
                    continue
        return attrs

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount musbat bo‘lishi kerak")
        return value

    # 👇 MANA SHU YERINI O'ZGARTIRAMIZ
    def create(self, validated_data):
        validated_data.pop('category_id', None)

        request = self.context.get('request')
        # Agar foydalanuvchi login qilgan bo'lsa, uning ID sini biriktiramiz
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        else:
            # ERROR QAYTARISHNI OLIB TASHLADIK!
            # Login qilmagan bo'lsa, shunchaki created_by = None (null) bo'lib saqlanadi
            validated_data['created_by'] = None

        return super().create(validated_data)