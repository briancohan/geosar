from pathlib import Path
from typing import Optional
import datetime
import ephem
import gpxpy
import numpy as np
import pandas as pd
import geosar.settings as s

day = datetime.timedelta(days=1)
sun = ephem.Sun()


class GPX:

    def __init__(self, gpx_file: Path):
        self._gpx_file = gpx_file
        self._gpx_data = gpxpy.parse(gpx_file.read_text())
        self.observer = self._observer_init()
        self.start_date = self.get_time_bounds().start_time.date()
        self.end_date = self.get_time_bounds().end_time.date()

    def __repr__(self):
        return f'<geosar.GPX(gpx_file="{self._gpx_file}")>'

    def __getattr__(self, item):
        return getattr(self._gpx_data, item)

    def _observer_init(self) -> ephem.Observer:
        """PyEphem Observer.

        Observer location is based on the median value for latitude and
        longitude. This reduces the impact of individual tracks that
        may not have been cleared before arriving on scene. This also
        avoids making assumptions about specific waypoints being included
        or picking a start or end point from a specific track.

        :return:
            ephem.Observer
        """
        obs = ephem.Observer()
        pts = np.array([
            (p[0].latitude, p[0].longitude)
            for p in self.walk()
        ])
        mid_lat, mid_lon = np.median(pts, axis=0)
        obs.lat, obs.lon = str(mid_lat), str(mid_lon)
        obs.date = self.get_time_bounds().start_time
        return obs

    def track_data(self, time: Optional[bool] = None) -> pd.DataFrame:
        """DataFrame containing all tracks.

        :param time:
            Boolean. Indicate which records are desired.
            'None' -> All records are returned
            'True' -> Only records with timestamp information are returned
            'False' -> Only records without timestamp information are returned
        :return:
            pandas.DataFrame
        """
        df = pd.concat([
            self._parse_track(track, index)
            for index, track in enumerate(self.tracks)
        ])
        df = self._expand_time_info(df)
        if time is None:
            return df
        elif time:
            return df.loc[~df.utc.isnull()]
        else:
            return df.loc[df.utc.isnull()]

    @staticmethod
    def _parse_track(track: gpxpy.gpx.GPXTrack, index: int) -> pd.DataFrame:
        """Convert track into a DataFrame.

        time is renamed to utc to make it clear that it is not the local time.
        This is important for self._expand_time_info.

        :param track:
            gpxpy.GPXTrack. Position and time information is pulled from each track point.
            Track name and description are included in all records
        :param index:
            sequential number to prevent merging tracks with the same name.
        :return:
            pandas.DataFrame
        """
        trkpt_vars = ['latitude', 'longitude', 'time']

        df = pd.DataFrame([
            {
                var: getattr(point, var, None)
                for var in trkpt_vars
            }
            for segment in track.segments
            for point in segment.points
        ])
        df['id'] = index
        for var in ['name', 'description']:
            df[var] = getattr(track, var)

        return df.rename(columns={'time': 'utc'})

    def _expand_time_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """Expands timestamp information into parts for utc and local times.

        UTC is maintained to avoid conversion efforts with PyEphem. Records
        are split into date and time components to facilitate identifying
        which times are day, night, or a twilight mode. Local times are used
        for display.

        :param df:
            DataFrame containing a column that has a column 'utc'. This column
            should only contain timestamp strings or None which will be
            converted to NaT.
        :return:
            pandas.DataFrame
        """
        df['utc'] = pd.to_datetime(df.utc, errors='coerce')
        df['utc'] = df.utc.dt.tz_convert('UTC')
        df['utc_date'] = pd.to_datetime(df.utc.dt.date, errors='coerce')
        df['utc_time'] = df.utc.dt.time

        df['local'] = df.utc.dt.tz_convert(s.TIMEZONE)
        df['date'] = pd.to_datetime(df.local.dt.date, errors='coerce')
        df['time'] = df.local.dt.time

        df['phase'] = s.PLANS
        df.loc[~df.utc.isnull(), 'phase'] = s.NIGHT
        for event in self.sun_events.itertuples():
            df.loc[df.utc >= event.datetime, 'phase'] = event.phase

        df = df.merge(
            df[['id', 'phase']]
            .groupby('id')
            .first()
            .reset_index()
            .rename(columns={'phase': 'start_phase'}),
            on='id'
        ).merge(
            df[['id', 'phase']]
            .groupby('id')
            .last()
            .reset_index()
            .rename(columns={'phase': 'end_phase'}),
            on='id'
        )
        return df

    def _sun_event(self, horizon, phase):
        self.observer.horizon = horizon
        return {
            'phase': phase,
            'rise': self.observer.previous_rising(sun).datetime(),
            'set': self.observer.next_setting(sun).datetime(),
        }

    @property
    def sun_events(self):
        times = []
        phases = (
            (s.ASTRO, s.ASTRO_HORIZ),
            (s.NAUTI, s.NAUTI_HORIZ),
            (s.CIVIL, s.CIVIL_HORIZ),
            (s.SHINE, s.SHINE_HORIZ),
        )
        for d in range(int((self.end_date - self.start_date) / day) + 1):
            self.observer.date = datetime.datetime.combine(
                self.start_date + (day * d),
                datetime.time(12, 0),
            )
            for phase, horizon in phases:
                times.append(self._sun_event(horizon, phase))

        times = (
            pd.DataFrame(times)
            .melt(
                id_vars=['phase'],
                var_name='direction',
                value_name='datetime',
            )
            .sort_values('datetime')
            .reset_index(drop=True)
        )

        setting_shifts = (
            (s.ASTRO, s.NIGHT),
            (s.NAUTI, s.ASTRO),
            (s.CIVIL, s.NAUTI),
            (s.SHINE, s.CIVIL),
        )
        for _from, _to in setting_shifts:
            times.loc[(times.direction == 'set') & (times.phase == _from), 'phase'] = _to

        times['datetime'] = times.datetime.dt.tz_localize('UTC')
        return times
