from django.db import migrations


def normalize_status(apps, schema_editor):
    Order = apps.get_model("order", "Order")

    Order.objects.filter(
        status="PENDING",
        payment_status="PENDING"
    ).update(status="PENDING_PAYMENT")


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0025_alter_order_address_alter_order_payment_method_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_status),
    ]
