from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_order_paid_at_order_payment_amount_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='shipping_service',
            field=models.CharField(help_text='Paket layanan kurir: REG, YES, OKE, dll', max_length=20, blank=True, default='REG'),
        ),
    ]
