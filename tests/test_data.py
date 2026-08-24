"""Tests for data ingestion: CDM parsing and Space-Track client."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from zerogravity.data.cdm import CDM, CDMObject
from zerogravity.data.spacetrack import SpaceTrackClient


# Realistic CDM test fixture in KVN format (CCSDS 508.0-B-1)
SAMPLE_CDM_KVN = """CCSDS_CDM_VERS               = 1.0
CREATION_DATE                = 2024-02-14T12:00:00.000
ORIGINATOR                   = JSPOC
MESSAGE_FOR                  = SATELLITE_A_OWNER
MESSAGE_ID                   = 25544_conj_48274_20240214_120000

COMMENT  Screening Information
TCA                          = 2024-02-15T08:30:15.555
MISS_DISTANCE                = 0.523 [km]
RELATIVE_SPEED               = 14.234 [km/s]
RELATIVE_POSITION_R          = 0.412 [km]
RELATIVE_POSITION_T          = 0.201 [km]
RELATIVE_POSITION_N          = 0.231 [km]
RELATIVE_VELOCITY_R          = 10.340 [km/s]
RELATIVE_VELOCITY_T          = 8.120 [km/s]
RELATIVE_VELOCITY_N          = 5.890 [km/s]

COMMENT  Probability Information
COLLISION_PROBABILITY         = 1.23e-05
COLLISION_PROBABILITY_METHOD  = FOSTER-1992

OBJECT                       = OBJECT1
OBJECT_DESIGNATOR            = 25544
CATALOG_NAME                 = SATCAT
OBJECT_NAME                  = ISS (ZARYA)
INTERNATIONAL_DESIGNATOR     = 1998-067A
OBJECT_TYPE                  = PAYLOAD
OPERATOR_CONTACT_POSITION    = FLIGHT_DIRECTOR
OPERATOR_ORGANIZATION        = NASA
EPHEMERIS_NAME               = NONE
COVARIANCE_METHOD            = CALCULATED
MANEUVERABLE                 = YES
ORBIT_CENTER                 = EARTH
REF_FRAME                    = ITRF
GRAVITY_MODEL                = EGM-96: 36D 36O
ATMOSPHERIC_MODEL            = JACCHIA 70 DCA
N_BODY_PERTURBATIONS         = MOON, SUN
SOLAR_RAD_PRESSURE           = YES
EARTH_TIDES                  = YES
INTRACK_THRUST               = NO

COMMENT  State Vector
X                            = 2345.678 [km]
Y                            = 4567.890 [km]
Z                            = 3456.789 [km]
X_DOT                        = 5.123 [km/s]
Y_DOT                        = 4.567 [km/s]
Z_DOT                        = 2.345 [km/s]

COMMENT  Covariance Matrix (RTN frame, lower-triangular)
CR_R                         = 44.0 [m**2]
CT_R                         = 0.5 [m**2]
CT_T                         = 2.4 [m**2]
CN_R                         = -0.3 [m**2]
CN_T                         = 0.1 [m**2]
CN_N                         = 7.2 [m**2]
CRDOT_R                      = 0.001 [m**2/s]
CRDOT_T                      = 0.002 [m**2/s]
CRDOT_N                      = -0.001 [m**2/s]
CRDOT_RDOT                   = 0.000015 [m**2/s**2]
CTDOT_R                      = 0.003 [m**2/s]
CTDOT_T                      = 0.004 [m**2/s]
CTDOT_N                      = 0.001 [m**2/s]
CTDOT_RDOT                   = 0.000020 [m**2/s**2]
CTDOT_TDOT                   = 0.000025 [m**2/s**2]
CNDOT_R                      = -0.002 [m**2/s]
CNDOT_T                      = 0.001 [m**2/s]
CNDOT_N                      = 0.002 [m**2/s]
CNDOT_RDOT                   = -0.000010 [m**2/s**2]
CNDOT_TDOT                   = 0.000012 [m**2/s**2]
CNDOT_NDOT                   = 0.000018 [m**2/s**2]

