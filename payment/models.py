from django.db import models
from order.models import Order

class Payment(models.Model):
    txn_id = models.CharField(max_length=100, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    method = models.CharField(max_length=20)  
    status = models.CharField(max_length=20)  
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.txn_id
