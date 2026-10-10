def migrate(cr, version):
    """Restore locking for existing back-office quotations and orders."""
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'sale_order'
           AND column_name = 'website_id'
        """
    )
    website_filter = "AND website_id IS NULL" if cr.fetchone() else ""
    cr.execute(
        f"""
        UPDATE sale_order
           SET blocked_order = TRUE
         WHERE state IN ('draft', 'sent', 'sale')
           AND blocked_order IS NOT TRUE
           {website_filter}
        """
    )
