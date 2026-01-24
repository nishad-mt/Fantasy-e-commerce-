from django.db import migrations


def forwards_func(apps, schema_editor):
    Order = apps.get_model("order", "Order")

    # Convert old online methods to ONLINE
    Order.objects.filter(
        payment_method__in=["UPI", "CARD"]
    ).update(
        payment_method="ONLINE"
    )


def reverse_func(apps, schema_editor):
    # Cannot reliably reverse ONLINE back to UPI/CARD
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0016_alter_order_payment_method"),  
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
