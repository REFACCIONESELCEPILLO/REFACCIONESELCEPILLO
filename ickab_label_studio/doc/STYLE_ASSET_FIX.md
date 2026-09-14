# Style asset isolation - 18.0.2.1.0

The Label Studio backend styles are intentionally distributed as plain CSS,
not SCSS. This prevents the addon from participating in Odoo's Sass compilation
and therefore prevents a Label Studio stylesheet error from invalidating the
whole `web.assets_backend` stylesheet bundle.

All visual selectors are scoped under `.o_ickab_label_studio`.

Notable changes:
- Removed mixed-unit CSS `min()` from SCSS (`min(100%, 800px)`).
- Removed conic-gradient syntax from preprocessed styles.
- Replaced `static/src/scss/label_designer.scss` with
  `static/src/css/label_designer.css`.
- No generic Odoo selectors such as `.o_form_view`, `.o_list_view`, `.btn`,
  `body`, or `:root` are overridden.
