from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement, StockAlert

@receiver(post_save, sender=StockMovement)
def update_stock(sender, instance, created, **kwargs):
    if not created:
        return

    product = instance.product
    previous_stock = product.stock_quantity

    if instance.movement_type == StockMovement.MOVEMENT_IN:
        product.stock_quantity += instance.quantity
    elif instance.movement_type == StockMovement.MOVEMENT_OUT:
        product.stock_quantity -= instance.quantity

    product.save(update_fields=['stock_quantity'])

    current_stock = product.stock_quantity

    if current_stock <= 0:
        StockAlert.objects.create(
            product=product,
            message=f"{product.name} is out of stock."
        )
        return

    if current_stock <= product.low_stock_threshold and previous_stock > product.low_stock_threshold:
        StockAlert.objects.create(
            product=product,
            message=f"{product.name} is low on stock: {current_stock} remaining."
        )
        return

    if (
        instance.movement_type == StockMovement.MOVEMENT_IN
        and previous_stock <= product.low_stock_threshold
        and current_stock > product.low_stock_threshold
    ):
        StockAlert.objects.create(
            product=product,
            message=f"{product.name} has been restocked to {current_stock} units."
        )