OBJECT                       = OBJECT2
OBJECT_DESIGNATOR            = 48274
CATALOG_NAME                 = SATCAT
OBJECT_NAME                  = COSMOS 2251 DEB
INTERNATIONAL_DESIGNATOR     = 1993-036JKL
OBJECT_TYPE                  = DEBRIS
OPERATOR_CONTACT_POSITION    = UNKNOWN
OPERATOR_ORGANIZATION        = UNKNOWN
EPHEMERIS_NAME               = NONE
COVARIANCE_METHOD            = CALCULATED
MANEUVERABLE                 = NO
ORBIT_CENTER                 = EARTH
REF_FRAME                    = ITRF
GRAVITY_MODEL                = EGM-96: 36D 36O
ATMOSPHERIC_MODEL            = JACCHIA 70 DCA
N_BODY_PERTURBATIONS         = MOON, SUN
SOLAR_RAD_PRESSURE           = YES
EARTH_TIDES                  = YES
INTRACK_THRUST               = NO

COMMENT  State Vector
X                            = 2345.156 [km]
Y                            = 4567.412 [km]
Z                            = 3456.558 [km]
X_DOT                        = -4.856 [km/s]
Y_DOT                        = -3.987 [km/s]
Z_DOT                        = -2.123 [km/s]

