def clear_coupon(order):
    if order.coupon or order.discount_amount > 0:
        order.coupon = None
        order.discount_amount = 0
        order.discount_type = None
        order.save(update_fields=[
            "coupon",
            "discount_amount",
            "discount_type"
        ])
