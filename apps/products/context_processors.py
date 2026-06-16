from .models import Category, Brand

def categories_processor(request):
    """
    Supplies all root categories and brands globally to the templates context.
    """
    root_categories = Category.objects.filter(parent_category__isnull=True).prefetch_related('subcategories')
    brands = Brand.objects.all().order_by('name')
    return {
        'global_categories': root_categories,
        'global_brands': brands
    }
