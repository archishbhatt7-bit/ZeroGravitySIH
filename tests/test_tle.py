"""Tests for TLE parsing."""

import pytest

from zerogravity.core.tle import TLE, parse_tle

# ISS (ZARYA) TLE — a well-known reference
ISS_NAME = "ISS (ZARYA)"
ISS_LINE1 = "1 25544U 98067A   24045.54896019  .00016717  00000-0  30093-3 0  9993"
ISS_LINE2 = "2 25544  51.6412 207.4925 0004948 290.5508 178.9792 15.49583488439596"


class TestTLEFromLines:
    def test_parse_basic(self) -> None:
        tle = TLE.from_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)
        assert tle.norad_id == 25544
        assert tle.name == ISS_NAME

    def test_orbital_elements_reasonable(self) -> None:
        tle = TLE.from_lines(ISS_LINE1, ISS_LINE2)
        assert 51.0 < tle.inclination_deg < 52.0
        assert 0.0 < tle.eccentricity < 0.01
        assert 15.0 < tle.mean_motion_rev_per_day < 16.0

    def test_epoch_parsed(self) -> None:
        tle = TLE.from_lines(ISS_LINE1, ISS_LINE2)
        assert tle.epoch.year == 2024
        assert tle.epoch.month == 2  # day 45 ~ Feb 14

    def test_bstar(self) -> None:
        tle = TLE.from_lines(ISS_LINE1, ISS_LINE2)
        assert abs(tle.bstar - 3.0093e-4) < 1e-7

    def test_satrec_available(self) -> None:
        tle = TLE.from_lines(ISS_LINE1, ISS_LINE2)
        assert tle.satrec is not None

    def test_str_roundtrip(self) -> None:
        tle = TLE.from_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)
        text = str(tle)
        assert ISS_LINE1 in text
        assert ISS_LINE2 in text
        assert ISS_NAME in text

    def test_invalid_line1_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid TLE line 1"):
            TLE.from_lines("garbage", ISS_LINE2)

    def test_invalid_line2_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid TLE line 2"):
            TLE.from_lines(ISS_LINE1, "garbage")


class TestParseTLE:
    def test_two_line_format(self) -> None:
        text = f"{ISS_LINE1}\n{ISS_LINE2}"
        tles = parse_tle(text)
        assert len(tles) == 1
        assert tles[0].norad_id == 25544

    def test_three_line_format(self) -> None:
        text = f"{ISS_NAME}\n{ISS_LINE1}\n{ISS_LINE2}"
        tles = parse_tle(text)
        assert len(tles) == 1
        assert tles[0].name == ISS_NAME

    def test_multiple_tles(self) -> None:
        text = f"{ISS_NAME}\n{ISS_LINE1}\n{ISS_LINE2}\n{ISS_LINE1}\n{ISS_LINE2}"
        tles = parse_tle(text)
        assert len(tles) == 2
