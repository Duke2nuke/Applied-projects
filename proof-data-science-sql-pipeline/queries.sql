-- Revenue by product category (join + aggregation)
SELECT p.category AS category,
       COUNT(*) AS n_orders,
       ROUND(SUM(o.quantity * p.unit_price), 2) AS revenue
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY p.category
ORDER BY revenue DESC;

-- Top 5 customers by spend (join + aggregation + ordering)
SELECT c.name AS customer,
       c.city AS city,
       COUNT(*) AS n_orders,
       ROUND(SUM(o.quantity * p.unit_price), 2) AS total_spent
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_id = o.product_id
GROUP BY c.customer_id
ORDER BY total_spent DESC
LIMIT 5;

-- Average order value by city
SELECT c.city AS city,
       COUNT(*) AS n_orders,
       ROUND(AVG(o.quantity * p.unit_price), 2) AS avg_order_value
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p ON p.product_id = o.product_id
GROUP BY c.city
ORDER BY avg_order_value DESC;
