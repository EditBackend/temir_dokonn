from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from organization.models import TenantModel





class AppPage(TenantModel):
    name = models.CharField(max_length=100, verbose_name="Sahifa nomi")
    codename = models.CharField(max_length=100, unique=True,verbose_name="Tizim uchun qisqa nomi")

    def __str__(self):
        return self.name


class RolePermission(TenantModel):
    role = models.ForeignKey('Role', on_delete=models.CASCADE, related_name='permissions')
    page = models.ForeignKey(AppPage, on_delete=models.CASCADE, related_name='page_permissions')
    can_view = models.BooleanField(default=False, verbose_name="Ko'rish")
    can_create = models.BooleanField(default=False, verbose_name="Yaratish")
    can_edit = models.BooleanField(default=False, verbose_name="Tahrirlash")
    can_delete = models.BooleanField(default=False, verbose_name="O'chirish")

    class Meta:
        unique_together = ('role', 'page')

    def __str__(self):
        return f"{self.role.name} - {self.page.name} huquqlari"

# User = get_user_model()
class Branch(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ExpenseCategory(TenantModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Expense(TenantModel):
    PAYMENT_TYPES = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('transfer', 'Transfer'),
    )

    date = models.DateField()
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('api.Employee', on_delete=models.SET_NULL, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)  # soft delete
    created_at = models.DateTimeField(auto_now_add=True)


class Role(TenantModel):
    name = models.CharField(max_length=50)
    can_sell = models.BooleanField(default=False)
    can_income = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)

    def __str__(self):
        return self.name




from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from organization.models import TenantModel


class EmployeeManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Telefon raqam shart!')
        extra_fields.setdefault('is_active', True)
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_password('temporary_pass')
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone, password, **extra_fields)


# api/models.py ichidagi Employee modelini toping va ichini mana shunday yangilang:

class Employee(AbstractBaseUser, PermissionsMixin, TenantModel):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    login = models.CharField(max_length=150, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=255)

    role = models.ForeignKey(
        'Role',
        on_delete=models.SET_NULL,
        null=True,
        related_name="employees"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_ceo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # 🟢 TO'QNASHUVNI BARTARAF ETISH UCHUN MANA SHU 2 TA MAYDONNI QO'SHAMIZ:
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='api_employee_groups',  # Nom o'zgatirildi
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to.'
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='api_employee_permissions',  # Nom o'zgartirildi
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.'
    )


    objects = EmployeeManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
class ActivityLog(TenantModel):



    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True
    )

    action = models.TextField()  # qanday ish qildi

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.action}"



class Customer(TenantModel):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    debt = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_debt = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    score = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Har safar save() bo'lganda yangilanadi
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"
# models.py ichida CustomerPayment modelini toping va mana shunga almashtiring:

class CustomerPayment(TenantModel):
    PAYMENT_METHODS = [
        ('cash', 'Naqd'),
        ('card', 'Karta'),
        ('click', 'Click'),
    ]
    #  related_name o'zgartirildi: 'payments' o'rniga 'customer_debt_payments' qilindi
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_debt_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="To'lov summasi")
    payment_type = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="To'lov sanasi")

    def __str__(self):
        return f"{self.customer.name} - {self.amount} so'm"


class Category(TenantModel):

    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name




class Unit(TenantModel):


    name = models.CharField(max_length=50, verbose_name="O'lchov birligi nomi")
    short_name = models.CharField(max_length=10, blank=True, null=True, verbose_name="Qisqartma nomi")

    class Meta:


        unique_together = ('company', 'name')

    def __str__(self):
        return self.name



class PaymentType(TenantModel):
    name = models.CharField(max_length=50, unique=True, verbose_name="To'lov turi nomi")

    def __str__(self):
        return self.name

