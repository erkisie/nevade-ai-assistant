from datetime import datetime


def create_order_from_cart(cart_products):
    if cart_products is None or len(cart_products) == 0:
        return None

    total_price = 0

    order_items = []

    for _, row in cart_products.iterrows():
        price = float(row.get("price", 0))
        total_price += price

        order_items.append({
            "product_id": str(row.get("product_id", "")),
            "product_name": row.get("product_name", ""),
            "brand": row.get("brand", ""),
            "price": price
        })

    order_id = "ORD-" + datetime.now().strftime("%H%M%S")

    order = {
        "order_id": order_id,
        "status": "Hazırlanıyor",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estimated_delivery": "2 iş günü",
        "total_price": total_price,
        "installment_months": 6,
        "monthly_installment": round(total_price / 6, 2),
        "items": order_items
    }

    return order


def get_latest_order(orders):
    if orders is None or len(orders) == 0:
        return None

    return orders[-1]


def get_order_status_message(order):
    if order is None:
        return (
            "Henüz oluşturulmuş bir sipariş bulunmuyor. "
            "Sepete ürün ekleyip sipariş oluşturduktan sonra sipariş durumunu buradan takip edebilirsiniz."
        )

    return (
        f"Son siparişiniz {order['order_id']} numarasıyla {order['status']} durumunda görünüyor. "
        f"Tahmini teslimat süresi {order['estimated_delivery']}. "
        f"Sipariş toplamı {order['total_price']:.0f} TL, peşin fiyatına 6 taksit seçeneğiyle "
        f"aylık {order['monthly_installment']:.0f} TL olarak görüntülenebilir."
    )