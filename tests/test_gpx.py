import ephem
import geosar
import geosar.settings as s
import pytest


@pytest.fixture
def mission(shared_datadir):
    file = shared_datadir / 'VA.gpx'
    return geosar.GPX(file)

def test_repr(mission):
    for chunk in ['<geosar.GPX(', 'gpx_file=', 'VA.gpx', ')>']:
        assert chunk in repr(mission)

def test_reads_file(mission, shared_datadir):
    file = shared_datadir / 'VA.gpx'
    assert mission._gpx_file == file


def test_can_access_gpxpy_attributes(mission):
    assert len(mission.waypoints) == 4
    assert len(mission.tracks) == 6


def test_tract_data_filters_time(mission):
    assert len(mission.track_data(time=None).id.unique()) == 6
    assert len(mission.track_data(time=True).id.unique()) == 4
    assert len(mission.track_data(time=False).id.unique()) == 2


def test_observer_in_middle(mission):
    wpts = {
        wpt.name: wpt
        for wpt in mission.waypoints
    }
    lat = mission.observer.lat / ephem.degree
    lon = mission.observer.lon / ephem.degree
    assert lat > wpts['RIC'].latitude
    assert lat < wpts['Henrico'].latitude
    assert lon > wpts['BASE'].longitude
    assert lon < wpts['RIC'].longitude


def test_phase_of_day(mission):
    expected = [
        {'start_phase': s.PLANS, 'end_phase': s.PLANS, 'name': 'Base to RIC'},
        {'start_phase': s.PLANS, 'end_phase': s.PLANS, 'name': 'RVA to Henrico'},
        {'start_phase': s.NIGHT, 'end_phase': s.NIGHT, 'name': 'RVA to RIC'},
        {'start_phase': s.SHINE, 'end_phase': s.SHINE, 'name': 'RIC to Henrico'},
        {'start_phase': s.ASTRO, 'end_phase': s.SHINE, 'name': 'Henrico to VDEM'},
        {'start_phase': s.CIVIL, 'end_phase': s.NIGHT, 'name': 'VEDM to RVA'},
    ]
    result = (
        mission
        .track_data()
        .groupby('id')
        .first()
        [['name', 'start_phase', 'end_phase']]
        .to_dict(orient='records')
    )
    assert result == expected
