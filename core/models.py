from django.db import models

class Agency(models.Model):
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name

class AdCampaign(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    platform = models.CharField(max_length=50, default="Meta")  # Meta/Instagram/Facebook
    campaign_name = models.CharField(max_length=150)
    daily_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.campaign_name} ({self.agency.name})"

class Order(models.Model):
    STATUS_CHOICES = (
        ("WAITING_PICKUP", "Waiting for Pickup"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("RETURNED", "Returned"),
    )

    platform = models.CharField(max_length=30, default="Instagram")  # Instagram/Facebook/Shopify
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    campaign = models.ForeignKey(AdCampaign, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    order_date = models.DateField()
    order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="WAITING_PICKUP")

    customer_name = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
