# ICKAB Label Studio 18.0.3.0.1

## Preview QWeb regression fix

The 18.0.3.0.0 preview template mixed Python percent-string formatting with CSS percentage tokens. A style such as `left:%s%;` can be parsed by Python as an additional formatting directive and raise `ValueError: unsupported format character` during QWeb rendering.

18.0.3.0.1 removes dynamic CSS construction from QWeb. Preview styles are computed from validated physical geometry in Python and QWeb only consumes the resulting style strings. This preserves the canonical millimetre geometry while making CSS `%` tokens inert to QWeb formatting.

A regression test now renders the real `ickab_label_studio.report_label_preview` template with circular media, safe margins, text, box and line elements.
