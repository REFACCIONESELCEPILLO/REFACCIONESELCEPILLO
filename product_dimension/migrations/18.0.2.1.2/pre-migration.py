def migrate(cr, version):
    """Create editable value metadata before loading the updated model."""
    cr.execute("""
        ALTER TABLE product_attribute_value
        ADD COLUMN IF NOT EXISTS component_internal_reference varchar
    """)
    cr.execute("""
        ALTER TABLE product_attribute_value
        ADD COLUMN IF NOT EXISTS component_cost double precision DEFAULT 0.0
    """)
