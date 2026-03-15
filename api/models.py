from django.db import models




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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"



class Category(models.Model):

    name = models.CharField(max_length=100)

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

    STATUS_CHOICES = (
        ('dona', 'dona'),
        ('kg', 'kg'),
        ('metr', 'metr'),
        ('litr', 'litr'),
        ('m2', 'm2'),
        ('m3', 'm3'),
    )

    unity = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='dona'
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

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='Naqd'
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    check_number = models.IntegerField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):

        # total price hisoblash
        self.total_price = (self.quantity or 0) * (self.price or 0)

        super().save(*args, **kwargs)

        # Omborga qo'shish
        if self.product:

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
        self.total_price = (self.quantity or 0) * (self.price or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        product_name = self.product.name if self.product else "Mahsulot yo'q"
        return f"{product_name} - {self.quantity}"


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