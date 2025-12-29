from datetime import date, timedelta
from decimal import Decimal
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from .models import Order, AdCampaign


PLATFORM_OPTIONS = ["All", "Facebook", "Insta", "Google", "YouTube", "LinkedIn"]
AGENCY_OPTIONS = ["All", "Agency 1", "Agency 2", "Agency 3"]  # demo list (you can load from DB)


def _date_range(preset: str, from_str: str | None, to_str: str | None):
    today = timezone.localdate()

    if preset == "today":
        return today, today
    if preset == "this_week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end
    if preset == "this_month":
        start = today.replace(day=1)
        next_month = start.replace(month=start.month + 1, day=1) if start.month != 12 else start.replace(year=start.year + 1, month=1, day=1)
        end = next_month - timedelta(days=1)
        return start, end
    if preset == "last_month":
        first_this = today.replace(day=1)
        last_month_end = first_this - timedelta(days=1)
        start = last_month_end.replace(day=1)
        return start, last_month_end
    if preset == "this_quarter":
        q = (today.month - 1) // 3 + 1
        start_month = 3 * (q - 1) + 1
        start = today.replace(month=start_month, day=1)
        next_q = start.replace(month=start_month + 3, day=1) if start_month != 10 else start.replace(year=start.year + 1, month=1, day=1)
        end = next_q - timedelta(days=1)
        return start, end

    # custom
    if from_str and to_str:
        try:
            f = date.fromisoformat(from_str)
            t = date.fromisoformat(to_str)
            if t < f:
                f, t = t, f
            return f, t
        except ValueError:
            pass

    return today, today


from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Order, AdCampaign


