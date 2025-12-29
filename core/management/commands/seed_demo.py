import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Agency, Product, AdCampaign, Order


class Command(BaseCommand):
    help = "Seed demo data for dashboard"

    def handle(self, *args, **kwargs):
        random.seed(7)
        today = timezone.localdate()

        agencies = ["Agency A", "Agency B", "Agency C", "Agency D", "Agency E"]
        products = [f"Shoe {i}" for i in range(1, 26)]
        platforms = ["Instagram", "Facebook", "Shopify"]

        Agency.objects.all().delete()
        Product.objects.all().delete()
        AdCampaign.objects.all().delete()
        Order.objects.all().delete()

        agency_objs = [Agency.objects.create(name=a) for a in agencies]
        product_objs = [Product.objects.create(name=p) for p in products]

        campaigns = []
        for ag in agency_objs:
            for j in range(1, 4):
                campaigns.append(
                    AdCampaign.objects.create(
                        agency=ag,
                        platform="Meta",
                        campaign_name=f"{ag.name} - Campaign {j}",
                        daily_spend=random.randint(20, 120)
                    )
                )

        statuses = ["WAITING_PICKUP", "SHIPPED", "DELIVERED", "RETURNED"]

        # Create 90 days of orders
        for d in range(0, 90):
            day = today - timedelta(days=d)
            orders_count = random.randint(5, 30)

            for _ in range(orders_count):
                product = random.choice(product_objs)

                # Weighted: better agencies perform more
                ag = random.choices(agency_objs, weights=[40, 30, 20, 10, 8])[0]
                camp = random.choice([c for c in campaigns if c.agency_id == ag.id])

                qty = random.randint(1, 3)
                value = random.randint(25, 160) * qty

                status = random.choices(statuses, weights=[25, 20, 45, 10])[0]

                Order.objects.create(
                    platform=random.choice(platforms),
                    agency=ag,
                    campaign=camp,
                    product=product,
                    order_date=day,
                    order_value=value,
                    quantity=qty,
                    status=status,
                    customer_name=f"Customer {random.randint(1, 999)}",
                    city=random.choice(["London", "Manchester", "Birmingham", "Leeds", "Glasgow"])
                )

        self.stdout.write(self.style.SUCCESS("✅ Demo data seeded successfully."))
