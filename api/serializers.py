from rest_framework import serializers
from django.contrib.auth import get_user_model
from datetime import datetime
from .models import Product, Sale, Category, Supplier, WarehouseIncome, Customer, Role, Employee, Batch, Expense, ExpenseCategory, Unit

User = get_user_model()

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"



#  Xodimlar uchun to'g'rilangan serializer
class EmployeeCreateSerializer(serializers.ModelSerializer):
    # read_only=True ni olib tashlaymiz, lekin faqat ma'lumot qaytayotganda ko'rinishi uchun default qoldiramiz
    role_name = serializers.CharField(source='role.name', required=False, default="-")

    class Meta:
        model = Employee
        fields = ['id', 'login', 'first_name', 'last_name', 'phone', 'is_active', 'role', 'role_name']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'role': {'required': False}
        }

    def validate(self, attrs):
        # 1. Frontenddan kelgan Role ID yoki Role Name'ni tekshiramiz
        role_id = self.initial_data.get('role')
        role_name_input = self.initial_data.get('role_name')

        from .models import Role

        # Variant A: Agar frontendchi Rol ID yuborgan bo'lsa
        if role_id:
            if isinstance(role_id, dict):
                role_id = role_id.get('id')
            try:
                attrs['role'] = Role.objects.get(id=int(role_id))
            except (Role.DoesNotExist, ValueError, TypeError):
                raise serializers.ValidationError({"role": "Bunday Rol ID topilmadi."})

        # Variant B: Agar frontendchi Rol NOMINI (role_name) yuborgan bo'lsa
        elif role_name_input:
            try:
                # Bazadan nomiga qarab (katta-kichik harfga qaramasdan iexact bilan) qidiramiz
                role_obj = Role.objects.filter(name__iexact=str(role_name_input).strip()).first()
                if role_obj:
                    attrs['role'] = role_obj
                else:
                    # Agar u yozgan nomli rol bazada bo'lmasa, yangi rol ochib ketamiz (ixtiyoriy)
                    role_obj = Role.objects.create(name=str(role_name_input).strip())
                    attrs['role'] = role_obj
            except Exception as e:
                raise serializers.ValidationError({"role_name": "Rolni biriktirishda xatolik."})

        return attrs
EmployeeSerializer = EmployeeCreateSerializer


#  Mahsulotlar uchun to'g'rilangan serializer
class ProductSerializer(serializers.ModelSerializer):
    # Ham camelCase, ham snake_case qilib ikkala variantini ham beramiz!
    supplierName = serializers.CharField(source='supplier.name', read_only=True, default="-")
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default="-")

    categoryName = serializers.CharField(source='category.name', read_only=True, default="-")
    category_name = serializers.CharField(source='category.name', read_only=True, default="-")

    unit_name = serializers.CharField(source='unit.name', read_only=True, default="-")
    unitName = serializers.CharField(source='unit.name', read_only=True, default="-")

    class Meta:
        model = Product
        # __all__ turaversa, qo'shimcha tepada yaratilgan text maydonlar ham qo'shilib boradi
        fields = '__all__'

    # class Meta:
    #     model = Product
    #     # 🔥 fields-ga aniq yozib qo'yamiz, shunda ID-lar bilan birga NOM-lar ham chiroyli ketadi
    #     fields = [
    #         'id', 'name', 'price', 'last_price', 'quantity', 'comment',
    #         'supplier', 'supplier_name', 'category', 'category_name',
    #         'unit', 'unit_name', 'created_at', 'updated_at'
    #     ]


EmployeeSerializer = EmployeeCreateSerializer



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
        fields = ['id', 'name', 'phone', 'debt', 'total_debt','boss_name','address']


# class ProductSerializer(serializers.ModelSerializer):
#     supplierName = serializers.CharField(source='supplier.name', read_only=True, default="-")
#     categoryName = serializers.CharField(source='category.name', read_only=True, default="-")
#     unit_name = serializers.CharField(source='unit.name', read_only=True, default="-")
#     class Meta:
#         model = Product
#         fields = '__all__'


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
    # Frontend jadvalda to'lov turi nomini (Naqd, Karta, Nasiya) ko'rishi uchun:
    payment_type_name = serializers.ReadOnlyField(source='payment_type.name')

    # 🌟 Frontendchi dropdown (select) dan tanlagan ID-sini yuborishi uchun maydon:
    payment_type_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = WarehouseIncome
        fields = [
            'id', 'product', 'product_name', 'supplier', 'supplier_name',
            'quantity', 'price', 'payment_type', 'payment_type_id', 'payment_type_name',
            'total_price', 'check_number', 'created_at', 'employee'
        ]
        read_only_fields = ('created_at', 'check_number', 'total_price')

    def validate(self, attrs):
        # Frontenddan kelayotgan payment_type_id ni tekshirib, modeldagi ForeignKeyga bog'laymiz
        payment_type_id = attrs.get('payment_type_id') or self.initial_data.get('payment_type')
        if isinstance(payment_type_id, dict):
            payment_type_id = payment_type_id.get('id')

        if payment_type_id:
            try:
                # O'zingizning loyihangizdagi PaymentType modelini chaqiramiz
                from .models import PaymentType
                attrs['payment_type'] = PaymentType.objects.get(id=int(payment_type_id))
            except (PaymentType.DoesNotExist, ValueError, TypeError):
                raise serializers.ValidationError({"payment_type": "Bunday to'lov turi topilmadi."})
        return attrs

    def create(self, validated_data):
        # Vaqtinchalik ishlatilgan ID maydonini o'chiramiz va saqlaymiz
        validated_data.pop('payment_type_id', None)

        return super().create(validated_data)
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

    def create(self, validated_data):
        validated_data.pop('category_id', None)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        else:
            validated_data['created_by'] = None
        return super().create(validated_data)