import pathlib
import pytest


@pytest.mark.parametrize(
    'file_path,expected_barcode',
    [
        (pathlib.Path('12345677890.mp4'), '5677890'),
        (pathlib.Path('12346677890.mov'), '6677890'),
    ]
)
def test_getBarcode(file_path, expected_barcode):
    import transcodeEngine
    assert transcodeEngine.getBarcode(str(file_path)) == expected_barcode