def _build_dashboard_payload(preset, from_date, to_date, platform, agency):
    start_date, end_date = _date_range(preset, from_date, to_date)

    qs = Order.objects.filter(order_date__range=[start_date, end_date])

    if platform and platform != "All":
        qs = qs.filter(platform=platform)

    if agency and agency != "All":
        qs = qs.filter(agency__name=agency)

    # -------------------------
    # KPIs
    # -------------------------
    total_orders = qs.count()
    total_revenue = qs.aggregate(v=Coalesce(Sum("order_value"), Decimal("0.00")))["v"]
    total_items = qs.aggregate(v=Coalesce(Sum("quantity"), 0))["v"]

    days_count = (end_date - start_date).days + 1

    # ✅ Better spend calculation: based on campaigns used by filtered orders
    campaign_ids = qs.values_list("campaign_id", flat=True).distinct()

    campaign_spend_daily = (AdCampaign.objects
        .filter(id__in=campaign_ids)
        .aggregate(v=Coalesce(Sum("daily_spend"), Decimal("0.00")))["v"]
    )

    total_ads_spend = (campaign_spend_daily * Decimal(days_count)).quantize(Decimal("0.01"))

    # -------------------------
    # Derived KPIs (WOW KPIs)
    # -------------------------
    total_orders_dec = Decimal(total_orders) if total_orders else Decimal("0")

    avg_order_value = (total_revenue / total_orders_dec).quantize(Decimal("0.01")) if total_orders else Decimal("0.00")
    cpo = (total_ads_spend / total_orders_dec).quantize(Decimal("0.01")) if total_orders else Decimal("0.00")

    assumed_margin = Decimal("0.38")  # realistic demo margin for dropshipping
    gross_profit = (total_revenue * assumed_margin - total_ads_spend).quantize(Decimal("0.01"))
    roi = (gross_profit / total_ads_spend * Decimal("100")).quantize(Decimal("0.01")) if total_ads_spend > 0 else Decimal("0.00")

    # -------------------------
    # Charts
    # -------------------------
    daily = list(
        qs.values("order_date")
          .annotate(revenue=Coalesce(Sum("order_value"), Decimal("0.00")))
          .order_by("order_date")
    )

    platform_split = list(
        qs.values("platform")
          .annotate(orders=Count("id"))
          .order_by("-orders")
    )

    top_products = list(
        qs.values("product__name")
          .annotate(revenue=Coalesce(Sum("order_value"), Decimal("0.00")))
          .order_by("-revenue")[:10]
    )

    top_agencies = list(
        qs.values("agency__name")
          .annotate(orders=Count("id"))
          .order_by("-orders")[:3]
    )

    top_ads = list(
        qs.values("campaign__campaign_name")
          .annotate(orders=Count("id"))
          .order_by("-orders")[:3]
    )

    campaign_perf = list(
        qs.values("campaign__campaign_name", "campaign__daily_spend")
          .annotate(orders=Count("id"))
          .order_by("-orders")[:10]
    )

    for c in campaign_perf:
        spend = (Decimal(c["campaign__daily_spend"]) * Decimal(days_count)).quantize(Decimal("0.01"))
        c["spend"] = float(spend)
        c["orders"] = int(c["orders"])
        c["cpo"] = float((spend / Decimal(c["orders"])).quantize(Decimal("0.01"))) if c["orders"] else 0.0

    # -------------------------
    # Lists
    # -------------------------
    recent_orders = list(
        qs.select_related("product", "agency", "campaign")
          .order_by("-order_date", "-id")
          .values("order_date", "product__name", "agency__name", "order_value", "status")[:10]
    )

    waiting_pickup = list(
        qs.filter(status="WAITING_PICKUP")
          .select_related("product", "campaign")
          .order_by("-order_date", "-id")
          .values("order_date", "product__name", "campaign__campaign_name", "order_value")[:10]
    )

    delivered = list(
        qs.filter(status="DELIVERED")
          .select_related("product", "agency")
          .order_by("-order_date", "-id")
          .values("order_date", "product__name", "agency__name", "order_value")[:10]
    )

    # -------------------------
    # Underperforming Agencies (auto-analysis)
    # -------------------------
    agency_perf = list(
        qs.values("agency__name")
          .annotate(
              orders=Count("id"),
              revenue=Coalesce(Sum("order_value"), Decimal("0.00")),
          )
          .order_by("-orders")
    )

    under_rows = []
    if agency_perf:
        # Spend per agency based on campaigns
        agency_spend_map = {}
        campaign_data = (qs.values("agency__name", "campaign__daily_spend")
                           .annotate(cnt=Count("id"))
                           .distinct())

        for r in campaign_data:
            name = r["agency__name"]
            daily_spend = Decimal(r["campaign__daily_spend"])
            agency_spend_map[name] = agency_spend_map.get(name, Decimal("0.00")) + daily_spend

        for a in agency_perf:
            name = a["agency__name"]
            orders = int(a["orders"])
            spend = (agency_spend_map.get(name, Decimal("0.00")) * Decimal(days_count)).quantize(Decimal("0.01"))
            cpo_a = (spend / Decimal(orders)).quantize(Decimal("0.01")) if orders else Decimal("0.00")

            under_rows.append({
                "agency": name,
                "orders": orders,
                "spend": float(spend),
                "cpo": float(cpo_a),
                "status": "OK"
            })

        # thresholds (looks smart)
        avg_orders = sum(r["orders"] for r in under_rows) / len(under_rows)
        avg_cpo = sum(r["cpo"] for r in under_rows) / len(under_rows)

        for r in under_rows:
            flags = []
            if r["orders"] < max(5, avg_orders * 0.6):
                flags.append("Low Orders")
            if r["cpo"] > max(20, avg_cpo * 1.35):
                flags.append("High CPO")
            r["status"] = " / ".join(flags) if flags else "OK"

        # show only agencies needing attention (else show top few)
        underperforming = [r for r in under_rows if r["status"] != "OK"]

        # 🔥 DEMO FALLBACK (when no agency qualifies as underperforming)
        if not underperforming and under_rows:
            demo_rows = sorted(
                under_rows,
                key=lambda x: (-x["cpo"], x["orders"])
            )[:3]

            for r in demo_rows:
                r["status"] = "Needs Attention (Demo)"
                r["is_demo"] = True

            underperforming = demo_rows

        else:
            for r in underperforming:
                r["is_demo"] = False

    else:
        underperforming = []

    return {
        "meta": {"start_date": str(start_date), "end_date": str(end_date)},
        "kpis": {
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "total_items": int(total_items),
            "total_ads_spend": float(total_ads_spend),

            # ✅ NEW KPIs
            "gross_profit": float(gross_profit),
            "roi": float(roi),
            "avg_order_value": float(avg_order_value),
            "cpo": float(cpo),
        },
        "charts": {
            "daily_revenue": daily,
            "platform_split": platform_split,
            "top_products": top_products,
            "top_agencies": top_agencies,
            "top_ads": top_ads,
            "campaign_perf": campaign_perf,
        },
        "lists": {
            "recent_orders": recent_orders,
            "waiting_pickup": waiting_pickup,
            "delivered": delivered,

            # ✅ NEW list
            "underperforming_agencies": underperforming
        }
    }



def dashboard(request):
    # first load defaults
    preset = request.GET.get("preset", "today")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    platform = request.GET.get("platform", "All")
    agency = request.GET.get("agency", "All")

    payload = _build_dashboard_payload(preset, from_date, to_date, platform, agency)

    return render(request, "d3.html", {
        "preset": preset,
        "from_date": from_date or "",
        "to_date": to_date or "",
        "platform": platform,
        "agency": agency,
        "platform_options": PLATFORM_OPTIONS,
        "agency_options": AGENCY_OPTIONS,
        "payload": payload,  # initial data
    })


def dashboard_data_api(request):
    preset = request.GET.get("preset", "today")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    platform = request.GET.get("platform", "All")
    agency = request.GET.get("agency", "All")

    payload = _build_dashboard_payload(preset, from_date, to_date, platform, agency)
    return JsonResponse(payload, safe=False)
