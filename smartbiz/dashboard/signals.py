from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement, StockAlert

@receiver(post_save, sender=StockMovement)
def update_stock(sender, instance, created, **kwargs):
    if not created:
        return

    product = instance.product

    if instance.movement_type == StockMovement.MOVEMENT_IN:
        product.stock += instance.quantity
    elif instance.movement_type == StockMovement.MOVEMENT_OUT:
        product.stock -= instance.quantity

    product.save()

    if product.stock <= product.low_stock_threshold:
        StockAlert.objects.create(
            product=product,
            message=f"{product.name} is low on stock: {product.stock} remaining"
        )