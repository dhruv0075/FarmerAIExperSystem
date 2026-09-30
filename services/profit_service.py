from __future__ import annotations

from typing import Any, Dict, List, Optional
from services.suitability_service import get_crop_knowledge
from services.market_service import get_market_prices_for_commodity


EXPENSE_CATEGORIES = [
    "SEEDS",
    "FERTILIZER",
    "PESTICIDES",
    "LABOR",
    "IRRIGATION",
    "FUEL",
    "MACHINERY",
    "TRANSPORT",
    "STORAGE",
    "OTHER",
]


def calculate_crop_profit_potential(
    crop_name: str,
    farm_area: float = 1.0,
    area_unit: str = "acre",
    farm_lat: Optional[float] = None,
    farm_lon: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes research-backed revenue, input cost, and profit projections for a crop,
    integrating real mandi price benchmarks.
    """
    crop_info = get_crop_knowledge(crop_name)
    econ = crop_info.get("economics", {})
    if not econ.get("verified_source_url"):
        return {}  # Bundled cost/yield ranges have no traceable observations.
    area = max(0.1, float(farm_area or 1.0))
    # Standardize area to acres if in hectares (1 hectare ≈ 2.471 acres)
    area_in_acres = area * 2.471 if "hectare" in area_unit.lower() else area

    yield_range = econ.get("yield_range_quintals_per_acre", [10, 20])
    cost_range = econ.get("input_cost_range_per_acre", [14000, 22000])
    price_range = econ.get("benchmark_selling_price_per_quintal", [2200, 3000])

    # Check if real mandi prices exist
    mandi_res = get_market_prices_for_commodity(crop_name, farm_lat, farm_lon)
    best_m = mandi_res.get("best_market")
    if best_m and best_m.get("modal_price"):
        modal_p = float(best_m["modal_price"])
        price_range = [round(modal_p * 0.95, 0), round(modal_p * 1.05, 0)]

    # Projected economics per acre
    rev_min_per_acre = yield_range[0] * price_range[0]
    rev_max_per_acre = yield_range[1] * price_range[1]
    profit_min_per_acre = rev_min_per_acre - cost_range[1]
    profit_max_per_acre = rev_max_per_acre - cost_range[0]

    # Total farm projections
    total_yield_min = round(yield_range[0] * area_in_acres, 1)
    total_yield_max = round(yield_range[1] * area_in_acres, 1)
    total_cost_min = round(cost_range[0] * area_in_acres, 0)
    total_cost_max = round(cost_range[1] * area_in_acres, 0)
    total_rev_min = round(rev_min_per_acre * area_in_acres, 0)
    total_rev_max = round(rev_max_per_acre * area_in_acres, 0)
    total_profit_min = round(profit_min_per_acre * area_in_acres, 0)
    total_profit_max = round(profit_max_per_acre * area_in_acres, 0)

    # Profitability score (0 - 100)
    avg_profit_acre = (profit_min_per_acre + profit_max_per_acre) / 2.0
    profit_score = min(100.0, max(20.0, round((avg_profit_acre / 45000.0) * 100.0, 1)))

    return {
        "crop_name": crop_info.get("name", crop_name.capitalize()),
        "farm_area": area,
        "area_unit": area_unit,
        "area_in_acres": round(area_in_acres, 2),
        "yield_range_quintals_per_acre": yield_range,
        "price_range_per_quintal": price_range,
        "cost_range_per_acre": cost_range,
        "projected_total_yield": [total_yield_min, total_yield_max],
        "projected_total_cost": [total_cost_min, total_cost_max],
        "projected_total_revenue": [total_rev_min, total_rev_max],
        "projected_total_profit": [total_profit_min, total_profit_max],
        "profitability_score": profit_score,
        "market_benchmark": best_m,
        "source": econ.get("source", "ICAR / Directorate of Economics & Statistics"),
    }


def aggregate_farm_financials(
    expenses: List[Dict[str, Any]],
    sales: List[Dict[str, Any]],
    expected_profit_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Computes actual farm costs, category breakdown, realized revenues from verified sales,
    and net actual profit.
    """
    total_actual_cost = 0.0
    category_totals = {cat: 0.0 for cat in EXPENSE_CATEGORIES}

    for exp in expenses:
        amt = float(exp.get("amount", 0.0) or 0.0)
        cat = exp.get("category", "OTHER").upper()
        if cat not in category_totals:
            cat = "OTHER"
        category_totals[cat] += amt
        total_actual_cost += amt

    # Category percentages
    category_breakdown = []
    for cat, val in category_totals.items():
        if val > 0 or cat in ["SEEDS", "FERTILIZER", "LABOR", "IRRIGATION"]:
            pct = round((val / total_actual_cost * 100.0), 1) if total_actual_cost > 0 else 0.0
            category_breakdown.append({
                "category": cat,
                "amount": round(val, 2),
                "percentage": pct,
            })

    # Actual Sales Realization
    total_actual_revenue = 0.0
    total_qty_sold = 0.0
    for sale in sales:
        total_actual_revenue += float(sale.get("total_amount", 0.0) or 0.0)
        total_qty_sold += float(sale.get("quantity_sold", 0.0) or 0.0) / (100 if str(sale.get("unit", "")).lower() == "kg" else 1)

    actual_net_profit = round(total_actual_revenue - total_actual_cost, 2)

    # Comparison with expected profit if available
    exp_rev_mid = None
    exp_profit_mid = None
    if expected_profit_info and expected_profit_info.get("projected_total_revenue"):
        revs = expected_profit_info["projected_total_revenue"]
        profs = expected_profit_info["projected_total_profit"]
        exp_rev_mid = round((revs[0] + revs[1]) / 2.0, 0)
        exp_profit_mid = round((profs[0] + profs[1]) / 2.0, 0)

    return {
        "total_actual_cost": round(total_actual_cost, 2),
        "total_actual_revenue": round(total_actual_revenue, 2),
        "total_actual_profit": actual_net_profit,
        "total_quantity_sold": round(total_qty_sold, 2),
        "category_breakdown": category_breakdown,
        "expected_revenue_benchmark": exp_rev_mid,
        "expected_profit_benchmark": exp_profit_mid,
        "has_sales": len(sales) > 0,
        "sales_count": len(sales),
        "expense_count": len(expenses),
    }