COMMENT  Covariance Matrix (RTN frame, lower-triangular)
CR_R                         = 120.5 [m**2]
CT_R                         = 1.8 [m**2]
CT_T                         = 8.9 [m**2]
CN_R                         = -1.2 [m**2]
CN_T                         = 0.6 [m**2]
CN_N                         = 15.3 [m**2]
CRDOT_R                      = 0.005 [m**2/s]
CRDOT_T                      = 0.008 [m**2/s]
CRDOT_N                      = -0.004 [m**2/s]
CRDOT_RDOT                   = 0.000045 [m**2/s**2]
CTDOT_R                      = 0.012 [m**2/s]
CTDOT_T                      = 0.015 [m**2/s]
CTDOT_N                      = 0.003 [m**2/s]
CTDOT_RDOT                   = 0.000062 [m**2/s**2]
CTDOT_TDOT                   = 0.000078 [m**2/s**2]
CNDOT_R                      = -0.007 [m**2/s]
CNDOT_T                      = 0.004 [m**2/s]
CNDOT_N                      = 0.009 [m**2/s]
CNDOT_RDOT                   = -0.000035 [m**2/s**2]
CNDOT_TDOT                   = 0.000041 [m**2/s**2]
CNDOT_NDOT                   = 0.000052 [m**2/s**2]
"""

# Simple XML CDM for testing
SAMPLE_CDM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<cdm xmlns="http://www.ccsds.org/schema/ndm/cdm">
  <header>
    <CCSDS_CDM_VERS>1.0</CCSDS_CDM_VERS>
    <CREATION_DATE>2024-02-14T12:00:00.000</CREATION_DATE>
    <ORIGINATOR>JSPOC</ORIGINATOR>
    <MESSAGE_ID>25544_conj_48274_20240214_120000</MESSAGE_ID>
  </header>
  <body>
    <relativeMetadataData>
      <TCA>2024-02-15T08:30:15.555</TCA>
      <MISS_DISTANCE>0.523</MISS_DISTANCE>
      <RELATIVE_SPEED>14.234</RELATIVE_SPEED>
      <COLLISION_PROBABILITY>1.23e-05</COLLISION_PROBABILITY>
    </relativeMetadataData>
    <segment>
      <metadata>
        <OBJECT_DESIGNATOR>25544</OBJECT_DESIGNATOR>
        <OBJECT_NAME>ISS (ZARYA)</OBJECT_NAME>
        <INTERNATIONAL_DESIGNATOR>1998-067A</INTERNATIONAL_DESIGNATOR>
        <EPHEMERIS_NAME>NONE</EPHEMERIS_NAME>
        <COVARIANCE_METHOD>CALCULATED</COVARIANCE_METHOD>
        <MANEUVERABLE>YES</MANEUVERABLE>
      </metadata>
      <data>
        <stateVector>
          <X>2345.678</X>
          <Y>4567.890</Y>
          <Z>3456.789</Z>
          <X_DOT>5.123</X_DOT>
          <Y_DOT>4.567</Y_DOT>
          <Z_DOT>2.345</Z_DOT>
        </stateVector>
        <covarianceMatrix>
          <CR_R>44.0</CR_R>
          <CT_R>0.5</CT_R>
          <CT_T>2.4</CT_T>
          <CN_R>-0.3</CN_R>
          <CN_T>0.1</CN_T>
          <CN_N>7.2</CN_N>
          <CRDOT_R>0.001</CRDOT_R>
          <CRDOT_T>0.002</CRDOT_T>
          <CRDOT_N>-0.001</CRDOT_N>
          <CRDOT_RDOT>0.000015</CRDOT_RDOT>
          <CTDOT_R>0.003</CTDOT_R>
          <CTDOT_T>0.004</CTDOT_T>
          <CTDOT_N>0.001</CTDOT_N>
          <CTDOT_RDOT>0.000020</CTDOT_RDOT>
          <CTDOT_TDOT>0.000025</CTDOT_TDOT>
          <CNDOT_R>-0.002</CNDOT_R>
          <CNDOT_T>0.001</CNDOT_T>
          <CNDOT_N>0.002</CNDOT_N>
          <CNDOT_RDOT>-0.000010</CNDOT_RDOT>
          <CNDOT_TDOT>0.000012</CNDOT_TDOT>
          <CNDOT_NDOT>0.000018</CNDOT_NDOT>
        </covarianceMatrix>
      </data>
    </segment>
    <segment>
      <metadata>
        <OBJECT_DESIGNATOR>48274</OBJECT_DESIGNATOR>
        <OBJECT_NAME>COSMOS 2251 DEB</OBJECT_NAME>
        <INTERNATIONAL_DESIGNATOR>1993-036JKL</INTERNATIONAL_DESIGNATOR>
        <EPHEMERIS_NAME>NONE</EPHEMERIS_NAME>
        <COVARIANCE_METHOD>CALCULATED</COVARIANCE_METHOD>
        <MANEUVERABLE>NO</MANEUVERABLE>
      </metadata>
      <data>
        <stateVector>
          <X>2345.156</X>
          <Y>4567.412</Y>
          <Z>3456.558</Z>
          <X_DOT>-4.856</X_DOT>
          <Y_DOT>-3.987</Y_DOT>
          <Z_DOT>-2.123</Z_DOT>
        </stateVector>
        <covarianceMatrix>
          <CR_R>120.5</CR_R>
          <CT_R>1.8</CT_R>
          <CT_T>8.9</CT_T>
          <CN_R>-1.2</CN_R>
          <CN_T>0.6</CN_T>
          <CN_N>15.3</CN_N>
          <CRDOT_R>0.005</CRDOT_R>
          <CRDOT_T>0.008</CRDOT_T>
          <CRDOT_N>-0.004</CRDOT_N>
          <CRDOT_RDOT>0.000045</CRDOT_RDOT>
          <CTDOT_R>0.012</CTDOT_R>
          <CTDOT_T>0.015</CTDOT_T>
          <CTDOT_N>0.003</CTDOT_N>
          <CTDOT_RDOT>0.000062</CTDOT_RDOT>
          <CTDOT_TDOT>0.000078</CTDOT_TDOT>
          <CNDOT_R>-0.007</CNDOT_R>
          <CNDOT_T>0.004</CNDOT_T>
          <CNDOT_N>0.009</CNDOT_N>
          <CNDOT_RDOT>-0.000035</CNDOT_RDOT>
          <CNDOT_TDOT>0.000041</CNDOT_TDOT>
          <CNDOT_NDOT>0.000052</CNDOT_NDOT>
        </covarianceMatrix>
      </data>
    </segment>
  </body>
</cdm>
"""


