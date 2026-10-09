def migrate(cr, version):
    """Release quotations locked by the former autosave-based policy."""
    cr.execute(
        """
        UPDATE sale_order
           SET blocked_order = FALSE
         WHERE state IN ('draft', 'sent')
           AND blocked_order IS TRUE
        """
    )