class Supplier(TenantModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    boss_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Boshliq ismi")
    address = models.TextField(null=True, blank=True, verbose_name="Manzil")
    debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Oxirgi qarzlar uchun
    total_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Jami qarzimiz

    def __str__(self):
        return self.name



class Product(TenantModel):
    name = models.CharField(max_length=255, null=True, blank=True)
    # sotuv narxi
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # oxirgi kirim narxi
    last_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    comment = models.CharField(max_length=500, null=True, blank=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
    def save(self, *args, **kwargs):
        # Agar mahsulot mavjud bo‘lsa eski narxni tekshiramiz
        if self.pk:
            old_product = Product.objects.get(pk=self.pk)

            if old_product.price != self.price:

                PriceHistory.objects.create(
                    product=self,
                    old_price=old_product.price,
                    new_price=self.price
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name if self.name else "Nomsiz mahsulot"



class WarehouseIncome(TenantModel):


    PAYMENT_TYPES = (
        ('Naqd', 'Naqd'),
        ('Karta', 'Karta'),
        ('Nasiya', 'Nasiya'),
    )


    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warehouse_incomes'
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warehouse_incomes'
    )

    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # BU YER O'ZGARDI CharField o'rniga ForeignKey
    payment_type = models.ForeignKey(
        PaymentType,
        on_delete=models.PROTECT,  # SET_PROTECT emas, shunchaki PROTECT
        null=True,
        blank=True,
        related_name='warehouse_incomes'
    )

    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    check_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        # 1. Umumiy summani hisoblash
        self.total_price = (self.quantity or 0) * (self.price or 0)
        is_new = self.pk is None

        # 2. Asosiy Django save funksiyasini chaqirish
        super().save(*args, **kwargs)

        # 3. Xarajatga yozish va Ta'minotchi qarzini hisoblash logikasi
        if is_new and self.payment_type:
            p_type_name = self.payment_type.name.lower()

            #  Agar to'lov turi Nasiya bo'lsa - Ta'minotchi qarzini oshiramiz
            if 'nasiya' in p_type_name:
                if self.supplier:
                    self.supplier.debt += self.total_price
                    self.supplier.total_debt += self.total_price
                    self.supplier.save()

            #  Agar Naqd yoki Karta bo'lsa - srazu Xarajat (Dashboard)ga yoziladi
            else:
                category, _ = ExpenseCategory.objects.get_or_create(name="Ombor kirimi uchun")
                expense_payment_type = 'card' if 'kart' in p_type_name else 'cash'

                Expense.objects.create(
                    date=timezone.now().date(),
                    category=category,
                    amount=self.total_price,
                    payment_type=expense_payment_type,
                    note=f"Kirim #{self.id}: {self.product.name if self.product else 'Nomsiz'} ({self.supplier.name if self.supplier else 'Nomsiz ta`minotchi'})",
                    created_by=None
                )

        # 4. Ombor qoldig'ini yangilash va FIFO batch yaratish
        if is_new and self.product:
            if self.product.quantity is None:
                self.product.quantity = 0
            self.product.quantity += self.quantity
            self.product.last_price = self.price
            self.product.save()

            # FIFO uchun batch yaratish
            Batch.objects.create(
                product=self.product,
                supplier=self.supplier,
                unit_cost=self.price,
                batch_code=f"BATCH-{self.product.id}-{self.id}",
                qty_in=self.quantity,
                qty_left=self.quantity
            )
    def __str__(self):
        product_name = self.product.name if self.product else "Mahsulot yo'q"
        return f"{product_name} - {self.quantity}"



class Batch(TenantModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="batches")
    received_date = models.DateField(auto_now_add=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    batch_code = models.CharField(max_length=50, unique=True)
    qty_in = models.DecimalField(max_digits=12, decimal_places=2)
    qty_left = models.DecimalField(max_digits=12, decimal_places=2)
    invoice_id = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):

        # birinchi saqlanishda qty_left = qty_in bo'ladi
        if not self.pk:
            self.qty_left = self.qty_in

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.batch_code}"


class Sale(TenantModel):

    PAYMENT_TYPES = (
        ('Naqd', 'Naqd'),
        ('Karta', 'Karta'),
        ('Nasiya', 'Nasiya'),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales'
    )

    # FIFO uchun qaysi batchdan sotilganini bilish
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales"
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='Naqd'
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    check_number = models.IntegerField(
        null=True,
        blank=True
    )
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # 1. Umumiy summani hisoblash
        self.total_price = (self.quantity or 0) * (self.price or 0)
        # 2. Mijozning qarzini yangilash (faqat yangi savdo yaratilayotganda)
        # self.pk bo'lmasa, demak bu yangi rekord
        if not self.pk and self.payment_type == 'Nasiya' and self.customer:
            # Mijozning joriy qarzi va umumiy qarzini oshiramiz
            self.customer.debt += self.total_price
            self.customer.total_debt += self.total_price
            # Mijoz modelini saqlash shart, aks holda o'zgarish bazaga kirmaydi
            self.customer.save()
        # 3. Asosiy save funksiyasini chaqirish
        super().save(*args, **kwargs)


    def __str__(self):
        product_name = self.product.name if self.product else "Mahsulot yo'q"
        return f"{product_name} - {self.quantity}"


class SaleItem(TenantModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    #Rollback auditlog narx tarixini saqlash
class PriceHistory(TenantModel):
    product = models.ForeignKey(
    Product,
    on_delete=models.CASCADE,
    related_name="price_histories"
    )
    old_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    changed_at = models.DateTimeField(auto_now_add=True)
    employee = models.ForeignKey(
    Employee,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
    )
    def __str__(self):
        return f"{self.product.name} {self.old_price} -> {self.new_price}"




# Crededit analitikalari
class Payment(TenantModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    def save(self, *args, **kwargs):
        #  Faqat yangi to'lov qo'shilayotganda mijoz qarzini kamaytiramiz
        if not self.pk:
            if self.customer:
                # Mijozning joriy qarzidan to'langan summani ayiramiz
                self.customer.debt -= self.amount
                # Qarz manfiy bo'lib ketmasligini tekshirish (ixtiyoriy, lekin foydali)
                # if self.customer.debt < 0:
                #     self.customer.debt = 0

                self.customer.save()

        #  Asosiy save funksiyasini chaqirish
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer} - {self.amount} ({self.date})"



class ArchivedItem(TenantModel):
    ITEM_TYPES = [
        ('supplier', 'Ta\'minotchi'),
        ('product', 'Mahsulot'),
        ('category', 'Kategoriya'),
        ('employee', 'Xodim'),
        ('customer', 'Mijoz'),
        ('role', 'Rol'),
    ]

    item_type = models.CharField(max_length=50, choices=ITEM_TYPES, verbose_name="Tur")
    name = models.CharField(max_length=255, verbose_name="Nomi")
    deleted_at = models.DateTimeField(auto_now_add=True, verbose_name="Sana")
    status = models.CharField(max_length=50, default="O'chirilgan", verbose_name="Status")
    original_id = models.IntegerField(null=True, blank=True)  # Qaysi ID li obyekt o'chgani

    def __str__(self):
        return f"{self.get_item_type_display()} - {self.name}"
