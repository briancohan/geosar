import geosar.settings


def test_mapbox_token_set():
    assert geosar.settings.MAPBOX is not None