def test_cdm_kvn_parsing():
    """Test CDM KVN parsing with realistic fixture."""
    cdm = CDM.from_kvn(SAMPLE_CDM_KVN)
    
    # Check header fields
    assert cdm.ccsds_cdm_vers == "1.0"
    assert cdm.originator == "JSPOC"
    assert cdm.message_id == "25544_conj_48274_20240214_120000"
    
    # Check datetime parsing
    assert cdm.creation_date == datetime(2024, 2, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert cdm.tca == datetime(2024, 2, 15, 8, 30, 15, 555000, tzinfo=timezone.utc)
    
    # Check screening metrics
    assert cdm.miss_distance_km == 0.523
    assert cdm.relative_speed_km_s == 14.234
    assert cdm.collision_probability == pytest.approx(1.23e-05)
    
    # Check object 1 (ISS)
    assert cdm.object1.designator == "25544"
    assert cdm.object1.name == "ISS (ZARYA)"
    assert cdm.object1.international_designator == "1998-067A"
    assert cdm.object1.maneuverable == "YES"
    assert cdm.object1.covariance_method == "CALCULATED"
    
    # Check object 1 state vector
    assert cdm.object1.x_km == pytest.approx(2345.678)
    assert cdm.object1.y_km == pytest.approx(4567.890)
    assert cdm.object1.z_km == pytest.approx(3456.789)
    assert cdm.object1.x_dot_km_s == pytest.approx(5.123)
    assert cdm.object1.y_dot_km_s == pytest.approx(4.567)
    assert cdm.object1.z_dot_km_s == pytest.approx(2.345)
    
    # Check object 2 (debris)
    assert cdm.object2.designator == "48274"
    assert cdm.object2.name == "COSMOS 2251 DEB"
    assert cdm.object2.international_designator == "1993-036JKL"
    assert cdm.object2.maneuverable == "NO"
    
    # Check object 2 state vector
    assert cdm.object2.x_km == pytest.approx(2345.156)
    assert cdm.object2.y_km == pytest.approx(4567.412)
    assert cdm.object2.z_km == pytest.approx(3456.558)
    assert cdm.object2.x_dot_km_s == pytest.approx(-4.856)
    assert cdm.object2.y_dot_km_s == pytest.approx(-3.987)
    assert cdm.object2.z_dot_km_s == pytest.approx(-2.123)


def test_cdm_covariance_matrix():
    """Test covariance matrix construction and symmetry."""
    cdm = CDM.from_kvn(SAMPLE_CDM_KVN)
    
    # Check that covariance matrices exist
    assert cdm.object1.covariance is not None
    assert cdm.object2.covariance is not None
    
    # Check shape
    assert cdm.object1.covariance.shape == (6, 6)
    assert cdm.object2.covariance.shape == (6, 6)
    
    # Check symmetry
    cov1 = cdm.object1.covariance
    assert np.allclose(cov1, cov1.T), "Object 1 covariance must be symmetric"
    
    cov2 = cdm.object2.covariance
    assert np.allclose(cov2, cov2.T), "Object 2 covariance must be symmetric"
    
    # Check specific values (diagonal and a few off-diagonal)
    # Object 1
    assert cov1[0, 0] == pytest.approx(44.0)  # CR_R
    assert cov1[1, 1] == pytest.approx(2.4)   # CT_T
    assert cov1[2, 2] == pytest.approx(7.2)   # CN_N
    assert cov1[3, 3] == pytest.approx(0.000015)  # CRDOT_RDOT
    assert cov1[1, 0] == pytest.approx(0.5)   # CT_R
    assert cov1[0, 1] == pytest.approx(0.5)   # Symmetric
    assert cov1[2, 1] == pytest.approx(0.1)   # CN_T
    assert cov1[1, 2] == pytest.approx(0.1)   # Symmetric
    
    # Object 2
    assert cov2[0, 0] == pytest.approx(120.5)  # CR_R
    assert cov2[1, 1] == pytest.approx(8.9)    # CT_T
    assert cov2[2, 2] == pytest.approx(15.3)   # CN_N
    assert cov2[5, 5] == pytest.approx(0.000052)  # CNDOT_NDOT


def test_cdm_xml_parsing():
    """Test CDM XML parsing."""
    cdm = CDM.from_xml(SAMPLE_CDM_XML)
    
    # Check header
    assert cdm.ccsds_cdm_vers == "1.0"
    assert cdm.originator == "JSPOC"
    assert cdm.message_id == "25544_conj_48274_20240214_120000"
    assert cdm.tca == datetime(2024, 2, 15, 8, 30, 15, 555000, tzinfo=timezone.utc)
    
    # Check screening metrics
    assert cdm.miss_distance_km == pytest.approx(0.523)
    assert cdm.relative_speed_km_s == pytest.approx(14.234)
    assert cdm.collision_probability == pytest.approx(1.23e-05)
    
    # Check objects
    assert cdm.object1.designator == "25544"
    assert cdm.object1.name == "ISS (ZARYA)"
    assert cdm.object2.designator == "48274"
    assert cdm.object2.name == "COSMOS 2251 DEB"
    
    # Check covariance exists and is symmetric
    assert cdm.object1.covariance is not None
    assert cdm.object1.covariance.shape == (6, 6)
    assert np.allclose(cdm.object1.covariance, cdm.object1.covariance.T)


def test_cdm_missing_collision_probability():
    """Test CDM parsing when collision_probability is absent."""
    cdm_text = """CCSDS_CDM_VERS               = 1.0
CREATION_DATE                = 2024-02-14T12:00:00.000
ORIGINATOR                   = JSPOC
MESSAGE_ID                   = TEST_NO_PROB
TCA                          = 2024-02-15T08:30:15.555
MISS_DISTANCE                = 0.523
RELATIVE_SPEED               = 14.234

OBJECT                       = OBJECT1
OBJECT_DESIGNATOR            = 25544
OBJECT_NAME                  = TEST_SAT_1
INTERNATIONAL_DESIGNATOR     = 1998-067A
EPHEMERIS_NAME               = NONE
COVARIANCE_METHOD            = CALCULATED
MANEUVERABLE                 = YES
X                            = 2345.678
Y                            = 4567.890
Z                            = 3456.789
X_DOT                        = 5.123
Y_DOT                        = 4.567
Z_DOT                        = 2.345

OBJECT                       = OBJECT2
OBJECT_DESIGNATOR            = 48274
OBJECT_NAME                  = TEST_SAT_2
INTERNATIONAL_DESIGNATOR     = 1993-036A
EPHEMERIS_NAME               = NONE
COVARIANCE_METHOD            = CALCULATED
MANEUVERABLE                 = NO
X                            = 2345.156
Y                            = 4567.412
Z                            = 3456.558
X_DOT                        = -4.856
Y_DOT                        = -3.987
Z_DOT                        = -2.123
"""
    
    cdm = CDM.from_kvn(cdm_text)
    assert cdm.collision_probability is None


def test_cdm_missing_covariance():
    """Test CDM parsing when covariance is absent."""
    cdm_text = """CCSDS_CDM_VERS               = 1.0
CREATION_DATE                = 2024-02-14T12:00:00
ORIGINATOR                   = JSPOC
MESSAGE_ID                   = TEST_NO_COV
TCA                          = 2024-02-15T08:30:15
MISS_DISTANCE                = 0.523
RELATIVE_SPEED               = 14.234
COLLISION_PROBABILITY        = 1.23e-05

OBJECT                       = OBJECT1
OBJECT_DESIGNATOR            = 25544
OBJECT_NAME                  = TEST_SAT_1
INTERNATIONAL_DESIGNATOR     = 1998-067A
EPHEMERIS_NAME               = NONE
COVARIANCE_METHOD            = CALCULATED
MANEUVERABLE                 = YES
X                            = 2345.678
Y                            = 4567.890
Z                            = 3456.789
X_DOT                        = 5.123
Y_DOT                        = 4.567
Z_DOT                        = 2.345

OBJECT                       = OBJECT2
OBJECT_DESIGNATOR            = 48274
OBJECT_NAME                  = TEST_SAT_2
INTERNATIONAL_DESIGNATOR     = 1993-036A
EPHEMERIS_NAME               = NONE
COVARIANCE_METHOD            = CALCULATED
MANEUVERABLE                 = NO
X                            = 2345.156
Y                            = 4567.412
Z                            = 3456.558
X_DOT                        = -4.856
Y_DOT                        = -3.987
Z_DOT                        = -2.123
"""
    
    cdm = CDM.from_kvn(cdm_text)
    assert cdm.object1.covariance is None
    assert cdm.object2.covariance is None


def test_spacetrack_client_init():
    """Test SpaceTrackClient initialization."""
    client = SpaceTrackClient(identity="test@example.com", password="secret123")
    
    assert client.identity == "test@example.com"
    assert client.password == "secret123"
    assert client._authenticated is False
    assert client.BASE_URL == "https://www.space-track.org"


def test_cdm_kvn_field_extraction():
    """Test specific field extraction from CDM."""
    cdm = CDM.from_kvn(SAMPLE_CDM_KVN)
    
    # Test all major field types
    assert isinstance(cdm.tca, datetime)
    assert isinstance(cdm.miss_distance_km, float)
    assert isinstance(cdm.object1.name, str)
    assert isinstance(cdm.object1.maneuverable, str)
    
    # Test that names match expected values
    assert "ISS" in cdm.object1.name
    assert "COSMOS" in cdm.object2.name or "DEB" in cdm.object2.name


# ---------------------------------------------------------------------------
# CDM edge cases
# ---------------------------------------------------------------------------

def test_cdm_to_kvn_raises_not_implemented():
    """Test that CDM.to_kvn() raises NotImplementedError."""
    cdm = CDM.from_kvn(SAMPLE_CDM_KVN)
    with pytest.raises(NotImplementedError, match="v0.2"):
        cdm.to_kvn()


def test_cdm_missing_optional_fields_still_parses():
    """Test CDM with missing optional fields (no covariance, no collision prob)."""
    cdm_text = """CCSDS_CDM_VERS               = 1.0
CREATION_DATE                = 2024-02-14T12:00:00
ORIGINATOR                   = TEST
MESSAGE_ID                   = MINIMAL_CDM
TCA                          = 2024-02-15T08:30:15
MISS_DISTANCE                = 1.0
RELATIVE_SPEED               = 7.0

OBJECT                       = OBJECT1
OBJECT_DESIGNATOR            = 11111
OBJECT_NAME                  = SAT_A
INTERNATIONAL_DESIGNATOR     = 2000-001A
EPHEMERIS_NAME               = NONE
COVARIANCE_METHOD            = CALCULATED
MANEUVERABLE                 = YES
X                            = 7000.0
Y                            = 0.0
Z                            = 0.0
X_DOT                        = 0.0
Y_DOT                        = 7.5
Z_DOT                        = 0.0

OBJECT                       = OBJECT2
OBJECT_DESIGNATOR            = 22222
OBJECT_NAME                  = SAT_B
INTERNATIONAL_DESIGNATOR     = 2000-002A
EPHEMERIS_NAME               = NONE
COVARIANCE_METHOD            = CALCULATED
MANEUVERABLE                 = NO
X                            = 7001.0
Y                            = 0.0
Z                            = 0.0
X_DOT                        = 0.0
Y_DOT                        = -7.5
Z_DOT                        = 0.0
"""
    cdm = CDM.from_kvn(cdm_text)
    assert cdm.collision_probability is None
    assert cdm.object1.covariance is None
    assert cdm.object2.covariance is None
    assert cdm.object1.designator == "11111"
    assert cdm.object2.designator == "22222"


def test_cdm_datetime_is_utc_aware():
    """Verify CDM datetimes are UTC-aware (audit C5 fix applied)."""
    cdm = CDM.from_kvn(SAMPLE_CDM_KVN)
    assert cdm.tca.tzinfo == timezone.utc
    assert cdm.creation_date.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# SpaceTrack client mocked HTTP tests
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock

ISS_TLE_TEXT = (
    "1 25544U 98067A   24045.54896019  .00016717  00000-0  30093-3 0  9993\n"
    "2 25544  51.6412 207.4925 0004948 290.5508 178.9792 15.49583488439596\n"
)


def _make_response(status_code: int = 200, text: str = "") -> MagicMock:
    """Helper to create a mock response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = __import__("requests").HTTPError(
            response=resp
        )
    return resp


def test_fetch_tle_success():
    """Test fetch_tle returns a TLE on success."""
    client = SpaceTrackClient(identity="user", password="pass")
    with patch.object(client._session, "post", return_value=_make_response(200, "OK")):
        with patch.object(client._session, "get", return_value=_make_response(200, ISS_TLE_TEXT)):
            tle = client.fetch_tle(25544)
            assert tle.norad_id == 25544


def test_fetch_tle_not_found():
    """Test fetch_tle raises ValueError on empty response (no TLE found)."""
    client = SpaceTrackClient(identity="user", password="pass")
    with patch.object(client._session, "post", return_value=_make_response(200, "OK")):
        with patch.object(client._session, "get", return_value=_make_response(200, "")):
            with pytest.raises(ValueError, match="No TLE found"):
                client.fetch_tle(99999)


def test_fetch_tle_auth_failure_reauth():
    """Test fetch_tle re-authenticates on 401 and retries."""
    client = SpaceTrackClient(identity="user", password="pass")
    
    login_resp = _make_response(200, "OK")
    resp_401 = MagicMock()
    resp_401.status_code = 401
    resp_success = _make_response(200, ISS_TLE_TEXT)
    
    with patch.object(client._session, "post", return_value=login_resp):
        with patch.object(client._session, "get", side_effect=[resp_401, resp_success]):
            tle = client.fetch_tle(25544)
            assert tle.norad_id == 25544


def test_fetch_catalog_success():
    """Test fetch_catalog returns list of TLEs."""
    client = SpaceTrackClient(identity="user", password="pass")
    two_tles = ISS_TLE_TEXT + ISS_TLE_TEXT  # two copies
    with patch.object(client._session, "post", return_value=_make_response(200, "OK")):
        with patch.object(client._session, "get", return_value=_make_response(200, two_tles)):
            tles = client.fetch_catalog()
            assert len(tles) == 2


def test_fetch_catalog_empty():
    """Test fetch_catalog returns empty list on empty response."""
    client = SpaceTrackClient(identity="user", password="pass")
    with patch.object(client._session, "post", return_value=_make_response(200, "OK")):
        with patch.object(client._session, "get", return_value=_make_response(200, "")):
            tles = client.fetch_catalog()
            assert tles == []


def test_fetch_cdms_success():
    """Test fetch_cdms parses CDM data."""
    client = SpaceTrackClient(identity="user", password="pass")
    with patch.object(client._session, "post", return_value=_make_response(200, "OK")):
        with patch.object(client._session, "get", return_value=_make_response(200, SAMPLE_CDM_KVN)):
            cdms = client.fetch_cdms(norad_id=25544)
            assert len(cdms) == 1
            assert cdms[0].object1.designator == "25544"


def test_fetch_cdms_empty():
    """Test fetch_cdms returns empty list on empty response."""
    client = SpaceTrackClient(identity="user", password="pass")
    with patch.object(client._session, "post", return_value=_make_response(200, "OK")):
        with patch.object(client._session, "get", return_value=_make_response(200, "")):
            cdms = client.fetch_cdms()
            assert cdms == []


def test_fetch_cdms_parse_error_skipped():
    """Test fetch_cdms silently skips malformed CDMs."""
    client = SpaceTrackClient(identity="user", password="pass")
    bad_cdm = "CCSDS_CDM_VERS = 1.0\nGARBAGE DATA\n"
    with patch.object(client._session, "post", return_value=_make_response(200, "OK")):
        with patch.object(client._session, "get", return_value=_make_response(200, bad_cdm)):
            cdms = client.fetch_cdms()
            assert cdms == []


def test_fetch_tle_rate_limit_429():
    """Test current behavior on 429 rate limit (raises HTTPError)."""
    import requests as req
    client = SpaceTrackClient(identity="user", password="pass")
    with patch.object(client._session, "post", return_value=_make_response(200, "OK")):
        with patch.object(client._session, "get", return_value=_make_response(429, "Rate limited")):
            with pytest.raises(req.HTTPError):
                client.fetch_tle(25544)
