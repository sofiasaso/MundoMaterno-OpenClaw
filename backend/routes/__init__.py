print(">>> ROUTES INIT EJECUTADO")

from .products import router as products_router
from .metrics import router as metrics_router
from .alerts import router as alerts_router
from .scraping import router as scraping_router
