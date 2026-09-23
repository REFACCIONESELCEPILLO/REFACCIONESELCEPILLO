{
    "name": "ICKAB Direct Print",
    "summary": "Cola y configuración de impresión directa para Odoo.sh y on-premise",
    "description": """
ICKAB Direct Print
==================

Infraestructura de impresión directa para Odoo 18 mediante agentes locales.
Permite administrar hosts, impresoras, tipos de papel, perfiles predeterminados
y una cola de trabajos. Direct Print es el único motor de impresión: recibe los PDF
estándar generados por Odoo, tickets, archivos externos y diseños de etiqueta,
y decide cómo enviarlos a la impresora seleccionada según sus capacidades.

Incluye catálogo de compatibilidad de impresoras por fabricante/modelo, con sugerencia
de lenguaje y resolución sin acoplar la lógica a una marca concreta.

El servidor Odoo nunca necesita acceder a la red privada del cliente. El agente
local consulta trabajos mediante HTTPS, por lo que funciona tanto en Odoo.sh
como en instalaciones on-premise.
    """,
    "version": "18.0.3.0.0",
    "category": "Productivity",
    "author": "ICKAB",
    "website": "https://ickab.mx",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "external_dependencies": {"python": ["PIL", "reportlab"]},
    "data": [
        "security/print_security.xml",
        "security/ir.model.access.csv",
        "data/print_sequence.xml",
        "data/print_paper_data.xml",
        "data/print_cron.xml",
        "data/compatibility_profile_data.xml",
        "views/print_branch_views.xml",
        "views/print_user_branch_views.xml",
        "views/print_assignment_views.xml",
        "views/print_host_views.xml",
        "views/ir_actions_report_views.xml",
        "wizard/direct_print_wizard_views.xml",
        "views/print_printer_views.xml",
        "views/print_paper_views.xml",
        "views/print_profile_views.xml",
        "views/print_compatibility_profile_views.xml",
        "views/print_job_views.xml",
        "views/res_users_views.xml",
        "views/res_config_settings_views.xml",
        "views/print_help_views.xml",
        "views/print_menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
