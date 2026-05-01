from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Product, Sale, Category, Supplier, WarehouseIncome, Customer, Role, Employee, Batch, Expense, \
    ExpenseCategory

User = get_user_model()


# class EmployeeSerializer(serializers.ModelSerializer):
#     # create/edit paytida password yoziladi, lekin response’da ko‘rsatilmaydi
#     password = serializers.CharField(write_only=True, required=False)
#
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


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"

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
    # Agar Product modelida supplier degan ForeignKey bo'lsa, uning nomini chiqarish:
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = '__all__' # Bu barcha fieldlarni, plyus yuqoridagi 'supplier_name'ni ham chiqaradi

class SaleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    payment_type_name = serializers.CharField(source='payment_type.name', read_only=True)

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ('total_price', 'created_at', 'check_number')

class WarehouseIncomeSerializer(serializers.ModelSerializer):
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
    category = ExpenseCategorySerializer(read_only=True)

    class Meta:
        model = Expense
        fields = '__all__'

class ExpenseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['date', 'category', 'amount', 'payment_type', 'note', 'branch']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount musbat bo‘lishi kerak")
        return value

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)