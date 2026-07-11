"""The natural-language questions we ask CRAFT.

No hand-written SQL anywhere in this project: `generate_sql` writes it. Because generate_sql
is non-deterministic, we record the SQL it produced alongside the rows, and assert on result
shape rather than SQL text — otherwise the suite would break every time CRAFT's model updates.
"""

CONNECTION = "brazilian-e-commerce-5f7bc95c"

SCHEMA = {
    "schema_name": "BRAZILIAN_E_COMMERCE",
    "schema_fqn": "brazilian-e-commerce-5f7bc95c.BRAZILIAN_E_COMMERCE.BRAZILIAN_E_COMMERCE",
}

QUESTIONS: dict[str, str] = {
    # The product. Everything else supports this.
    "lanes": (
        "For delivered orders, group by customer_state (only states with at least 500 orders). "
        "For each state compute: the order count, the average promised days (purchase to "
        "estimated delivery), the median actual delivery days, the 95th percentile of actual "
        "delivery days, and the current late rate. Then compute a recommended promise equal to "
        "the 95th percentile of actual delivery days, and the difference between that "
        "recommended promise and the current average promised days. Order by that difference "
        "ascending."
    ),
    # The promise is blind to time, not just to place.
    "seasonality": (
        "For delivered orders, group by the year and month of order_purchase_timestamp and show "
        "the number of orders, the average actual delivery days, the average promised days, and "
        "the late rate. Only months with at least 500 orders, ordered chronologically."
    ),
    # Splitting the promise into handling + transit is what makes it attributable.
    "seller_handling": (
        "For each seller with at least 50 delivered items, compute the 95th percentile of seller "
        "handling days (order_approved_at to order_delivered_carrier_date), the median handling "
        "days, and the number of delivered items."
    ),
    "state_transit": (
        "For each customer_state with at least 500 delivered orders, compute the 95th percentile "
        "of carrier transit days (order_delivered_carrier_date to order_delivered_customer_date) "
        "and the median carrier transit days."
    ),
    # Why a broken promise costs anything at all.
    "review_damage": (
        "Bucket delivered orders by how many days late they were versus the estimated delivery "
        "date (early, on time, 1-3 days late, 4-7 days late, 8-15 days late, more than 15 days "
        "late) and for each bucket show the number of orders, the average review score, and the "
        "percentage of reviews that are 1 star."
    ),
    # Falsification: the hypothesis the hackathon guide itself suggested. It is false.
    "churn": (
        "Using OLIST_CUSTOMERS.customer_unique_id as the true person, for customers whose FIRST "
        "order received a given review score (1 to 5), show the review score, the number of such "
        "customers, and the percentage who went on to place another order. Also include the "
        "overall repeat purchase rate across all customers."
    ),
    # Falsification: "a few terrible sellers cause the lateness". Also false — they're big, not bad.
    # We ask CRAFT for the summary statistics directly rather than pulling 462 rows to reduce in
    # Python: the hypothesis turns on four numbers, so ask for four numbers.
    "seller_lateness": (
        "Consider only sellers with at least 50 delivered items. Compute the overall baseline "
        "late rate across all their items, the highest late rate achieved by any single seller, "
        "the number of sellers whose late rate exceeds 40 percent, and separately the combined "
        "late rate of the 30 sellers who have the largest number of late items. Return this as a "
        "single row."
    ),
}
