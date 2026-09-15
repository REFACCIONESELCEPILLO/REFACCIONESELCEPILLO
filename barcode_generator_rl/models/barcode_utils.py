# -*- coding: utf-8 -*-
"""Shared constants and helpers for barcode generation."""

BARCODE_SELECTION_MAP = [
    ('ean13', 'EAN-13'),
    ('upca', 'UPC-A'),
    ('code128', 'Code 128'),
    ('GS1_128', 'GS1-128'),
    ('ean8', 'EAN-8'),
    ('isbn', 'ISBN'),
    ('issn', 'ISSN'),
    ('code39', 'Code 39'),
]

BARCODE_TYPE_MAP = {
    'ean13': 'ean13',
    'upca': 'upca',
    'code128': 'code128',
    'GS1_128': 'gs1_128',
    'ean8': 'ean8',
    'isbn': 'ean13',
    'issn': 'ean13',
    'code39': 'code39',
}

CONFIG_BARCODE_SELECTION_MAP = [
    ('code128', 'Code 128'),
    ('ean13', 'EAN-13'),
    ('upca', 'UPC-A'),
    ('ean8', 'EAN-8'),
    ('code39', 'Code 39'),
    ('GS1_128', 'GS1-128'),
]

CHECKSUM_TYPES = {'ean13', 'upca', 'ean8', 'isbn', 'issn'}


def calculate_ean13_checksum(payload):
    """Return EAN-13 checksum for a 12-digit payload iterable."""
    digits = [int(x) for x in payload]
    if len(digits) != 12:
        raise ValueError('EAN-13 payload must contain 12 digits.')
    total = sum(d if i % 2 == 0 else d * 3 for i, d in enumerate(digits))
    return (10 - (total % 10)) % 10


def calculate_ean8_checksum(payload):
    """Return EAN-8 checksum for a 7-digit payload iterable."""
    digits = [int(x) for x in payload]
    if len(digits) != 7:
        raise ValueError('EAN-8 payload must contain 7 digits.')
    total = sum(d * 3 if i % 2 == 0 else d for i, d in enumerate(digits))
    return (10 - (total % 10)) % 10


def calculate_upca_checksum(payload):
    """Return UPC-A checksum for an 11-digit payload string."""
    code = ''.join(str(x) for x in payload)
    if len(code) != 11 or not code.isdigit():
        raise ValueError('UPC-A payload must contain 11 digits.')
    odd_sum = sum(int(code[i]) for i in range(0, 11, 2))
    even_sum = sum(int(code[i]) for i in range(1, 11, 2))
    total = (odd_sum * 3) + even_sum
    return (10 - (total % 10)) % 10


def standard_total_length(barcode_type, code128_length=13):
    """Total printed length used by the structured internal generator."""
    if barcode_type in ('ean13', 'isbn', 'issn'):
        return 13
    if barcode_type == 'upca':
        return 12
    if barcode_type == 'ean8':
        return 8
    return code128_length


def payload_length(barcode_type, code128_length=13):
    total = standard_total_length(barcode_type, code128_length)
    return total - 1 if barcode_type in CHECKSUM_TYPES else total
