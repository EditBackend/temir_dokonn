from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Product, Sale, Category, Supplier, WarehouseIncome,Customer,Role,Employee,Batch

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
    #         user.set_password(password)  # ✅ hash
    #     else:
    #         user.set_password("12345678")  # xohlasangiz olib tashlang
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
            "id",
            "first_name",
            "last_name",
            "phone",
            "address",
            "debt",
            "total_debt",
            "created_at",
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


# class PaymentTypeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PaymentType
#         fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'



class SaleSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    payment_type_name = serializers.CharField(
        source='payment_type.name',
        read_only=True
    )

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = (
            'total_price',
            'created_at',
            'check_number'
        )


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"



class WarehouseIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseIncome
        fields = "__all__"
        read_only_fields = (
            'created_at',
            'check_number'
        )


#ombor kirimi partiya
class BatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Batch
        fields = '__all__'