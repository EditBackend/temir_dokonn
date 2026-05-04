from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
User = get_user_model()
class Branch(models.Model):
    name = models.CharField(max_length=100)  # filial nomi
    address = models.TextField(blank=True, null=True)  # manzil
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
#boshliq uchun expences oynasi
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Expense(models.Model):
    PAYMENT_TYPES = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('transfer', 'Transfer'),
    )

    date = models.DateField()
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_deleted = models.BooleanField(default=False)  # soft delete
    created_at = models.DateTimeField(auto_now_add=True)


class Role(models.Model):
    """
    Lavozim modeli.
    Masalan:
    Egasi
    Sotuvchi
    Omborchi
    ishlovchi
    va hokazo
    """


    name = models.CharField(max_length=50)

    # Har bir rolga ruxsatlar beramiz
    can_sell = models.BooleanField(default=False)       # sotish mumkinmi
    can_income = models.BooleanField(default=False)     # kirim qilish mumkinmi
    can_view_reports = models.BooleanField(default=False) # hisobot ko'rish mumkinmi
    can_manage_users = models.BooleanField(default=False) # xodim qo'shish mumkinmi

    def __str__(self):
        return self.name



class Employee(models.Model):
    """
    Xodim modeli
    Telefon bu login
    password bu parol
    role bu lavozim
    """
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    phone = models.CharField(
        max_length=20,
        unique=True
    )  # login sifatida ishlaydi

    password = models.CharField(
        max_length=255
    )  # keyinchalik hashing qilish mumkin

    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employees"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ActivityLog(models.Model):
    """
    Kim nima qilganini yozib boradi
    har bir harakat saqlanadi.
    kimdir omborga kirim qilsa yoziladi,
    kimdir sotsa ham yozilib boradi.

    """

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True
    )

    action = models.TextField()  # qanday ish qildi

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.action}"



class Customer(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    debt = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_debt = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    score = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Har safar save() bo'lganda yangilanadi
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"



class Category(models.Model):

    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# O'lchov birligi uchun
class Unit(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="O'lchov birligi nomi")
    short_name = models.CharField(max_length=10, blank=True, null=True, verbose_name="Qisqartma nomi") # masalan: kg, l

    def __str__(self):
        return self.name

class PaymentType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="To'lov turi nomi")

    def __str__(self):
        return self.name


class Product(models.Model):

    name = models.CharField(max_length=255, null=True, blank=True)

    # sotuv narxi
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # oxirgi kirim narxi
    last_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    comment = models.CharField(max_length=500, null=True, blank=True)

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

class Supplier(models.Model):

    name = models.CharField(max_length=255)

    phone = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class WarehouseIncome(models.Model):
    # PAYMENT_TYPES (tuple) qismini o'chirib tashlaymiz, chunki endi dinamik bo'ladi

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

    # BU YER O'ZGARDI: CharField o'rniga ForeignKey
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
        self.total_price = (self.quantity or 0) * (self.price or 0)
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Xarajatga yozish logikasi (Dinamik holatga moslandi)
        if is_new and self.payment_type:
            # Nasiyadan boshqa har qanday to'lov turi xarajat hisoblanadi
            if self.payment_type.name.lower() != 'nasiya':
                category, _ = ExpenseCategory.objects.get_or_create(name="Ombor kirimi uchun")

                # Expense modelidagi payment_type CharField bo'lgani uchun string beramiz
                # Agar Expense'dagi payment_type ham dinamik bo'lsa, uni ham o'zgartirish kerak bo'ladi
                Expense.objects.create(
                    date=timezone.now().date(),  # created_at o'rniga hozirgi vaqtni beramiz
                    category=category,
                    amount=self.total_price,
                    payment_type='cash',
                    note=f"Kirim #{self.id}: {self.product.name if self.product else 'Nomsiz'}",
                    # created_by qismini soddalashtiramiz:
                    created_by=self.employee.user if self.employee and hasattr(self.employee, 'user') else None
                )
        #Ombor qoldig'ini yangilash va FIFO batch yaratish
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

class Batch(models.Model):
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


class Sale(models.Model):

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


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    #Rollback auditlog narx tarixini saqlash
class PriceHistory(models.Model):
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
class Payment(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    def save(self, *args, **kwargs):
        # 1. Faqat yangi to'lov qo'shilayotganda mijoz qarzini kamaytiramiz
        if not self.pk:
            if self.customer:
                # Mijozning joriy qarzidan to'langan summani ayiramiz
                self.customer.debt -= self.amount
                # Qarz manfiy bo'lib ketmasligini tekshirish (ixtiyoriy, lekin foydali)
                # if self.customer.debt < 0:
                #     self.customer.debt = 0

                self.customer.save()

        # 2. Asosiy save funksiyasini chaqirish
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer} - {self.amount} ({self.date})"
