from platinum.core.types import type_abbreviation, format_types, strip_ansi

def test_type_abbreviations_primary():
    assert type_abbreviation('fire') == 'FIR'
    assert type_abbreviation('ground') == 'GRN'


def test_format_types_dual():
    out = format_types(('fire','flying'))
    plain = strip_ansi(out)
    assert plain == 'FIR/FLY'
